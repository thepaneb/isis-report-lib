"""Expressiveness tests: median/distinct aggregates, color scales, data bars, summary side."""

import io

import pytest

from isis_report_lib import generate_xlsx, render_html
from isis_report_lib.formatting import color_scale_fill, normalize_color_scale, scale_fill
from isis_report_lib.layout import aggregate_values, color_domain


def test_median_and_distinct_aggregates():
    rows = [{"v": 3}, {"v": 1}, {"v": 2}, {"v": None}, {"x": 1}]
    assert aggregate_values(rows, "v", "median") == 2.0
    assert aggregate_values([], "v", "median") == ""
    assert aggregate_values([{"v": "a"}, {"v": "a"}, {"v": "b"}, {"v": None}], "v", "distinct") == 2
    assert aggregate_values([], "v", "distinct") == 0
    assert aggregate_values([{"v": [1]}, {"v": [1]}], "v", "distinct") == 1  # unhashable fallback


def test_color_scale_helpers():
    assert normalize_color_scale({"min": "#000000", "max": "#ffffff"}, "f") == {"min": "#000000", "max": "#ffffff"}
    assert color_scale_fill(0, 0, 10, "#000000", "#FFFFFF") == "#000000"
    assert color_scale_fill(10, 0, 10, "#000000", "#FFFFFF") == "#FFFFFF"
    assert color_scale_fill(5, 0, 10, "#000000", "#FFFFFF") == "#808080"
    assert color_scale_fill(99, 0, 10, "#000000", "#FFFFFF") == "#FFFFFF"  # clamped
    assert color_scale_fill(5, 5, 5, "#000000", "#FFFFFF") == "#808080"  # zero span
    assert color_domain([3, 1, 2, None, True, "x"]) == [1.0, 3.0]
    assert color_domain([]) is None and color_domain(["x"]) is None
    with pytest.raises(ValueError, match="Invalid color_scale"):
        normalize_color_scale({"min": "#000"}, "f")
    with pytest.raises(ValueError, match="Invalid color"):
        normalize_color_scale({"min": "#000000", "max": "red"}, "f")
    with pytest.raises(ValueError, match="Invalid color"):
        normalize_color_scale({"min": "#zzzzzz", "max": "#ffffff"}, "f")


def test_scale_fill_and_cell_style_integration():
    field = {"color_scale": {"min": "#000000", "max": "#FFFFFF"}, "color_domain": [0.0, 10.0]}
    assert scale_fill(0, field) == "#000000"
    assert scale_fill(10, field) == "#FFFFFF"
    assert scale_fill(None, field) is None
    assert scale_fill("x", field) is None
    assert scale_fill(True, field) is None
    assert scale_fill(5, {}) is None
    assert scale_fill(5, None) is None

    from isis_report_lib import render_html as _render

    html = _render(
        {
            "meta": {"title": "T"},
            "layout": {"v": {"label": "V", "format_mask": "float", "color_scale": {"min": "#000000", "max": "#FFFFFF"}}},
            "data": [{"v": 0}, {"v": 10}],
        }
    )
    assert "background:#000000" in html and "background:#FFFFFF" in html


def test_cell_rules_background_wins_over_scale():
    from isis_report_lib import render_html as _render

    html = _render(
        {
            "meta": {"title": "T"},
            "layout": {
                "v": {
                    "label": "V",
                    "format_mask": "float",
                    "color_scale": {"min": "#000000", "max": "#FFFFFF"},
                    "cell_rules": [{"lt": 5, "background": "#FF0000"}],
                }
            },
            "data": [{"v": 0}, {"v": 10}],
        }
    )
    assert "background:#FF0000" in html and "background:#FFFFFF" in html


def test_color_scale_validation_and_crosstab():
    with pytest.raises(ValueError, match="Invalid color_scale"):
        render_html(
            {
                "meta": {"title": "T"},
                "layout": {"v": {"label": "V", "color_scale": {"min": "#000"}}},
                "data": [{"v": 1}],
            }
        )
    with pytest.raises(ValueError, match="Invalid data_bar"):
        render_html(
            {
                "meta": {"title": "T"},
                "layout": {"v": {"label": "V", "data_bar": "yes"}},
                "data": [{"v": 1}],
            }
        )
    html = render_html(
        {
            "meta": {"title": "T"},
            "sections": [
                {
                    "type": "crosstab",
                    "title": "C",
                    "data": [{"r": "a", "c": "x", "v": 1}, {"r": "b", "c": "x", "v": 9}],
                    "rows": "r",
                    "columns": "c",
                    "measure": {"field": "v", "color_scale": {"min": "#000000", "max": "#FFFFFF"}},
                    "function": "sum",
                }
            ],
        }
    )
    assert "background:#000000" in html and "background:#FFFFFF" in html


def test_summary_side_top_and_validation():
    payload = {
        "meta": {"title": "T", "summary_side": "top"},
        "layout": {"v": {"label": "V", "format_mask": "int", "aggregate": "sum"}},
        "data": [{"v": 1}],
    }
    html = render_html(payload)
    assert html.index('<section class="summary">') < html.index('section class="group-header-0"')
    bottom = render_html({**payload, "meta": {"title": "T"}})
    assert bottom.index('<section class="summary">') > bottom.index('section class="group-header-0"')
    with pytest.raises(ValueError, match="Invalid meta.summary_side"):
        render_html({"meta": {"title": "T", "summary_side": "sideways"}, "data": [{"v": 1}]})


def test_xlsx_data_bars_and_gradient():
    from openpyxl import load_workbook

    payload = {
        "meta": {"title": "T"},
        "layout": {
            "v": {
                "label": "V",
                "format_mask": "float",
                "color_scale": {"min": "#000000", "max": "#FFFFFF"},
                "data_bar": True,
            }
        },
        "data": [{"v": 0}, {"v": 5}, {"v": 10}],
    }
    wb = load_workbook(io.BytesIO(generate_xlsx(payload)))
    ws = wb["data"]
    fills = {ws.cell(row=r, column=1).fill.start_color.rgb for r in range(3, 6)}
    assert fills == {"FF000000", "FF808080", "FFFFFFFF"}
    (cf_range,) = list(ws.conditional_formatting._cf_rules)
    assert "A3:A5" in str(cf_range)


def test_keep_together_css():
    html = render_html({"meta": {"title": "T"}, "data": [{"a": 1}]})
    assert "break-inside: avoid" in html and "break-after: avoid" in html
