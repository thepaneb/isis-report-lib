"""Crosstab tests: pivot math, rendering, export (no browser needed)."""

import io

import pytest

from isis_report_lib import build_crosstab, generate_csv, generate_xlsx, render_html

DATA = [
    {"region": "N", "q": "Q1", "total": 10},
    {"region": "N", "q": "Q2", "total": 20},
    {"region": "S", "q": "Q1", "total": 5},
]

SPEC = {"rows": "region", "columns": "q", "measure": "total", "function": "sum"}


def test_build_crosstab_matrix_and_totals():
    ct = build_crosstab(DATA, SPEC)
    assert ct.row_headers == ["N", "S"]
    assert ct.col_headers == ["Q1", "Q2"]
    assert ct.cells == [[10.0, 20.0], [5.0, 0]]
    assert ct.row_totals == [30.0, 5.0]
    assert ct.col_totals == [15.0, 20.0]
    assert ct.grand_total == 35.0
    assert ct.totals is True and ct.has_data


def test_build_crosstab_count_needs_no_measure():
    ct = build_crosstab(DATA, {"rows": "region", "columns": "q", "function": "count"})
    assert ct.cells == [[1, 1], [1, 0]]
    assert ct.grand_total == 3


def test_build_crosstab_avg_min_max():
    ct = build_crosstab(DATA, {**SPEC, "function": "avg"})
    assert ct.cells[0] == [10.0, 20.0]
    assert ct.grand_total == pytest.approx(35 / 3)
    ct = build_crosstab(DATA, {**SPEC, "function": "max"})
    assert ct.cells == [[10.0, 20.0], [5.0, ""]]
    assert ct.grand_total == 20.0


def test_build_crosstab_no_totals_and_sorting():
    data = [{"r": "b", "c": 2, "v": 1}, {"r": "a", "c": 10, "v": 2}, {"r": None, "c": 1, "v": 3}]
    ct = build_crosstab(data, {"rows": "r", "columns": "c", "measure": "v", "function": "sum", "totals": False})
    assert ct.row_headers == ["a", "b", None]
    assert ct.col_headers == [1, 2, 10]
    assert ct.totals is False
    assert ct.row_totals == [2.0, 1.0, 3.0]


def test_build_crosstab_validation():
    with pytest.raises(ValueError, match="needs a measure"):
        build_crosstab(DATA, {"rows": "r", "columns": "c", "function": "sum"})
    with pytest.raises(ValueError, match="Unknown crosstab function"):
        build_crosstab(DATA, {**SPEC, "function": "median"})
    with pytest.raises(ValueError, match="Invalid crosstab rows"):
        build_crosstab(DATA, {**SPEC, "rows": {"label": "x"}})
    with pytest.raises(ValueError, match="Invalid crosstab totals"):
        build_crosstab(DATA, {**SPEC, "totals": "yes"})
    with pytest.raises(ValueError, match="Invalid crosstab empty_text"):
        build_crosstab(DATA, {**SPEC, "empty_text": 5})


def test_build_crosstab_field_defs_and_dict_spec():
    ct = build_crosstab(
        DATA,
        {
            "rows": {"field": "region", "label": "Region"},
            "columns": {"field": "q", "label": "Quarter"},
            "measure": {"field": "total", "label": "Sales", "format_mask": "currency"},
            "function": "sum",
            "total_label": "All",
        },
    )
    assert ct.row_label == "Region" and ct.total_label == "All" and ct.mask == "currency"


def test_crosstab_renders_html_with_totals():
    html = render_html({"meta": {"title": "T"}, "sections": [{"type": "crosstab", "title": "Sales", "data": DATA, **SPEC}]})
    assert "<table" in html
    assert "Sales" in html
    assert "35,00" in html  # pt-BR grand total
    assert "Total" in html


def test_crosstab_empty_data_message():
    html = render_html(
        {
            "meta": {"title": "T"},
            "sections": [{"type": "crosstab", "title": "Sales", "data": [], **SPEC, "empty_text": "No data"}],
        }
    )
    assert "No data" in html
    assert "<table" not in html


def test_crosstab_csv_and_xlsx():
    payload = {"meta": {"title": "T"}, "sections": [{"type": "crosstab", "title": "Sales", "data": DATA, **SPEC}]}
    csv_text = generate_csv(payload)
    assert "# table: Sales" in csv_text
    assert "Total" in csv_text

    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(generate_xlsx(payload)))
    ws = wb["Sales"]
    assert ws["A1"].value == "T"
    assert ws["B2"].value == "Q1"
    assert ws.cell(row=3, column=2).value == 10.0
    assert ws.cell(row=5, column=4).value == 35.0  # grand total, bold total row
