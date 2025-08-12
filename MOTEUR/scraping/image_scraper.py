import os
import re
import time
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin, urlparse, unquote
import unicodedata

from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

UPLOADS_BASE_URL = "https://www.planetebob.fr/wp-content/uploads/"


def build_uploads_url(
    product_slug: str, variant_slug: str, *, year=None, month=None
) -> str:
    if year is None or month is None:
        now = datetime.now()
        year, month = now.year, now.month
    return f"{UPLOADS_BASE_URL}{year}/{month:02d}/{product_slug}-{variant_slug}.jpg"


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
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"-\d+$", "", stem)
    name = f"{stem}{ext}"
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


def scrape_images(
    page_url: str,
    selector: str,
    folder: str | Path = "images",
    *,
    keep_driver: bool = False,
) -> int | tuple[int, webdriver.Chrome]:
    """Download images from ``page_url`` into a subfolder of ``folder``.

    The subfolder name is derived from the URL's last path segment. When
    ``keep_driver`` is ``True``, the Selenium driver is returned alongside the
    image count and left open for further processing by the caller.
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
        if not keep_driver:
            driver.quit()

    base_dir = Path(folder)
    images_dir = base_dir / _folder_from_url(page_url)
    images_dir.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(urls, 1):
        print(f"T\u00e9l\u00e9chargement de l'image n\u00b0{i}/{total}")
        _download(url, images_dir)
    print("\u2705 Termin\u00e9")

    if keep_driver:
        return total, driver
    return total


def scrape_variants(driver: webdriver.Chrome) -> dict[str, str]:
    """Extract product variant names and associated image URLs using ``driver``.

    ``driver`` must already be on the product page. Each variant input is
    expected inside the ``.variant-picker__option-values`` container.  The
    function clicks on each corresponding label, waits for the main product
    image to update and collects the resulting URL.
    """

    mapping: dict[str, str] = {}

    def _slugify(text: str) -> str:
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text).strip("-")
        return text.lower()

    product_path = unquote(urlparse(driver.current_url).path).rstrip("/")
    product_name = Path(product_path).name
    product_slug = _slugify(product_name)

    def _img_url(el):
        return (
            el.get_attribute("src")
            or el.get_attribute("data-photoswipe-src")
            or el.get_attribute("data-src")
        )

    selectors = [
        ".woocommerce-product-gallery__image img",
        ".product-media img",
        ".product-image img",
        ".product-gallery img",
        ".product-main img",
    ]

    def _find_main_image() -> WebElement | None:
        for sel in selectors + ["img"]:
            try:
                img = driver.find_element(By.CSS_SELECTOR, sel)
                if img.is_displayed():
                    return img
            except Exception:
                continue
        return None

    try:
        inputs = driver.find_elements(
            By.CSS_SELECTOR, ".variant-picker__option-values input[type='radio']"
        )
        if not inputs:
            return mapping

        main_img = _find_main_image()
        if main_img is None:
            return mapping

        for inp in inputs:
            value = inp.get_attribute("value") or inp.get_attribute("data-value")
            input_id = inp.get_attribute("id")
            label = None
            if input_id:
                try:
                    label = driver.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                except Exception:
                    label = None
            if label is None:
                try:
                    label = inp.find_element(By.XPATH, "following-sibling::label[1]")
                except Exception:
                    continue

            previous = _img_url(main_img)
            driver.execute_script("arguments[0].click()", label)
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: (_img_url(_find_main_image()) or "") != (previous or "")
                )
            except Exception:
                pass

            new_img = _find_main_image() or main_img
            main_img = new_img
            if value:
                variant_slug = _slugify(value)
                url = build_uploads_url(product_slug, variant_slug)
                mapping[value] = url
    except Exception as exc:
        print(f"⚠️ Erreur lors du scraping des variantes: {exc}")

    return mapping


if __name__ == "__main__":
    scrape_images("https://exemple.com/produit", ".product-image img")
