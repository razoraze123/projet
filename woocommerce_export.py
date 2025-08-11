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
    'url/beige.jpg,url/noir.jpg'

The resulting rows are compatible with WooCommerce's CSV importer.
"""

from __future__ import annotations

import csv
import logging
import re
import unicodedata
from collections import defaultdict
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


def transform_woocommerce_rows(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """Transform raw WooCommerce export rows.

    Parameters
    ----------
    rows:
        Iterable of dictionaries representing CSV rows.
    """
    parent_colours: Dict[str, set] = defaultdict(set)
    result: List[Dict[str, str]] = []

    for row in rows:
        r = {k: _fix_encoding(v) for k, v in row.items()}
        r_type = r.get("Type", "")
        sku = r.get("SKU", "")
        r["Images"] = _clean_images(r.get("Images", ""), variation=r_type == "variation")

        if r_type == "variation":
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
        _apply_defaults(r)
        result.append({col: r.get(col, "") for col in COLUMNS})

    # Populate parent attributes once all variation colours are known.
    for row in result:
        if row["Type"] == "variable":
            colours = parent_colours.get(row.get("SKU", ""))
            if colours:
                row["Attribute 1 name"] = "Couleur"
                row["Attribute 1 value(s)"] = "|".join(sorted(colours))
                row["Attribute 1 visible"] = "1"
                row["Attribute 1 global"] = "1"
        for key, value in list(row.items()):
            if isinstance(value, str):
                row[key] = _fix_encoding(value)
    return result


def write_woocommerce_csv(rows: Iterable[Dict[str, str]], path: str, delimiter: str = ",") -> None:
    """Write transformed rows to ``path`` with UTF-8 encoding and no BOM."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=COLUMNS, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in COLUMNS})
