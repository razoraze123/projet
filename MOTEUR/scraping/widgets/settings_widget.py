from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QTextEdit,
)
from PySide6.QtCore import Signal, Slot, QCoreApplication, QProcess
from pathlib import Path


class ScrapingSettingsWidget(QWidget):
    module_toggled = Signal(str, bool)
    rename_toggled = Signal(bool)

    def __init__(self, modules_order=None, *, show_maintenance: bool = False):
        super().__init__()
        from ..utils.restart import relaunch_current_process
        from ..utils.update import PROJECT_ROOT

        layout = QVBoxLayout(self)
        # (conserver vos éléments existants ici)
        _ = (modules_order or [])

        self._project_root = PROJECT_ROOT
        self._relaunch_current_process = relaunch_current_process

        if show_maintenance:
            self._build_maintenance_ui(layout)

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

        # Simple log output
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        # Prepare git QProcess
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
        if hasattr(self, "log_edit") and self.log_edit is not None:
            txt = text.strip()
            if txt:
                self.log_edit.append(txt)

    # ------------------------------------------------------------------
    @Slot()
    def _on_update_clicked(self) -> None:
        root = Path(self._project_root)
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
        self._relaunch_current_process(delay_sec=0.3)
        QCoreApplication.quit()
