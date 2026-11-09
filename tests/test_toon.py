"""`.toon` parser tests."""

from pathlib import Path

from isis_report_lib.toon import ToonParser, parse_toon

parser = ToonParser()


def test_simple_key_value():
    assert parser.parse("title: Hello") == {"title": "Hello"}


def test_type_coercion():
    result = parser.parse("a: 1\nb: 2.5\nc: true\nd: false\ne: text")
    assert result == {"a": 1, "b": 2.5, "c": True, "d": False, "e": "text"}


def test_compact_layout_field():
    result = parser.parse("layout:\n  product{Product,str,left}")
    assert result["layout"]["product"] == {"label": "Product", "format_mask": "str", "alignment": "left"}


def test_compact_array_of_objects():
    result = parser.parse("items[2]{qty,price}:\n  1,1500\n  2,1000")
    assert result["items"] == [{"qty": 1, "price": 1500}, {"qty": 2, "price": 1000}]


def test_data_maps_to_data():
    result = parser.parse("data[1]:\n  - product: Pen")
    assert result["data"] == [{"product": "Pen"}]


def test_legacy_dados_maps_to_data():
    result = parser.parse("dados[1]:\n  - produto: Caneta")
    assert result["data"] == [{"produto": "Caneta"}]


def test_full_example_file():
    text = (Path(__file__).parent.parent / "examples" / "sales_order.toon").read_text(encoding="utf-8")
    result = parse_toon(text)
    assert result["meta"]["title"] == "Sales Order"
    assert result["layout"]["company"]["label"] == "Company"
    assert len(result["data"]) == 1
    assert len(result["data"][0]["orders"]) == 2
