import json
from typing import Any


class SettingsManager:
    """Simple JSON-backed settings manager."""

    def __init__(self, path: str = "settings.json") -> None:
        self.path = path
        self._settings: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._settings = json.load(f)
        except FileNotFoundError:
            self._settings = {}

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value


def apply_settings(widget: Any, manager: SettingsManager) -> None:
    """Apply stored settings to the given widget.

    This is a placeholder implementation. Extend as needed to apply
    geometry, state or other settings specific to your application.
    """
    geometry = manager.get("geometry")
    if geometry and hasattr(widget, "restoreGeometry"):
        widget.restoreGeometry(bytes.fromhex(geometry))

