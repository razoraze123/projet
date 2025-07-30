import json
from pathlib import Path


class SiteProfileManager:
    """Manage site profiles for selectors."""

    def __init__(self, directory: str = "profiles") -> None:
        self.dir = Path(directory)
        self.dir.mkdir(exist_ok=True)

    def load_profile(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    def save_profile(self, path: Path, data: dict) -> None:
        try:
            path.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def apply_profile_to_ui(self, data: dict, main_window) -> None:
        """Apply selectors from profile to main window fields."""
        selectors = data.get("selectors", {})
        main_window.page_images.input_options.setText(selectors.get("images", ""))
        main_window.page_desc.input_selector.setText(selectors.get("description", ""))
        main_window.page_scrap.input_selector.setText(selectors.get("collection", ""))
        main_window.page_price.input_selector.setText(selectors.get("price", ""))

    def detect_and_apply(self, url: str, main_window) -> None:
        """Dummy detection that does nothing in this stub."""
        pass
