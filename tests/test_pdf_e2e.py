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
