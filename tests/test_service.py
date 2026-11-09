"""HTML rendering tests (no browser needed) and pipeline tests with mocks."""

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


async def test_arender_html_matches_sync():
    assert await arender_html(PAYLOAD) == render_html(PAYLOAD)


def test_render_html_from_toon():
    html = render_html_from_toon("meta:\n  title: T\n  mode: exact\ndata[1]:\n  - name: John")
    assert "John" in html


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


async def test_execute_propagates_render_error():
    service = TabularReportService()
    with patch("isis_report_lib.rendering.arender_report_html", side_effect=ValueError("fail")):
        with pytest.raises(ValueError, match="fail"):
            await service.execute(PAYLOAD)
