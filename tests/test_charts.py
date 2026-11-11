"""SVG chart builder tests (no browser needed)."""

import pytest

from isis_report_lib.charts import bar_chart, build_chart, line_chart


def test_bar_chart_structure():
    svg = bar_chart(["Jan", "Feb"], [10, 20])
    assert svg.startswith("<svg")
    assert svg.count("<rect") == 2
    assert "Jan" in svg and "Feb" in svg


def test_bar_chart_scales_to_max():
    svg = bar_chart(["A", "B"], [5, 10], width=200, height=100)
    assert 'height="60.0"' in svg  # max value fills the plot area (100-10-30)


def test_line_chart_structure():
    svg = line_chart(["Jan", "Feb", "Mar"], [1, 3, 2])
    assert "<polyline" in svg
    assert svg.count("<circle") == 3


def test_charts_escape_labels():
    svg = bar_chart(["<b>&"], [1])
    assert "&lt;b&gt;&amp;" in svg
    assert "<b>" not in svg.replace("<svg", "").replace("</svg>", "")


def test_charts_reject_bad_series():
    with pytest.raises(ValueError, match="non-empty"):
        bar_chart([], [])
    with pytest.raises(ValueError, match="must match"):
        line_chart(["a", "b"], [1])
    with pytest.raises(ValueError, match="numeric"):
        bar_chart(["a"], ["x"])


def test_build_chart_dispatch_and_options():
    svg = build_chart({"kind": "line", "labels": ["a"], "values": [1], "color": "#FF0000", "width": 400, "height": 200})
    assert 'width="400"' in svg and "#FF0000" in svg
    with pytest.raises(ValueError, match="Unknown chart kind"):
        build_chart({"kind": "pie", "labels": ["a"], "values": [1]})
