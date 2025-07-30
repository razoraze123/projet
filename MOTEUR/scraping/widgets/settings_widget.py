from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal


class ScrapingSettingsWidget(QWidget):
    module_toggled = Signal(str, bool)
    rename_toggled = Signal(bool)

    def __init__(self, modules_order=None):
        super().__init__()
        layout = QVBoxLayout(self)
        (modules_order or [])


