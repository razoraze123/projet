import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal


class BaseWorker(QThread):
    log = Signal(str)

    def run(self) -> None:
        self.log.emit("Operation started (stub)...")
        time.sleep(1)
        self.log.emit("Operation finished (stub)")


class ScrapLienWorker(BaseWorker):
    def __init__(self, url: str, output: Path, selector: str, log_level: str, fmt: str) -> None:
        super().__init__()
        self.url = url
        self.output = output


class ScraperImagesWorker(BaseWorker):
    progress = Signal(int, int)
    preview_path = Signal(str)

    def __init__(self, urls: list[str], dest: Path, selector: str, open_folder: bool, show_preview: bool, alt_json: str | None, threads: int) -> None:
        super().__init__()
        self.urls = urls

    def run(self) -> None:
        total = len(self.urls)
        for i, _ in enumerate(self.urls, 1):
            self.log.emit(f"Downloading image {i}/{total} (stub)")
            self.progress.emit(i, total)
            time.sleep(0.5)
        self.log.emit("Download complete (stub)")


class ScrapDescriptionWorker(BaseWorker):
    def __init__(self, url: str, selector: str, output: Path) -> None:
        super().__init__()
        self.url = url


class ScrapPriceWorker(BaseWorker):
    def __init__(self, url: str, selector: str, output: Path) -> None:
        super().__init__()
        self.url = url


class ScrapVariantWorker(BaseWorker):
    def __init__(self, url: str, selector: str, output: Path) -> None:
        super().__init__()
        self.url = url


class VariantFetchWorker(BaseWorker):
    result = Signal(str, dict)

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def run(self) -> None:
        time.sleep(1)
        self.result.emit("Product Title", {"Variant": "image.jpg"})
        self.log.emit("Variants fetched (stub)")
