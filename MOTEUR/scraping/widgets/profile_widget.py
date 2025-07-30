from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QLineEdit,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Signal, Slot

from .. import profile_manager as pm


class ProfileWidget(QWidget):
    """Widget to manage scraping profiles."""

    profile_chosen = Signal(str)
    profiles_updated = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.profile_list = QListWidget()
        self.profile_list.itemSelectionChanged.connect(self._on_profile_selected)

        self.name_edit = QLineEdit()
        self.selector_edit = QLineEdit()

        self.add_btn = QPushButton("Ajouter")
        self.add_btn.clicked.connect(self._add_profile)
        self.update_btn = QPushButton("Modifier")
        self.update_btn.clicked.connect(self._update_profile)
        self.delete_btn = QPushButton("Supprimer")
        self.delete_btn.clicked.connect(self._delete_profile)

        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("Nom:"))
        form_layout.addWidget(self.name_edit)
        form_layout.addWidget(QLabel("Sélecteur CSS:"))
        form_layout.addWidget(self.selector_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.delete_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Profils existants:"))
        layout.addWidget(self.profile_list)
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)

        self._load_profiles()

    # ------------------------------------------------------------------
    def _load_profiles(self) -> None:
        """Load profiles from :mod:`profile_manager` and populate the list."""
        self.profiles = pm.load_profiles()
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.profile_list.clear()
        for profile in self.profiles:
            self.profile_list.addItem(profile.get("name", ""))

    @Slot()
    def _on_profile_selected(self) -> None:
        current = self.profile_list.currentRow()
        if current < 0 or current >= len(self.profiles):
            return
        profile = self.profiles[current]
        self.name_edit.setText(profile.get("name", ""))
        self.selector_edit.setText(profile.get("selector", ""))
        self.profile_chosen.emit(profile.get("name", ""))

    @Slot()
    def _add_profile(self) -> None:
        name = self.name_edit.text().strip()
        selector = self.selector_edit.text().strip()
        if not name or not selector:
            return
        try:
            pm.add_profile(name, selector)
        except ValueError:
            return
        self._load_profiles()
        self.profiles_updated.emit()

    @Slot()
    def _update_profile(self) -> None:
        name = self.name_edit.text().strip()
        selector = self.selector_edit.text().strip()
        if not name or not selector:
            return
        if pm.update_profile(name, selector):
            self._load_profiles()

    @Slot()
    def _delete_profile(self) -> None:
        current = self.profile_list.currentRow()
        if current < 0 or current >= len(self.profiles):
            return
        name = self.profiles[current].get("name", "")
        if pm.delete_profile(name):
            self._load_profiles()
            self.profiles_updated.emit()

