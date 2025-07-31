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
    QComboBox,
    QApplication,
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QClipboard

import sys


class _ConsoleStream:
    """File-like object writing text directly to a :class:`QTextEdit`."""

    def __init__(self, widget: QTextEdit) -> None:
        self.widget = widget

    def write(self, text: str) -> int:
        if text:
            # Qt widgets must be manipulated from the GUI thread. Using
            # ``append`` is safe enough for short text snippets.
            self.widget.append(text.rstrip())
        return len(text)

    def flush(self) -> None:  # pragma: no cover - required for file-like API
        pass

from .. import profile_manager as pm
from .. import history

from ..image_scraper import scrape_images


class ImageScraperWidget(QWidget):
    """Simple interface to run the image scraper."""

    def __init__(self) -> None:
        super().__init__()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL de la page")

        self.profile_combo = QComboBox()
        self.profiles: list[dict[str, str]] = []
        self.selected_selector: str = ""
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Dossier de destination")

        browse_btn = QPushButton("Parcourir…")
        browse_btn.clicked.connect(self._choose_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(browse_btn)

        self.start_btn = QPushButton("Lancer")
        self.start_btn.clicked.connect(self._start)
        self.copy_btn = QPushButton("Copier")
        self.copy_btn.clicked.connect(self._copy_console)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.copy_btn)

        self.console = QTextEdit()
        self.console.setReadOnly(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(self.url_edit)
        layout.addWidget(QLabel("Profil:"))
        layout.addWidget(self.profile_combo)
        layout.addWidget(QLabel("Dossier:"))
        layout.addLayout(folder_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.console)
        layout.addWidget(self.progress_bar)

        self.refresh_profiles()
        last = history.load_last_used()
        self.url_edit.setText(last.get("url", ""))
        self.folder_edit.setText(last.get("folder", ""))

    # ------------------------------------------------------------------
    def _on_profile_changed(self, index: int) -> None:
        if 0 <= index < len(self.profiles):
            self.selected_selector = self.profiles[index].get("selector", "")
        else:
            self.selected_selector = ""

    def set_selected_profile(self, profile: str) -> None:
        for i, p in enumerate(self.profiles):
            if p.get("name") == profile:
                self.profile_combo.setCurrentIndex(i)
                self.selected_selector = p.get("selector", "")
                return
        self.profile_combo.setCurrentIndex(-1)
        self.selected_selector = ""

    def refresh_profiles(self) -> None:
        self.profiles = pm.load_profiles()
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        for p in self.profiles:
            self.profile_combo.addItem(p.get("name", ""))
        # restore previous selection if possible
        if current:
            self.set_selected_profile(current)
        else:
            self._on_profile_changed(self.profile_combo.currentIndex())

    @Slot()
    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if path:
            self.folder_edit.setText(path)

    @Slot()
    def _copy_console(self) -> None:
        """Copy the console's contents to the clipboard."""
        text = self.console.toPlainText()
        QApplication.clipboard().setText(text, mode=QClipboard.Clipboard)
        # Also populate the selection clipboard on platforms that support it.
        QApplication.clipboard().setText(text, mode=QClipboard.Selection)

    @Slot()
    def _start(self) -> None:
        url = self.url_edit.text().strip()
        selector = self.selected_selector.strip()
        folder = self.folder_edit.text().strip() or "images"
        if not url or not selector:
            self.console.append("❌ URL ou sélecteur manquant")
            return

        self.start_btn.setEnabled(False)
        self.console.clear()
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        stream = _ConsoleStream(self.console)
        old_stdout = sys.stdout
        sys.stdout = stream
        try:
            total = scrape_images(url, selector, folder)
        except Exception as exc:
            self.console.append(f"❌ Erreur: {exc}")
        else:
            self.console.append("✅ Terminé")
            history.log_scrape(url, self.profile_combo.currentText(), total, folder)
        finally:
            sys.stdout = old_stdout
            self.progress_bar.hide()
            self.start_btn.setEnabled(True)

