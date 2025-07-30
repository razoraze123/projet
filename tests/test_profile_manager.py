from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pytest

from MOTEUR.scraping import profile_manager as pm


def test_load_profiles_empty(tmp_path: Path):
    pm.PROFILES_FILE = tmp_path / "profiles.json"
    assert pm.load_profiles() == []


def test_add_update_delete_profile(tmp_path: Path):
    pm.PROFILES_FILE = tmp_path / "profiles.json"

    # Add a profile
    pm.add_profile("test", ".selector")
    profiles = pm.load_profiles()
    assert profiles == [{"name": "test", "selector": ".selector"}]

    # Update the profile
    updated = pm.update_profile("test", "div.img")
    assert updated is True
    profiles = pm.load_profiles()
    assert profiles[0]["selector"] == "div.img"

    # Delete the profile
    removed = pm.delete_profile("test")
    assert removed is True
    assert pm.load_profiles() == []

    # Update/delete non-existing returns False
    assert pm.update_profile("missing", "x") is False
    assert pm.delete_profile("missing") is False
