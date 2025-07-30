from pathlib import Path
import sys
import os
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from MOTEUR.scraping import profile_manager as pm
from MOTEUR.scraping.widgets.profile_widget import ProfileWidget


def setup_widget(tmp_path):
    pm.PROFILES_FILE = tmp_path / "profiles.json"
    pm.save_profiles([
        {"name": "p1", "selector": ".a"},
        {"name": "p2", "selector": ".b"},
    ])
    app = QApplication.instance() or QApplication([])
    widget = ProfileWidget()
    return widget


def test_load_and_select(tmp_path):
    widget = setup_widget(tmp_path)
    assert widget.profile_list.count() == 2

    chosen = []
    widget.profile_chosen.connect(lambda name: chosen.append(name))
    widget.profile_list.setCurrentRow(1)
    assert chosen == ["p2"]
    widget.close()


def test_add_and_delete(tmp_path):
    widget = setup_widget(tmp_path)
    updates = []
    widget.profiles_updated.connect(lambda: updates.append(1))

    widget.name_edit.setText("new")
    widget.selector_edit.setText(".c")
    widget.add_btn.click()
    assert widget.profile_list.count() == 3
    assert len(updates) == 1

    widget.profile_list.setCurrentRow(0)
    widget.delete_btn.click()
    assert widget.profile_list.count() == 2
    assert len(updates) == 2
    widget.close()


def test_profile_selection_updates_image_widget(tmp_path):
    """Selecting a profile should update the ImageScraperWidget."""
    from MOTEUR.scraping.widgets.image_widget import ImageScraperWidget

    pm.PROFILES_FILE = tmp_path / "profiles.json"
    pm.save_profiles([
        {"name": "p1", "selector": ".a"},
        {"name": "p2", "selector": ".b"},
    ])

    app = QApplication.instance() or QApplication([])
    profile_widget = ProfileWidget()
    image_widget = ImageScraperWidget()
    image_widget.refresh_profiles()
    profile_widget.profile_chosen.connect(image_widget.set_selected_profile)

    profile_widget.profile_list.setCurrentRow(1)
    assert image_widget.profile_combo.currentText() == "p2"
    profile_widget.close()
    image_widget.close()
