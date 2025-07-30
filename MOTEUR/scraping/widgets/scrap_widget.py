from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QPushButton, QTextEdit, QProgressBar, QLineEdit


class _DummySubWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.start_btn = QPushButton("Start")
        self.console = QTextEdit()
        self.progress_bar = QProgressBar()
        self.url_edit = QLineEdit()
        self.folder_edit = QLineEdit()
        layout = QVBoxLayout(self)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.console)
        layout.addWidget(self.progress_bar)

    def set_selected_profile(self, profile: str) -> None:
        pass

    def refresh_profiles(self) -> None:
        pass


class ScrapWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.modules_order = []
        self.images_widget = _DummySubWidget()
        self.combined_widget = _DummySubWidget()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.images_widget, "Images")
        self.tabs.addTab(self.combined_widget, "Combined")
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def toggle_module(self, name: str, enabled: bool) -> None:
        pass

    def set_rename(self, enabled: bool) -> None:
        pass
