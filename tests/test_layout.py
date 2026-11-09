"""Layout converter tests."""

from isis_report_lib.layout import convert_data, convert_layout, infer_layout, is_template_format


def test_empty_layout():
    assert convert_layout({}) == {"groups": {"header": []}}


def test_simple_fields():
    result = convert_layout(
        {
            "name": {"label": "Name", "format_mask": "str", "alignment": "left"},
            "age": {"label": "Age", "format_mask": "int", "alignment": "right"},
        }
    )
    assert len(result["groups"]["header"]) == 2
    assert result["groups"]["header"][0]["name"] == "name"


def test_single_group():
    result = convert_layout(
        {
            "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
            "orders": {
                "order": {"label": "Order", "format_mask": "int", "alignment": "right"},
                "total": {"label": "Total", "format_mask": "float", "alignment": "right"},
            },
        }
    )
    assert result["groups"]["header"][0]["name"] == "company"
    assert result["groups"]["groups"]["header"][0]["name"] == "order"


def test_group_with_detail():
    result = convert_layout(
        {
            "title": {"label": "Title", "format_mask": "str", "alignment": "left"},
            "group": {
                "field": {"label": "Field", "format_mask": "str", "alignment": "left"},
                "details": {
                    "sub1": {"label": "Sub 1", "format_mask": "str", "alignment": "left"},
                    "sub2": {"label": "Sub 2", "format_mask": "int", "alignment": "right"},
                },
            },
        }
    )
    groups = result["groups"]["groups"]
    assert groups["header"][0]["name"] == "field"
    assert groups["detail"][0]["name"] == "sub1"


def test_convert_data_template_format_passthrough():
    data = [{"fields": {"name": "John"}, "groups": []}]
    assert convert_data(data, {}) == {"groups": data}


def test_convert_data_with_group_and_detail():
    data = [{"title": "A", "group": [{"field": "x", "details": [{"sub": 1}, {"sub": 2}]}]}]
    layout = {
        "title": {"label": "Title", "format_mask": "str", "alignment": "left"},
        "group": {
            "field": {"label": "Field", "format_mask": "str", "alignment": "left"},
            "details": {"sub": {"label": "Sub", "format_mask": "int", "alignment": "right"}},
        },
    }
    result = convert_data(data, layout)
    subgroup = result["groups"][0]["groups"][0]
    assert subgroup["fields"] == {"field": "x"}
    assert subgroup["detail"] == [{"sub": 1}, {"sub": 2}]


def test_infer_layout_types():
    result = infer_layout([{"name": "John", "age": 30, "price": 9.9, "active": True, "items": [1]}])
    by_name = {f["name"]: f for f in result["groups"]["header"]}
    assert set(by_name) == {"name", "age", "price", "active"}
    assert by_name["age"]["format_mask"] == "int"
    assert by_name["price"]["format_mask"] == "float"
    assert by_name["active"]["format_mask"] == "str"


def test_is_template_format():
    assert is_template_format([]) is False
    assert is_template_format([{"fields": {}}]) is True
    assert is_template_format([{"name": 1}]) is False
