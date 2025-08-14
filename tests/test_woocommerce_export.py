from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import woocommerce_export as we


def test_transform_rows_example():
    rows = [
        {"Type": "variable", "SKU": "SKU-ABC", "Name": "Bob Test", "Images": "url/beige.jpg, url/noir.jpg"},
        {"Type": "variation", "SKU": "SKU-ABC-beige", "Name": "Bob Test Beige", "Images": "url/beige.jpg"},
        {"Type": "variation", "SKU": "SKU-ABC-noir", "Name": "Bob Test Noir", "Images": "url/noir.jpg"},
    ]

    transformed = we.transform_woocommerce_rows(rows)

    expected = [
        {
            "ID": "",
            "Type": "variable",
            "SKU": "SKU-ABC",
            "Parent": "",
            "Name": "Bob Test",
            "Published": "1",
            "Short description": "",
            "Description": "",
            "Regular price": "",
            "Sale price": "",
            "Categories": "",
            "Tags": "",
            "Images": f"url/beige.jpg{we.IMAGES_JOINER}url/noir.jpg",
            "In stock?": "yes",
            "Stock": "",
            "Tax status": "taxable",
            "Shipping class": "",
            "Attribute 1 name": "Couleur",
            "Attribute 1 value(s)": "Beige|Noir",
            "Attribute 1 visible": "1",
            "Attribute 1 global": "1",
        },
        {
            "ID": "",
            "Type": "variation",
            "SKU": "SKU-ABC-beige",
            "Parent": "SKU-ABC",
            "Name": "Bob Test Beige",
            "Published": "1",
            "Short description": "",
            "Description": "",
            "Regular price": "",
            "Sale price": "",
            "Categories": "",
            "Tags": "",
            "Images": "url/beige.jpg",
            "In stock?": "yes",
            "Stock": "",
            "Tax status": "taxable",
            "Shipping class": "",
            "Attribute 1 name": "Couleur",
            "Attribute 1 value(s)": "Beige",
            "Attribute 1 visible": "1",
            "Attribute 1 global": "1",
        },
        {
            "ID": "",
            "Type": "variation",
            "SKU": "SKU-ABC-noir",
            "Parent": "SKU-ABC",
            "Name": "Bob Test Noir",
            "Published": "1",
            "Short description": "",
            "Description": "",
            "Regular price": "",
            "Sale price": "",
            "Categories": "",
            "Tags": "",
            "Images": "url/noir.jpg",
            "In stock?": "yes",
            "Stock": "",
            "Tax status": "taxable",
            "Shipping class": "",
            "Attribute 1 name": "Couleur",
            "Attribute 1 value(s)": "Noir",
            "Attribute 1 visible": "1",
            "Attribute 1 global": "1",
        },
    ]

    assert transformed == expected


def test_export_parent_images_aggregated():
    base = "https://www.planetebob.fr/wp-content/uploads/2025/08"
    rows = [
        {
            "Type": "variable",
            "SKU": "SKU-FMMTNZTB",
            "Name": "bob avec lacet",
            "Images": f"{base}/bob-avec-lacet.webp",
            "Regular price": 29.9,
        },
        {
            "Type": "variation",
            "SKU": "SKU-FMMTNZTB-camel",
            "Name": "bob avec lacet Camel",
            "Images": f"{base}/bob-avec-lacet-camel.webp",
        },
        {
            "Type": "variation",
            "SKU": "SKU-FMMTNZTB-noir",
            "Name": "bob avec lacet Noir",
            "Images": f"{base}/bob-avec-lacet-noir.webp",
        },
    ]
    transformed = we.transform_woocommerce_rows(rows)
    parent = transformed[0]
    assert (
        parent["Images"]
        == f"{base}/bob-avec-lacet.webp{we.IMAGES_JOINER}{base}/bob-avec-lacet-camel.webp{we.IMAGES_JOINER}{base}/bob-avec-lacet-noir.webp"
    )
    assert transformed[1]["Images"] == f"{base}/bob-avec-lacet-camel.webp"


def test_variation_inherits_regular_price():
    rows = [
        {
            "Type": "variable",
            "SKU": "SKU-PRICE",
            "Name": "parent",
            "Images": "url/base.webp",
            "Regular price": 29.9,
        },
        {
            "Type": "variation",
            "SKU": "SKU-PRICE-red",
            "Name": "parent Red",
            "Images": "url/red.webp",
        },
    ]
    transformed = we.transform_woocommerce_rows(rows)
    assert transformed[1]["Regular price"] == 29.9


def test_csv_semicolon_and_quoting(tmp_path):
    base = "https://example.com"
    rows = [
        {
            "Type": "variable",
            "SKU": "SKU-CSV",
            "Name": "Parent",
            "Images": f"{base}/img1.webp",
            "Regular price": 29.9,
        },
        {
            "Type": "variation",
            "SKU": "SKU-CSV-red",
            "Name": "Parent Red",
            "Images": f"{base}/img2.webp",
        },
    ]
    transformed = we.transform_woocommerce_rows(rows)
    path = tmp_path / "out.csv"
    we.write_woocommerce_csv(transformed, path)
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    assert we.CSV_DELIM in lines[0]
    assert (
        f"\"{base}/img1.webp{we.IMAGES_JOINER}{base}/img2.webp\"" in lines[1]
    )
    assert content.count("29,9") == 2


def test_decimal_comma_toggle(tmp_path, monkeypatch):
    rows = [
        {
            "Type": "variable",
            "SKU": "SKU-DC",
            "Name": "Parent",
            "Images": "img.webp",
            "Regular price": 29.9,
        }
    ]
    monkeypatch.setattr(we, "DECIMAL_COMMA", False)
    path = tmp_path / "no_comma.csv"
    we.write_woocommerce_csv(rows, path)
    content = path.read_text(encoding="utf-8")
    assert "29.9" in content
