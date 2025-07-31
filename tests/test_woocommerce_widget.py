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


def test_widget_headers():
    app = QApplication.instance() or QApplication([])
    widget = WooCommerceProductWidget()
    assert widget.table.columnCount() == len(widget.HEADERS)
    widget.close()


def test_tab_added_to_scrapwidget():
    app = QApplication.instance() or QApplication([])
    sw = ScrapWidget()
    labels = [sw.tabs.tabText(i) for i in range(sw.tabs.count())]
    assert "Fiche Produit WooCommerce" in labels
    sw.close()
