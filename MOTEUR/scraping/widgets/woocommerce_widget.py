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
    QCheckBox,
)
from PySide6.QtCore import Slot
import csv
import random
import string
import re
import unicodedata
from pathlib import Path
import requests


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

    # Folder containing downloaded product images. Tests monkeypatch this path.
    IMAGES_ROOT = Path("images")

    # Base URL for uploaded WooCommerce images.
    BASE_IMAGE_URL = "https://www.planetebob.fr/wp-content/uploads/2025/07/"

    @staticmethod
    def _slugify(text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text).strip("-")
        return text.lower()

    @staticmethod
    def _clean_image_urls(urls: list[str]) -> list[str]:
        """Remove duplicate image URLs using exact and prefix based checks."""
        # Remove exact duplicates first
        unique_urls = list(set(urls))

        prefix_set: set[str] = set()
        final_images: list[str] = []

        for url in sorted(unique_urls):
            filename = url.split("/")[-1]
            prefix = filename.split("_")[0].split("-56cm")[0]

            if prefix not in prefix_set:
                final_images.append(url)
                prefix_set.add(prefix)

        return final_images

    def __init__(self, *, storage_widget=None) -> None:
        super().__init__()
        self.storage_widget = storage_widget
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        add_btn = QPushButton("Ajouter une ligne")
        del_btn = QPushButton("Supprimer la ligne sélectionnée")
        fill_btn = QPushButton("Remplir")
        check_btn = QPushButton("Vérifier URLs")
        import_btn = QPushButton("Importer CSV")
        export_btn = QPushButton("Exporter CSV")

        add_btn.clicked.connect(self.add_row)
        del_btn.clicked.connect(self.delete_selected_row)
        fill_btn.clicked.connect(self.fill_from_storage)
        check_btn.clicked.connect(self.check_urls)
        import_btn.clicked.connect(self.import_csv)
        export_btn.clicked.connect(self.export_csv)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(fill_btn)
        btn_layout.addWidget(check_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(export_btn)

        self.clean_images_checkbox = QCheckBox("Nettoyer les images dupliquées")
        self.clean_images_checkbox.setChecked(True)

        layout = QVBoxLayout(self)
        layout.addLayout(btn_layout)
        layout.addWidget(self.clean_images_checkbox)
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
            writer = csv.writer(f, delimiter=";")
            writer.writerow(self.HEADERS)
            for row in range(self.table.rowCount()):
                data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    data.append(item.text() if item else "")
                writer.writerow(data)

    @Slot()
    def check_urls(self) -> None:
        """Check that image URLs in the table are reachable and export a CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter résultat", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        img_col = self.HEADERS.index("Images")
        urls: list[str] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, img_col)
            if not item:
                continue
            urls.extend(u.strip() for u in item.text().split(", ") if u.strip())

        results: list[tuple[str, str]] = []
        for url in urls:
            try:
                resp = requests.head(url, timeout=5)
                ok = resp.status_code == 200
            except Exception:
                ok = False
            results.append((url, "oui" if ok else "non"))

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["URL", "OK"])
            writer.writerows(results)

    # ------------------------------------------------------------------
    @Slot()
    def fill_from_storage(self) -> None:
        """Create new rows from the linked storage widget."""
        if not self.storage_widget:
            return
        products = self.storage_widget.get_products()
        # Clear any previously populated rows before filling again so
        # repeated calls don't accumulate duplicates.
        self.table.setRowCount(0)
        type_col = self.HEADERS.index("Type")
        sku_col = self.HEADERS.index("SKU")
        name_col = self.HEADERS.index("Name")
        img_col = self.HEADERS.index("Images")

        used_skus: set[str] = set()

        def _gen_sku() -> str:
            """Generate a unique random SKU."""
            while True:
                sku = "SKU-" + "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=8)
                )
                if sku not in used_skus:
                    used_skus.add(sku)
                    return sku

        for prod in products:
            product_name = prod["name"]
            variants = prod["variants"]
            product_slug = self._slugify(product_name)
            folder = self.IMAGES_ROOT / product_name
            local_images: list[str] = []
            if folder.is_dir():
                for p in sorted(folder.iterdir()):
                    if p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}:
                        local_images.append(p.name)

            variant_files = [
                f"{product_slug}-{self._slugify(v)}.jpg" for v in variants
            ]
            generic_images = [img for img in local_images if img not in variant_files]

            is_variable = len(variants) > 1

            if is_variable:
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col in range(self.table.columnCount()):
                    self.table.setItem(row, col, QTableWidgetItem(""))

                parent_sku = _gen_sku()
                self.table.setItem(row, type_col, QTableWidgetItem("variable"))
                self.table.setItem(row, sku_col, QTableWidgetItem(parent_sku))
                self.table.setItem(row, name_col, QTableWidgetItem(product_name))
                parent_images = [
                    self.BASE_IMAGE_URL + img for img in generic_images + variant_files
                ]
                if self.clean_images_checkbox.isChecked():
                    parent_images = self._clean_image_urls(parent_images)
                if parent_images:
                    self.table.setItem(
                        row,
                        img_col,
                        QTableWidgetItem(", ".join(parent_images)),
                    )

                current_row = row
                for variant in variants:
                    current_row += 1
                    self.table.insertRow(current_row)
                    for c in range(self.table.columnCount()):
                        self.table.setItem(current_row, c, QTableWidgetItem(""))
                    self.table.setItem(current_row, type_col, QTableWidgetItem("variation"))
                    var_slug = self._slugify(variant)
                    sku_var = f"{parent_sku}-{var_slug}"
                    used_skus.add(sku_var)
                    name_var = f"{product_name} {variant}"
                    self.table.setItem(current_row, sku_col, QTableWidgetItem(sku_var))
                    self.table.setItem(current_row, name_col, QTableWidgetItem(name_var))
                    var_img = self.BASE_IMAGE_URL + f"{product_slug}-{var_slug}.jpg"
                self.table.setItem(current_row, img_col, QTableWidgetItem(var_img))
            else:
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col in range(self.table.columnCount()):
                    self.table.setItem(row, col, QTableWidgetItem(""))

                sku_val = _gen_sku()
                self.table.setItem(row, type_col, QTableWidgetItem("simple"))
                self.table.setItem(row, sku_col, QTableWidgetItem(sku_val))
                self.table.setItem(row, name_col, QTableWidgetItem(product_name))
                images = [self.BASE_IMAGE_URL + img for img in generic_images + variant_files]
                if self.clean_images_checkbox.isChecked():
                    images = self._clean_image_urls(images)
                if images:
                    self.table.setItem(
                        row,
                        img_col,
                        QTableWidgetItem(", ".join(images)),
                    )


