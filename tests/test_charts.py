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
    assert 'height="48.0"' in svg  # max value fills the plot area (100-22-30)


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
        build_chart({"kind": "radar", "labels": ["a"], "values": [1]})
    with pytest.raises(ValueError, match="Unknown bar orientation"):
        build_chart({"kind": "bar", "labels": ["a"], "values": [1], "orientation": "diagonal"})


def test_horizontal_bar_chart():
    from isis_report_lib.charts import bar_chart

    svg = bar_chart(["A", "B"], [5, 10], orientation="horizontal")
    assert svg.count("<rect") == 2
    assert "A" in svg and "10" in svg


def test_pie_and_donut_charts():
    from isis_report_lib.charts import build_chart, pie_chart

    svg = pie_chart(["A", "B"], [30, 70])
    assert svg.count("<path") == 2
    assert "30%" in svg and "70%" in svg
    donut = build_chart({"kind": "donut", "labels": ["A", "B"], "values": [1, 1]})
    assert "<circle" in donut
    with pytest.raises(ValueError, match="positive total"):
        pie_chart(["A", "B"], [0, 0])
