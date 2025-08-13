from __future__ import annotations

"""Widget de contrôle pour :class:`FlaskBridgeServer`."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QApplication,
)
from PySide6.QtCore import Slot
import json, requests
import os
from pathlib import Path

try:
    from localapp.log_safe import open_utf8
except ImportError:
    from log_safe import open_utf8
import secrets
from ui_helpers import show_toast

from ..server.flask_server import FlaskBridgeServer

CFG_FILE = "server_config.json"


class FlaskServerWidget(QWidget):
    """Interface graphique minimaliste pour démarrer le serveur Flask."""

    def __init__(self) -> None:
        super().__init__()
        self.server = FlaskBridgeServer(on_log=self._append)
        self._build_ui()
        self._load_cfg()
        self._last_job_id = ""

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.port = QLineEdit("5001")
        self.api_key = QLineEdit(os.getenv("SCRAPER_API_KEY", ""))
        gen = QPushButton("Générer")
        gen.clicked.connect(self._gen_key)
        self.expose = QCheckBox("Expose via ngrok")
        self.ngrok_token = QLineEdit(os.getenv("NGROK_AUTHTOKEN", ""))
        self.ngrok_token.setEchoMode(QLineEdit.Password)
        self.headless = QCheckBox("Headless par défaut")
        self.headless.setChecked(True)
        self.ignore_robots = QCheckBox("Ignorer robots.txt par défaut")
        self.rate = QLineEdit("0")
        self.maxw = QLineEdit("1")

        self.start = QPushButton("Démarrer")
        self.stop = QPushButton("Arrêter")
        self.stop.setEnabled(False)
        self.url_label = QLabel("URL publique : (non exposé)")
        self.status_label = QLabel("Statut : Arrêté")
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        copyurl = QPushButton("Copier URL")
        copyurl.clicked.connect(self._copy_url)
        self.test_health_btn = QPushButton("Test health")
        self.test_health_btn.clicked.connect(self._test_health)

        # image actions
        self.source_folder = QLineEdit()
        self.target_subdir = QLineEdit("image fait par gpt")
        self.sample_alias = QLineEdit()
        self.operations_json = QLineEdit(
            '[{"op":"resize","width":1024,"height":1024,"keep_ratio":true}]'
        )
        self.launch_action_btn = QPushButton("Lancer action")
        self.launch_action_btn.clicked.connect(self._launch_action)
        self.status_btn = QPushButton("Status job")
        self.status_btn.clicked.connect(self._status_job)

        # layouts
        top = QHBoxLayout()
        top.addWidget(QLabel("Port:"))
        top.addWidget(self.port)

        k = QHBoxLayout()
        k.addWidget(QLabel("API Key:"))
        k.addWidget(self.api_key)
        k.addWidget(gen)

        n = QHBoxLayout()
        n.addWidget(self.expose)
        n.addWidget(QLabel("Ngrok token:"))
        n.addWidget(self.ngrok_token)

        o = QHBoxLayout()
        o.addWidget(self.headless)
        o.addWidget(self.ignore_robots)

        r = QHBoxLayout()
        r.addWidget(QLabel("Rate (img/min):"))
        r.addWidget(self.rate)
        r.addWidget(QLabel("Max workers:"))
        r.addWidget(self.maxw)

        btn = QHBoxLayout()
        btn.addWidget(self.start)
        btn.addWidget(self.stop)
        btn.addWidget(copyurl)
        btn.addWidget(self.test_health_btn)

        lay = QVBoxLayout(self)
        for row in (top, k, n, o, r, btn):
            lay.addLayout(row)

        act1 = QHBoxLayout()
        act1.addWidget(QLabel("Source folder"))
        act1.addWidget(self.source_folder)
        act2 = QHBoxLayout()
        act2.addWidget(QLabel("Target subdir"))
        act2.addWidget(self.target_subdir)
        act_alias = QHBoxLayout()
        act_alias.addWidget(QLabel("Alias 'sample_folder' →"))
        act_alias.addWidget(self.sample_alias)
        act3 = QHBoxLayout()
        act3.addWidget(QLabel("Operations (JSON)"))
        act3.addWidget(self.operations_json)
        actb = QHBoxLayout()
        actb.addWidget(self.launch_action_btn)
        actb.addWidget(self.status_btn)

        for row in (act1, act2, act_alias, act3, actb):
            lay.addLayout(row)
        lay.addWidget(self.status_label)
        lay.addWidget(self.url_label)
        lay.addWidget(self.console)

        self.start.clicked.connect(self._start)
        self.stop.clicked.connect(self._stop)

    # ------------------------------------------------------------------
    def _append(self, text: str) -> None:
        self.console.append(text)

    def _gen_key(self) -> None:
        self.api_key.setText(secrets.token_urlsafe(24))

    def _copy_url(self) -> None:
        QApplication.clipboard().setText(
            self.url_label.text().replace("URL publique : ", "")
        )

    def _request(self, method: str, url: str, **kwargs):
        try:
            r = requests.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)
            if r.status_code == 401:
                show_toast(self, "Clé API absente ou invalide (401).", error=True)
                return None
            r.raise_for_status()
            return r
        except requests.Timeout:
            show_toast(self, "Requête expirée (timeout).", error=True)
        except Exception as e:
            show_toast(self, f"Erreur API: {e}", error=True)
        return None

    # ------------------------------------------------------------------
    def _load_cfg(self) -> None:
        try:
            if os.path.exists(CFG_FILE):
                with open_utf8(CFG_FILE, "r") as f:
                    cfg = json.load(f)
                self.port.setText(str(cfg.get("port", 5001)))
                self.api_key.setText(cfg.get("api_key", ""))
                self.expose.setChecked(bool(cfg.get("expose", False)))
                self.ngrok_token.setText(cfg.get("ngrok_token", ""))
                self.headless.setChecked(bool(cfg.get("headless", True)))
                self.ignore_robots.setChecked(bool(cfg.get("ignore_robots", False)))
                self.rate.setText(str(cfg.get("rate", 0)))
                self.maxw.setText(str(cfg.get("max_workers", 1)))
                self.sample_alias.setText(
                    (cfg.get("path_aliases") or {}).get("sample_folder", "")
                )
        except Exception:
            pass

    def _save_cfg(self) -> dict:
        cfg = {
            "port": int(self.port.text() or 5001),
            "api_key": self.api_key.text().strip(),
            "expose": self.expose.isChecked(),
            "ngrok_token": self.ngrok_token.text().strip(),
            "headless": self.headless.isChecked(),
            "ignore_robots": self.ignore_robots.isChecked(),
            "rate": int(self.rate.text() or 0),
            "max_workers": int(self.maxw.text() or 1),
        }
        cfg["path_aliases"] = {
            "sample_folder": self.sample_alias.text().strip()
        }
        with open_utf8(CFG_FILE, "w") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return cfg

    # ------------------------------------------------------------------
    @Slot()
    def _start(self) -> None:
        cfg = self._save_cfg()
        try:
            self.server.start(
                port=cfg["port"],
                api_key=cfg["api_key"],
                headless_default=cfg["headless"],
                user_agent=None,
                ignore_robots_default=cfg["ignore_robots"],
                rate_limit=cfg["rate"],
                max_workers=cfg["max_workers"],
            )
            pub = ""
            if cfg["expose"]:
                pub = self.server.enable_ngrok(cfg["ngrok_token"], cfg["port"])
            try:
                if cfg.get("path_aliases", {}):
                    url = f"http://localhost:{cfg['port']}/aliases"
                    headers = {
                        "X-API-KEY": cfg["api_key"],
                        "Content-Type": "application/json",
                    }
                    requests.post(
                        url,
                        headers=headers,
                        data=json.dumps(cfg["path_aliases"]),
                        timeout=10,
                    )
                    self._append(f"↔︎ Aliases synced: {cfg['path_aliases']}")
            except Exception as e:
                self._append(f"⚠️ Alias sync error: {e}")
            self.status_label.setText("Statut : En cours d’exécution")
            self.url_label.setText(
                f"URL publique : {pub or f'http://localhost:{cfg['port']}/health'}"
            )
            self.start.setEnabled(False)
            self.stop.setEnabled(True)
            self._append("🚀 Serveur démarré")
        except Exception as e:  # pragma: no cover - UI feedback
            self._append(f"❌ Erreur démarrage : {e}")

    @Slot()
    def _stop(self) -> None:
        try:
            self.server.stop()
            self.status_label.setText("Statut : Arrêté")
            self.url_label.setText("URL publique : (non exposé)")
            self.start.setEnabled(True)
            self.stop.setEnabled(False)
            self._append("🛑 Serveur arrêté")
        except Exception as e:  # pragma: no cover - UI feedback
            self._append(f"❌ Erreur arrêt : {e}")

    @Slot()
    def _test_health(self) -> None:
        try:
            port = int(self.port.text() or 5001)
            base = (
                self.server.public_url.strip()
                if self.expose.isChecked() and self.server.public_url.strip()
                else f"http://localhost:{port}"
            )
            url = base.rstrip("/") + "/health"
            r = self._request(
                "get", url, headers={"ngrok-skip-browser-warning": "1"}
            )
            if r:
                self._append(f"[health] GET {url} -> {r.status_code}")
                self._append(r.text or "<no body>")
        except Exception as e:
            self._append(f"❌ health error: {e}")

    # ------------------------------------------------------------------
    @Slot()
    def _launch_action(self) -> None:
        try:
            port = int(self.port.text() or 5001)
            api_key = self.api_key.text().strip()
            src = self.source_folder.text().strip()
            alias = self.sample_alias.text().strip()
            tgt = self.target_subdir.text().strip()
            ops_text = self.operations_json.text().strip()
            ops = json.loads(ops_text) if ops_text else []
            if src:
                p = Path(src)
                if not p.exists():
                    self._append(f"❌ Dossier introuvable : {src}")
                    return
                exts = {".jpg", ".jpeg", ".png", ".webp"}
                has_img = any(
                    pp.suffix.lower() in exts for pp in p.iterdir() if pp.is_file()
                )
                if not has_img:
                    self._append(f"❌ Aucun fichier image dans : {src}")
                    return
            elif not alias:
                self._append(
                    "❌ Source folder vide et aucun alias 'sample_folder' défini."
                )
                return
            if not ops:
                self._append("❌ Operations JSON manquant")
                return
            url = f"http://localhost:{port}/actions/image-edit"
            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
            payload = {
                "source": {"folder": src},
                "operations": ops,
                "target_subdir": tgt,
            }
            r = self._request(
                "post", url, headers=headers, data=json.dumps(payload), timeout=15
            )
            if not r or r.status_code != 202:
                if r:
                    self._append(f"❌ {r.status_code}: {r.text}")
                return
            self._last_job_id = r.json().get("job_id", "")
            self._append(f"🚀 Action lancée — job_id: {self._last_job_id}")
        except Exception as e:
            self._append(f"❌ Erreur envoi action: {e}")

    @Slot()
    def _status_job(self) -> None:
        try:
            if not self._last_job_id:
                self._append("ℹ️ Aucun job_id — lance d’abord une action.")
                return
            port = int(self.port.text() or 5001)
            api_key = self.api_key.text().strip()
            url = f"http://localhost:{port}/jobs/{self._last_job_id}"
            headers = {"X-API-KEY": api_key}
            r = self._request("get", url, headers=headers, timeout=10)
            if r:
                self._append(r.text)
        except Exception as e:
            self._append(f"❌ Erreur status: {e}")
