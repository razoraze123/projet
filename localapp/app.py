# --- Bootstrap UTF-8, compatible run module ET run direct ---
try:
    from .utf8_bootstrap import force_utf8_stdio
except ImportError:
    # ex: si lancé par chemin direct (pas en module)
    from utf8_bootstrap import force_utf8_stdio
force_utf8_stdio()

# Logs robustes (print_safe)
try:
    from .log_safe import print_safe, open_utf8
except ImportError:
    from log_safe import print_safe, open_utf8

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
        QSizePolicy,
        QFrame,
        QScrollArea,
        QCheckBox,
    )
    from PySide6.QtCore import Qt, QPropertyAnimation, Slot, QEasingCurve
    from PySide6.QtGui import QIcon, QKeySequence, QShortcut
except ModuleNotFoundError:
    print_safe("Install dependencies with pip install -r requirements.txt")
    sys.exit(1)

from MOTEUR.scraping.widgets.scrap_widget import ScrapWidget
from MOTEUR.compta.achats.widget import AchatWidget
from MOTEUR.compta.ventes.widget import VenteWidget
from MOTEUR.compta.accounting.widget import AccountWidget
from MOTEUR.scraping.widgets.profile_widget import ProfileWidget
from MOTEUR.compta.dashboard.widget import DashboardWidget
from MOTEUR.ui.settings_widget import SettingsWidget
from gallery_widget import GalleryWidget

from localapp.ui_theme import ThemeManager
from localapp.ui_icons import get_icon
from localapp.ui_animations import AnimatedStack, toast
from localapp.utils_copytxt import regenerate_copy_txt


class SidebarButton(QPushButton):
    """Custom button used in the vertical sidebar."""

    def __init__(self, text: str, icon: QIcon | None = None) -> None:
        super().__init__(text)
        if icon:
            self.setIcon(icon)
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

    def __init__(self, theme: ThemeManager | None = None) -> None:
        super().__init__()
        self.theme = theme
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
            "📁 Comptabilité", hide_title_when_collapsed=False
        )
        compta_items = [
            ("Tableau de bord", "dashboard", self.show_dashboard_page),
            ("Journal", "journal", lambda b: self.display_content("Comptabilité : Journal", b)),
            (
                "Grand Livre",
                "grand_livre",
                lambda b: self.display_content("Comptabilité : Grand Livre", b),
            ),
            ("Bilan", "bilan", lambda b: self.display_content("Comptabilité : Bilan", b)),
            (
                "Résultat",
                "resultat",
                lambda b: self.display_content("Comptabilité : Résultat", b),
            ),
            ("Comptes", "comptes", self.show_accounts_page),
            ("Révision", "revision", self.show_revision_page),
            ("Paramètres", "parametres", self.show_journals_page),
        ]
        for name, icon_name, handler in compta_items:
            btn = SidebarButton(name, get_icon(icon_name))
            self.compta_buttons[name] = btn
            btn.clicked.connect(lambda _, b=btn, h=handler: h(b))
            self.compta_section.add_widget(btn)
            self.button_group.append(btn)
        nav_layout.addWidget(self.compta_section)

        self.scrap_section = CollapsibleSection("🛠️ Scraping")

        self.scrap_btn = SidebarButton("Scrap", get_icon("scrap"))
        self.scrap_btn.clicked.connect(
            lambda _, b=self.scrap_btn: self.show_scrap_page(b)
        )
        self.scrap_section.add_widget(self.scrap_btn)
        self.button_group.append(self.scrap_btn)

        self.profiles_btn = SidebarButton(
            "Profil Scraping", get_icon("profil_scraping")
        )
        self.profiles_btn.clicked.connect(
            lambda _, b=self.profiles_btn: self.show_profiles(b)
        )
        self.scrap_section.add_widget(self.profiles_btn)
        self.button_group.append(self.profiles_btn)

        self.gallery_btn = SidebarButton("Galerie", get_icon("galerie"))
        self.gallery_btn.clicked.connect(lambda _, b=self.gallery_btn: self.show_gallery_tab())
        self.scrap_section.add_widget(self.gallery_btn)
        self.button_group.append(self.gallery_btn)

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


        foot = QWidget()
        foot_layout = QHBoxLayout(foot)
        foot_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(get_icon("parametres"))
        self.settings_btn.clicked.connect(self.show_settings)
        foot_layout.addWidget(self.settings_btn)
        if self.theme:
            self.theme_toggle = QCheckBox()
            self.theme_toggle.setChecked(self.theme.current == "dark")
            self.theme_toggle.toggled.connect(
                lambda checked: self.theme.apply("dark" if checked else "light")
            )
            foot_layout.addWidget(self.theme_toggle)
            self.theme_label = QLabel()
            foot_layout.addWidget(self.theme_label)
            self._update_theme_label(self.theme.current)
            self.theme.theme_changed.connect(self._on_theme_changed)
        foot_layout.addStretch()
        sidebar_layout.addWidget(foot)
        self.stack = AnimatedStack()
        self.stack.addWidget(
            QLabel("Bienvenue sur COMPTA", alignment=Qt.AlignCenter)
        )

        self.profile_page = ProfileWidget()
        self.stack.addWidget(self.profile_page)

        self.scrap_page = ScrapWidget()
        self.stack.addWidget(self.scrap_page)


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
        self.copy_txt_path = r"C:\\Users\\Lamine\\Desktop\\scrap\\projet\\copy.txt"
        self.settings_page.btn_update_txt.clicked.connect(
            lambda: self._on_update_txt_clicked()
        )

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
        self.stack.setCurrentWidget(self.settings_page)

    def _update_theme_label(self, theme: str) -> None:
        if hasattr(self, "theme_label"):
            self.theme_label.setText(
                "Mode sombre" if theme == "dark" else "Mode clair"
            )

    def _on_theme_changed(self, name: str) -> None:
        if hasattr(self, "theme_toggle"):
            block = self.theme_toggle.blockSignals(True)
            self.theme_toggle.setChecked(name == "dark")
            self.theme_toggle.blockSignals(block)
        self._update_theme_label(name)
        toast(self, f"Thème {name}")

    def _on_update_txt_clicked(self) -> None:
        try:
            msg = regenerate_copy_txt(self.copy_txt_path)
            print(msg)
        except Exception as e:
            print(f"Erreur régénération copy.txt: {e}")



if __name__ == "__main__":
    import faulthandler, pathlib

    path = pathlib.Path("crash.log")
    try:
        faulthandler.enable(all_threads=True)
        faulthandler.dump_traceback_later(30, repeat=True, file=open_utf8(path, "a"))
    except Exception:
        pass

    app = QApplication(sys.argv)
    try:
        import localapp.resources_rc  # noqa: F401
    except Exception:
        pass
    theme = ThemeManager(app)
    interface = MainWindow(theme)
    interface.show()
    sys.exit(app.exec())
