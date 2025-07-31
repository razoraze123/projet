from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from .image_widget import ImageScraperWidget
from .history_widget import HistoryWidget
from .woocommerce_widget import WooCommerceProductWidget
from .storage_widget import StorageWidget


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
        self.modules_order = [
            "images",
            "combined",
            "history",
            "woocommerce",
            "stockage",
        ]
        self.storage_widget = StorageWidget()
        self.images_widget = ImageScraperWidget(storage_widget=self.storage_widget)
        self.combined_widget = _DummySubWidget()
        self.history_widget = HistoryWidget()
        self.woocommerce_widget = WooCommerceProductWidget(
            storage_widget=self.storage_widget
        )
        self.tabs = QTabWidget()
        self.tabs.addTab(self.images_widget, "Images")
        self.tabs.addTab(self.combined_widget, "Combined")
        self.tabs.addTab(self.history_widget, "Historique")
        self.tabs.addTab(self.woocommerce_widget, "Fiche Produit WooCommerce")
        self.tabs.addTab(self.storage_widget, "Stockage")
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def toggle_module(self, name: str, enabled: bool) -> None:
        pass

    def set_rename(self, enabled: bool) -> None:
        pass

