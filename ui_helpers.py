from contextlib import contextmanager
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QLabel, QProgressDialog


class Toast(QWidget):
    def __init__(self, parent=None, text="", error=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.lbl = QLabel(text, self)
        self.lbl.setWordWrap(True)
        self.lbl.setStyleSheet(
            "QLabel{padding:8px 12px;border-radius:8px;"
            f"background:{'#C62828' if error else '#424242'};color:white;font-weight:600;}"
        )
        self.lbl.adjustSize()
        self.resize(self.lbl.size())
        QTimer.singleShot(2200, self.close)


def show_toast(parent: QWidget, text: str, error: bool = False):
    if parent is None:
        return
    t = Toast(parent, text, error)
    g = parent.geometry()
    t.adjustSize()
    t.move(g.center().x() - t.width() // 2, g.top() + 30)
    t.show()


@contextmanager
def busy_dialog(parent: QWidget, message="Traitement en cours…"):
    dlg = QProgressDialog(message, None, 0, 0, parent)
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setAutoClose(False)
    dlg.setMinimumDuration(0)
    dlg.show()
    try:
        yield dlg
    finally:
        dlg.close()
        dlg.deleteLater()
