import json
from pathlib import Path


class SettingsManager:
    """Simple manager for user settings."""

    def __init__(self, path: str = "settings.json") -> None:
        self.path = Path(path)
        self.settings = {
            "button_bg_color": "#3498db",
            "button_text_color": "#ffffff",
            "theme": "light",
            "button_radius": 4,
            "lineedit_radius": 4,
            "console_radius": 4,
            "font_family": "Arial",
            "font_size": 10,
            "animations": True,
        }
        if self.path.exists():
            try:
                self.settings.update(json.loads(self.path.read_text()))
            except Exception:
                pass

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.settings, indent=2))
        except Exception:
            pass

    def save_setting(self, key: str, value) -> None:
        self.settings[key] = value
        self.save()

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
        self.__init__(self.path)


def apply_settings(app, settings: dict) -> None:
    """Apply minimal stylesheet using settings."""
    app.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {settings['button_bg_color']};
            color: {settings['button_text_color']};
            border-radius: {settings['button_radius']}px;
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{
            border-radius: {settings['lineedit_radius']}px;
        }}
        """
    )
