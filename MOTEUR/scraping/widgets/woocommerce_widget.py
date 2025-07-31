from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QAbstractItemView,
)
from PySide6.QtCore import Slot
import csv


class WooCommerceProductWidget(QWidget):
    """Widget to edit WooCommerce product data in a table."""

    HEADERS = [
        "ID",
        "Type",
        "SKU",
        "Name",
        "Published",
        "Short description",
        "Description",
        "Regular price",
        "Sale price",
        "Categories",
        "Tags",
        "Images",
        "In stock?",
        "Stock",
        "Tax status",
        "Shipping class",
        "Attribute 1 name",
        "Attribute 1 value(s)",
        "Attribute 1 visible",
        "Attribute 1 global",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        add_btn = QPushButton("Ajouter une ligne")
        del_btn = QPushButton("Supprimer la ligne sélectionnée")
        import_btn = QPushButton("Importer CSV")
        export_btn = QPushButton("Exporter CSV")

        add_btn.clicked.connect(self.add_row)
        del_btn.clicked.connect(self.delete_selected_row)
        import_btn.clicked.connect(self.import_csv)
        export_btn.clicked.connect(self.export_csv)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(export_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(btn_layout)
        layout.addWidget(self.table)

    # ------------------------------------------------------------------
    @Slot()
    def add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(self.table.columnCount()):
            self.table.setItem(row, col, QTableWidgetItem(""))

    @Slot()
    def delete_selected_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    @Slot()
    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importer CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                rows = list(reader)
        except Exception:
            return
        if not rows:
            return
        start = 1 if rows[0][: len(self.HEADERS)] == self.HEADERS else 0
        for data in rows[start:]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col in range(len(self.HEADERS)):
                value = data[col] if col < len(data) else ""
                self.table.setItem(row, col, QTableWidgetItem(value))

    @Slot()
    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(self.HEADERS)
            for row in range(self.table.rowCount()):
                data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    data.append(item.text() if item else "")
                writer.writerow(data)
