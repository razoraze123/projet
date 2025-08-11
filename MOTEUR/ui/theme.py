from __future__ import annotations

from pathlib import Path
import json

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor


THEME_FILE = Path(__file__).resolve().parents[2] / "settings.json"


def load_theme() -> str:
    """Return the persisted theme name ("light" or "dark")."""
    try:
        if THEME_FILE.exists():
            data = json.loads(THEME_FILE.read_text(encoding="utf-8") or "{}")
            theme = (data.get("theme") or "light").lower()
            return "dark" if theme == "dark" else "light"
    except Exception:
        pass
    return "light"


def save_theme(name: str) -> None:
    """Persist the theme name into :data:`THEME_FILE`."""
    name = "dark" if name.lower() == "dark" else "light"
    THEME_FILE.write_text(
        json.dumps({"theme": name}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#2b2b2b"))
    palette.setColor(QPalette.WindowText, QColor("#eeeeee"))
    palette.setColor(QPalette.Base, QColor("#3c3f41"))
    palette.setColor(QPalette.AlternateBase, QColor("#2f3234"))
    palette.setColor(QPalette.ToolTipBase, QColor("#2b2b2b"))
    palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
    palette.setColor(QPalette.Text, QColor("#eeeeee"))
    palette.setColor(QPalette.Button, QColor("#3c3f41"))
    palette.setColor(QPalette.ButtonText, QColor("#eeeeee"))
    palette.setColor(QPalette.BrightText, QColor("#ff6b6b"))
    palette.setColor(QPalette.Highlight, QColor("#4c78ff"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor("#62a8ff"))
    return palette


def _light_palette() -> QPalette:
    app = QApplication.instance()
    if app:
        palette = app.style().standardPalette()
    else:
        palette = QPalette()
    palette.setColor(QPalette.Highlight, QColor("#3d6cff"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor("#0b61ff"))
    return palette


def apply_theme(name: str) -> None:
    """Apply the given theme to the running :class:`QApplication`."""
    app = QApplication.instance()
    if not app:
        return
    app.setStyle("Fusion")
    if name.lower() == "dark":
        palette = _dark_palette()
        app.setPalette(palette)
        app.setStyleSheet(
            "QToolTip { color: #ffffff; background-color: #2b2b2b; border: 0px; }"
        )
    else:
        palette = _light_palette()
        app.setPalette(palette)
        app.setStyleSheet("")
