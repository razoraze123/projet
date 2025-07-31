import sys
from pathlib import Path
import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from localapp.app import MainWindow


def test_mainwindow_creation():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "COMPTA - Interface de gestion comptable"
    window.close()
