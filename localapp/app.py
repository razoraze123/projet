from pathlib import Path
import sys

# Allow running this module directly by ensuring the project root is in
# ``sys.path``.  When executed with ``python localapp/app.py`` the Python
# interpreter only adds the ``localapp`` directory to ``sys.path`` which
# prevents imports from the sibling ``MOTEUR`` package.  Adding the parent
# directory resolves ``ModuleNotFoundError`` for these local imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
try:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QStackedWidget,
        QSizePolicy,
        QFrame,
        QScrollArea,
    )
    from PySide6.QtCore import Qt, QPropertyAnimation, Slot, QEasingCurve
    from PySide6.QtGui import QIcon, QKeySequence, QShortcut
except ModuleNotFoundError:
    print("Install dependencies with pip install -r requirements.txt")
    sys.exit(1)

from MOTEUR.scraping.widgets.scrap_widget import ScrapWidget
from MOTEUR.scraping.widgets.settings_widget import ScrapingSettingsWidget
from MOTEUR.compta.achats.widget import AchatWidget
from MOTEUR.compta.ventes.widget import VenteWidget
from MOTEUR.compta.accounting.widget import AccountWidget
from MOTEUR.scraping.widgets.profile_widget import ProfileWidget
from MOTEUR.compta.dashboard.widget import DashboardWidget
from MOTEUR.ui.settings_widget import SettingsWidget
from MOTEUR.ui.theme import load_theme, apply_theme
from gallery_widget import GalleryWidget

BASE_DIR = Path(__file__).resolve().parent


class SidebarButton(QPushButton):
    """Custom button used in the vertical sidebar."""

    def __init__(self, text: str, icon_path: str | None = None) -> None:
        super().__init__(text)
        if icon_path:
            self.setIcon(QIcon(icon_path))
        self.setStyleSheet(
            """
            QPushButton {
                padding: 10px;
                border: none;
                background-color: #f0f0f0;
                color: #333;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:checked {
                background-color: #c0c0c0;
                font-weight: bold;
            }
            """
        )
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class CollapsibleSection(QWidget):
    """Section with a header button that can show or hide its content."""

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
        *,
        hide_title_when_collapsed: bool = False,
    ) -> None:
        super().__init__(parent)
        self.original_title = title
        self.hide_title_when_collapsed = hide_title_when_collapsed
        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet(
            """
            QPushButton {
                background-color: #444;
                color: white;
                padding: 10px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #666;
            }
            """
        )

        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.toggle_animation = QPropertyAnimation(
            self.content_area,
            b"maximumHeight",
        )
        self.toggle_animation.setDuration(300)
        self.toggle_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggle_animation.setStartValue(0)
        self.toggle_animation.setEndValue(0)

        self.toggle_button.clicked.connect(self.toggle)
        if (
            self.hide_title_when_collapsed
            and not self.toggle_button.isChecked()
        ):
            self.toggle_button.setText("")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)

        self.inner_layout = QVBoxLayout()
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)
        self.content_area.setLayout(self.inner_layout)

    def toggle(self) -> None:
        checked = self.toggle_button.isChecked()
        total_height = self.content_area.sizeHint().height()
        self.toggle_animation.setDirection(
            QPropertyAnimation.Forward
            if checked
            else QPropertyAnimation.Backward
        )
        self.toggle_animation.setEndValue(total_height if checked else 0)
        self.toggle_animation.start()
        if self.hide_title_when_collapsed:
            self.toggle_button.setText(self.original_title if checked else "")

    def collapse(self) -> None:
        if self.toggle_button.isChecked():
            self.toggle_button.setChecked(False)
            self.toggle()

    def expand(self) -> None:
        if not self.toggle_button.isChecked():
            self.toggle_button.setChecked(True)
            self.toggle()

    def add_widget(self, widget: QWidget) -> None:
        self.inner_layout.addWidget(widget)


class MainWindow(QMainWindow):
    """Main application window with a sidebar and central stack."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("COMPTA - Interface de gestion comptable")
        self.setMinimumSize(1200, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        nav_layout = QVBoxLayout(scroll_content)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)
        scroll.setWidget(scroll_content)

        sidebar_container.setStyleSheet("background-color: #ffffff;")
        scroll_content.setStyleSheet("background-color: #ffffff;")

        self.button_group: list[SidebarButton] = []
        self.compta_buttons: dict[str, SidebarButton] = {}

        self.compta_section = CollapsibleSection(
            "\ud83d\udcc1 Comptabilit\u00e9", hide_title_when_collapsed=False
        )
        compta_icons = {
            "Tableau de bord": BASE_DIR / "icons" / "dashboard.svg",
            "Journal": BASE_DIR / "icons" / "journal.svg",
            "Grand Livre": BASE_DIR / "icons" / "grand_livre.svg",
            "Bilan": BASE_DIR / "icons" / "bilan.svg",
            "Résultat": BASE_DIR / "icons" / "resultat.svg",
            "Comptes": BASE_DIR / "icons" / "journal.svg",
            "Révision": BASE_DIR / "icons" / "bilan.svg",
            "Paramètres": BASE_DIR / "icons" / "settings.svg",
            "Achat": BASE_DIR / "icons" / "achat.svg",
            "Fournisseurs": BASE_DIR / "icons" / "achat.svg",
            "Ventes": BASE_DIR / "icons" / "ventes.svg",
        }
        for name in compta_icons:
            btn = SidebarButton(name, icon_path=str(compta_icons[name]))
            self.compta_buttons[name] = btn
            if name == "Tableau de bord":
                self.dashboard_btn = btn
                btn.clicked.connect(
                    lambda _, b=btn: self.show_dashboard_page(b)
                )
            elif name == "Achat":
                self.achat_btn = btn
                btn.clicked.connect(
                    lambda _, b=btn: self.show_achat_page(b)
                )
            elif name == "Fournisseurs":
                self.suppliers_btn = btn
                btn.clicked.connect(
                    lambda _, b=btn: self.show_suppliers_page(b)
                )
            elif name == "Comptes":
                self.accounts_btn = btn
                btn.clicked.connect(
                    lambda _, b=btn: self.show_accounts_page(b)
                )
            elif name == "Révision":
                self.revision_btn = btn
                btn.clicked.connect(
                    lambda _, b=btn: self.show_revision_page(b)
                )
            elif name == "Paramètres":
                self.param_journals_btn = btn
                btn.clicked.connect(
                    lambda _, b=btn: self.show_journals_page(b)
                )
            elif name == "Ventes":
                self.ventes_btn = btn
                btn.clicked.connect(
                    lambda _, b=btn: self.show_ventes_page(b)
                )
            else:
                btn.clicked.connect(
                    lambda _, n=name, b=btn: self.display_content(
                        f"Comptabilité : {n}", b
                    )
                )
            self.compta_section.add_widget(btn)
            self.button_group.append(btn)
        nav_layout.addWidget(self.compta_section)

        self.scrap_section = CollapsibleSection("\ud83d\udee0 Scraping")

        self.profiles_btn = SidebarButton(
            "Profil Scraping",
            icon_path=str(BASE_DIR / "icons" / "profile.svg"),
        )
        self.profiles_btn.clicked.connect(
            lambda _, b=self.profiles_btn: self.show_profiles(b)
        )
        self.scrap_section.add_widget(self.profiles_btn)
        self.button_group.append(self.profiles_btn)

        self.scrap_btn = SidebarButton(
            "Scrap",
            icon_path=str(BASE_DIR / "icons" / "scraping.svg"),
        )
        self.scrap_btn.clicked.connect(
            lambda _, b=self.scrap_btn: self.show_scrap_page(b)
        )
        self.scrap_section.add_widget(self.scrap_btn)
        self.button_group.append(self.scrap_btn)

        self.gallery_btn = SidebarButton("Galerie")
        self.gallery_btn.clicked.connect(lambda _, b=self.gallery_btn: self.show_gallery_tab())
        self.scrap_section.add_widget(self.gallery_btn)
        self.button_group.append(self.gallery_btn)

        btn = SidebarButton(
            "Scraping Descriptions",
            icon_path=str(BASE_DIR / "icons" / "text.svg"),
        )
        btn.clicked.connect(
            lambda _, b=btn: self.display_content("Scraping : Descriptions", b)
        )
        self.scrap_section.add_widget(btn)
        self.button_group.append(btn)

        self.scrap_settings_btn = SidebarButton(
            "Paramètres Scraping",
            icon_path=str(BASE_DIR / "icons" / "settings.svg"),
        )
        self.scrap_settings_btn.clicked.connect(
            lambda _, b=self.scrap_settings_btn: self.show_scraping_settings_page(b)
        )
        self.scrap_section.add_widget(self.scrap_settings_btn)
        self.button_group.append(self.scrap_settings_btn)
        nav_layout.addWidget(self.scrap_section)

        # Collapse the other section when one is expanded
        self.compta_section.toggle_button.clicked.connect(
            lambda: self._collapse_other(self.compta_section)
        )
        self.scrap_section.toggle_button.clicked.connect(
            lambda: self._collapse_other(self.scrap_section)
        )

        nav_layout.addStretch()

        sidebar_layout.addWidget(scroll)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("margin:5px 0;")
        sidebar_layout.addWidget(line)

        self.settings_btn = SidebarButton(
            "\u2699\ufe0f Paramètres",
            icon_path=str(BASE_DIR / "icons" / "settings.svg"),
        )
        self.settings_btn.clicked.connect(self.show_settings)
        sidebar_layout.addWidget(self.settings_btn)
        self.button_group.append(self.settings_btn)

        self.stack = QStackedWidget()
        self.stack.addWidget(
            QLabel("Bienvenue sur COMPTA", alignment=Qt.AlignCenter)
        )

        self.profile_page = ProfileWidget()
        self.stack.addWidget(self.profile_page)

        self.scrap_page = ScrapWidget()
        self.stack.addWidget(self.scrap_page)

        self.scraping_settings_page = ScrapingSettingsWidget(
            self.scrap_page.modules_order,
            show_maintenance=False,
        )
        self.scraping_settings_page.module_toggled.connect(
            self.scrap_page.toggle_module
        )
        self.scraping_settings_page.rename_toggled.connect(
            self.scrap_page.set_rename
        )
        self.stack.addWidget(self.scraping_settings_page)

        base_url = getattr(self, "flask_base_url", "")
        api_key = getattr(self, "api_key", None)
        self.gallery_page = GalleryWidget(self, base_url=base_url, api_key=api_key)
        self.stack.addWidget(self.gallery_page)

        self.profile_page.profile_chosen.connect(
            self.scrap_page.images_widget.set_selected_profile
        )
        self.profile_page.profiles_updated.connect(
            self.scrap_page.images_widget.refresh_profiles
        )

        self.dashboard_page = DashboardWidget()
        self.dashboard_page.journal_requested.connect(
            lambda: self.open_from_dashboard("Journal")
        )
        self.dashboard_page.grand_livre_requested.connect(
            lambda: self.open_from_dashboard("Grand Livre")
        )
        self.dashboard_page.scraping_summary_requested.connect(
            lambda: self.show_scrap_page(self.scrap_btn)
        )
        self.stack.addWidget(self.dashboard_page)

        self.achat_page = AchatWidget()
        self.stack.addWidget(self.achat_page)

        from MOTEUR.compta.suppliers import SupplierTab

        self.suppliers_page = SupplierTab()
        self.stack.addWidget(self.suppliers_page)

        self.accounts_page = AccountWidget()
        self.accounts_page.accounts_updated.connect(
            self.achat_page.refresh_accounts
        )
        self.stack.addWidget(self.accounts_page)

        from MOTEUR.compta.parameters import JournalsWidget

        self.journals_page = JournalsWidget()
        self.stack.addWidget(self.journals_page)

        from MOTEUR.compta.revision import RevisionTab

        self.revision_page = RevisionTab()
        self.stack.addWidget(self.revision_page)

        self.ventes_page = VenteWidget()
        self.stack.addWidget(self.ventes_page)

        self.settings_page = SettingsWidget()
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(sidebar_container, 1)
        main_layout.addWidget(self.stack, 4)

        # Install global shortcuts
        self._install_shortcuts()

    def clear_selection(self) -> None:
        for btn in self.button_group:
            btn.setChecked(False)

    def _collapse_other(self, active: CollapsibleSection) -> None:
        if active.toggle_button.isChecked():
            other = (
                self.scrap_section if active is self.compta_section else self.compta_section
            )
            other.collapse()

    def _install_shortcuts(self) -> None:
        def add(key: str, fn):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(fn)

        if hasattr(self, "show_scrap_page"):
            add("Ctrl+1", lambda: self.show_scrap_page(self.scrap_btn))
        if hasattr(self, "show_profiles"):
            add("Ctrl+2", lambda: self.show_profiles(self.profiles_btn))
        if hasattr(self, "show_gallery_tab"):
            add("Ctrl+3", self.show_gallery_tab)
        if hasattr(self, "show_flask_tab"):
            add("Ctrl+4", self.show_flask_tab)
        if hasattr(self, "show_settings"):
            add("Ctrl+5", self.show_settings)

        target = getattr(self, "scrap_page", None)
        if target and hasattr(target, "start_scan"):
            add("Ctrl+L", target.start_scan)
        if target and hasattr(target, "copy_links_to_clipboard"):
            add("Ctrl+C", target.copy_links_to_clipboard)
        if target and hasattr(target, "dedupe_links"):
            add("Ctrl+D", target.dedupe_links)
        if target and hasattr(target, "export_links_csv"):
            add("Ctrl+E", target.export_links_csv)

    def display_content(self, text: str, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        label = QLabel(text, alignment=Qt.AlignCenter)
        self.stack.addWidget(label)
        self.stack.setCurrentWidget(label)

    def show_scrap_page(self, button: SidebarButton, tab_index: int = 0) -> None:
        self.clear_selection()
        button.setChecked(True)
        try:
            self.scrap_page.tabs.setCurrentIndex(tab_index)
        except Exception:
            pass
        self.stack.setCurrentWidget(self.scrap_page)

    def show_scraping_images(self, button: SidebarButton) -> None:
        self.show_scrap_page(button, tab_index=0)

    def show_profiles(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.profile_page)

    def show_gallery_tab(self) -> None:
        self.clear_selection()
        if hasattr(self, "gallery_btn"):
            self.gallery_btn.setChecked(True)
        self.stack.setCurrentWidget(self.gallery_page)

    def show_dashboard_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.dashboard_page.refresh()
        self.stack.setCurrentWidget(self.dashboard_page)

    def show_accounts_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.accounts_page)

    def show_revision_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.revision_page)

    def show_journals_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.journals_page)

    def show_achat_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.achat_page)

    def show_suppliers_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.suppliers_page)

    def show_scraping_settings_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.scraping_settings_page)

    def show_ventes_page(self, button: SidebarButton) -> None:
        self.clear_selection()
        button.setChecked(True)
        self.stack.setCurrentWidget(self.ventes_page)

    def open_from_dashboard(self, name: str) -> None:
        btn = self.compta_buttons.get(name)
        if btn:
            self.display_content(f"Comptabilité : {name}", btn)

    def show_settings(self) -> None:
        self.clear_selection()
        self.settings_btn.setChecked(True)
        self.stack.setCurrentWidget(self.settings_page)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_theme(load_theme())
    interface = MainWindow()
    interface.show()
    sys.exit(app.exec())
