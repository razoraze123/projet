from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from MOTEUR.scraping.image_scraper import _download


class DummyResponse:
    def __init__(self):
        from PIL import Image
        from io import BytesIO

        buf = BytesIO()
        Image.new("RGB", (50, 50), "white").save(buf, format="PNG")
        self.content = buf.getvalue()
        self.headers = {"Content-Type": "image/png"}

    def raise_for_status(self):
        pass


class DummySession:
    def get(self, url, timeout):
        return DummyResponse()


def test_download_name_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRAPER_FORCE_WEBP", "1")
    monkeypatch.setattr(
        "MOTEUR.scraping.image_scraper._make_http_session",
        lambda: DummySession(),
    )

    url1 = "http://example.com/bob-avec-lacet-409.jpg"
    url2 = "http://example.com/bob-avec-lacet-1023.jpg"
    _download(url1, tmp_path)
    _download(url2, tmp_path)

    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["bob-avec-lacet.webp", "bob-avec-lacet_1.webp"]

