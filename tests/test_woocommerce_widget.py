import sys
import os
from pathlib import Path
import csv
import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from MOTEUR.scraping.widgets.woocommerce_widget import WooCommerceProductWidget
from MOTEUR.scraping.widgets.scrap_widget import ScrapWidget
from MOTEUR.scraping.widgets.storage_widget import StorageWidget


def test_widget_headers():
    app = QApplication.instance() or QApplication([])
    widget = WooCommerceProductWidget(storage_widget=StorageWidget())
    assert widget.table.columnCount() == len(widget.HEADERS)
    widget.close()


def test_tab_added_to_scrapwidget():
    app = QApplication.instance() or QApplication([])
    sw = ScrapWidget()
    labels = [sw.tabs.tabText(i) for i in range(sw.tabs.count())]
    assert "Fiche Produit WooCommerce" in labels
    assert "Stockage" in labels
    sw.close()

def test_fill_from_storage(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    storage = StorageWidget()
    storage.add_product("bob", ["Noir", "Beige"])
    storage.add_product("chapeau", ["Unique"])

    images_root = tmp_path / "images"
    (images_root / "bob").mkdir(parents=True)
    (images_root / "bob" / "bob.jpg").write_text("x")
    (images_root / "bob" / "bob-noir.jpg").write_text("x")
    (images_root / "bob" / "bob-beige.jpg").write_text("x")
    (images_root / "chapeau").mkdir()
    (images_root / "chapeau" / "chapeau.jpg").write_text("x")
    (images_root / "chapeau" / "chapeau-unique.jpg").write_text("x")

    monkeypatch.setattr(WooCommerceProductWidget, "IMAGES_ROOT", images_root)

    widget = WooCommerceProductWidget(storage_widget=storage)
    widget.fill_from_storage()
    assert widget.table.rowCount() == 4
    type_col = widget.HEADERS.index("Type")
    name_col = widget.HEADERS.index("Name")
    sku_col = widget.HEADERS.index("SKU")
    img_col = widget.HEADERS.index("Images")

    parent_sku = widget.table.item(0, sku_col).text()
    assert widget.table.item(0, name_col).text() == "bob"
    assert widget.table.item(0, type_col).text() == "variable"
    images0 = set(widget.table.item(0, img_col).text().split(', '))
    assert images0 == {
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob.jpg",
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob-noir.jpg",
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob-beige.jpg",
    }

    assert widget.table.item(1, type_col).text() == "variation"
    assert widget.table.item(1, sku_col).text() == f"{parent_sku}-noir"
    assert widget.table.item(1, name_col).text() == "bob Noir"
    assert widget.table.item(1, img_col).text() == (
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob-noir.jpg"
    )

    assert widget.table.item(2, type_col).text() == "variation"
    assert widget.table.item(2, sku_col).text() == f"{parent_sku}-beige"
    assert widget.table.item(2, img_col).text() == (
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob-beige.jpg"
    )

    assert widget.table.item(3, type_col).text() == "simple"
    images3 = set(widget.table.item(3, img_col).text().split(', '))
    assert images3 == {
        "https://www.planetebob.fr/wp-content/uploads/2025/07/chapeau.jpg",
        "https://www.planetebob.fr/wp-content/uploads/2025/07/chapeau-unique.jpg",
    }
    widget.close()
    storage.close()


def test_export_csv_delimiter(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    widget = WooCommerceProductWidget(storage_widget=StorageWidget())
    widget.add_row()
    name_col = widget.HEADERS.index("Name")
    widget.table.setItem(0, name_col, QtWidgets.QTableWidgetItem("bob"))

    out_file = tmp_path / "out.csv"
    monkeypatch.setattr(
        "MOTEUR.scraping.widgets.woocommerce_widget.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(out_file), ""),
    )

    widget.export_csv()

    with open(out_file, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter=";"))

    assert rows[0] == widget.HEADERS
    assert rows[1][name_col] == "bob"
    widget.close()


def test_clean_image_urls_option(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    storage = StorageWidget()
    storage.add_product("bob", ["Unique"])

    images_root = tmp_path / "images"
    (images_root / "bob").mkdir(parents=True)
    (images_root / "bob" / "bob.jpg").write_text("x")
    (images_root / "bob" / "bob_1.jpg").write_text("x")
    (images_root / "bob" / "bob-unique.jpg").write_text("x")

    monkeypatch.setattr(WooCommerceProductWidget, "IMAGES_ROOT", images_root)

    # Cleaning enabled (default)
    widget = WooCommerceProductWidget(storage_widget=storage)
    widget.fill_from_storage()
    img_col = widget.HEADERS.index("Images")
    images = widget.table.item(0, img_col).text().split(", ")
    assert images == [
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob.jpg",
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob-unique.jpg",
    ]
    widget.close()

    # Cleaning disabled
    widget2 = WooCommerceProductWidget(storage_widget=storage)
    widget2.clean_images_checkbox.setChecked(False)
    widget2.fill_from_storage()
    images2 = widget2.table.item(0, img_col).text().split(", ")
    assert images2 == [
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob.jpg",
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob_1.jpg",
        "https://www.planetebob.fr/wp-content/uploads/2025/07/bob-unique.jpg",
    ]
    widget2.close()


def test_fill_multiple_times_no_duplicates(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    storage = StorageWidget()
    storage.add_product("bob", ["Unique"])

    widget = WooCommerceProductWidget(storage_widget=storage)
    widget.fill_from_storage()
    first_count = widget.table.rowCount()

    # Fill again - row count should remain the same
    widget.fill_from_storage()
    assert widget.table.rowCount() == first_count

    out_file = tmp_path / "out.csv"
    monkeypatch.setattr(
        "MOTEUR.scraping.widgets.woocommerce_widget.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(out_file), ""),
    )

    widget.export_csv()

    with open(out_file, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter=";"))

    # one header row + one product row
    assert len(rows) - 1 == first_count
    widget.close()
    storage.close()
