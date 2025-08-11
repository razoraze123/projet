from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QPushButton,
    QTextEdit,
    QMessageBox,
)
from PySide6.QtCore import Slot, QProcess, QCoreApplication

from .theme import load_theme, save_theme, apply_theme
from MOTEUR.scraping.utils.restart import relaunch_current_process
from MOTEUR.scraping.utils.update import PROJECT_ROOT


class SettingsWidget(QWidget):
    """General application settings."""

    def __init__(self) -> None:
        super().__init__()

        self.light_radio = QRadioButton("Clair")
        self.dark_radio = QRadioButton("Sombre")

        current = load_theme()
        (self.dark_radio if current == "dark" else self.light_radio).setChecked(True)

        self.light_radio.toggled.connect(lambda _: self._apply())
        self.dark_radio.toggled.connect(lambda _: self._apply())

        self.apply_btn = QPushButton("Appliquer")
        self.apply_btn.clicked.connect(self._apply)

        radios = QHBoxLayout()
        radios.addWidget(self.light_radio)
        radios.addWidget(self.dark_radio)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Thème de l’application"))
        layout.addLayout(radios)
        layout.addWidget(self.apply_btn)
        layout.addWidget(
            QLabel("Appliqué à toute l’application. Persistant dans settings.json")
        )

        self._build_maintenance_ui(layout)

    @Slot()
    def _apply(self) -> None:
        name = "dark" if self.dark_radio.isChecked() else "light"
        apply_theme(name)
        save_theme(name)

    # ------------------------------------------------------------------
    def _build_maintenance_ui(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.update_btn = QPushButton("Mettre à jour")
        self.update_btn.setObjectName("btn_update")
        self.restart_btn = QPushButton("Redémarrer")
        self.restart_btn.setObjectName("btn_restart")
        row.addWidget(self.update_btn)
        row.addWidget(self.restart_btn)
        layout.addLayout(row)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        self._git_proc = QProcess(self)
        self._git_proc.readyReadStandardOutput.connect(
            lambda: self._append_log(
                bytes(self._git_proc.readAllStandardOutput()).decode("utf-8", "ignore")
            )
        )
        self._git_proc.readyReadStandardError.connect(
            lambda: self._append_log(
                bytes(self._git_proc.readAllStandardError()).decode("utf-8", "ignore")
            )
        )
        self._git_proc.finished.connect(self._on_git_finished)

        self.update_btn.clicked.connect(self._on_update_clicked)
        self.restart_btn.clicked.connect(self._on_restart_clicked)

    # ------------------------------------------------------------------
    def _append_log(self, text: str) -> None:
        txt = text.strip()
        if txt:
            self.log_edit.append(txt)

    # ------------------------------------------------------------------
    @Slot()
    def _on_update_clicked(self) -> None:
        root = Path(PROJECT_ROOT)
        if not (root / ".git").exists():
            QMessageBox.critical(
                self, "Mettre à jour", f"Aucun dépôt Git détecté dans :\n{root}"
            )
            return

        self.update_btn.setEnabled(False)
        self.update_btn.setText("Mise à jour en cours…")
        self._append_log(f"> git pull origin main (cwd={root})")
        self._git_proc.setWorkingDirectory(str(root))
        self._git_proc.start("git", ["pull", "origin", "main"])

        if not self._git_proc.waitForStarted(2000):
            self.update_btn.setEnabled(True)
            self.update_btn.setText("Mettre à jour")
            QMessageBox.critical(
                self,
                "Mettre à jour",
                "Impossible de démarrer Git. Est-il installé et dans le PATH ?",
            )

    # ------------------------------------------------------------------
    def _on_git_finished(self, code: int, status) -> None:
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Mettre à jour")
        if code == 0:
            QMessageBox.information(self, "Mettre à jour", "Mise à jour réussie.")
        else:
            QMessageBox.critical(
                self,
                "Mettre à jour",
                f"Échec du 'git pull' (code {code}). Consulte les logs.",
            )

    # ------------------------------------------------------------------
    @Slot()
    def _on_restart_clicked(self) -> None:
        ret = QMessageBox.question(
            self,
            "Redémarrer",
            "Voulez-vous vraiment redémarrer l’application ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        relaunch_current_process(delay_sec=0.3)
        QCoreApplication.quit()
