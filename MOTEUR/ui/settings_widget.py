from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QPushButton,
)
from PySide6.QtCore import Slot

from .theme import load_theme, save_theme, apply_theme


class SettingsWidget(QWidget):
    """General application settings."""

    def __init__(self) -> None:
        super().__init__()

        self.light_radio = QRadioButton("Clair")
        self.dark_radio = QRadioButton("Sombre")

        current = load_theme()
        (self.dark_radio if current == "dark" else self.light_radio).setChecked(True)

        self.light_radio.toggled.connect(lambda _: self._apply())
        self.dark_radio.toggled.connect(lambda _: self._apply())

        self.apply_btn = QPushButton("Appliquer")
        self.apply_btn.clicked.connect(self._apply)

        radios = QHBoxLayout()
        radios.addWidget(self.light_radio)
        radios.addWidget(self.dark_radio)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Thème de l’application"))
        layout.addLayout(radios)
        layout.addWidget(self.apply_btn)
        layout.addWidget(
            QLabel(
                "Appliqué à toute l’application. Persistant dans settings.json"
            )
        )

    @Slot()
    def _apply(self) -> None:
        name = "dark" if self.dark_radio.isChecked() else "light"
        apply_theme(name)
        save_theme(name)
