"""Layout converter tests."""

import pytest

from isis_report_lib.layout import (
    aggregate_values,
    build_report,
    convert_data,
    convert_layout,
    evaluate_condition,
    field_visible,
    filter_rows,
    infer_layout,
    is_template_format,
    sort_rows,
    template_header_layout,
)


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


AGG_LAYOUT = {
    "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
    "orders": {
        "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
        "total": {"label": "Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
        "items": {
            "qty": {"label": "Qty", "format_mask": "int", "alignment": "right", "aggregate": "sum"},
            "unit_price": {"label": "Unit", "format_mask": "float", "alignment": "right"},
        },
    },
}

AGG_DATA = [
    {
        "company": "ACME",
        "orders": [
            {
                "order": 1,
                "total": 4000,
                "items": [
                    {"qty": 1, "unit_price": 1500},
                    {"qty": 2, "unit_price": 1250},
                ],
            },
            {"order": 2, "total": 2000, "items": [{"qty": 4, "unit_price": 500}]},
        ],
    }
]


def test_evaluate_condition_operators():
    row = {"status": "paid", "total": 100, "note": None}
    assert evaluate_condition(row, {"field": "status", "equals": "paid"}) is True
    assert evaluate_condition(row, {"field": "status", "not_equals": "paid"}) is False
    assert evaluate_condition(row, {"field": "status", "in": ["paid", "open"]}) is True
    assert evaluate_condition(row, {"field": "status", "not_in": ["paid"]}) is False
    assert evaluate_condition(row, {"field": "total", "gt": 50}) is True
    assert evaluate_condition(row, {"field": "total", "gte": 100}) is True
    assert evaluate_condition(row, {"field": "total", "lt": 50}) is False
    assert evaluate_condition(row, {"field": "total", "lte": 100}) is True
    assert evaluate_condition(row, {"field": "note", "is_null": True}) is True
    assert evaluate_condition(row, {"field": "total", "not_null": True}) is True
    assert evaluate_condition(row, {"field": "total", "gt": "x"}) is False
    with pytest.raises(ValueError, match="no known operator"):
        evaluate_condition(row, {"field": "total", "approx": 100})


def test_filter_rows():
    rows = [{"s": "paid"}, {"s": "cancelled"}]
    assert filter_rows(rows, {"field": "s", "equals": "paid"}) == [{"s": "paid"}]
    assert filter_rows(rows, None) == rows
    with pytest.raises(ValueError, match="Invalid \\$print_when"):
        filter_rows(rows, {"equals": "paid"})


def test_sort_rows():
    rows = [{"o": 2}, {"o": 1}, {"o": None}]
    assert [r["o"] for r in sort_rows(rows, [{"field": "o", "direction": "asc"}])] == [1, 2, None]
    assert [r["o"] for r in sort_rows(rows, "-o")] == [2, 1, None]
    assert sort_rows(rows, None) == rows
    with pytest.raises(ValueError, match="Invalid sort direction"):
        sort_rows(rows, [{"field": "o", "direction": "sideways"}])
    with pytest.raises(ValueError, match="Invalid \\$order_by spec"):
        sort_rows(rows, [42])


def test_sort_rows_mixed_types_fall_back_to_str():
    rows = [{"o": 10}, {"o": "b"}, {"o": "a"}]
    assert [r["o"] for r in sort_rows(rows, "o")] == [10, "a", "b"]


def test_field_visible():
    assert field_visible({"label": "A"}, [{"x": 1}]) is True
    assert field_visible({"label": "A", "visible": False}, [{"x": 1}]) is False
    assert field_visible({"label": "A", "visible_when": {"field": "x", "equals": 1}}, [{"x": 1}]) is True
    assert field_visible({"label": "A", "visible_when": {"field": "x", "equals": 1}}, [{"x": 2}]) is False
    cond = {"field": "x", "not_null": True, "scope": "all"}
    assert field_visible({"label": "A", "visible_when": cond}, [{"x": 1}]) is True
    assert field_visible({"label": "A", "visible_when": cond}, [{"x": 1}, {}]) is False
    with pytest.raises(ValueError, match="Invalid visible_when condition"):
        field_visible({"label": "A", "visible_when": {"equals": 1}}, [{"x": 1}])
    with pytest.raises(ValueError, match="Invalid visible_when scope"):
        field_visible({"label": "A", "visible_when": {"field": "x", "equals": 1, "scope": "many"}}, [{"x": 1}])


def test_aggregate_values():
    rows = [{"v": 10}, {"v": 20}, {"v": None}, {"x": 1}]
    assert aggregate_values(rows, "v", "sum") == 30
    assert aggregate_values(rows, "v", "count") == 4
    assert aggregate_values(rows, "v", "avg") == 15
    assert aggregate_values(rows, "v", "min") == 10
    assert aggregate_values(rows, "v", "max") == 20
    assert aggregate_values([], "v", "sum") == ""
    assert aggregate_values([{"x": 1}], "v", "sum") == ""
    assert aggregate_values([{"v": 10}, "not-a-dict", 42], "v", "sum") == 10
    with pytest.raises(ValueError, match="Unknown aggregate"):
        aggregate_values(rows, "v", "median")


def test_build_report_footers_and_summary():
    dataset, layout = build_report(AGG_DATA, AGG_LAYOUT)
    company = dataset["groups"][0]
    assert company["footer"] == {"total": 6000}
    first, second = company["groups"]
    assert first["details"]["items"]["footer"] == {"qty": 3}
    assert second["details"]["items"]["footer"] == {"qty": 4}
    assert [f["name"] for f in layout["groups"]["groups"]["details"]["items"]] == ["qty", "unit_price"]
    assert dataset["summary"] == {"total": 6000, "qty": 7}
    assert [f["name"] for f in layout["groups"]["footer"]] == ["total"]
    assert [f["name"] for f in layout["summary"]] == ["total", "qty"]


def test_build_report_print_when_and_order_by():
    layout = {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "orders": {
            "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
            "$print_when": {"field": "status", "not_equals": "cancelled"},
            "$order_by": "-order",
        },
    }
    data = [
        {
            "company": "ACME",
            "orders": [
                {"order": 1, "status": "paid"},
                {"order": 3, "status": "cancelled"},
                {"order": 2, "status": "paid"},
            ],
        }
    ]
    dataset, _layout = build_report(data, layout)
    table = dataset["groups"][0]["details"]["orders"]
    assert [r["order"] for r in table["rows"]] == [2, 1]


def test_template_header_layout_ignores_non_dict_fields():
    assert template_header_layout([{"fields": [1, 2]}]) == {"groups": {"header": []}}
    assert template_header_layout([]) == {"groups": {"header": []}}


def test_build_report_visible_false_drops_column():    layout = {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "secret": {"label": "Secret", "format_mask": "str", "alignment": "left", "visible": False},
    }
    dataset, result = build_report([{"company": "ACME", "secret": "shh"}], layout)
    assert [f["name"] for f in result["groups"]["header"]] == ["company"]
    assert dataset["groups"][0]["fields"] == {"company": "ACME", "secret": "shh"}


def test_build_report_multiple_detail_tables():
    layout = {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "orders": {
            "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
            "total": {"label": "Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
            "items": {
                "qty": {"label": "Qty", "format_mask": "int", "alignment": "right", "aggregate": "sum"},
            },
            "fees": {
                "kind": {"label": "Fee", "format_mask": "str", "alignment": "left"},
                "amount": {"label": "Amount", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
            },
        },
    }
    data = [
        {
            "company": "ACME",
            "orders": [
                {
                    "order": 1,
                    "total": 4000,
                    "items": [{"qty": 1}, {"qty": 2}],
                    "fees": [{"kind": "Service", "amount": 5.00}, {"kind": "Tax", "amount": 4.01}],
                }
            ],
        }
    ]
    dataset, result = build_report(data, layout)
    order = dataset["groups"][0]["groups"][0]
    assert set(order["details"]) == {"items", "fees"}
    assert order["details"]["items"]["footer"] == {"qty": 3}
    assert order["details"]["fees"]["footer"] == {"amount": 9.01}
    assert "footer" not in order  # table totals live in tfoot; no redundant recap
    assert dataset["groups"][0]["footer"] == {"total": 4000}
    assert [f["name"] for f in result["groups"]["groups"]["details"]["fees"]] == ["kind", "amount"]
    assert dataset["summary"] == {"total": 4000, "qty": 3, "amount": 9.01}
