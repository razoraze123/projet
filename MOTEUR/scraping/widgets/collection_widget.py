from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..image_scraper import scrape_collection_products


class CollectionWidget(QWidget):
    """UI widget to list products from a collection page."""

    def __init__(self) -> None:
        super().__init__()
        self._pairs: list[tuple[str, str]] = []

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL de la page collection")

        self.list_btn = QPushButton("Scanner la collection")
        self.list_btn.clicked.connect(self._scan_collection)

        self.save_btn = QPushButton("Enregistrer la liste…")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_list)

        self.console = QTextEdit(readOnly=True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL :"))
        layout.addWidget(self.url_edit)
        layout.addWidget(self.list_btn)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.console)

    # ------------------------------------------------------------------
    @Slot()
    def _scan_collection(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            self.console.append("❌ Saisis une URL de collection.")
            return
        self.console.append("⏳ Scan de la collection…")
        try:
            pairs = scrape_collection_products(url)
        except Exception as exc:
            self.console.append(f"❌ Erreur collecte: {exc}")
            self._pairs = []
            self.save_btn.setEnabled(False)
            return
        self._pairs = pairs
        if not pairs:
            self.console.append("⚠️ Aucun produit détecté.")
            self.save_btn.setEnabled(False)
            return
        for name, href in pairs:
            self.console.append(f"{name}\t{href}")
        self.console.append(f"✅ {len(pairs)} produits trouvés.")
        self.save_btn.setEnabled(True)

    @Slot()
    def _save_list(self) -> None:
        if not self._pairs:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la liste",
            "",
            "Text files (*.txt)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for name, href in self._pairs:
                    f.write(f"{name}\t{href}\n")
        except Exception as exc:
            QMessageBox.critical(self, "Export", f"Erreur: {exc}")
            return
        QMessageBox.information(self, "Export", f"✅ Liste enregistrée : {path}")
