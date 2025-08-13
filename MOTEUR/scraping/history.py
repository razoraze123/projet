import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from log_safe import open_utf8

# Path to the history log file at project root
HISTORY_FILE = Path(__file__).resolve().parents[2] / "scraping_history.json"

# Path to file storing last used url/folder
LAST_USED_FILE = Path(__file__).resolve().parents[2] / "scraping_last_used.json"


def _read_json(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        with open_utf8(path, "r") as f:
            return json.load(f) or []
    except Exception:
        return []


def _write_json(path: Path, data) -> None:
    with open_utf8(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def log_scrape(url: str, profile: str, images: int, folder: str) -> None:
    """Append a scraping entry to :data:`HISTORY_FILE`."""
    entries = _read_json(HISTORY_FILE)
    entries.append(
        {
            "date": datetime.now().isoformat(timespec="seconds"),
            "url": url,
            "profile": profile,
            "images": images,
            "folder": folder,
        }
    )
    _write_json(HISTORY_FILE, entries)
    save_last_used(url, folder)


def load_history() -> List[Dict]:
    """Return the list of logged scraping entries."""
    return _read_json(HISTORY_FILE)


def save_last_used(url: str, folder: str) -> None:
    data = {
        "url": url,
        "folder": folder,
        "last_file": load_last_file(),
    }
    _write_json(LAST_USED_FILE, data)


def load_last_used() -> Dict[str, str]:
    if not LAST_USED_FILE.exists():
        return {"url": "", "folder": ""}
    try:
        with open_utf8(LAST_USED_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {"url": data.get("url", ""), "folder": data.get("folder", "")}
    except Exception:
        pass
    return {"url": "", "folder": ""}


def save_last_file(path: str) -> None:
    data = load_last_used()
    data["last_file"] = path or ""
    _write_json(LAST_USED_FILE, data)


def load_last_file() -> str:
    if not LAST_USED_FILE.exists():
        return ""
    try:
        with open_utf8(LAST_USED_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("last_file", "")
    except Exception:
        pass
    return ""
