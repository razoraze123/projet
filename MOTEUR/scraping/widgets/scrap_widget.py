from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from MOTEUR.ui.theme import load_theme, apply_theme
from .settings_widget import ScrapingSettingsWidget as SettingsWidget

from .image_widget import ImageScraperWidget
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
            "flask",
            "history",
            "woocommerce",
            "stockage",
        ]
        self.storage_widget = StorageWidget()
        self.images_widget = ImageScraperWidget(storage_widget=self.storage_widget)
        self.flask_widget = FlaskServerWidget()
        self.history_widget = HistoryWidget()
        self.woocommerce_widget = WooCommerceProductWidget(
            storage_widget=self.storage_widget
        )
        self.tabs = QTabWidget()
        self.tabs.addTab(self.images_widget, "Images")
        self.tabs.addTab(self.flask_widget, "Serveur Flask")
        self.tabs.addTab(self.history_widget, "Historique")
        self.tabs.addTab(self.woocommerce_widget, "Fiche Produit WooCommerce")
        self.tabs.addTab(self.storage_widget, "Stockage")
        self.settings_widget = SettingsWidget(show_maintenance=True)
        self.tabs.addTab(self.settings_widget, "Paramètres")
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def toggle_module(self, name: str, enabled: bool) -> None:
        pass

    def set_rename(self, enabled: bool) -> None:
        pass

