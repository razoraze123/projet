from PySide6.QtCore import QObject, Signal
import sys
from selenium.webdriver.common.by import By
from pathlib import Path
from ..image_scraper import scrape_images, scrape_variants
from .. import history


class _SignalStream(QObject):
    text = Signal(str)
    def write(self, s: str):
        s = (s or "").rstrip()
        if s:
            self.text.emit(s)
    def flush(self): pass


class ImageJobWorker(QObject):
    log = Signal(str)
    progress = Signal(int, int)        # done, total_urls
    item_done = Signal(str, int, dict) # url, total_images, variants
    finished = Signal()

    def __init__(self, urls, selector, folder, with_variants: bool):
        super().__init__()
        self.urls = urls
        self.selector = selector
        self.folder = folder or "images"
        self.with_variants = with_variants

    def run(self):
        # capture prints du scraper
        stream = _SignalStream()
        stream.text.connect(self.log.emit)
        old_stdout = sys.stdout
        sys.stdout = stream
        try:
            tot = len(self.urls)
            for i, url in enumerate(self.urls, 1):
                try:
                    if self.with_variants:
                        total, driver = scrape_images(url, self.selector, self.folder, keep_driver=True)
                        try:
                            _ = driver.find_element(By.TAG_NAME, "h1")  # warmup
                        except Exception:
                            pass
                        variants = scrape_variants(driver)
                        driver.quit()
                    else:
                        total = scrape_images(url, self.selector, self.folder)
                        variants = {}
                    history.log_scrape(url, self.selector, total, self.folder)
                    self.item_done.emit(url, total, variants)
                except Exception as e:
                    self.log.emit(f"❌ Erreur sur {url}: {e}")
                self.progress.emit(i, tot)
        finally:
            sys.stdout = old_stdout
            self.finished.emit()
