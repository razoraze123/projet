import io
import traceback
import requests
from typing import List
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
            h["X-API-Key"] = self.api_key
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
        target = self.input_edit.text().strip()
        if not target:
            show_toast(self, "Veuillez saisir un alias ou un chemin.", error=True)
            return
        with busy_dialog(self, "Récupération de la liste de fichiers…"):
            try:
                r = self._api_get("/files/list", params={"alias": target})
                if r is None or r.status_code != 200:
                    r = self._api_get("/files/list", params={"path": target})
                    if r is None:
                        return
                data = r.json()
                files = data.get("files", []) if isinstance(data, dict) else data
                self._files = files[: self.limit_spin.value()]
                self._render_grid()
                self.status_lbl.setText(f"{len(self._files)} fichiers affichés (sur {len(files)}).")
                self.open_dir_btn.setEnabled(True)
            except Exception as ex:
                traceback.print_exc()
                show_toast(self, f"Échec de la liste: {ex}", error=True)

    def _render_grid(self):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()

        col_count = 5
        row = col = 0
        for path in self._files:
            card = self._make_thumb_card(path)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1

    def _make_thumb_card(self, path: str) -> QWidget:
        w = QWidget(self)
        v = QVBoxLayout(w)
        lbl_img = QLabel(w)
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setFixedSize(QSize(180, 140))
        lbl_img.setText("Chargement…")

        try:
            rr = self._api_get("/files/raw", params={"path": path})
            if rr is not None and rr.status_code == 200:
                pm = QPixmap()
                pm.loadFromData(rr.content)
                if not pm.isNull():
                    pm = pm.scaled(lbl_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    lbl_img.setPixmap(pm)
                else:
                    lbl_img.setText("Non image")
            else:
                lbl_img.setText("Erreur")
        except Exception:
            lbl_img.setText("Erreur")

        lbl_name = QLabel(path.split("/")[-1], w)
        btn_view = QPushButton("Aperçu", w)
        btn_view.clicked.connect(lambda: self._open_preview(path))

        v.addWidget(lbl_img)
        v.addWidget(lbl_name)
        v.addWidget(btn_view)
        return w

    def _open_preview(self, path: str):
        try:
            rr = self._api_get("/files/raw", params={"path": path})
            if rr is None:
                return
            pm = QPixmap()
            pm.loadFromData(rr.content)
            if pm.isNull():
                show_toast(self, "Fichier non image.", error=True)
                return
            dlg = ImagePreviewDialog(self, title=path.split("/")[-1], pixmap=pm)
            dlg.exec()
        except Exception as ex:
            show_toast(self, f"Impossible d’ouvrir l’aperçu: {ex}", error=True)
