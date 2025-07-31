from pathlib import Path
import sys
import os
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from MOTEUR.scraping import profile_manager as pm
from MOTEUR.scraping import history
from MOTEUR.scraping.widgets.image_widget import ImageScraperWidget


def test_scrape_logs_history(tmp_path, monkeypatch):
    pm.PROFILES_FILE = tmp_path / "profiles.json"
    history.HISTORY_FILE = tmp_path / "history.json"
    history.LAST_USED_FILE = tmp_path / "last.json"
    pm.save_profiles([{"name": "p1", "selector": ".a"}])

    app = QApplication.instance() or QApplication([])
    widget = ImageScraperWidget()
    widget.refresh_profiles()
    widget.set_selected_profile("p1")
    widget.url_edit.setText("http://example.com")
    widget.folder_edit.setText(str(tmp_path))

    monkeypatch.setattr(
        "MOTEUR.scraping.widgets.image_widget.scrape_images",
        lambda url, sel, folder: 5,
    )

    widget._start()

    entries = history.load_history()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["url"] == "http://example.com"
    assert entry["profile"] == "p1"
    assert entry["images"] == 5
    widget.close()
