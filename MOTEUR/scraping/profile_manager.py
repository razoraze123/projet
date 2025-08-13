import json
from pathlib import Path
from typing import List, Dict
from log_safe import open_utf8

# Path to the JSON file storing profiles. By default it is located at the
# project root but can be overridden in tests by changing this variable.
PROFILES_FILE = Path(__file__).resolve().parents[2] / "profiles.json"


def load_profiles() -> List[Dict[str, str]]:
    """Load scraping profiles from :data:`PROFILES_FILE`.

    Returns an empty list if the file does not exist or is empty.
    """
    if not PROFILES_FILE.exists():
        return []
    try:
        with open_utf8(PROFILES_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
    except Exception:
        pass
    return []


def save_profiles(profiles: List[Dict[str, str]]) -> None:
    """Write ``profiles`` to :data:`PROFILES_FILE` in JSON format."""
    with open_utf8(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)


def add_profile(name: str, selector: str) -> None:
    """Add a new profile with ``name`` and ``selector``.

    Raises ``ValueError`` if a profile with the same name already exists.
    """
    profiles = load_profiles()
    if any(p.get("name") == name for p in profiles):
        raise ValueError(f"Profile '{name}' already exists")
    profiles.append({"name": name, "selector": selector})
    save_profiles(profiles)


def update_profile(name: str, selector: str) -> bool:
    """Update an existing profile's selector.

    Returns ``True`` if the profile was updated, ``False`` otherwise.
    """
    profiles = load_profiles()
    updated = False
    for profile in profiles:
        if profile.get("name") == name:
            profile["selector"] = selector
            updated = True
            break
    if updated:
        save_profiles(profiles)
    return updated


def delete_profile(name: str) -> bool:
    """Delete the profile with ``name``.

    Returns ``True`` if the profile was removed, ``False`` otherwise.
    """
    profiles = load_profiles()
    new_profiles = [p for p in profiles if p.get("name") != name]
    if len(new_profiles) == len(profiles):
        return False
    save_profiles(new_profiles)
    return True
