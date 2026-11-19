"""Sparkline tests: SVG nanoplots in HTML, block-art fallback in CSV/XLSX."""

import io

from isis_report_lib import format_value, generate_csv, generate_xlsx, render_html
from isis_report_lib.charts import sparkline
from isis_report_lib.formatting import sparkline_text


def test_sparkline_line_and_bar():
    line = sparkline([1, 2, 3, 2, 1])
    assert line.startswith("<svg") and "<polyline" in line and "<circle" in line
    bar = sparkline([1, 2, 3], kind="bar")
    assert bar.startswith("<svg") and bar.count("<rect") == 3
    assert sparkline([]) == ""
    assert sparkline([None, "x"]) == ""
    assert sparkline(5).count("<circle") == 1  # scalar becomes one point
    import pytest

    with pytest.raises(ValueError, match="Unknown sparkline kind"):
        sparkline([1, 2], kind="area")


def test_sparkline_text_blocks():
    assert sparkline_text([]) == ""
    assert sparkline_text([1, 2, 3, 4, 5, 6, 7, 8]) == "▁▂▃▄▅▆▇█"
    assert sparkline_text(None) == ""
    assert len(sparkline_text([5])) == 1


def test_format_value_sparkline_mask():
    assert format_value([1, 2, 3], "sparkline").startswith("<svg")
    assert format_value([1, 2, 3], "sparkline", field={"spark_kind": "bar"}).count("<rect") == 3
    assert format_value(None, "sparkline") == ""
    import pytest

    with pytest.raises(ValueError, match="Unknown sparkline kind"):
        format_value([1, 2], "sparkline", field={"spark_kind": "area"})
    with pytest.raises(ValueError, match="Unknown sparkline kind"):
        format_value([1, 2], "sparkline", field={"spark_kind": 5})


def test_sparkline_renders_in_html_table():
    payload = {
        "meta": {"title": "T"},
        "layout": {"trend": {"label": "Trend", "format_mask": "sparkline", "alignment": "left"}},
        "data": [{"trend": [3, 1, 2]}],
    }
    html = render_html(payload)
    assert "<svg" in html and "<polyline" in html


def test_sparkline_csv_and_xlsx_use_block_art():
    payload = {
        "meta": {"title": "T"},
        "layout": {"trend": {"label": "Trend", "format_mask": "sparkline", "alignment": "left"}},
        "data": [{"trend": [1, 2, 3, 4, 5, 6, 7, 8]}],
    }
    csv_text = generate_csv(payload)
    assert "▁▂▃▄▅▆▇█" in csv_text
    assert "<svg" not in csv_text

    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(generate_xlsx(payload)))
    ws = wb["data"]
    assert ws["A3"].value == "▁▂▃▄▅▆▇█"
