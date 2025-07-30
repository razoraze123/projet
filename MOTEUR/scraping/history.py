import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Path to the history log file at project root
HISTORY_FILE = Path(__file__).resolve().parents[2] / "scraping_history.json"

# Path to file storing last used url/folder
LAST_USED_FILE = Path(__file__).resolve().parents[2] / "scraping_last_used.json"


def _read_json(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []


def _write_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
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
    _write_json(LAST_USED_FILE, {"url": url, "folder": folder})


def load_last_used() -> Dict[str, str]:
    if not LAST_USED_FILE.exists():
        return {"url": "", "folder": ""}
    try:
        with open(LAST_USED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {"url": data.get("url", ""), "folder": data.get("folder", "")}
    except Exception:
        pass
    return {"url": "", "folder": ""}
