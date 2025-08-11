from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QTextEdit,
    QDialog,
    QLabel,
    QProgressBar,
    QApplication,
)
from PySide6.QtCore import Signal, Slot, QCoreApplication, QProcess, Qt, QTimer
import sys, os


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mise à jour en cours")
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(420)

        self.label = QLabel("Mise à jour en cours…")
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)

        self.btn_show_log = QPushButton("Afficher les détails")
        self.btn_show_log.setCheckable(True)
        self.btn_show_log.toggled.connect(self.log.setVisible)

        lay = QVBoxLayout(self)
        lay.addWidget(self.label)
        lay.addWidget(self.bar)
        lay.addWidget(self.btn_show_log)
        lay.addWidget(self.log)

    def append_log(self, text: str):
        if text := (text or "").strip():
            self.log.append(text)

    def set_status(self, text: str):
        self.label.setText(text)

    def set_done(self, text: str = "Mise à jour réussie."):
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        self.set_status(text)


def restart_app():
    QProcess.startDetached(sys.executable, sys.argv, os.getcwd())
    QApplication.instance().quit()


class ScrapingSettingsWidget(QWidget):
    module_toggled = Signal(str, bool)
    rename_toggled = Signal(bool)

    def __init__(self, modules_order=None, *, show_maintenance: bool = False):
        super().__init__()
        from ..utils.restart import relaunch_current_process

        layout = QVBoxLayout(self)
        # (conserver vos éléments existants ici)
        _ = (modules_order or [])

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

        # Prepare git QProcess
        self._git_proc = QProcess(self)

        self.update_btn.clicked.connect(self._on_update_clicked)
        self.restart_btn.clicked.connect(self._on_restart_clicked)

    # ------------------------------------------------------------------
    @Slot()
    def _on_update_clicked(self) -> None:
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        if not (root / ".git").exists():
            QMessageBox.critical(self, "Mettre à jour", f"Aucun dépôt Git détecté dans :\n{root}")
            return

        self._upd = UpdateDialog(self)
        self._upd.set_status("Mise à jour en cours…")
        self._upd.show()

        self.update_btn.setEnabled(False)

        self._git_proc.setWorkingDirectory(str(root))

        try:
            self._git_proc.readyReadStandardOutput.disconnect()
        except Exception:
            pass
        self._git_proc.readyReadStandardOutput.connect(
            lambda: self._upd.append_log(bytes(self._git_proc.readAllStandardOutput()).decode("utf-8", "ignore"))
        )

        try:
            self._git_proc.readyReadStandardError.disconnect()
        except Exception:
            pass
        self._git_proc.readyReadStandardError.connect(
            lambda: self._upd.append_log(bytes(self._git_proc.readAllStandardError()).decode("utf-8", "ignore"))
        )

        try:
            self._git_proc.finished.disconnect()
        except Exception:
            pass
        self._git_proc.finished.connect(self._on_git_finished_with_restart)

        self._upd.append_log(f"> git pull origin main (cwd={root})")
        self._git_proc.start("git", ["pull", "origin", "main"])

        if not self._git_proc.waitForStarted(2000):
            self.update_btn.setEnabled(True)
            self._upd.close()
            QMessageBox.critical(
                self, "Mettre à jour", "Impossible de démarrer Git. Est-il installé et dans le PATH ?"
            )

    def _on_git_finished_with_restart(self, code: int, status):
        self.update_btn.setEnabled(True)

        if code == 0:
            self._upd.set_done("Mise à jour réussie, redémarrage…")
            QTimer.singleShot(800, restart_app)
        else:
            if hasattr(self, "_upd"):
                self._upd.close()
            QMessageBox.critical(self, "Mettre à jour", f"Échec du 'git pull' (code {code}). Consulte les détails.")

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
