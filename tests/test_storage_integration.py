import sys
import os
from pathlib import Path
import pytest

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from MOTEUR.scraping import profile_manager as pm, history
from MOTEUR.scraping.widgets.image_widget import ImageScraperWidget
from MOTEUR.scraping.widgets.storage_widget import StorageWidget


class DummyDriver:
    def find_element(self, by, value):
        class El:
            text = "Bob"
        return El()

    def quit(self):
        pass


def test_image_scraper_adds_to_storage(tmp_path, monkeypatch):
    pm.PROFILES_FILE = tmp_path / "profiles.json"
    history.HISTORY_FILE = tmp_path / "history.json"
    history.LAST_USED_FILE = tmp_path / "last.json"
    pm.save_profiles([{"name": "p1", "selector": ".a"}])

    app = QApplication.instance() or QApplication([])
    storage = StorageWidget()
    widget = ImageScraperWidget(storage_widget=storage)
    widget.refresh_profiles()
    widget.set_selected_profile("p1")
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text("http://example.com\n")
    widget.file_edit.setText(str(urls_file))
    widget.folder_edit.setText(str(tmp_path))
    widget.variants_checkbox.setChecked(True)

    monkeypatch.setattr(
        "MOTEUR.scraping.widgets.image_widget.scrape_images",
        lambda url, sel, folder, keep_driver=False: (0, DummyDriver()),
    )
    monkeypatch.setattr(
        "MOTEUR.scraping.widgets.image_widget.scrape_variants",
        lambda driver: {"Noir": "img1", "Beige": "img2"},
    )

    widget._start()

    assert storage.table.rowCount() == 1
    assert storage.table.item(0, 0).text() == "Bob"
    assert "Noir" in storage.table.item(0, 1).text()
    widget.close()
    storage.close()
