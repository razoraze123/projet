from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Signal, Slot, QCoreApplication
from PySide6.QtWidgets import QApplication

from .flask_server_widget import FlaskServerWidget  # pour introspection douce
from ..utils.restart import relaunch_current_process

class ScrapingSettingsWidget(QWidget):
    module_toggled = Signal(str, bool)
    rename_toggled = Signal(bool)

    def __init__(self, modules_order=None):
        super().__init__()
        layout = QVBoxLayout(self)

        self.btn_update = QPushButton("Mettre à jour depuis GitHub")
        self.btn_restart = QPushButton("Redémarrer l’application")

        layout.addWidget(self.btn_update)
        layout.addWidget(self.btn_restart)
        layout.addStretch(1)

        self.btn_restart.clicked.connect(self._on_restart_clicked)
        # NOTE: btn_update reste inchangé ici (placeholder)

    # ------------------------------------------------------------------
    def _find_flask_widgets(self) -> list[FlaskServerWidget]:
        """Retourne tous les FlaskServerWidget présents dans l'app (best effort)."""
        app = QApplication.instance()
        if not app:
            return []
        found = []
        for w in app.allWidgets():
            try:
                if isinstance(w, FlaskServerWidget):
                    found.append(w)
            except Exception:
                pass
        return found

    @Slot()
    def _on_restart_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "Redémarrer",
            "Voulez-vous vraiment redémarrer l’application ?\n"
            "Les opérations en cours seront arrêtées.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Arrêt propre des serveurs Flask/ngrok si présents
        try:
            for fw in self._find_flask_widgets():
                try:
                    fw._stop()  # utilise la méthode existante du widget
                    print("[restart] Serveur Flask/ngrok arrêté.")
                except Exception as e:
                    print(f"[restart] Impossible d’arrêter Flask: {e}")
        except Exception as e:
            print(f"[restart] Recherche des widgets Flask échouée: {e}")

        # Relance du process puis fermeture de l’actuel
        print("[restart] Relance de l’application…")
        relaunch_current_process(delay_sec=0.2)
        QCoreApplication.quit()
