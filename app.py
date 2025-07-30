import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt

class CollapsibleBox(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton(text=title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)

        self.toggle_button.clicked.connect(self.toggle)

        self.content_widget = QWidget()
        self.content_widget.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_widget)

    def toggle(self):
        expanded = self.toggle_button.isChecked()
        self.content_widget.setVisible(expanded)
        self.toggle_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        if expanded and self.parent() is not None:
            for child in self.parent().findChildren(CollapsibleBox):
                if child is not self:
                    child.collapse()

    def collapse(self):
        self.toggle_button.setChecked(False)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.content_widget.setVisible(False)


def create_tabs(titles):
    tabs = QTabWidget()
    for title in titles:
        tabs.addTab(QLabel(title), title)
    return tabs

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo")
        self.resize(600, 400)
        main_layout = QHBoxLayout(self)

        sidebar = QVBoxLayout()
        sidebar.setAlignment(Qt.AlignTop)

        compta_box = CollapsibleBox("comptabilité")
        compta_tabs = create_tabs([f"à venir {i}" for i in range(1,5)])
        comp_layout = QVBoxLayout(compta_box.content_widget)
        comp_layout.addWidget(compta_tabs)

        scrape_box = CollapsibleBox("scraping")
        scrape_tabs = create_tabs([f"à venir {i}" for i in range(1,5)])
        scrape_layout = QVBoxLayout(scrape_box.content_widget)
        scrape_layout.addWidget(scrape_tabs)

        sidebar.addWidget(compta_box)
        sidebar.addWidget(scrape_box)
        sidebar.addStretch()

        main_layout.addLayout(sidebar)
        main_layout.addStretch()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
