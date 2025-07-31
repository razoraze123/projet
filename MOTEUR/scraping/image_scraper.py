import os
import re
import time
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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


def _simulate_slider_interaction(driver: webdriver.Chrome) -> None:
    try:
        dots = driver.find_elements(By.CSS_SELECTOR, ".flickity-page-dots .dot")
        for i, dot in enumerate(dots):
            driver.execute_script("arguments[0].click();", dot)
            print(f"🟡 Clic sur le point {i+1}/{len(dots)}")
            time.sleep(1.2)
    except Exception as e:
        print(f"⚠️ Aucun slider détecté ou erreur : {e}")


def _extract_urls(driver: webdriver.Chrome, selector: str) -> List[str]:
    elements = driver.find_elements(By.CSS_SELECTOR, selector)
    urls: Set[str] = set()

    for el in elements:
        tag = el.tag_name.lower()

        # Si c'est une balise <a>, on essaie de récupérer l'attribut href
        if tag == "a":
            href = el.get_attribute("href")
            if href and href.endswith((".jpg", ".jpeg", ".png", ".webp")):
                urls.add(href)
                continue

        # Si c'est une balise <img> ou autre avec data-photoswipe-src / src / data-src
        src = (
            el.get_attribute("data-photoswipe-src")
            or el.get_attribute("src")
            or el.get_attribute("data-src")
        )
        if src:
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(driver.current_url, src)
        if src and not src.startswith("data:image"):
            urls.add(src)
            continue

        # Vérifie aussi dans le style (cas d'image en background)
        style = el.get_attribute("style") or ""
        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
        if match:
            url = match.group(1)
            if not url.startswith("data:image"):
                urls.add(url)

    return list(urls)


def _download(url: str, folder: Path) -> None:
    if url.startswith("data:image"):
        print(f"\u26A0\uFE0F Ignoré (image base64) : {url[:50]}...")
        return

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        # Vérifie que la réponse est bien une image
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            print(f"\u274c Mauvais type de contenu pour {url}: {content_type}")
            return

        # Ignore les contenus vides ou trop petits pour être une image réelle
        if not resp.content or len(resp.content) < 100:
            print(f"\u26A0\uFE0F Réponse vide ou suspecte pour {url}")
            return

    except Exception as exc:
        print(f"\u274c Erreur lors du téléchargement de {url}: {exc}")
        return

    # Enregistrement avec gestion de collision de nom
    name = os.path.basename(url.split("?")[0]) or "image"
    path = folder / name
    base, ext = os.path.splitext(path)
    idx = 1
    while path.exists():
        path = Path(f"{base}_{idx}{ext}")
        idx += 1
    with open(path, "wb") as f:
        f.write(resp.content)


def _folder_from_url(url: str) -> Path:
    """Return a folder name derived from ``url``.

    The last segment of the path is used, hyphens are replaced with spaces and
    unsafe characters are removed.
    """
    from urllib.parse import urlparse, unquote

    path = unquote(urlparse(url).path)
    name = Path(path).name.replace("-", " ")
    # keep alphanumeric characters, spaces and underscores only
    name = re.sub(r"[^\w\s]", "", name).strip()
    return Path(name or "images")


def scrape_images(page_url: str, selector: str, folder: str | Path = "images") -> int:
    """Download images from ``page_url`` into a subfolder of ``folder``.

    The subfolder name is derived from the URL's last path segment.
    """
    print("Chargement...")
    driver = _create_driver()
    try:
        driver.get(page_url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        _simulate_slider_interaction(driver)
        _scroll_page(driver)
        urls = _extract_urls(driver, selector)
        total = len(urls)
        if total == 0:
            print(
                "⚠️ Aucune image trouvée. Vérifie si le slider charge bien dynamiquement."
            )
        else:
            print(f"{total} images trouv\u00e9es")
    finally:
        driver.quit()

    base_dir = Path(folder)
    images_dir = base_dir / _folder_from_url(page_url)
    images_dir.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(urls, 1):
        print(f"T\u00e9l\u00e9chargement de l'image n\u00b0{i}/{total}")
        _download(url, images_dir)
    print("\u2705 Termin\u00e9")
    return total


if __name__ == "__main__":
    scrape_images("https://exemple.com/produit", ".product-image img")
