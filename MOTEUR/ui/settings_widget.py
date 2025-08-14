from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QPushButton,
    QGroupBox,
)
from PySide6.QtCore import Slot

from .theme import load_theme, save_theme, apply_theme


class SettingsWidget(QWidget):
    """General application settings."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        maint_group = QGroupBox("Maintenance")
        maint_layout = QVBoxLayout(maint_group)
        self.btn_update_txt = QPushButton("Mettre à jour le txt")
        self.btn_update_txt.setObjectName("btn_update_txt")
        maint_layout.addWidget(self.btn_update_txt)
        maint_layout.addWidget(QLabel("Régénère copy.txt"))
        layout.addWidget(maint_group)

        theme_group = QGroupBox("Thème de l’application")
        t_layout = QVBoxLayout(theme_group)
        radios = QHBoxLayout()
        self.light_radio = QRadioButton("Clair")
        self.dark_radio = QRadioButton("Sombre")
        current = load_theme()
        (self.dark_radio if current == "dark" else self.light_radio).setChecked(True)
        self.light_radio.toggled.connect(lambda _: self._apply())
        self.dark_radio.toggled.connect(lambda _: self._apply())
        radios.addWidget(self.light_radio)
        radios.addWidget(self.dark_radio)
        t_layout.addLayout(radios)
        self.apply_btn = QPushButton("Appliquer")
        self.apply_btn.clicked.connect(self._apply)
        t_layout.addWidget(self.apply_btn)
        layout.addWidget(theme_group)
        layout.addWidget(QLabel("Appliqué à toute l’application. Persistant dans settings.json"))

    @Slot()
    def _apply(self) -> None:
        name = "dark" if self.dark_radio.isChecked() else "light"
        apply_theme(name)
        save_theme(name)
