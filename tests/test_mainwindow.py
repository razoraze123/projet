from PySide6.QtWidgets import QApplication
from localapp.app import MainWindow


def test_mainwindow_creation():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle() == "COMPTA - Interface de gestion comptable"
    window.close()
