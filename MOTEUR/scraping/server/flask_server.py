from __future__ import annotations

"""Small Flask server to remotely trigger scraping jobs.

The module exposes :class:`FlaskBridgeServer` which wraps a Flask
application and provides a thread based HTTP server.  The endpoints are
minimal and secured through an API key passed in the ``X-API-KEY``
header.  Jobs are executed in a :class:`~concurrent.futures.ThreadPoolExecutor`
so the UI remains responsive.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import datetime as _dt
import os
import threading
import time
import uuid
import logging
from pathlib import Path

from flask import Flask, request, jsonify
from werkzeug.serving import make_server
from concurrent.futures import ThreadPoolExecutor, Future

from ..image_scraper import scrape_images, scrape_variants
from ..profile_manager import load_profiles
from ..history import load_history


log = logging.getLogger("flask-bridge")
log.setLevel(logging.INFO)


@dataclass
class JobStatus:
    """Represents the state of a running scraping job."""

    job_id: str
    status: str = "queued"   # queued|running|done|error
    progress: Dict[str, int] = field(
        default_factory=lambda: {"found": 0, "downloaded": 0, "failed": 0}
    )
    output_dir: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    variants: Dict[str, str] = field(default_factory=dict)
    sample_images: list[str] = field(default_factory=list)
    errors: list[Dict[str, str]] = field(default_factory=list)
    message: str = ""


class JobManager:
    """Simple registry for running scraping jobs."""

    def __init__(self, max_workers: int = 2) -> None:
        self.jobs: Dict[str, JobStatus] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()

    def submit(self, fn, *args, **kwargs) -> JobStatus:
        job_id = uuid.uuid4().hex[:12]
        st = JobStatus(job_id=job_id)
        with self.lock:
            self.jobs[job_id] = st
        self.executor.submit(fn, st, *args, **kwargs)
        return st


class StoppableWSGIServer(threading.Thread):
    """Wrapper around Werkzeug's WSGI server allowing clean shutdown."""

    def __init__(self, app: Flask, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self.srv = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self) -> None:  # pragma: no cover - simple thread runner
        self.srv.serve_forever()

    def shutdown(self) -> None:
        self.srv.shutdown()
        self.ctx.pop()


class FlaskBridgeServer:
    """Expose scraping helpers through a small Flask application."""

    def __init__(self, on_log=None) -> None:
        self.on_log = on_log
        self.app = Flask(__name__)
        self._server: Optional[StoppableWSGIServer] = None
        self._ngrok_tunnel = None
        self.public_url = ""
        self.api_key = os.getenv("SCRAPER_API_KEY", "")
        self.default_flags = {
            "headless": True,
            "ignore_robots": False,
            "rate_limit": 0,
            "max_workers": 1,
        }
        self.jobs = JobManager(max_workers=2)
        self._mount_routes()

    # ------------------------------------------------------------------
    # helpers
    def _log(self, msg: str) -> None:
        log.info(msg)
        if self.on_log:
            self.on_log(msg)

    # ------------------------------------------------------------------
    # Flask routes
    def _mount_routes(self) -> None:
        app = self.app

        @app.get("/health")
        def health() -> Any:
            return jsonify(
                {
                    "ok": True,
                    "version": "1.0",
                    "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            )

        def require_key():
            key = request.headers.get("X-API-KEY", "")
            if not self.api_key or key != self.api_key:
                return jsonify({"error": "unauthorized"}), 401
            return None

        @app.post("/scrape")
        def scrape() -> Any:
            auth = require_key()
            if auth:
                return auth
            data = request.get_json(force=True, silent=True) or {}
            url = data.get("url")
            selector = data.get("selector")
            if not url or not selector:
                return (
                    jsonify({"error": "invalid_request", "detail": "url & selector required"}),
                    400,
                )
            folder = data.get("folder") or "images"
            opts = {**self.default_flags, **(data.get("options") or {})}
            st = self.jobs.submit(self._run_scrape_job, url, selector, folder, opts)
            self._log(f"Job {st.job_id} accepté pour {url}")
            return jsonify({"job_id": st.job_id, "message": "accepted"}), 202

        @app.get("/jobs/<job_id>")
        def job_status(job_id: str) -> Any:
            auth = require_key()
            if auth:
                return auth
            st = self.jobs.jobs.get(job_id)
            if not st:
                return jsonify({"error": "not_found"}), 404
            return jsonify(st.__dict__)

        @app.get("/jobs")
        def list_jobs() -> Any:
            auth = require_key()
            if auth:
                return auth
            return jsonify([j.__dict__ for j in self.jobs.jobs.values()])

        @app.get("/profiles")
        def profiles() -> Any:
            auth = require_key()
            if auth:
                return auth
            profs = load_profiles()
            out = [
                {"name": p.get("name", ""), "selector": p.get("selector", "")}
                for p in profs
            ]
            return jsonify(out)

        @app.get("/history")
        def hist() -> Any:
            auth = require_key()
            if auth:
                return auth
            return jsonify(load_history())

    # ------------------------------------------------------------------
    # job execution
    def _run_scrape_job(
        self,
        st: JobStatus,
        url: str,
        selector: str,
        folder: str,
        opts: Dict[str, Any],
    ) -> None:
        st.status = "running"
        st.started_at = _dt.datetime.utcnow().isoformat() + "Z"
        try:
            if opts.get("with_variants"):
                total, driver = scrape_images(
                    url,
                    selector,
                    folder,
                    keep_driver=True,
                )
                st.variants = scrape_variants(driver)
                driver.quit()
            else:
                total = scrape_images(url, selector, folder)
            st.progress["found"] = total
            st.progress["downloaded"] = total
            st.output_dir = folder
            images_dir = Path(folder)
            if images_dir.exists():
                files = sorted(images_dir.glob("*"))[:5]
                st.sample_images = [f.name for f in files]
            st.status = "done"
        except Exception as exc:  # pragma: no cover - hard to trigger in tests
            st.status = "error"
            st.message = str(exc)
            st.errors.append({"url": url, "error": str(exc)})
        finally:
            st.finished_at = _dt.datetime.utcnow().isoformat() + "Z"

    # ------------------------------------------------------------------
    # public API
    def start(
        self,
        port: int,
        api_key: str,
        *,
        headless_default: bool,
        user_agent: str | None,
        ignore_robots_default: bool,
        rate_limit: int,
        max_workers: int,
    ) -> None:
        """Start the HTTP server."""

        self.api_key = api_key or self.api_key
        self.default_flags.update(
            {
                "headless": headless_default,
                "user_agent": user_agent,
                "ignore_robots": ignore_robots_default,
                "rate_limit": rate_limit,
                "max_workers": max_workers,
            }
        )
        self.jobs = JobManager(max_workers=max_workers)
        self._server = StoppableWSGIServer(self.app, "0.0.0.0", port)
        self._server.start()
        self._log(f"Serveur lancé sur le port {port}")

    def stop(self) -> None:
        """Stop the HTTP server and any active ngrok tunnel."""

        if self._server:
            self._server.shutdown()
            self._server = None
            self._log("Serveur arrêté")
        self.disable_ngrok()

    def enable_ngrok(self, authtoken: str, port: int) -> str:
        """Expose the local server via ngrok."""

        try:
            from pyngrok import ngrok

            if authtoken:
                ngrok.set_auth_token(authtoken)
            self._ngrok_tunnel = ngrok.connect(port, "http")
            self.public_url = self._ngrok_tunnel.public_url
            self._log(f"Ngrok exposé sur {self.public_url}")
        except Exception as exc:  # pragma: no cover - requires network
            self._log(f"Erreur ngrok : {exc}")
            self.public_url = ""
        return self.public_url

    def disable_ngrok(self) -> None:
        """Close the ngrok tunnel if opened."""

        try:
            if self._ngrok_tunnel:
                from pyngrok import ngrok

                ngrok.disconnect(self._ngrok_tunnel.public_url)
                ngrok.kill()
                self._log("Ngrok arrêté")
        except Exception:  # pragma: no cover - best effort
            pass
        finally:
            self._ngrok_tunnel = None
            self.public_url = ""

    def is_running(self) -> bool:
        """Return ``True`` if the server is currently running."""

        return self._server is not None
