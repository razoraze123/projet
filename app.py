import sys
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QScrollArea,
    QSplitter,
    QFrame,
)

SIDEBAR_EXPANDED_WIDTH = 200
SIDEBAR_COLLAPSED_WIDTH = 40


class CollapsibleSection(QWidget):
    """Simple collapsible section used in the sidebar."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.header = QToolButton(text=title)
        self.header.setCheckable(True)
        self.header.setChecked(True)
        self.header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.header.setArrowType(Qt.DownArrow)
        self.header.clicked.connect(self._toggle)

        self.content = QWidget()
        self._content_layout = QVBoxLayout(self.content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.content)

    def addWidget(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def _toggle(self, checked: bool) -> None:
        self.content.setVisible(checked)
        self.header.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)


class PageAvenir1(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Page \u00c0 venir 1"))
        layout.addStretch()


class PageAvenir2(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Page \u00c0 venir 2"))
        layout.addStretch()


class PageAvenir3(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Page \u00c0 venir 3"))
        layout.addStretch()


class PageAvenir4(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Page \u00c0 venir 4"))
        layout.addStretch()


class PageAvenir5(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Page \u00c0 venir 5"))
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Demo")

        # --- Toolbar -------------------------------------------------
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.toggle_sidebar_btn = QToolButton()
        self.toggle_sidebar_btn.setArrowType(Qt.LeftArrow)
        self.toggle_sidebar_btn.clicked.connect(self.toggle_sidebar)
        self.toolbar.addWidget(self.toggle_sidebar_btn)

        self.title_button = QToolButton()
        self.title_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.title_button.setEnabled(False)
        self.toolbar.addWidget(self.title_button)

        # --- Stack ---------------------------------------------------
        self.stack = QStackedWidget()
        self.pages = [
            PageAvenir1(),
            PageAvenir2(),
            PageAvenir3(),
            PageAvenir4(),
            PageAvenir5(),
        ]
        for p in self.pages:
            self.stack.addWidget(p)
        self.stack.currentChanged.connect(self.update_title)

        # --- Sidebar -------------------------------------------------
        self.sidebar = QWidget()
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setAlignment(Qt.AlignTop)

        self.side_buttons = []

        compta_section = CollapsibleSection("Compta")
        for idx, text in enumerate(["\u00c0 venir 1", "\u00c0 venir 2"], start=0):
            btn = QToolButton(text=text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, i=idx: self.show_page(i))
            compta_section.addWidget(btn)
            self.side_buttons.append(btn)
        side_layout.addWidget(compta_section)

        scrape_section = CollapsibleSection("Scraping")
        for idx, text in enumerate([
            "\u00c0 venir 3",
            "\u00c0 venir 4",
            "\u00c0 venir 5",
        ], start=2):
            btn = QToolButton(text=text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, i=idx: self.show_page(i))
            scrape_section.addWidget(btn)
            self.side_buttons.append(btn)
        side_layout.addWidget(scrape_section)
        side_layout.addStretch()

        self.sidebar.setMinimumWidth(0)
        self.sidebar.setMaximumWidth(SIDEBAR_EXPANDED_WIDTH)

        # --- Central layout -----------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.stack)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.setStretchFactor(1, 1)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.setCentralWidget(container)

        self.sidebar_visible = True
        self.show_page(0)

    # --- Page Management -------------------------------------------
    def show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.side_buttons):
            btn.setChecked(i == index)
        self.update_title(index)

    def update_title(self, index: int) -> None:
        if 0 <= index < len(self.side_buttons):
            self.title_button.setText(self.side_buttons[index].text())

    # --- Sidebar animation ----------------------------------------
    def toggle_sidebar(self) -> None:
        start = self.sidebar.width()
        end = (
            SIDEBAR_COLLAPSED_WIDTH if self.sidebar_visible else SIDEBAR_EXPANDED_WIDTH
        )
        if not self.sidebar_visible:
            self.sidebar.setVisible(True)

        self._anim = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        self._anim.setDuration(200)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.finished.connect(self._on_sidebar_toggled)
        self._anim.start()

    def _on_sidebar_toggled(self) -> None:
        self.sidebar_visible = not self.sidebar_visible
        if not self.sidebar_visible:
            self.sidebar.setMaximumWidth(SIDEBAR_COLLAPSED_WIDTH)
        else:
            self.sidebar.setMaximumWidth(SIDEBAR_EXPANDED_WIDTH)
        arrow = Qt.LeftArrow if self.sidebar_visible else Qt.RightArrow
        self.toggle_sidebar_btn.setArrowType(arrow)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
