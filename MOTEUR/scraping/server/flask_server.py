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
import csv
import datetime as _dt
from datetime import datetime
import json
import logging
import os
import re
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from functools import wraps

from flask import Flask, request, jsonify, send_file
from werkzeug.serving import make_server
from concurrent.futures import ThreadPoolExecutor, Future

from ..image_scraper import scrape_images, scrape_variants
from ..profile_manager import load_profiles
from ..history import load_history


log = logging.getLogger("flask-bridge")
log.setLevel(logging.INFO)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


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
        self.path_aliases = getattr(self, "path_aliases", {"sample_folder": ""})
        self._normalize_aliases()
        self._mount_routes()

    # ------------------------------------------------------------------
    # helpers
    def _log(self, msg: str) -> None:
        log.info(msg)
        if self.on_log:
            self.on_log(msg)

    def _resolve_folder(self, raw: str) -> str:
        s = (raw or "").strip()
        if not s:
            return ""
        if s in self.path_aliases and self.path_aliases[s]:
            return self.path_aliases[s]
        s = os.path.expandvars(os.path.expanduser(s))
        return str(Path(s))

    def _normalize_aliases(self) -> None:
        """Garantit que 'sample_images' pointe sur 'sample_folder' si non défini."""
        try:
            sf = (self.path_aliases.get("sample_folder") or "").strip()
            si = (self.path_aliases.get("sample_images") or "").strip()
            if sf and not si:
                self.path_aliases["sample_images"] = sf
                self._log(f"Alias ajouté : sample_images -> {sf}")
        except Exception as e:
            self._log(f"⚠️ Normalisation alias échouée: {e}")

    # ------------------------------------------------------------------
    # Flask routes
    def _mount_routes(self) -> None:
        app = self.app

        # CONSTANTES / CONFIG ---------------------------------------------
        image_exts = IMAGE_EXTS

        # UTILS -----------------------------------------------------------
        def _load_products_file(path: Path) -> list[dict]:
            if path.suffix.lower() == ".json":
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f) or []
                return data if isinstance(data, list) else []
            if path.suffix.lower() == ".csv":
                with path.open("r", encoding="utf-8", newline="") as f:
                    return list(csv.DictReader(f))
            raise ValueError("unsupported file type")

        # SÉCURITÉ -------------------------------------------------------
        def require_api_key(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                key = request.headers.get("X-API-KEY", "")
                if not self.api_key or key != self.api_key:
                    return jsonify({"error": "unauthorized"}), 401
                return fn(*args, **kwargs)

            return wrapper

        # ENDPOINTS ------------------------------------------------------

        @app.get("/health")
        def health() -> Any:
            return (
                jsonify(
                    {
                        "ok": True,
                        "version": "1.0",
                        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                ),
                200,
            )

        @app.get("/aliases")
        @require_api_key
        def get_aliases() -> Any:
            return jsonify(self.path_aliases)

        @app.post("/aliases")
        @require_api_key
        def post_aliases() -> Any:
            data = request.get_json(force=True, silent=True) or {}
            for k, v in (data.items() if isinstance(data, dict) else []):
                if isinstance(v, str):
                    self.path_aliases[k] = v.strip()
            self._normalize_aliases()
            return jsonify(self.path_aliases), 200

        @app.get("/files/list")
        @require_api_key
        def files_list() -> Any:
            raw_folder = (request.args.get("folder") or "").strip()
            folder = (
                self._resolve_folder(raw_folder)
                if hasattr(self, "_resolve_folder")
                else raw_folder
            )
            p = Path(folder)
            if not p.exists() or not p.is_dir():
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": f"folder not found: {folder}",
                        }
                    ),
                    400,
                )

            files = [
                f.name
                for f in p.iterdir()
                if f.is_file() and f.suffix.lower() in image_exts
            ]
            base = request.host_url.rstrip("/")
            urls = [
                f"{base}/files/raw?folder={quote(raw_folder)}&name={quote(name)}"
                for name in files
            ]
            return jsonify(
                {
                    "folder": raw_folder or folder,
                    "count": len(files),
                    "files": files,
                    "urls": urls,
                }
            )

        @app.get("/files/raw")
        @require_api_key
        def files_raw() -> Any:
            raw_folder = (request.args.get("folder") or "").strip()
            name = (request.args.get("name") or "").strip()
            if not name:
                return (
                    jsonify({"error": "invalid_request", "detail": "name required"}),
                    400,
                )
            folder = (
                self._resolve_folder(raw_folder)
                if hasattr(self, "_resolve_folder")
                else raw_folder
            )
            p = Path(folder) / name
            if not p.exists() or not p.is_file():
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": f"file not found: {p}",
                        }
                    ),
                    404,
                )
            if p.suffix.lower() not in image_exts:
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": "unsupported file type",
                        }
                    ),
                    400,
                )
            return send_file(str(p), as_attachment=False)

        @app.get("/products")
        @require_api_key
        def products() -> Any:
            raw_path = (request.args.get("path") or "").strip()
            if not raw_path:
                return jsonify({"total": 0, "count": 0, "products": []})

            path_str = (
                self._resolve_folder(raw_path)
                if hasattr(self, "_resolve_folder")
                else raw_path
            )
            p = Path(path_str)
            if not p.exists() or not p.is_file():
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": f"file not found: {path_str}",
                        }
                    ),
                    400,
                )
            try:
                data = _load_products_file(p)
            except Exception as e:
                return (
                    jsonify(
                        {"error": "invalid_request", "detail": str(e)}
                    ),
                    400,
                )

            def _to_int(val: str, default: int) -> int:
                try:
                    return max(int(val), 0)
                except Exception:
                    return default

            offset = _to_int(request.args.get("offset", "0"), 0)
            limit = _to_int(request.args.get("limit", "0"), 0)

            total = len(data)
            items = data[offset:]
            if limit:
                items = items[:limit]
            return jsonify({"total": total, "count": len(items), "products": items})

        @app.post("/scrape")
        @require_api_key
        def scrape() -> Any:
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

        @app.post("/actions/image-edit")
        @require_api_key
        def image_edit() -> Any:
            data = request.get_json(force=True, silent=True) or {}
            raw_src = ((data.get("source") or {}).get("folder") or "").strip()
            src = self._resolve_folder(raw_src)
            ops = data.get("operations") or []
            target_subdir = (data.get("target_subdir") or "image fait par gpt").strip()
            if not src:
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": "source.folder is empty",
                        }
                    ),
                    400,
                )
            p = Path(src)
            if not p.exists():
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": f"source not found: {src}",
                        }
                    ),
                    400,
                )
            has_images = any(
                pp.suffix.lower() in image_exts for pp in p.iterdir() if pp.is_file()
            )
            if not has_images:
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": f"no images in: {src}",
                        }
                    ),
                    400,
                )
            if not ops:
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": "operations required",
                        }
                    ),
                    400,
                )
            st = self.jobs.submit(self._run_image_action_job, src, ops, target_subdir)
            self._log(
                f"Job {st.job_id} image-edit: {src} -> {target_subdir} ({len(ops)} ops)"
            )
            return jsonify({"job_id": st.job_id, "message": "accepted"}), 202

        @app.get("/jobs/<job_id>")
        @require_api_key
        def job_status(job_id: str) -> Any:
            st = self.jobs.jobs.get(job_id)
            if not st:
                return jsonify({"error": "not_found"}), 404
            return jsonify(st.__dict__)

        @app.get("/jobs")
        @require_api_key
        def list_jobs() -> Any:
            return jsonify([j.__dict__ for j in self.jobs.jobs.values()])

        @app.get("/profiles")
        @require_api_key
        def profiles() -> Any:
            profs = load_profiles()
            out = [
                {"name": p.get("name", ""), "selector": p.get("selector", "")}
                for p in profs
            ]
            out.sort(key=lambda p: p["name"])
            return jsonify(out), 200

        @app.post("/profiles")
        @require_api_key
        def add_profile_route() -> Any:
            data = request.get_json(force=True, silent=True) or {}
            name = (data.get("name") or "").strip()
            selector = (data.get("selector") or "").strip()
            if not name or not selector:
                return (
                    jsonify(
                        {
                            "error": "invalid_request",
                            "detail": "name and selector required",
                        }
                    ),
                    400,
                )
            try:
                from .. import profile_manager as pm

                pm.add_profile(name, selector)
            except ValueError:
                return jsonify({"error": "exists"}), 409

            try:
                from PySide6.QtCore import QMetaObject, Qt
                from ..bus.event_bus import bus

                QMetaObject.invokeMethod(bus, "profiles_changed", Qt.QueuedConnection)
            except Exception as e:  # pragma: no cover - best effort
                log.warning("Impossible d'émettre profiles_changed: %s", e)

            self._log(f"Profil '{name}' ajouté")
            log.info("Profil ajouté: %s -> %s", name, selector)
            return jsonify({"name": name, "selector": selector}), 201

        @app.get("/history")
        @require_api_key
        def hist() -> Any:
            return jsonify(load_history())

        @app.get("/debug/ping")
        @require_api_key
        def debug_ping() -> Any:
            from PySide6.QtCore import QCoreApplication

            return jsonify(
                {
                    "thread": "flask",
                    "qt_alive": QCoreApplication.instance() is not None,
                }
            )

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

    def _run_image_action_job(
        self, st: JobStatus, src_folder: str, ops: list[dict], target_subdir: str
    ) -> None:
        from pathlib import Path
        from time import sleep
        from PIL import Image, ImageFilter
        import datetime as _dt

        st.status = "running"
        st.started_at = _dt.datetime.utcnow().isoformat() + "Z"
        try:
            rate = int(self.default_flags.get("rate_limit", 0) or 0)  # images/min
            delay = (60.0 / rate) if rate > 0 else 0.0

            src = Path(src_folder)
            if not src.exists():
                raise FileNotFoundError(f"source not found: {src}")

            dst = src / (target_subdir or "image fait par gpt")
            dst.mkdir(parents=True, exist_ok=True)

            files = [
                p for p in src.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            ]
            st.progress["found"] = len(files)
            samples: list[str] = []

            def apply_ops(img: Image.Image) -> Image.Image:
                out = img
                for op in ops:
                    kind = str(op.get("op", "")).lower()
                    if kind == "resize":
                        w = int(op.get("width", 0))
                        h = int(op.get("height", 0))
                        keep = bool(op.get("keep_ratio", True))
                        if w > 0 and h > 0:
                            if keep:
                                out = out.copy()
                                out.thumbnail((w, h))
                            else:
                                out = out.resize((w, h))
                    elif kind == "sharpen":
                        amt = float(op.get("amount", 0.6))
                        out = out.filter(
                            ImageFilter.UnsharpMask(percent=int(amt * 150), radius=2)
                        )
                    elif kind == "remove_bg":
                        out = out.convert("RGBA")
                        bg = Image.new("RGBA", out.size, (255, 255, 255, 255))
                        bg.paste(out, mask=out.split()[-1] if out.mode == "RGBA" else None)
                        out = bg.convert("RGB")
                return out

            for i, f in enumerate(files, 1):
                try:
                    with Image.open(f) as im:
                        out = apply_ops(im)
                        out_path = dst / f.name
                        out.save(out_path)
                    st.progress["downloaded"] += 1
                    if len(samples) < 5:
                        samples.append(out_path.name)
                except Exception as e:
                    st.progress["failed"] += 1
                    st.errors.append({"file": f.name, "error": str(e)})
                if delay:
                    sleep(delay)

            st.sample_images = samples
            st.output_dir = str(dst)
            st.status = "done"
        except Exception as exc:
            st.status = "error"
            st.message = str(exc)
            st.errors.append({"error": str(exc), "folder": src_folder})
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
        self._normalize_aliases()
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
