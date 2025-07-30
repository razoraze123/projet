from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PySide6.QtCore import Slot

from .. import history


class HistoryWidget(QWidget):
    """Display previous scraping runs."""

    def __init__(self) -> None:
        super().__init__()
        self.text = QTextEdit(readOnly=True)
        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.clicked.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        layout.addWidget(self.refresh_btn)

        self.refresh()

    @Slot()
    def refresh(self) -> None:
        entries = history.load_history()
        lines = []
        for entry in entries:
            lines.append(
                f"{entry.get('date','')} - {entry.get('url','')} ("\
                f"{entry.get('profile','')} - {entry.get('images',0)} images)"
            )
        self.text.setPlainText("\n".join(lines))
