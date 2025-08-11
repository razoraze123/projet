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
import json
import os
import secrets

from ..server.flask_server import FlaskBridgeServer

CFG_FILE = "server_config.json"


class FlaskServerWidget(QWidget):
    """Interface graphique minimaliste pour démarrer le serveur Flask."""

    def __init__(self) -> None:
        super().__init__()
        self.server = FlaskBridgeServer(on_log=self._append)
        self._build_ui()
        self._load_cfg()

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

        # image actions
        self.src_folder = QLineEdit()
        self.target_subdir = QLineEdit("image fait par gpt")
        self.ops_edit = QLineEdit(
            '[{"op":"resize","width":1024,"height":1024,"keep_ratio":true}]'
        )
        self.launch_action = QPushButton("Lancer action")
        self.launch_action.clicked.connect(self._launch_action)
        self.check_job = QPushButton("Status job")
        self.check_job.clicked.connect(self._check_job)
        self.last_job_id: str | None = None

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

        lay = QVBoxLayout(self)
        for row in (top, k, n, o, r, btn):
            lay.addLayout(row)

        act1 = QHBoxLayout()
        act1.addWidget(QLabel("Source folder"))
        act1.addWidget(self.src_folder)
        act2 = QHBoxLayout()
        act2.addWidget(QLabel("Target subdir"))
        act2.addWidget(self.target_subdir)
        act3 = QHBoxLayout()
        act3.addWidget(QLabel("Operations (JSON)"))
        act3.addWidget(self.ops_edit)
        actb = QHBoxLayout()
        actb.addWidget(self.launch_action)
        actb.addWidget(self.check_job)

        for row in (act1, act2, act3, actb):
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

    # ------------------------------------------------------------------
    def _load_cfg(self) -> None:
        try:
            if os.path.exists(CFG_FILE):
                with open(CFG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.port.setText(str(cfg.get("port", 5001)))
                self.api_key.setText(cfg.get("api_key", ""))
                self.expose.setChecked(bool(cfg.get("expose", False)))
                self.ngrok_token.setText(cfg.get("ngrok_token", ""))
                self.headless.setChecked(bool(cfg.get("headless", True)))
                self.ignore_robots.setChecked(bool(cfg.get("ignore_robots", False)))
                self.rate.setText(str(cfg.get("rate", 0)))
                self.maxw.setText(str(cfg.get("max_workers", 1)))
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
        with open(CFG_FILE, "w", encoding="utf-8") as f:
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

    # ------------------------------------------------------------------
    def _launch_action(self) -> None:
        import requests

        try:
            port = int(self.port.text() or 5001)
            url = f"http://localhost:{port}/actions/image-edit"
            ops = json.loads(self.ops_edit.text() or "[]")
            data = {
                "source": {"folder": self.src_folder.text().strip()},
                "operations": ops,
                "target_subdir": self.target_subdir.text().strip()
                or "image fait par gpt",
            }
            headers = {
                "X-API-KEY": self.api_key.text().strip(),
                "Content-Type": "application/json",
            }
            self._append(f"POST {url}")
            r = requests.post(url, headers=headers, json=data, timeout=30)
            if r.ok:
                self.last_job_id = r.json().get("job_id")
                self._append(f"Job lancé: {self.last_job_id}")
            else:  # pragma: no cover - simple UI feedback
                self._append(f"Erreur: {r.status_code} {r.text}")
        except Exception as e:  # pragma: no cover - simple UI feedback
            self._append(f"❌ Erreur action: {e}")

    def _check_job(self) -> None:
        import requests

        if not self.last_job_id:
            self._append("Aucun job")
            return
        try:
            port = int(self.port.text() or 5001)
            url = f"http://localhost:{port}/jobs/{self.last_job_id}"
            headers = {"X-API-KEY": self.api_key.text().strip()}
            r = requests.get(url, headers=headers, timeout=30)
            self._append(r.text)
        except Exception as e:  # pragma: no cover - simple UI feedback
            self._append(f"❌ Erreur status: {e}")
