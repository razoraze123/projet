# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QFile, QIODevice, QSettings
from PySide6.QtGui import QFontDatabase, QPalette, QColor


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(self, app, *, org="app", name="ui"):
        super().__init__()
        self.app = app
        self.settings = QSettings(org, name)
        self._theme = self.settings.value("theme", "dark")
        self._ensure_font()
        self.apply(self._theme)

    def _ensure_font(self):
        try:
            QFontDatabase.addApplicationFont(":/fonts/Inter-Regular.ttf")
        except Exception:
            pass

    def _load_qss(self, path: str) -> str:
        """
        Charge un fichier QSS en UTF-8.
        - Tente d'abord la ressource Qt (ex: :/themes/dark.qss)
        - Si absente, fallback vers un fichier sur disque: <dir>/themes/<name>.qss
        """
        # 1) Essai via ressource Qt
        f = QFile(path)
        if f.exists():
            if not f.open(QIODevice.ReadOnly | QIODevice.Text):
                return ""
            try:
                # Qt6: plus de setCodec; on lit les octets et on décode nous-mêmes
                data = f.readAll()              # QByteArray
                qss = bytes(data).decode("utf-8", errors="replace")
                return qss
            finally:
                f.close()

        # 2) Fallback fichier local (même nom que la ressource)
        name = Path(path).name  # ex: 'dark.qss' ou 'light.qss'
        local = Path(__file__).resolve().parent / "themes" / name
        if local.exists():
            return local.read_text(encoding="utf-8", errors="replace")

        return ""

    def apply(self, theme: str):
        qss = self._load_qss(f":/themes/{'dark' if theme=='dark' else 'light'}.qss")
        self.app.setStyleSheet(qss)
        pal = QPalette()
        if theme == "dark":
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#3f8cff"))
            pal.setColor(QPalette.ColorRole.Window, QColor("#0f1115"))
            pal.setColor(QPalette.ColorRole.WindowText, QColor("#e7eaf0"))
        else:
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#2463eb"))
            pal.setColor(QPalette.ColorRole.Window, QColor("#f7f8fb"))
            pal.setColor(QPalette.ColorRole.WindowText, QColor("#0e1726"))
        self.app.setPalette(pal)
        self._theme = theme
        self.settings.setValue("theme", theme)
        self.theme_changed.emit(theme)

    def toggle(self):
        self.apply("light" if self._theme == "dark" else "dark")

    @property
    def current(self) -> str:
        return self._theme
