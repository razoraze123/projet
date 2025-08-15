# --- Bootstrap UTF-8, compatible run module ET run direct ---
try:
    from localapp.utf8_bootstrap import force_utf8_stdio
except ImportError:
    from utf8_bootstrap import force_utf8_stdio
force_utf8_stdio()

# Logs robustes (print_safe)
try:
    from localapp.log_safe import print_safe, open_utf8
except ImportError:
    from log_safe import print_safe, open_utf8

import sys
import json
from pathlib import Path
from selenium.webdriver.common.by import By

from MOTEUR.scraping.image_scraper import scrape_images, scrape_variants
from MOTEUR.scraping import history


def main():
    if len(sys.argv) < 5:
        print_safe(json.dumps({"event": "error", "msg": "missing args"}))
        sys.stdout.flush()
        return
    cfg = {
        "input": sys.argv[1],
        "selector": sys.argv[2],
        "folder": sys.argv[3],
        "with_variants": sys.argv[4] == "1",
    }
    print_safe(json.dumps({"event": "start", "cfg": cfg}))
    sys.stdout.flush()
    with open_utf8(cfg["input"]) as f:
        urls = [u.strip() for u in f if u.strip()]
    total_urls = len(urls)
    for i, url in enumerate(urls, 1):
        try:
            if cfg["with_variants"]:
                total, driver = scrape_images(url, cfg["selector"], cfg["folder"], keep_driver=True)
                try:
                    driver.find_element(By.TAG_NAME, "h1")
                except Exception:
                    pass
                variants = scrape_variants(driver)
                driver.quit()
            else:
                total = scrape_images(url, cfg["selector"], cfg["folder"])
                variants = {}
            history.log_scrape(url, cfg["selector"], total, cfg["folder"])
            print_safe(json.dumps({"event": "item", "url": url, "total": total, "variants": variants}))
            sys.stdout.flush()
        except Exception as e:
            print_safe(json.dumps({"event": "log", "msg": f"Erreur sur {url}: {e}"}))
            sys.stdout.flush()
        print_safe(json.dumps({"event": "progress", "done": i, "total": total_urls}))
        sys.stdout.flush()
    print_safe(json.dumps({"event": "done", "total": total_urls}))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
