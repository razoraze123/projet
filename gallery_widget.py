import traceback
import requests
from typing import List
from urllib.parse import quote
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QSpinBox,
    QLabel, QScrollArea, QGridLayout, QDialog
)
from ui_helpers import show_toast, busy_dialog


class ImagePreviewDialog(QDialog):
    def __init__(self, parent=None, title="Aperçu", pixmap: QPixmap = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QVBoxLayout(self)
        lbl = QLabel(self)
        lbl.setAlignment(Qt.AlignCenter)
        if pixmap:
            lbl.setPixmap(pixmap)
        lay.addWidget(lbl)
        self.resize(900, 700)


class GalleryWidget(QWidget):
    def __init__(self, parent=None, base_url: str = "", api_key: str | None = None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._files: List[str] = []
        self._setup_ui()

    def _setup_ui(self):
        main = QVBoxLayout(self)

        top = QHBoxLayout()
        self.input_edit = QLineEdit(self)
        self.input_edit.setPlaceholderText("Alias ou chemin (ex: images_produit)")
        self.limit_spin = QSpinBox(self)
        self.limit_spin.setRange(1, 500)
        self.limit_spin.setValue(80)
        self.list_btn = QPushButton("Lister", self)
        self.open_dir_btn = QPushButton("Ouvrir dossier (via OS)", self)
        self.open_dir_btn.setEnabled(False)

        top.addWidget(self.input_edit, 2)
        top.addWidget(QLabel("Max:", self))
        top.addWidget(self.limit_spin)
        top.addWidget(self.list_btn)
        top.addWidget(self.open_dir_btn)
        main.addLayout(top)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.grid_host = QWidget(self.scroll)
        self.grid = QGridLayout(self.grid_host)
        self.grid.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.grid_host)
        main.addWidget(self.scroll)

        self.status_lbl = QLabel("Aucune liste chargée.", self)
        main.addWidget(self.status_lbl)

        self.list_btn.clicked.connect(self.on_list_clicked)
        self.open_dir_btn.clicked.connect(self.on_open_dir_clicked)

    # --- API helpers ---
    def _headers(self):
        h = {}
        if self.api_key:
            h["X-API-KEY"] = self.api_key
        return h

    def _api_get(self, path, params=None):
        url = f"{self.base_url}{path}"
        try:
            r = requests.get(url, params=params or {}, headers=self._headers(), timeout=20)
            if r.status_code == 401:
                show_toast(self, "Clé API absente ou invalide (401).", error=True)
                return None
            r.raise_for_status()
            return r
        except requests.Timeout:
            show_toast(self, "Requête expirée (timeout).", error=True)
        except Exception as ex:
            show_toast(self, f"Erreur de requête: {ex}", error=True)
        return None

    # --- Actions ---
    def on_open_dir_clicked(self):
        show_toast(self, "Ouverture dossier côté OS non disponible.", error=True)

    def on_list_clicked(self):
        """
        Appelle /files/list avec 'folder' (alias OU chemin absolu),
        consomme 'urls' du backend et affiche les vignettes à partir de ces URLs.
        """
        target = (
            self.input_edit.text().strip()
            if hasattr(self, "input_edit")
            else "images_root"
        )
        r = self._api_get("/files/list", params={"folder": target})
        if r is None:
            return
        r.raise_for_status()
        data = r.json()

        self._raw_folder = data.get("folder", target)
        files = data.get("files", [])
        urls = data.get("urls", [])

        # Mémoriser la liste structurée pour l'UI
        self._items = []
        for name, url in zip(files, urls):
            self._items.append({"name": name, "url": url})

        self._items = self._items[: self.limit_spin.value()]
        self._render_thumbs(self._items)
        self.status_lbl.setText(
            f"{len(self._items)} fichiers affichés (sur {len(files)})."
        )
        self.open_dir_btn.setEnabled(True)

    def _render_thumbs(self, items):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()

        col_count = 5
        row = col = 0
        for item in items:
            card = self._make_thumb_card(item)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1

    def _make_thumb_card(self, item):
        """
        item = {"name": "...", "url": "..."}
        Utilise l'URL directe. En fallback, reconstruit /files/raw?folder=...&name=...
        """
        name = item.get("name", "")
        url = item.get("url") or ""
        if not url:
            base = self.base_url.rstrip("/")
            url = (
                f"{base}/files/raw?folder={quote(str(getattr(self, '_raw_folder', '')))}"
                f"&name={quote(name)}"
            )

        w = QWidget(self)
        v = QVBoxLayout(w)
        lbl_img = QLabel(w)
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setFixedSize(QSize(180, 140))
        lbl_img.setText("Chargement…")

        try:
            rr = requests.get(url, headers=self._headers(), timeout=20)
            if rr.status_code == 200:
                pm = QPixmap()
                pm.loadFromData(rr.content)
                if not pm.isNull():
                    pm = pm.scaled(
                        lbl_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    lbl_img.setPixmap(pm)
                else:
                    lbl_img.setText("Non image")
            else:
                lbl_img.setText("Erreur")
        except Exception:
            lbl_img.setText("Erreur")

        lbl_name = QLabel(name, w)
        btn_view = QPushButton("Aperçu", w)
        btn_view.clicked.connect(lambda: self._open_preview(name, url))

        v.addWidget(lbl_img)
        v.addWidget(lbl_name)
        v.addWidget(btn_view)
        return w

    def _open_preview(self, name: str, url: str):
        try:
            rr = requests.get(url, headers=self._headers(), timeout=20)
            if rr.status_code != 200:
                show_toast(self, "Erreur", error=True)
                return
            pm = QPixmap()
            pm.loadFromData(rr.content)
            if pm.isNull():
                show_toast(self, "Fichier non image.", error=True)
                return
            dlg = ImagePreviewDialog(self, title=name, pixmap=pm)
            dlg.exec()
        except Exception as ex:
            show_toast(self, f"Impossible d’ouvrir l’aperçu: {ex}", error=True)
