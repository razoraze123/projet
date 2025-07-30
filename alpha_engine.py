from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


class AlphaEngine(QWidget):
    """Placeholder widget for Alpha engine."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Alpha Engine placeholder"))
