from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Signal


class DashboardWidget(QWidget):
    journal_requested = Signal()
    grand_livre_requested = Signal()
    scraping_summary_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Dashboard"))

    def refresh(self) -> None:
        pass
