"""Utilities to transform WooCommerce CSV exports.

This module exposes two helpers:

- ``transform_woocommerce_rows`` converts raw exported rows into rows
  ready for import into WooCommerce. It handles parent SKU linking, color
  attributes, image cleanup and default values.
- ``write_woocommerce_csv`` writes the transformed rows to a CSV file in
  UTF-8 without BOM.

Example
=======
A minimal example with one variable product and two variations::

    >>> rows = [
    ...     {"Type": "variable", "SKU": "SKU-ABC", "Name": "Bob Test",
    ...      "Images": "url/beige.jpg, url/noir.jpg"},
    ...     {"Type": "variation", "SKU": "SKU-ABC-beige",
    ...      "Name": "Bob Test Beige", "Images": "url/beige.jpg"},
    ...     {"Type": "variation", "SKU": "SKU-ABC-noir",
    ...      "Name": "Bob Test Noir", "Images": "url/noir.jpg"},
    ... ]
    >>> transformed = transform_woocommerce_rows(rows)
    >>> [r["Parent"] for r in transformed]
    ['', 'SKU-ABC', 'SKU-ABC']
    >>> transformed[0]['Attribute 1 value(s)']
    'Beige|Noir'
    >>> transformed[1]['Attribute 1 value(s)']
    'Beige'
    >>> transformed[0]['Images']
    'url/beige.jpg;url/noir.jpg'

The resulting rows are compatible with WooCommerce's CSV importer.
"""

from __future__ import annotations

import csv
import logging
import os
import re
import unicodedata
from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List

# Columns expected by WooCommerce in the desired order.
COLUMNS: List[str] = [
    "ID",
    "Type",
    "SKU",
    "Parent",
    "Name",
    "Published",
    "Short description",
    "Description",
    "Regular price",
    "Sale price",
    "Categories",
    "Tags",
    "Images",
    "In stock?",
    "Stock",
    "Tax status",
    "Shipping class",
    "Attribute 1 name",
    "Attribute 1 value(s)",
    "Attribute 1 visible",
    "Attribute 1 global",
]

# Mapping for colour/adjective normalisation.
_ADJECTIVE_MAP = {
    "fonce": "foncé",
    "foncé": "foncé",
    "clair": "clair",
    "ciel": "ciel",
}


# Configuration constants (can be overridden via environment variables).
CSV_DELIM: str = os.getenv("CSV_DELIM", ";")
IMAGES_JOINER: str = os.getenv("IMAGES_JOINER", ";")
DECIMAL_COMMA: bool = os.getenv("DECIMAL_COMMA", "True").lower() in {
    "1",
    "true",
    "yes",
}


def _fix_encoding(text: str) -> str:
    """Return text normalised in UTF-8 NFC form.

    Many CSV exports have UTF-8 that was mistakenly decoded as latin-1,
    leading to artefacts such as ``"Bleu foncÃ©"``.  This helper attempts to
    round-trip the string to recover the proper representation and then
    normalises it.
    """
    if not isinstance(text, str):
        return text
    try:
        text = text.encode("latin1").decode("utf-8")
    except UnicodeEncodeError:
        # Already a proper unicode string.
        pass
    return unicodedata.normalize("NFC", text)


def _normalize_color(value: str) -> str | None:
    """Normalise a colour name from a slug or free text.

    Parameters
    ----------
    value:
        Raw colour value obtained from SKU or Name.
    """
    if not value:
        return None
    value = _fix_encoding(value)
    value = re.sub(r"[-_]+", " ", value).strip().lower()
    if not value:
        return None
    parts = value.split()
    normalised = []
    for i, part in enumerate(parts):
        part = _ADJECTIVE_MAP.get(part, part)
        if i == 0:
            normalised.append(part.capitalize())
        else:
            normalised.append(part.lower())
    return " ".join(normalised)


def _slugify(value: str) -> str:
    """Return a slugified version of ``value`` suitable for URLs."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value)
    return value.strip("-").lower()


def build_parent_images_cell(
    base_url: str,
    year: int,
    month: int,
    product_slug: str,
    variant_values: list[str],
    imgs_variant_map: dict[str, list[str]] | None = None,
    images_joiner: str = IMAGES_JOINER,
) -> str:
    """Return a single string for the parent ``Images`` cell.

    The resulting string starts with the generic image (if it exists) followed by
    the first image of each variant in ``variant_values``.  Duplicates and empty
    values are ignored and the URLs are joined with ``images_joiner``.
    """
    urls: List[str] = []
    generic_url = (
        f"{base_url}/wp-content/uploads/{year:04d}/{month:02d}/{product_slug}.webp"
    )
    try:  # Try to include the generic image only if it exists.
        import requests

        resp = requests.head(generic_url, timeout=5)
        if resp.status_code < 400:
            urls.append(generic_url)
    except Exception:
        # Network issues or 404 -> fall back to variants.
        pass

    for value in variant_values:
        slug = _slugify(value)
        url = None
        if imgs_variant_map and imgs_variant_map.get(slug):
            url = imgs_variant_map[slug][0]
        if not url:
            url = (
                f"{base_url}/wp-content/uploads/{year:04d}/{month:02d}/{product_slug}-{slug}.webp"
            )
        if url and url not in urls:
            urls.append(url)

    return images_joiner.join(urls)


def _extract_color(row: Dict[str, str]) -> str | None:
    """Infer the colour for a variation row.

    Tries SKU first (assuming ``parentSKU-colour`` pattern) and falls back to
    the last word of the Name field.
    """
    sku = row.get("SKU", "")
    if sku and "-" in sku:
        candidate = sku.rsplit("-", 1)[1]
        colour = _normalize_color(candidate)
        if colour:
            return colour
    name = row.get("Name", "")
    if name:
        candidate = name.split()[-1]
        colour = _normalize_color(candidate)
        if colour:
            return colour
    return None


def _clean_images(images: str, variation: bool) -> str:
    """Remove spaces around commas and keep only the main image for variations."""
    if not images:
        return ""
    urls = [u.strip() for u in images.split(",") if u.strip()]
    if variation and urls:
        urls = urls[:1]
    return ",".join(urls)


def _apply_defaults(row: Dict[str, str]) -> None:
    if not row.get("Published"):
        row["Published"] = "1"
    if not row.get("In stock?"):
        row["In stock?"] = "yes"
    if not row.get("Tax status"):
        row["Tax status"] = "taxable"


def _format_for_csv(value) -> str:
    """Format ``value`` for CSV output respecting ``DECIMAL_COMMA``."""
    if DECIMAL_COMMA:
        if isinstance(value, (float, Decimal)):
            return f"{value}".replace(".", ",")
        if isinstance(value, str) and re.match(r"^-?\d+\.\d+$", value):
            return value.replace(".", ",")
    return "" if value is None else str(value)


def transform_woocommerce_rows(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """Transform raw WooCommerce export rows.

    Parameters
    ----------
    rows:
        Iterable of dictionaries representing CSV rows.
    """
    parent_colours: Dict[str, set] = defaultdict(set)
    parent_images: Dict[str, List[str]] = defaultdict(list)
    parent_prices: Dict[str, str] = {}
    variations_needing_price: List[tuple[Dict[str, str], str]] = []
    result: List[Dict[str, str]] = []

    for row in rows:
        r = {k: _fix_encoding(v) for k, v in row.items()}
        r_type = r.get("Type", "")
        sku = r.get("SKU", "")
        r["Images"] = _clean_images(r.get("Images", ""), variation=r_type == "variation")

        if r_type == "variable":
            parent_prices[sku] = r.get("Regular price", "")
            imgs = [u for u in r["Images"].split(",") if u]
            existing = parent_images.get(sku, [])
            combined: List[str] = []
            for img in imgs + existing:
                if img and img not in combined:
                    combined.append(img)
            parent_images[sku] = combined
        elif r_type == "variation":
            parent_sku = sku.rsplit("-", 1)[0] if "-" in sku else ""
            r["Parent"] = parent_sku
            colour = _extract_color(r)
            if colour:
                r["Attribute 1 name"] = "Couleur"
                r["Attribute 1 value(s)"] = colour
                r["Attribute 1 visible"] = "1"
                r["Attribute 1 global"] = "1"
                parent_colours[parent_sku].add(colour)
            else:
                logging.warning("No colour found for variation %s", sku)
            img = r.get("Images")
            if img and img not in parent_images[parent_sku]:
                parent_images[parent_sku].append(img)
        _apply_defaults(r)
        result_row = {col: r.get(col, "") for col in COLUMNS}
        result.append(result_row)
        if r_type == "variation" and not result_row.get("Regular price"):
            variations_needing_price.append((result_row, parent_sku))

    # Populate parent attributes once all variation data are known.
    for row in result:
        if row["Type"] == "variable":
            sku = row.get("SKU", "")
            colours = parent_colours.get(sku)
            if colours:
                row["Attribute 1 name"] = "Couleur"
                row["Attribute 1 value(s)"] = "|".join(sorted(colours))
                row["Attribute 1 visible"] = "1"
                row["Attribute 1 global"] = "1"
            imgs = parent_images.get(sku)
            if imgs:
                row["Images"] = IMAGES_JOINER.join(imgs)
        for key, value in list(row.items()):
            if isinstance(value, str):
                row[key] = _fix_encoding(value)

    for row, parent_sku in variations_needing_price:
        if not row.get("Regular price"):
            row["Regular price"] = parent_prices.get(parent_sku, "")

    return result


def write_woocommerce_csv(
    rows: Iterable[Dict[str, str]],
    path: str,
    delimiter: str = CSV_DELIM,
) -> None:
    """Write transformed rows to ``path`` with UTF-8 encoding and no BOM."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=COLUMNS, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _format_for_csv(row.get(col, "")) for col in COLUMNS})
