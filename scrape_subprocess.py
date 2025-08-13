import sys
import json
from pathlib import Path
from selenium.webdriver.common.by import By

from MOTEUR.scraping.image_scraper import scrape_images, scrape_variants
from MOTEUR.scraping import history


def main():
    if len(sys.argv) < 5:
        print(json.dumps({"event": "error", "msg": "missing args"}), flush=True)
        return
    cfg = {
        "input": sys.argv[1],
        "selector": sys.argv[2],
        "folder": sys.argv[3],
        "with_variants": sys.argv[4] == "1",
    }
    print(json.dumps({"event": "start", "cfg": cfg}), flush=True)
    urls = [u.strip() for u in Path(cfg["input"]).read_text(encoding="utf-8").splitlines() if u.strip()]
    total_urls = len(urls)
    for i, url in enumerate(urls, 1):
        try:
            if cfg["with_variants"]:
                count, driver = scrape_images(url, cfg["selector"], cfg["folder"], keep_driver=True)
                try:
                    driver.find_element(By.TAG_NAME, "h1")
                except Exception:
                    pass
                variants = scrape_variants(driver)
                driver.quit()
            else:
                count = scrape_images(url, cfg["selector"], cfg["folder"])
                variants = {}
            history.log_scrape(url, cfg["selector"], count, cfg["folder"])
            print(json.dumps({"event": "item", "url": url, "total": count, "variants": variants}), flush=True)
        except Exception as e:
            print(json.dumps({"event": "log", "msg": f"Erreur sur {url}: {e}"}), flush=True)
        print(json.dumps({"event": "progress", "done": i, "total": total_urls}), flush=True)
    print(json.dumps({"event": "done", "total": total_urls}), flush=True)


if __name__ == "__main__":
    main()
