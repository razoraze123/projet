from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from .image_widget import ImageScraperWidget


class _DummySubWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

    def set_selected_profile(self, profile: str) -> None:
        pass

    def refresh_profiles(self) -> None:
        pass


class ScrapWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.modules_order = ["images", "combined"]
        self.images_widget = ImageScraperWidget()
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

