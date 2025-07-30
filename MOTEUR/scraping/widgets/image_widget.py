from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QLineEdit,
    QFileDialog,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, Slot

from ..image_scraper import scrape_images


class ImageScraperWidget(QWidget):
    """Simple interface to run the image scraper."""

    def __init__(self) -> None:
        super().__init__()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL de la page")

        self.selector_edit = QLineEdit()
        self.selector_edit.setPlaceholderText("Sélecteur CSS des images")

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Dossier de destination")

        browse_btn = QPushButton("Parcourir…")
        browse_btn.clicked.connect(self._choose_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(browse_btn)

        self.start_btn = QPushButton("Lancer")
        self.start_btn.clicked.connect(self._start)

        self.console = QTextEdit()
        self.console.setReadOnly(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(self.url_edit)
        layout.addWidget(QLabel("Sélecteur:"))
        layout.addWidget(self.selector_edit)
        layout.addWidget(QLabel("Dossier:"))
        layout.addLayout(folder_layout)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.console)
        layout.addWidget(self.progress_bar)

    def set_selected_profile(self, profile: str) -> None:
        """Placeholder for profile selection support."""
        self.console.append(f"Profil sélectionné: {profile}")

    def refresh_profiles(self) -> None:
        """Placeholder to refresh available profiles."""
        pass

    @Slot()
    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if path:
            self.folder_edit.setText(path)

    @Slot()
    def _start(self) -> None:
        url = self.url_edit.text().strip()
        selector = self.selector_edit.text().strip()
        folder = self.folder_edit.text().strip() or "images"
        if not url or not selector:
            self.console.append("❌ URL ou sélecteur manquant")
            return

        self.start_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        try:
            scrape_images(url, selector)
        except Exception as exc:
            self.console.append(f"❌ Erreur: {exc}")
        else:
            self.console.append("✅ Terminé")
        finally:
            self.progress_bar.hide()
            self.start_btn.setEnabled(True)

