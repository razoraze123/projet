from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from MOTEUR.scraping.image_scraper import _download
import types

class DummyResponse:
    def __init__(self):
        self.content = b'x' * 200
        self.headers = {'Content-Type': 'image/png'}
    def raise_for_status(self):
        pass

def test_download_name_cleanup(tmp_path, monkeypatch):
    def fake_get(url, timeout=10):
        return DummyResponse()
    monkeypatch.setattr('MOTEUR.scraping.image_scraper.requests.get', fake_get)

    url1 = 'http://example.com/bob-avec-lacet-409.jpg'
    url2 = 'http://example.com/bob-avec-lacet-1023.jpg'
    _download(url1, tmp_path)
    _download(url2, tmp_path)

    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ['bob-avec-lacet.jpg', 'bob-avec-lacet_1.jpg']

