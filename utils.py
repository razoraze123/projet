from pathlib import Path
from PySide6.QtWidgets import QWidget, QToolButton, QVBoxLayout, QCheckBox
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

ICON_SIZE = 24
ICONS_DIR = Path("icons")
SIDEBAR_EXPANDED_WIDTH = 180
SIDEBAR_COLLAPSED_WIDTH = 50


def load_stylesheet() -> None:
    """No-op stylesheet loader."""
    pass


class ToggleSwitch(QCheckBox):
    """Simple toggle switch based on QCheckBox."""
    pass


class CollapsibleSection(QWidget):
    """Simple wrapper providing a button used in the sidebar."""

    def __init__(self, toggle_cls, text: str, icon: QIcon, callback) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.header = QToolButton(text=text, icon=icon)
        self.header.setCheckable(True)
        self.header.setToolButtonStyle(self.header.toolButtonStyle())
        self.header.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.header.clicked.connect(callback)
        layout.addWidget(self.header)
        layout.addStretch()
