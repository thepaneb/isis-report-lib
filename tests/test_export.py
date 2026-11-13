"""XLSX/CSV export tests (no browser needed)."""

import io

import pytest

from isis_report_lib import (
    agenerate_csv,
    agenerate_xlsx,
    collect_tables,
    generate_csv,
    generate_csv_from_toon,
    generate_xlsx,
    generate_xlsx_from_toon,
)
from isis_report_lib.service import prepare_report

PAYLOAD = {
    "meta": {"title": "Order", "mode": "exact"},
    "layout": {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "orders": {
            "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
            "total": {"label": "Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
            "items": {
                "qty": {"label": "Qty", "format_mask": "int", "alignment": "right", "aggregate": "sum"},
                "unit_price": {"label": "Unit", "format_mask": "float", "alignment": "right"},
            },
        },
    },
    "data": [
        {
            "company": "ACME",
            "orders": [
                {"order": 1, "total": 4000, "items": [{"qty": 1, "unit_price": 1500}, {"qty": 2, "unit_price": 1250}]},
                {"order": 2, "total": 2000, "items": [{"qty": 4, "unit_price": 500}]},
            ],
        }
    ],
}


def _prepared():
    dataset, layout, meta = prepare_report(PAYLOAD)
    return collect_tables(dataset, layout)


def test_collect_tables_structure():
    tables, summaries = _prepared()
    assert [t.key for t in tables] == ["items"]
    items = tables[0]
    assert [c.label for c in items.columns] == ["Company", "Code", "Total", "Qty", "Unit"]
    assert len(items.rows) == 5  # 3 + 1 footer + 1 + 1 footer
    assert items.rows[0]["company"] == "ACME"
    assert items.rows[0]["order"] == 1
    assert items.rows[0]["qty"] == 1
    assert items.total_rows == {2, 4}
    assert items.rows[2] == {"qty": 3}
    assert items.rows[4] == {"qty": 4}
    labels = [label for label, _value, _mask in summaries]
    assert "ACME / Total" in labels
    assert "Total" in labels


def test_collect_tables_empty_dataset():
    tables, summaries = collect_tables({"groups": [], "summary": None}, {"groups": {"header": []}})
    assert tables == []
    assert summaries == []


def test_generate_xlsx_bytes_and_sheets():
    from openpyxl import load_workbook

    blob = generate_xlsx(PAYLOAD)
    assert blob[:4] == b"PK\x03\x04"  # zip container
    wb = load_workbook(io.BytesIO(blob))
    assert set(wb.sheetnames) == {"items", "Summary"}
    ws = wb["items"]
    assert ws["A1"].value == "Order"
    assert ws["A2"].value == "Company"
    assert ws["A3"].value == "ACME"
    assert ws["B3"].value == 1
    assert ws["D3"].value == 1
    assert ws["D3"].number_format == "#,##0"
    assert ws["E3"].number_format == "#,##0.00"
    for row in ws.iter_rows():
        for cell in row:
            assert cell.value != "None"
    # per-order footer rows are bold with a top border (row 5: qty 3, row 7: qty 4)
    assert ws.cell(row=5, column=4).value == 3
    assert ws.cell(row=5, column=4).font.bold is True
    assert ws.cell(row=7, column=4).value == 4
    assert ws.cell(row=7, column=4).font.bold is True
    summary = wb["Summary"]
    assert summary["A1"].value == "Order"
    values = {summary.cell(row=r, column=1).value: summary.cell(row=r, column=2).value for r in range(2, summary.max_row + 1)}
    assert values["ACME / Total"] == 6000
    assert values["Total"] == 6000


def test_generate_xlsx_title_and_subtitle_rows():
    from openpyxl import load_workbook

    payload = {**PAYLOAD, "meta": {"title": "T", "sub_title": "S", "mode": "exact"}}
    wb = load_workbook(io.BytesIO(generate_xlsx(payload)))
    assert wb["items"]["A1"].value == "T"
    assert wb["items"]["A2"].value == "S"


def test_generate_xlsx_applies_cell_rules():
    from openpyxl import load_workbook

    payload = {
        "meta": {"title": "T", "mode": "exact"},
        "layout": {
            "total": {
                "label": "Total",
                "format_mask": "float",
                "alignment": "right",
                "cell_rules": [{"lt": 0, "color": "C00000", "bold": True, "background": "FFFF00"}],
            },
        },
        "data": [{"total": -5}, {"total": 10}],
    }
    wb = load_workbook(io.BytesIO(generate_xlsx(payload)))
    ws = wb["data"]
    assert ws["A2"].value == "Total"
    assert ws["A3"].font.color.rgb.endswith("C00000")
    assert ws["A3"].font.bold is True
    assert ws["A3"].fill.fgColor.rgb.endswith("FFFF00")
    assert ws["A4"].font.bold is not True


def test_generate_xlsx_print_setup():
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(generate_xlsx(PAYLOAD)))
    ws = wb["items"]
    assert ws.print_title_rows == "$2:$2"  # header row repeats on printed pages (openpyxl absolutizes)
    assert ws.freeze_panes == "A3"
    assert ws.auto_filter.ref is not None


async def test_agenerate_xlsx_and_csv():
    assert (await agenerate_xlsx(PAYLOAD))[:4] == b"PK\x03\x04"
    assert "ACME" in await agenerate_csv(PAYLOAD)


def test_generate_xlsx_from_toon():
    assert generate_xlsx_from_toon("meta:\n  title: T\n  mode: exact\ndata[1]:\n  - a: 1")[:4] == b"PK\x03\x04"


def test_generate_csv_content_and_delimiter():
    text = generate_csv(PAYLOAD)
    lines = text.splitlines()
    assert lines[0] == "# Order"
    assert lines[1] == "# table: items"
    assert lines[2] == "Company,Code,Total,Qty,Unit"
    assert 'ACME,1,"4.000,00",1,"1.500,00"' in lines
    assert "# summary" in lines
    semi = generate_csv(PAYLOAD, delimiter=";")
    assert "Company;Code;Total;Qty;Unit" in semi.splitlines()


def test_generate_csv_from_toon():
    assert "Pen" in generate_csv_from_toon("meta:\n  title: T\n  mode: exact\ndata[1]:\n  - product: Pen")


def test_generate_csv_with_bom():
    from isis_report_lib import generate_csv

    assert generate_csv(PAYLOAD, bom=True).startswith("\ufeff# Order")
    assert not generate_csv(PAYLOAD).startswith("\ufeff")


def test_generate_csv_locale():
    payload = {"meta": {"title": "T", "locale": "en-US"}, "layout": PAYLOAD["layout"], "data": PAYLOAD["data"]}
    assert "4,000.00" in generate_csv(payload)


def test_missing_openpyxl_raises_helpful_error(monkeypatch):
    import sys

    from isis_report_lib import export

    monkeypatch.setitem(sys.modules, "openpyxl", None)
    monkeypatch.setitem(sys.modules, "openpyxl.styles", None)
    monkeypatch.setitem(sys.modules, "openpyxl.workbook", None)
    with pytest.raises(ImportError, match="pip install isis-report-lib\\[xlsx\\]"):
        export.build_workbook([], [], {})


def test_sheet_name_sanitized_and_deduped():
    from isis_report_lib.export import _sheet_name

    used: set[str] = set()
    assert _sheet_name("a/b:c*d?e[f]g", used) == "a-b-c-d-e-f-g"
    assert _sheet_name("x" * 40, used) != ""
    assert len(_sheet_name("x" * 40, used)) <= 31
    assert _sheet_name("items", used) != _sheet_name("items", used)


def test_native_value_conversions():
    import datetime

    from isis_report_lib.export import _native_value, _number_format

    assert _native_value(None, "int") is None
    assert _native_value("abc", "int") == "abc"
    assert _native_value("abc", "float") == "abc"
    assert _native_value(True, "bool") == "Yes"
    assert _native_value(0, "bool") == "No"
    assert _native_value("no", "bool") == "No"
    assert _native_value(datetime.date(2024, 1, 1), "date") == datetime.date(2024, 1, 1)
    assert _native_value("hello", "str") == "hello"
    assert _number_format("percent") == "0.00%"
    assert _number_format("currency") == '"$"#,##0.00'
    assert _number_format("currency", "R$") == '"R$"#,##0.00'
    assert _number_format("date") == "yyyy-mm-dd"
    assert _number_format("str") is None
    assert _number_format("unknown") is None


def test_collect_tables_skips_non_dict_items():
    tables, _summaries = collect_tables(
        {"groups": ["nope", {"fields": {"a": 1}}], "summary": None},
        {"groups": {"header": [{"name": "a", "label": "A", "format_mask": "str", "alignment": "left"}]}},
    )
    assert len(tables) == 1
    assert tables[0].key == "data"


def test_collect_tables_skips_table_missing_from_data():
    """A layout table with no matching data rows is skipped (empty-table guard)."""
    tables, summaries = collect_tables(
        {
            "groups": [{"fields": {"company": "ACME"}, "groups": [{"fields": {"order": 1}}]}],
            "summary": None,
        },
        {
            "groups": {
                "header": [{"name": "company", "label": "Company", "format_mask": "str", "alignment": "left"}],
                "groups": {
                    "header": [{"name": "order", "label": "Code", "format_mask": "int", "alignment": "right"}],
                    "details": {"items": [{"name": "qty", "label": "Qty", "format_mask": "int", "alignment": "right"}]},
                },
            }
        },
    )
    # The missing "items" table is skipped; flat top-level fields fall back to a "data" sheet.
    assert [t.key for t in tables] == ["data"]
    assert summaries == []


def test_collect_tables_keeps_footer_only_table():
    tables, _summaries = collect_tables(
        {
            "groups": [
                {
                    "fields": {"company": "ACME"},
                    "groups": [{"fields": {"order": 1}, "details": {"items": {"rows": [], "footer": {"qty": 3}}}}],
                }
            ],
            "summary": None,
        },
        {
            "groups": {
                "header": [{"name": "company", "label": "Company", "format_mask": "str", "alignment": "left"}],
                "groups": {
                    "header": [{"name": "order", "label": "Code", "format_mask": "int", "alignment": "right"}],
                    "details": {"items": [{"name": "qty", "label": "Qty", "format_mask": "int", "alignment": "right"}]},
                },
            }
        },
    )
    assert [t.key for t in tables] == ["items"]
    assert tables[0].rows == [{"qty": 3}]


def test_merge_columns_dedupes():
    from isis_report_lib.export import Column, _merge_columns

    cols = _merge_columns(
        [Column(key="a", label="A"), Column(key="b", label="B")],
        [{"name": "b", "label": "B2", "format_mask": "str"}, {"name": "c", "label": "C", "format_mask": "str"}],
    )
    assert [c.key for c in cols] == ["a", "b", "c"]
    assert cols[1].label == "B"


def test_build_workbook_empty():
    from openpyxl import load_workbook

    from isis_report_lib.export import build_workbook

    wb = load_workbook(io.BytesIO(build_workbook([], [], {"title": "T"})))
    assert wb.active["A1"].value == "T"
    wb = load_workbook(io.BytesIO(build_workbook([], [], {})))
    assert wb.active["A1"].value == "Report"


def test_currency_symbol_fallbacks():
    from isis_report_lib.export import _currency_symbol

    assert _currency_symbol({"locale": "xx-YY"}) == "$"
    assert _currency_symbol({"locale": "pt-BR"}) == "R$"
    # Unknown codes pass through as-is (visible user error, not silent).
    assert _currency_symbol({"locale": "pt-BR", "currency": "NOPE"}) == "NOPE"


def test_currency_symbol_lookup_failure_falls_back(monkeypatch):
    import babel.numbers

    from isis_report_lib.export import _currency_symbol

    def boom(*args, **kwargs):
        raise ValueError("lookup failed")

    monkeypatch.setattr(babel.numbers, "get_currency_symbol", boom)
    assert _currency_symbol({"locale": "en-US", "currency": "USD"}) == "$"


SECTIONS_EXPORT_PAYLOAD = {
    "meta": {"title": "Board Pack", "mode": "exact"},
    "sections": [
        {"type": "text", "title": "Intro", "paragraphs": ["Hello."]},
        {
            "type": "table",
            "title": "Sales",
            "layout": {"product": {"label": "Product", "format_mask": "str", "alignment": "left"}},
            "data": [{"product": "Pen"}],
        },
        {"type": "kpi", "title": "Totals", "items": [{"label": "Orders", "value": 42}]},
        {"type": "chart", "title": "Trend", "chart": {"kind": "bar", "labels": ["Jan", "Feb"], "values": [10, 20]}},
    ],
}


def test_collect_tables_with_sections():
    from isis_report_lib.service import prepare_report

    dataset, layout, _meta = prepare_report(SECTIONS_EXPORT_PAYLOAD)
    tables, summaries = collect_tables(dataset, layout)
    by_key = {t.key: t for t in tables}
    assert set(by_key) == {"Sales", "Intro", "Totals", "Trend"}
    assert by_key["Sales"].rows == [{"product": "Pen"}]
    assert by_key["Intro"].rows == [{"text": "Hello."}]
    assert by_key["Totals"].rows == [{"label": "Orders", "value": 42}]


def test_generate_xlsx_from_sections():
    import io

    from openpyxl import load_workbook

    from isis_report_lib import generate_xlsx

    wb = load_workbook(io.BytesIO(generate_xlsx(SECTIONS_EXPORT_PAYLOAD)))
    assert wb.sheetnames == ["Intro", "Sales", "Totals", "Trend"]


def test_generate_csv_from_sections():
    from isis_report_lib import generate_csv

    text = generate_csv(SECTIONS_EXPORT_PAYLOAD)
    assert "# table: Sales" in text
    assert "Pen" in text
    assert "# table: Intro" in text


def test_collect_tables_skips_non_dict_sections():
    tables, summaries = collect_tables({"groups": [], "summary": None, "sections": ["nope", 42]}, {"groups": {"header": []}})
    assert tables == []
    assert summaries == []


def test_collect_tables_dedupes_section_table_names():
    from isis_report_lib.service import prepare_report

    payload = {
        "meta": {"title": "T"},
        "sections": [
            {"type": "table", "layout": {"a": {"label": "A"}}, "data": [{"a": 1}]},
            {"type": "table", "layout": {"a": {"label": "A"}}, "data": [{"a": 2}]},
        ],
    }
    dataset, layout, _meta = prepare_report(payload)
    tables, _summaries = collect_tables(dataset, layout)
    assert sorted(t.key for t in tables) == ["table", "table_2"]
    assert tables[1].rows == [{"a": 2}]


def test_collect_tables_section_with_summary():
    from isis_report_lib.service import prepare_report

    payload = {
        "meta": {"title": "T"},
        "sections": [
            {
                "type": "table",
                "title": "S",
                "layout": {"v": {"label": "V", "format_mask": "int", "alignment": "right", "aggregate": "sum"}},
                "data": [{"v": 1}, {"v": 2}],
            }
        ],
    }
    dataset, layout, _meta = prepare_report(payload)
    tables, summaries = collect_tables(dataset, layout)
    assert [t.key for t in tables] == ["S"]
    assert ("S / V", 3, "int") in summaries


def test_chart_section_with_non_dict_spec_raises():
    from isis_report_lib import render_html

    with pytest.raises(ValueError, match="non-empty"):
        render_html({"meta": {"title": "T"}, "sections": [{"type": "chart", "chart": "nope"}]})
