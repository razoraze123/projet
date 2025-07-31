from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)
from PySide6.QtCore import Slot


class StorageWidget(QWidget):
    """Simple table to store scraped product names and variants."""

    HEADERS = ["Nom du produit", "Variantes"]

    def __init__(self) -> None:
        super().__init__()
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)

        self.clear_btn = QPushButton("Vider le stockage")
        self.clear_btn.clicked.connect(self.clear)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.clear_btn)

    # ------------------------------------------------------------------
    def add_product(self, name: str, variants: list[str]) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(", ".join(variants)))

    def get_products(self) -> list[dict[str, list[str]]]:
        products: list[dict[str, list[str]]] = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            variants_item = self.table.item(row, 1)
            name = name_item.text() if name_item else ""
            variants_text = variants_item.text() if variants_item else ""
            variants = [v.strip() for v in variants_text.split(",") if v.strip()]
            products.append({"name": name, "variants": variants})
        return products

    @Slot()
    def clear(self) -> None:
        self.table.setRowCount(0)
