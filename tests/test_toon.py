"""`.toon` parser tests."""

from pathlib import Path

import pytest

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


def test_compact_layout_field_with_aggregate():
    result = parser.parse("layout:\n  total{Total,float,right,sum}")
    assert result["layout"]["total"] == {
        "label": "Total",
        "format_mask": "float",
        "alignment": "right",
        "aggregate": "sum",
    }


def test_compact_array_of_objects():
    result = parser.parse("items[2]{qty,price}:\n  1,1500\n  2,1000")
    assert result["items"] == [{"qty": 1, "price": 1500}, {"qty": 2, "price": 1000}]


def test_data_maps_to_data():
    result = parser.parse("data[1]:\n  - product: Pen")
    assert result["data"] == [{"product": "Pen"}]


def test_legacy_dados_maps_to_data():
    result = parser.parse("dados[1]:\n  - produto: Caneta")
    assert result["data"] == [{"produto": "Caneta"}]


def test_stray_deeper_line_is_skipped():
    result = parser.parse("a: 1\n    stray deep\nb: 2")
    assert result == {"a": 1, "b": 2}


def test_dangling_dash_line_is_skipped():
    result = parser.parse("a: 1\n- orphan\nb: 2")
    assert result == {"a": 1, "b": 2}


def test_empty_value_at_end_becomes_empty_dict():
    result = parser.parse("a: 1\nempty:")
    assert result == {"a": 1, "empty": {}}


def test_garbage_line_is_ignored():
    result = parser.parse("a: 1\n???\nb: 2")
    assert result == {"a": 1, "b": 2}


def test_array_followed_by_sibling_key():
    result = parser.parse("a[2]:\n  - x: 1\n  - y: 2\nb: 3")
    assert result == {"a": [{"x": 1}, {"y": 2}], "b": 3}


def test_array_item_with_nested_mapping():
    result = parser.parse("items[1]:\n  - address:\n    city: Rome")
    assert result == {"items": [{"address": {"city": "Rome"}}]}


def test_array_of_scalars():
    result = parser.parse("nums[2]:\n  - 42\n  - 7")
    assert result == {"nums": [42, 7]}


def test_extra_indented_line_inside_array_is_skipped():
    result = parser.parse("a[1]:\n  - x: 1\n      deep: junk\n  - y: 2")
    assert result == {"a": [{"x": 1}, {"y": 2}]}


def test_non_dash_line_inside_array_is_skipped():
    result = parser.parse("a[1]:\n  - x: 1\n  trailing: x")
    assert result == {"a": [{"x": 1}]}


def test_deeply_nested_input_raises_value_error():
    deep = "".join(f"{'  ' * i}level{i}:\n" for i in range(5000))
    with pytest.raises(ValueError, match="nested too deeply"):
        parser.parse(deep)


def test_full_example_file():
    text = (Path(__file__).parent.parent / "examples" / "sales_order.toon").read_text(encoding="utf-8")
    result = parse_toon(text)
    assert result["meta"]["title"] == "Sales Order"
    assert result["layout"]["company"]["label"] == "Company"
    assert len(result["data"]) == 1
    assert len(result["data"][0]["orders"]) == 2
