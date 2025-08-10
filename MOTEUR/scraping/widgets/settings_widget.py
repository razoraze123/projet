from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtCore import Signal, Slot, QCoreApplication


class ScrapingSettingsWidget(QWidget):
    module_toggled = Signal(str, bool)
    rename_toggled = Signal(bool)

    def __init__(self, modules_order=None, *, show_maintenance: bool = False):
        super().__init__()
        from ..utils.restart import relaunch_current_process
        from ..utils.update import pull_latest

        layout = QVBoxLayout(self)
        # (conserver vos éléments existants ici)
        _ = (modules_order or [])

        if show_maintenance:
            row = QHBoxLayout()
            btn_update = QPushButton("Mettre à jour")
            btn_update.setObjectName("btn_update")
            btn_restart = QPushButton("Redémarrer")
            btn_restart.setObjectName("btn_restart")
            row.addWidget(btn_update)
            row.addWidget(btn_restart)
            layout.addLayout(row)

            @Slot()
            def _on_update_clicked():
                pull_latest()

            @Slot()
            def _on_restart_clicked():
                ret = QMessageBox.question(
                    self, "Redémarrer",
                    "Voulez-vous vraiment redémarrer l’application ?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if ret != QMessageBox.Yes:
                    return
                relaunch_current_process(delay_sec=0.3)
                QCoreApplication.quit()

            btn_update.clicked.connect(_on_update_clicked)
            btn_restart.clicked.connect(_on_restart_clicked)
