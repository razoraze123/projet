from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class ProfileWidget(QWidget):
    profile_chosen = Signal(str)
    profiles_updated = Signal()

    def __init__(self) -> None:
        super().__init__()


