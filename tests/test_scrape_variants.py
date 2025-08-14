from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from MOTEUR.scraping import image_scraper
from MOTEUR.scraping.image_scraper import scrape_variants
from selenium.webdriver.common.by import By

class DummyElement:
    def __init__(self, attrs=None):
        self.attrs = attrs or {}
    def get_attribute(self, name):
        return self.attrs.get(name)
    def is_displayed(self):
        return True
    def find_element(self, by, value):
        # only used to get following sibling label
        return DummyElement()

class DummyDriver:
    def __init__(self, url):
        self.current_url = url
        self.inputs = [
            DummyElement({'value': 'Camel', 'id': 'v1'}),
            DummyElement({'value': 'Noir', 'id': 'v2'})
        ]
        self.label_map = { 'v1': DummyElement(), 'v2': DummyElement() }
        self.img = DummyElement({'src': 'http://x'})
    def find_elements(self, by, value):
        if value == ".variant-picker__option-values input[type='radio']":
            return self.inputs
        return []
    def find_element(self, by, value):
        if value.startswith("label[for='"):
            key = value.split("'")[1]
            return self.label_map[key]
        return self.img
    def execute_script(self, script, el):
        pass

class DummyWait:
    def __init__(self, driver, timeout):
        pass
    def until(self, method):
        method(None)


def test_scrape_variants_generate_urls(monkeypatch):
    monkeypatch.setattr('MOTEUR.scraping.image_scraper.WebDriverWait', DummyWait)
    class DummyDateTime:
        @staticmethod
        def now():
            class D:
                year = 2025
                month = 7

            return D

    monkeypatch.setattr(image_scraper, 'datetime', DummyDateTime)
    driver = DummyDriver('https://competitor.com/products/bob-avec-lacet')
    mapping = scrape_variants(driver)
    assert mapping == {
        'Camel': 'https://www.planetebob.fr/wp-content/uploads/2025/07/bob-avec-lacet-camel.webp',
        'Noir': 'https://www.planetebob.fr/wp-content/uploads/2025/07/bob-avec-lacet-noir.webp',
    }
