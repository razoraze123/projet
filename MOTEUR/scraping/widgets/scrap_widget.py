import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from MOTEUR.ui.theme import load_theme, apply_theme

from .image_widget import ImageScraperWidget
from MOTEUR.scraping.widgets.collection_widget import CollectionWidget, VERSION_COLLECTION_WIDGET
from .history_widget import HistoryWidget
from .woocommerce_widget import WooCommerceProductWidget
from .storage_widget import StorageWidget
from .flask_server_widget import FlaskServerWidget


class ScrapWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        apply_theme(load_theme())
        self.modules_order = [
            "images",
            "collections",
            "flask",
            "history",
            "woocommerce",
            "stockage",
        ]
        self.storage_widget = StorageWidget()
        self.images_widget = ImageScraperWidget(storage_widget=self.storage_widget)
        self.collections_widget = CollectionWidget()
        self.flask_widget = FlaskServerWidget()
        self.history_widget = HistoryWidget()
        self.woocommerce_widget = WooCommerceProductWidget(
            storage_widget=self.storage_widget
        )
        self.tabs = QTabWidget()
        self.tabs.addTab(self.images_widget, "Images")
        self.tabs.addTab(self.collections_widget, "Collections")
        logging.getLogger(__name__).debug(
            "Collections widget v%s loaded", VERSION_COLLECTION_WIDGET
        )
        self.tabs.addTab(self.flask_widget, "Serveur Flask")
        self.tabs.addTab(self.history_widget, "Historique")
        self.tabs.addTab(self.woocommerce_widget, "Fiche Produit WooCommerce")
        self.tabs.addTab(self.storage_widget, "Stockage")
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def toggle_module(self, name: str, enabled: bool) -> None:
        pass

    def set_rename(self, enabled: bool) -> None:
        pass

