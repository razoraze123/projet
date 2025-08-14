import os
import re
import time
import itertools
import math
import json
from pathlib import Path
from typing import Any, Callable, List, Set
from urllib.parse import urljoin, urlparse, unquote
from io import BytesIO
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress

from datetime import datetime

try:
    from localapp.log_safe import print_safe
except ImportError:
    from log_safe import print_safe

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

try:
    from PIL import Image  # pour conversion WEBP (déjà utilisée)
except Exception:
    Image = None

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# -------------------- Performance & comportement (env overrides) --------------------
STATIC_SCRAPE_FIRST = bool(int(os.getenv("STATIC_SCRAPE_FIRST", "1")))   # tenter requests+BS4 avant Selenium
REQUEST_TIMEOUT     = float(os.getenv("REQUEST_TIMEOUT", "6"))           # sec
REQUEST_RETRIES     = int(os.getenv("REQUEST_RETRIES", "2"))
DOWNLOAD_MAX_WORKERS= int(os.getenv("DOWNLOAD_MAX_WORKERS", "6"))        # parallélisme téléchargement
MAX_IMAGES_PER_PRODUCT = int(os.getenv("MAX_IMAGES_PER_PRODUCT", "6"))   # limite utile (1 principale + up to 5)

SCROLL_STEP_PX      = int(os.getenv("SCROLL_STEP_PX", "1000"))
SCROLL_PAUSE        = float(os.getenv("SCROLL_PAUSE", "0.10"))           # sec
SCROLL_MAX_SEC      = float(os.getenv("SCROLL_MAX_SEC", "8"))            # stop hard après X s
SLIDER_CLICK_DELAY  = float(os.getenv("SLIDER_CLICK_DELAY", "0.20"))     # sec

# Conversion WEBP (déjà ajoutée précédemment)
FORCE_WEBP: bool = bool(int(os.getenv("SCRAPER_FORCE_WEBP", "1")))
WEBP_QUALITY: int = int(os.getenv("SCRAPER_WEBP_QUALITY", "90"))
WEBP_LOSSLESS: bool = bool(int(os.getenv("SCRAPER_WEBP_LOSSLESS", "0")))
WEBP_METHOD: int = int(os.getenv("SCRAPER_WEBP_METHOD", "4"))         # 4 pour alléger le CPU

UPLOADS_BASE_URL = "https://www.planetebob.fr/wp-content/uploads/"


def _make_http_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=REQUEST_RETRIES,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    return s


_DROP_PATTERNS = (
    "-150x150", "-300x300", "-600x600",  # tailles WP courantes
    "thumbnail", "thumb", "mini", "small",
)


def _is_useful_image_url(u: str) -> bool:
    if not u:
        return False
    lu = u.lower()
    if any(p in lu for p in _DROP_PATTERNS):
        return False
    if lu.startswith("data:") or lu.endswith(".svg"):
        return False
    return True


def _collect_images_static(url: str, selector: str | None, session: requests.Session) -> list[str]:
    """Retourne une liste d'URLs d'images en mode statique (sans JS).
    Si selector est donné, on l'applique; sinon heuristique pour WooCommerce."""
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception:
        return []
    html = r.text
    with suppress(Exception):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        nodes = []
        if selector:
            nodes = soup.select(selector)
        else:
            nodes = soup.select(
                ".woocommerce-product-gallery__image a, .product__media a, a[href$='.jpg'], a[href$='.webp'], img[src]"
            )
        urls = []
        for n in nodes:
            href = n.get("href") or n.get("src") or ""
            if href and _is_useful_image_url(href):
                urls.append(href)
        return list(dict.fromkeys(urls))
    return []


def _scroll_quick(driver):
    import time as _time

    start = _time.perf_counter()
    last_h = 0
    while True:
        driver.execute_script(f"window.scrollBy(0, {SCROLL_STEP_PX});")
        _time.sleep(SCROLL_PAUSE)
        h = driver.execute_script("return document.body.scrollHeight")
        if h == last_h:
            break
        last_h = h
        if _time.perf_counter() - start > SCROLL_MAX_SEC:
            break


def _try_slider_clicks(driver, dots_selector: str):
    import time as _time

    with suppress(Exception):
        dots = driver.find_elements("css selector", dots_selector)
        for d in dots[:8]:
            with suppress(Exception):
                d.click()
                _time.sleep(SLIDER_CLICK_DELAY)


def _collect_images_selenium(driver, url: str, selector: str | None) -> list[str]:
    driver.get(url)
    _scroll_quick(driver)
    if selector:
        nodes = driver.find_elements("css selector", selector)
    else:
        nodes = driver.find_elements(
            "css selector", ".woocommerce-product-gallery__image a, .product__media a, img"
        )
    urls = []
    for el in nodes:
        href = ""
        with suppress(Exception):
            href = el.get_attribute("href") or el.get_attribute("src") or ""
        if href and _is_useful_image_url(href):
            urls.append(href)
    _try_slider_clicks(driver, ".flickity-page-dots .dot")
    return list(dict.fromkeys(urls))

def build_uploads_url(
    product_slug: str,
    variant_slug: str,
    *,
    year=None,
    month=None,
    ext: str | None = None,
) -> str:
    if year is None or month is None:
        now = datetime.now()
        year, month = now.year, now.month
    # Détermine l'extension par défaut selon le feature flag, sans casser les appels existants.
    if ext is None:
        ext = ".webp" if FORCE_WEBP else ".jpg"
    if not ext.startswith("."):
        ext = "." + ext
    return f"{UPLOADS_BASE_URL}{year}/{month:02d}/{product_slug}-{variant_slug}{ext}"


def _create_driver(user_agent: str = DEFAULT_USER_AGENT) -> ChromeDriver:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument(f"--user-agent={user_agent}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    opts.page_load_strategy = "eager"

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
    )
    return driver


def _scroll_page(driver: ChromeDriver, pause: float = 0.5) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")
    position = 0
    while position < last_height:
        position += 600
        driver.execute_script(f"window.scrollTo(0, {position});")
        time.sleep(pause)
        last_height = driver.execute_script("return document.body.scrollHeight")


def infer_pagination_template(url: str) -> tuple[str | None, int]:
    """
    Retourne (template, start_page) si détecté, sinon (None, 1).
    """
    m = re.search(r"([?&](?:page|paged)=(\d+))", url)
    if m:
        full, num = m.groups()
        tpl = url.replace(full, full.split("=")[0] + "={page}")
        return tpl, int(num)
    m = re.search(r"/page/(\d+)", url)
    if m:
        num = m.group(1)
        tpl = re.sub(r"/page/\d+", "/page/{page}", url)
        return tpl, int(num)
    return None, 1


def generate_page_urls(template: str, start: int, end: int) -> list[str]:
    return [template.replace("{page}", str(i)) for i in range(start, end + 1)]


def find_next_link(driver) -> str | None:
    selectors = [
        "a[rel='next']",
        "link[rel='next']",
        "nav .pagination a.next",
        ".pagination [aria-label*='Suivant']",
        ".pagination [aria-label*='Next']",
        "a.next",
    ]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            href = (el.get_attribute("href") or "").strip()
            if href:
                if href.startswith("/"):
                    return urljoin(driver.current_url, href)
                return href
        except Exception:
            continue
    return None


def scrape_collection_products_paginated(
    page_urls: list[str],
    on_driver_ready: Callable[[Any], None],
    is_cancelled: Callable[[], bool],
    log: Callable[[str], None] | None,
    link_cb: Callable[[str], None] | None,
    page_cb: Callable[[int, int, int, int], None] | None = None,
    *,
    auto_follow: bool = False,
    max_pages: int = 20,
) -> list[str]:
    """
    Parcourt chaque URL de collection, extrait les liens produits (href),
    déduplique globalement, annulation coopérative.
    """
    driver = _create_driver()
    on_driver_ready(driver)
    seen: set[str] = set()
    try:
        idx = 0
        while idx < len(page_urls):
            if is_cancelled():
                raise RuntimeError("cancelled")
            url = page_urls[idx]
            driver.get(url)
            if log:
                log(f"📄 {idx+1}/{len(page_urls)} — {url}")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "product-card,.product-card,[data-product-card],ul#product-grid li,.collection .grid .grid__item",
                    )
                )
            )
            _scroll_page(driver, pause=0.5)

            for _ in range(3):
                if is_cancelled():
                    raise RuntimeError("cancelled")
                try:
                    btn = driver.find_element(
                        By.CSS_SELECTOR,
                        "button#product-grid-load-more,a.load-more,button.load-more",
                    )
                    if not btn.is_displayed() or not btn.is_enabled():
                        break
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.8)
                    _scroll_page(driver, pause=0.3)
                except Exception:
                    break

            cards = driver.find_elements(
                By.CSS_SELECTOR,
                "product-card,.product-card,[data-product-card],ul#product-grid li,.collection .grid .grid__item",
            )
            before = len(seen)
            for card in cards:
                if is_cancelled():
                    raise RuntimeError("cancelled")
                a = None
                for sel in (
                    ".product-card__title a",
                    "a[href^='/products/']",
                    "a.card-information__link",
                ):
                    try:
                        a = card.find_element(By.CSS_SELECTOR, sel)
                        break
                    except Exception:
                        continue
                if not a:
                    continue
                href = (
                    a.get_attribute("href")
                    or a.get_attribute("data-href")
                    or ""
                ).strip()
                if href.startswith("/"):
                    href = urljoin(url, href)
                if href.startswith("http") and href not in seen:
                    seen.add(href)
                    if link_cb:
                        link_cb(href)
            new = len(seen) - before
            if page_cb:
                page_cb(idx + 1, len(page_urls), new, len(seen))

            idx += 1
            if auto_follow and len(page_urls) < max_pages:
                nxt = find_next_link(driver)
                if nxt and nxt not in page_urls:
                    page_urls.append(nxt)

        return sorted(seen)
    except Exception as exc:
        if str(exc) == "cancelled":
            raise
        raise RuntimeError(f"paginated scrape failed: {exc}") from exc
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def scrape_collection_products_cancelable(
    page_url: str,
    on_driver_ready: Callable[[Any], None],
    is_cancelled: Callable[[], bool],
    log: Callable[[str], None] | None = None,
) -> list[tuple[str, str]]:
    """
    Variante annulable. on_driver_ready(driver) est appelé après création.
    is_cancelled() est consulté régulièrement (avant/pendant les waits, boucles, scrolls).
    """
    driver = _create_driver()
    if on_driver_ready:
        on_driver_ready(driver)
    try:
        out: list[tuple[str, str]] = []

        if is_cancelled():
            raise RuntimeError("cancelled")
        driver.set_page_load_timeout(25)
        driver.get(page_url)
        if log:
            log("🌐 Page chargée.")

        selectors = [
            "product-card, .product-card",
            "[data-product-card]",
            "ul#product-grid li, .collection .grid .grid__item",
        ]
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ",".join(selectors)))
        )

        if is_cancelled():
            raise RuntimeError("cancelled")
        _scroll_page(driver, pause=0.5)

        clicks = 0
        while clicks < 5:
            if is_cancelled():
                raise RuntimeError("cancelled")
            try:
                load_more = driver.find_element(
                    By.CSS_SELECTOR,
                    "button#product-grid-load-more, a.load-more, button.load-more",
                )
                if not load_more.is_displayed() or not load_more.is_enabled():
                    break
                driver.execute_script("arguments[0].click();", load_more)
                clicks += 1
                if log:
                    log(f"↻ Voir plus… ({clicks})")
                time.sleep(1.0)
                _scroll_page(driver, pause=0.3)
            except Exception:
                break

        if is_cancelled():
            raise RuntimeError("cancelled")
        cards = driver.find_elements(By.CSS_SELECTOR, ",".join(selectors))

        for card in cards:
            if is_cancelled():
                raise RuntimeError("cancelled")
            a = None
            for sel in (
                ".product-card__title a",
                "a[href^='/products/']",
                "a.card-information__link",
            ):
                try:
                    a = card.find_element(By.CSS_SELECTOR, sel)
                    if a:
                        break
                except Exception:
                    continue
            if not a:
                continue
            name = (a.text or "").strip()
            href = (a.get_attribute("href") or a.get_attribute("data-href") or "").strip()
            if href.startswith("/"):
                href = urljoin(page_url, href)
            if name and href and href.startswith("http"):
                out.append((name, href))

        unique: list[tuple[str, str]] = []
        seen: set[str] = set()
        for name, href in out:
            if href not in seen:
                seen.add(href)
                unique.append((name, href))
        return unique
    except Exception as exc:
        if str(exc) == "cancelled":
            raise
        raise RuntimeError(
            f"scrape_collection_products failed for '{page_url}': {exc}"
        ) from exc
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def scrape_collection_products(page_url: str) -> list[tuple[str, str]]:
    return scrape_collection_products_cancelable(page_url, lambda d: None, lambda: False, None)


def _simulate_slider_interaction(driver: ChromeDriver) -> None:
    try:
        dots = driver.find_elements(By.CSS_SELECTOR, ".flickity-page-dots .dot")
        for i, dot in enumerate(dots):
            driver.execute_script("arguments[0].click();", dot)
            print_safe(f"🟡 Clic sur le point {i+1}/{len(dots)}")
            time.sleep(1.2)
    except Exception as e:
        print_safe(f"⚠️ Aucun slider détecté ou erreur : {e}")


def _extract_urls(driver: ChromeDriver, selector: str) -> List[str]:
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


def _download(url: str, folder: Path, session: requests.Session | None = None) -> None:
    if url.startswith("data:image"):
        print_safe(f"\u26A0\uFE0F Ignoré (image base64) : {url[:50]}...")
        return

    try:
        s = session or _make_http_session()
        resp = s.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        # Vérifie que la réponse est bien une image
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            print_safe(f"\u274c Mauvais type de contenu pour {url}: {content_type}")
            return

        # Ignore les contenus vides ou trop petits pour être une image réelle
        if not resp.content or len(resp.content) < 100:
            print_safe(f"\u26A0\uFE0F Réponse vide ou suspecte pour {url}")
            return

    except Exception as exc:
        print_safe(f"\u274c Erreur lors du téléchargement de {url}: {exc}")
        return

    # --- Normalisation du nom et de l'extension ---
    orig_name = os.path.basename(url.split("?")[0]) or "image"
    stem, orig_ext = os.path.splitext(orig_name)
    stem = re.sub(r"-\d+$", "", stem)  # nettoie suffixes type "-409"

    # Choix de l'extension cible
    target_ext = ".webp" if FORCE_WEBP else (orig_ext or ".jpg")
    path = folder / f"{stem}{target_ext}"
    base, _ = os.path.splitext(path)
    idx = 1
    while path.exists():
        path = Path(f"{base}_{idx}{target_ext}")
        idx += 1

    # Récupération du Content-Type pour fallback intelligent
    content_type = resp.headers.get("Content-Type", "").lower()

    if FORCE_WEBP:
        if Image is None:
            print_safe("⚠️ Pillow non installé : conversion WEBP impossible, écriture brute à l’extension source.")
            # fallback : on écrit le flux tel quel avec l’extension d’origine si dispo, sinon .jpg
            raw_ext = orig_ext if orig_ext else ".jpg"
            raw_path = folder / f"{stem}{raw_ext}"
            raw_base, _ = os.path.splitext(raw_path)
            i = 1
            while raw_path.exists():
                raw_path = Path(f"{raw_base}_{i}{raw_ext}")
                i += 1
            with open(raw_path, "wb") as f:
                f.write(resp.content)
            return

        try:
            im = Image.open(BytesIO(resp.content))
            # Normalise le mode couleur pour éviter les erreurs d’enregistrement
            if im.mode in ("P", "LA"):
                im = im.convert("RGBA")
            elif im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")

            save_kwargs = {"format": "WEBP", "method": WEBP_METHOD}
            if WEBP_LOSSLESS:
                save_kwargs.update(lossless=True, quality=100)
            else:
                save_kwargs.update(quality=WEBP_QUALITY)
            im.save(path, **save_kwargs)
        except Exception as e:
            # Fallback: si la source était déjà webp ou que Pillow échoue, écrit brut
            if "image/webp" in content_type or (orig_ext.lower() == ".webp"):
                with open(path, "wb") as f:
                    f.write(resp.content)
            else:
                print_safe(f"❌ Erreur conversion WEBP pour {url}: {e}")
                # ne pas lever d’exception dure : on log et on continue le lot
                return
    else:
        # Mode legacy : écrit tel quel
        with open(path, "wb") as f:
            f.write(resp.content)


def download_many(urls: list[str], folder: Path, session: requests.Session | None = None):
    if not urls:
        return
    folder.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=DOWNLOAD_MAX_WORKERS) as ex:
        futures = [ex.submit(_download, u, folder, session) for u in urls]
        for _ in as_completed(futures):
            pass

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


def scrape_images(urls: list[str], selector: str | None, folder: Path) -> None:
    session = _make_http_session()
    driver = None
    try:
        for url in urls:
            images: list[str] = []
            if STATIC_SCRAPE_FIRST:
                images = _collect_images_static(url, selector, session)
            if not images:
                if driver is None:
                    driver = _create_driver()
                images = _collect_images_selenium(driver, url, selector)
            images = [u for u in images if _is_useful_image_url(u)]
            images = list(dict.fromkeys(images))[:MAX_IMAGES_PER_PRODUCT]
            dest = Path(folder) / _folder_from_url(url)
            download_many(images, dest, session=session)
    finally:
        if driver is not None:
            with suppress(Exception):
                driver.quit()


def scrape_variants(driver: ChromeDriver) -> dict[str, str]:
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
        print_safe(f"⚠️ Erreur lors du scraping des variantes: {exc}")

    return mapping


if __name__ == "__main__":
    scrape_images("https://exemple.com/produit", ".product-image img")
