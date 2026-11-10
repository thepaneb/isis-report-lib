"""HTML rendering tests (no browser needed) and pipeline tests with mocks."""

import re
from unittest.mock import AsyncMock, patch

import pytest

from isis_report_lib import arender_html, render_html, render_html_from_toon
from isis_report_lib.service import TabularReportService

PAYLOAD = {
    "meta": {"title": "Order", "sub_title": "2024", "mode": "exact"},
    "layout": {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "orders": {
            "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
            "total": {"label": "Total", "format_mask": "float", "alignment": "right"},
        },
    },
    "data": [{"company": "ACME", "orders": [{"order": 750, "total": 4000}]}],
}


def test_render_html_sync_contains_values():
    html = render_html(PAYLOAD)
    assert "Order" in html
    assert "ACME" in html
    assert "750" in html
    assert "4.000,00" in html


def test_render_html_respects_meta_locale():
    payload = {
        "meta": {"title": "Order", "mode": "exact", "locale": "en-US"},
        "layout": {
            "total": {"label": "Total", "format_mask": "float", "alignment": "right"},
        },
        "data": [{"total": 4000}],
    }
    html = render_html(payload)
    assert "4,000.00" in html


async def test_arender_html_matches_sync():
    assert await arender_html(PAYLOAD) == render_html(PAYLOAD)


def test_render_html_from_toon():
    html = render_html_from_toon("meta:\n  title: T\n  mode: exact\ndata[1]:\n  - name: John")
    assert "John" in html


def test_accent_color_overrides_brand():
    html = render_html({"meta": {"title": "T", "accent_color": "#FF0000"}, "data": []})
    assert "--brand-color: #FF0000" in html


def test_default_brand_color_without_accent():
    html = render_html({"meta": {"title": "T"}, "data": []})
    assert "--brand-color: #0A2F46" in html
    assert "accent_color" not in html


async def test_generate_pdf_sync_api_inside_running_loop():
    """Sync API called with a running loop uses the helper thread and returns the PDF (mock)."""
    from isis_report_lib import generate_pdf

    with patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf:
        mock_pdf.return_value = b"%PDF-1.4"
        assert generate_pdf(PAYLOAD).startswith(b"%PDF")
        mock_pdf.assert_awaited_once()


def test_render_report_html_sync_entrypoint():
    from isis_report_lib.rendering import render_report_html

    html = render_report_html(dataset={"groups": []}, layout={"groups": {"header": []}}, meta={"title": "T"})
    assert "T" in html


def test_render_with_custom_template_dir(tmp_path):
    tpl = tmp_path / "custom.jinja"
    tpl.write_text("<html><body>CUSTOM:{{ meta.title }}</body></html>", encoding="utf-8")
    html = render_html({"meta": {"title": "Hi"}, "data": []}, template_dir=tmp_path, template_name="custom.jinja")
    assert "CUSTOM:Hi" in html


def test_render_custom_dir_falls_back_to_bundled(tmp_path):
    html = render_html(PAYLOAD, template_dir=tmp_path)
    assert "ACME" in html


def test_render_missing_template_dir_fails():
    with pytest.raises(ValueError, match="Template directory not found"):
        render_html(PAYLOAD, template_dir="/nonexistent-dir")


async def test_generate_with_custom_template_uses_it(tmp_path):
    from unittest.mock import AsyncMock, patch

    tpl = tmp_path / "custom.jinja"
    tpl.write_text("<html><body>CUSTOM</body></html>", encoding="utf-8")
    service = TabularReportService(template_dir=tmp_path, template_name="custom.jinja")
    with patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf:
        mock_pdf.return_value = b"%PDF-1.4"
        assert await service.execute(PAYLOAD) == b"%PDF-1.4"
        (html,) = mock_pdf.call_args.args
        assert "CUSTOM" in html


def test_render_html_infers_layout_without_layout_key():
    html = render_html({"meta": {"title": "T"}, "data": [{"name": "John", "age": 30}]})
    assert "John" in html


async def test_execute_success_with_mocks():
    service = TabularReportService()
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        result = await service.execute(PAYLOAD)
        assert result == b"%PDF-1.4"


async def test_execute_fills_printed_at_by_default():
    service = TabularReportService()
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        await service.execute({"meta": {"title": "T"}, "data": []})
        meta = mock_render.call_args.kwargs["meta"]
        assert meta["title"] == "T"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", meta["printed_at"])


async def test_execute_keeps_explicit_printed_at():
    service = TabularReportService()
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        await service.execute({"meta": {"title": "T", "printed_at": "custom"}, "data": []})
        assert mock_render.call_args.kwargs["meta"]["printed_at"] == "custom"


def test_default_footer_layout():
    from isis_report_lib.pdf import default_footer

    html = default_footer("2024-01-01 10:00")
    assert "powered by" in html
    assert "<svg" in html
    assert "Printed on 2024-01-01 10:00" in html
    assert "pageNumber" in html
    assert html.index("Printed on") < html.index("Page") < html.index("powered by")


def test_default_footer_without_date():
    from isis_report_lib.pdf import default_footer

    assert "pageNumber" in default_footer()
    assert "Printed on" not in default_footer()


async def test_execute_puts_printed_at_in_pdf_footer():
    service = TabularReportService()
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        await service.execute({"meta": {"title": "T", "printed_at": "2024-01-01 10:00"}, "data": []})
        footer = mock_pdf.call_args.kwargs["footer_template"]
        assert "Printed on 2024-01-01 10:00" in footer


async def test_execute_keeps_custom_footer_template():
    service = TabularReportService(pdf_options={"footer_template": "CUSTOM"})
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        await service.execute({"meta": {"title": "T"}, "data": []})
        assert mock_pdf.call_args.kwargs["footer_template"] == "CUSTOM"


async def test_execute_maps_meta_page_to_pdf_options():
    service = TabularReportService()
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        await service.execute({"meta": {"title": "T", "page": {"size": "Letter", "orientation": "landscape"}}, "data": []})
        kwargs = mock_pdf.call_args.kwargs
        assert kwargs["format"] == "Letter"
        assert kwargs["landscape"] is True
        assert kwargs["margin"]["top"] == ".15in"


async def test_execute_explicit_pdf_options_win_over_meta_page():
    service = TabularReportService(pdf_options={"format": "Legal"})
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        await service.execute({"meta": {"title": "T", "page": {"size": "A3"}}, "data": []})
        assert mock_pdf.call_args.kwargs["format"] == "Legal"


async def test_execute_rejects_invalid_orientation():
    service = TabularReportService()
    with (
        patch("isis_report_lib.rendering.arender_report_html", new_callable=AsyncMock) as mock_render,
        patch("isis_report_lib.pdf.get_pdf_from_html", new_callable=AsyncMock) as mock_pdf,
    ):
        mock_render.return_value = "<html>OK</html>"
        mock_pdf.return_value = b"%PDF-1.4"
        with pytest.raises(ValueError, match="Invalid page orientation"):
            await service.execute({"meta": {"title": "T", "page": {"orientation": "diagonal"}}, "data": []})


AGG_PAYLOAD = {
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
                {"order": 2, "total": 2000, "items": [{"qty": 4, "unit_price": 500}]},
                {
                    "order": 1,
                    "total": 4000,
                    "items": [
                        {"qty": 1, "unit_price": 1500},
                        {"qty": 2, "unit_price": 1250},
                    ],
                },
            ],
        }
    ],
}


def test_render_html_with_aggregates_shows_totals():
    html = render_html(AGG_PAYLOAD)
    # Detail tfoot: 1+2 and 4.
    assert "<tfoot>" in html
    # Group footer: 6.000,00. Summary: 6.000,00 and 7.
    assert html.count("6.000,00") >= 2
    assert ">7<" in html


async def test_execute_propagates_render_error():
    service = TabularReportService()
    with patch("isis_report_lib.rendering.arender_report_html", side_effect=ValueError("fail")):
        with pytest.raises(ValueError, match="fail"):
            await service.execute(PAYLOAD)
