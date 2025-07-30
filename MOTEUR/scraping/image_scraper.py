import os
import re
import time
from pathlib import Path
from typing import List, Set

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _create_driver(user_agent: str = DEFAULT_USER_AGENT) -> webdriver.Chrome:
    options = Options()
    options.add_argument(f"--user-agent={user_agent}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        },
    )
    return driver


def _scroll_page(driver: webdriver.Chrome, pause: float = 0.5) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")
    position = 0
    while position < last_height:
        position += 600
        driver.execute_script(f"window.scrollTo(0, {position});")
        time.sleep(pause)
        last_height = driver.execute_script("return document.body.scrollHeight")


def _extract_urls(driver: webdriver.Chrome, selector: str) -> List[str]:
    elements = driver.find_elements(By.CSS_SELECTOR, selector)
    urls: Set[str] = set()
    for el in elements:
        src = el.get_attribute("src") or el.get_attribute("data-src")
        if src:
            urls.add(src)
            continue
        style = el.get_attribute("style") or ""
        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
        if match:
            urls.add(match.group(1))
    return list(urls)


def _download(url: str, folder: Path) -> None:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        print(f"\u274c Erreur lors du téléchargement de {url}: {exc}")
        return

    name = os.path.basename(url.split("?")[0]) or "image"
    path = folder / name
    base, ext = os.path.splitext(path)
    idx = 1
    while path.exists():
        path = Path(f"{base}_{idx}{ext}")
        idx += 1
    with open(path, "wb") as f:
        f.write(resp.content)


def scrape_images(page_url: str, selector: str) -> int:
    print("Chargement...")
    driver = _create_driver()
    try:
        driver.get(page_url)
        _scroll_page(driver)
        urls = _extract_urls(driver, selector)
        total = len(urls)
        print(f"{total} images trouv\u00e9es")
    finally:
        driver.quit()

    images_dir = Path("images")
    images_dir.mkdir(exist_ok=True)
    for i, url in enumerate(urls, 1):
        print(f"T\u00e9l\u00e9chargement de l'image n\u00b0{i}/{total}")
        _download(url, images_dir)
    print("\u2705 Termin\u00e9")
    return total


if __name__ == "__main__":
    scrape_images("https://exemple.com/produit", ".product-image img")
