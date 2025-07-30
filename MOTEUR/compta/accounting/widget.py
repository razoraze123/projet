from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class AccountWidget(QWidget):
    accounts_updated = Signal()
