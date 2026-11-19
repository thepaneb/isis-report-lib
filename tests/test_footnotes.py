"""Footnote + source-note tests (HTML, CSV, XLSX)."""

import io

from isis_report_lib import generate_csv, generate_xlsx, render_html

PAYLOAD = {
    "meta": {"title": "T", "source_note": "Source: ERP."},
    "layout": {
        "total": {
            "label": "Total",
            "format_mask": "float",
            "alignment": "right",
            "footnote": "Audited figures.",
        },
        "status": {
            "label": "Status",
            "format_mask": "str",
            "alignment": "left",
            "footnote": {"mark": "†", "text": "As of closing."},
        },
    },
    "data": [{"total": 10, "status": "A"}],
}


def test_footnote_marks_and_list_in_html():
    html = render_html(PAYLOAD)
    assert "<sup>*</sup>" in html and "<sup>†</sup>" in html
    assert html.index("<sup>*</sup>") < html.index("<sup>†</sup>")
    assert "<li><sup>*</sup> Audited figures.</li>" in html
    assert "<li><sup>†</sup> As of closing.</li>" in html
    assert '<p class="source-note">Source: ERP.</p>' in html


def test_footnotes_invalid_schema():
    import pytest

    with pytest.raises(ValueError, match="Invalid footnote"):
        render_html(
            {
                "meta": {"title": "T"},
                "layout": {"a": {"label": "A", "footnote": {"mark": "*"}}},
                "data": [{"a": 1}],
            }
        )
    with pytest.raises(ValueError, match="Invalid meta.source_note"):
        render_html({"meta": {"title": "T", "source_note": 5}, "data": []})
    with pytest.raises(ValueError, match="Invalid section source"):
        render_html(
            {
                "meta": {"title": "T"},
                "sections": [{"type": "text", "paragraphs": ["x"], "source": 5}],
            }
        )


def test_section_source_and_kpi_footnote():
    html = render_html(
        {
            "meta": {"title": "T"},
            "sections": [
                {"type": "kpi", "title": "K", "source": "Board pack.", "items": [{"label": "Orders", "value": 3, "footnote": "Counted."}]},
            ],
        }
    )
    assert "<sup>*</sup>" in html
    assert "Counted." in html and "Board pack." in html


def test_footnotes_csv_and_xlsx():
    csv_text = generate_csv(PAYLOAD)
    assert "# [source] Source: ERP." in csv_text
    assert "# [*] Audited figures." in csv_text
    assert "Total [*]" in csv_text

    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(generate_xlsx(PAYLOAD)))
    assert "Notes" in wb.sheetnames
    notes = wb["Notes"]
    assert notes["B2"].value == "source" and notes["C2"].value == "Source: ERP."
    marks = {(notes.cell(row=r, column=2).value, notes.cell(row=r, column=3).value) for r in range(3, 5)}
    assert ("*", "Audited figures.") in marks
    assert wb["data"]["A2"].value == "Total [*]"


def test_no_notes_no_extra_output():
    from openpyxl import load_workbook

    payload = {"meta": {"title": "T"}, "layout": {"a": {"label": "A"}}, "data": [{"a": 1}]}
    html = render_html(payload)
    assert '<ol class="footnotes"' not in html and '<p class="source-note"' not in html
    assert "[source]" not in generate_csv(payload)
    wb = load_workbook(io.BytesIO(generate_xlsx(payload)))
    assert "Notes" not in wb.sheetnames
