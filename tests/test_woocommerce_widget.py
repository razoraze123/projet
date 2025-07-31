import sys
import os
from pathlib import Path
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

def test_fill_from_storage():
    app = QApplication.instance() or QApplication([])
    storage = StorageWidget()
    storage.add_product("bob", ["Noir", "Beige"])
    storage.add_product("chapeau", ["Unique"])
    widget = WooCommerceProductWidget(storage_widget=storage)
    widget.fill_from_storage()
    assert widget.table.rowCount() == 2
    type_col = widget.HEADERS.index("Type")
    name_col = widget.HEADERS.index("Name")
    assert widget.table.item(0, name_col).text() == "bob"
    assert widget.table.item(0, type_col).text() == "variable"
    assert widget.table.item(1, type_col).text() == "simple"
    widget.close()
    storage.close()
