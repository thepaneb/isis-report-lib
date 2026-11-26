"""End-to-end test with a real browser. Requires `playwright install chromium`.

Automatically skipped when Chromium is not installed.
"""

import shutil
import sys
from pathlib import Path

import pytest

from isis_report_lib import agenerate_pdf, agenerate_pdf_from_toon

pytestmark = pytest.mark.browser


def _browser_available() -> bool:
    if shutil.which("chromium") or shutil.which("chrome") or shutil.which("google-chrome"):
        return True
    if sys.platform.startswith("win"):
        candidates = [Path.home() / "AppData" / "Local" / "ms-playwright"]
    elif sys.platform == "darwin":
        candidates = [Path.home() / "Library" / "Caches" / "ms-playwright"]
    else:
        candidates = [Path.home() / ".cache" / "ms-playwright"]
    return any(c.is_dir() and any(c.glob("chromium*")) for c in candidates)


needs_chromium = pytest.mark.skipif(
    not _browser_available(),
    reason="Chromium not found (run `playwright install chromium`)",
)

PAYLOAD = {
    "meta": {"title": "Order", "mode": "exact"},
    "layout": {"product": {"label": "Product", "format_mask": "str", "alignment": "left"}},
    "data": [{"product": "Pen"}],
}


@pytest.fixture(scope="session", autouse=True)
async def _clean_browser():
    yield
    from isis_report_lib.pdf import close_browser

    await close_browser()


@needs_chromium
async def test_agenerate_pdf_starts_with_pdf_magic():
    pdf = await agenerate_pdf(PAYLOAD)
    assert pdf.startswith(b"%PDF")


@needs_chromium
async def test_agenerate_pdf_from_toon():
    pdf = await agenerate_pdf_from_toon("meta:\n  title: T\n  mode: exact\ndata[1]:\n  - product: Pen")
    assert pdf.startswith(b"%PDF")


@needs_chromium
async def test_agenerate_pdf_reuses_shared_browser():
    # Second call on the same loop: exercises pool reuse without relaunching the browser.
    assert (await agenerate_pdf(PAYLOAD)).startswith(b"%PDF")
    assert (await agenerate_pdf(PAYLOAD)).startswith(b"%PDF")


@needs_chromium
async def test_pdf_with_logo_watermark_toc_and_image():
    png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    payload = {
        "meta": {"title": "T", "company": "ACME", "logo": png, "watermark": {"text": "DRAFT", "opacity": 0.1}},
        "sections": [
            {"type": "toc", "title": "Contents"},
            {"type": "text", "title": "Intro", "paragraphs": ["Hello."]},
            {"type": "image", "title": "Logo", "src": png, "alt": "ACME logo", "width": 80},
            {
                "type": "table",
                "title": "Sales",
                "layout": {"product": {"label": "Product", "format_mask": "str", "alignment": "left"}},
                "data": [{"product": "Pen"}],
            },
        ],
    }
    pdf = await agenerate_pdf(payload)
    assert pdf.startswith(b"%PDF")
    assert b"/Outlines" in pdf


@needs_chromium
async def test_agenerate_many_e2e():
    from isis_report_lib import agenerate_many

    results = await agenerate_many([PAYLOAD, PAYLOAD, PAYLOAD], max_concurrency=2)
    assert len(results) == 3
    assert all(pdf.startswith(b"%PDF") for pdf in results)


@needs_chromium
async def test_outbound_blocked_by_default_and_allowed_per_host(tmp_path):
    """Deny-by-default route guard, verified against a hermetic local server."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    hits: list[str] = []
    pixel = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01"
        b"\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(pixel)))
            self.end_headers()
            self.wfile.write(pixel)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        tpl = tmp_path / "img.jinja"
        tpl.write_text(f'<html><body><img src="http://127.0.0.1:{port}/p.png"></body></html>', encoding="utf-8")
        payload = {"meta": {"title": "T"}, "data": []}
        denied = await agenerate_pdf(payload, template_dir=tmp_path, template_name="img.jinja")
        assert denied.startswith(b"%PDF")
        assert hits == []
        allowed = await agenerate_pdf(payload, template_dir=tmp_path, template_name="img.jinja", allowed_hosts=["127.0.0.1"])
        assert allowed.startswith(b"%PDF")
        assert hits == ["/p.png"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
