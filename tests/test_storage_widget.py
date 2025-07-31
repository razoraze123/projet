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

from MOTEUR.scraping.widgets.storage_widget import StorageWidget
from MOTEUR.scraping.widgets.woocommerce_widget import WooCommerceProductWidget


def test_storage_basic_operations():
    app = QApplication.instance() or QApplication([])
    storage = StorageWidget()
    storage.add_product("bob", ["Noir", "Beige"])
    assert storage.table.rowCount() == 1
    products = storage.get_products()
    assert products[0]["name"] == "bob"
    assert products[0]["variants"] == ["Noir", "Beige"]
    storage.clear()
    assert storage.table.rowCount() == 0
    storage.close()
