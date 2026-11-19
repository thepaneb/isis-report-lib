"""Missing-data fidelity tests: missing_text, substitutions, empty_text (HTML)."""

from isis_report_lib import render_html


def _payload(**overrides):
    payload = {
        "meta": {"title": "T"},
        "layout": {
            "name": {"label": "Name", "format_mask": "str", "alignment": "left"},
            "status": {
                "label": "Status",
                "format_mask": "str",
                "alignment": "left",
                "missing_text": "unknown",
                "substitutions": {"A": "Active"},
            },
        },
        "data": [{"name": "x", "status": None}, {"name": "y", "status": "A"}],
    }
    payload.update(overrides)
    return payload


def test_missing_text_and_substitutions_in_cells():
    html = render_html(_payload())
    assert "unknown" in html
    assert "Active" in html


def test_empty_detail_table_message():
    payload = {
        "meta": {"title": "T"},
        "layout": {
            "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
            "orders": {
                "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
                "empty_text": "No orders in the period",
            },
        },
        "data": [{"company": "ACME", "orders": []}],
    }
    html = render_html(payload)
    assert "No orders in the period" in html
    assert "<table" not in html


def test_empty_detail_without_message_renders_nothing():
    payload = {
        "meta": {"title": "T"},
        "layout": {
            "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
            "orders": {"order": {"label": "Code", "format_mask": "int", "alignment": "right"}},
        },
        "data": [{"company": "ACME", "orders": []}],
    }
    html = render_html(payload)
    assert "<table" not in html
    assert '<p class="empty-table"' not in html


def test_meta_empty_text_for_empty_report():
    html = render_html({"meta": {"title": "T", "empty_text": "No data at all"}, "data": []})
    assert "No data at all" in html


def test_section_table_empty_text():
    html = render_html(
        {
            "meta": {"title": "T"},
            "sections": [{"type": "table", "title": "Moves", "layout": {}, "data": [], "empty_text": "No moves"}],
        }
    )
    assert "No moves" in html
