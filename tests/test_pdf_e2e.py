"""Teste fim-a-fim com browser real. Requer `playwright install chromium`.

Pulados automaticamente se o Chromium não estiver instalado.
"""

import shutil
from pathlib import Path

import pytest

from isis_report_lib import generate_pdf, generate_pdf_from_toon

pytestmark = pytest.mark.browser


def _browser_available() -> bool:
    if shutil.which("chromium") or shutil.which("chrome"):
        return True
    ms_playwright = Path.home() / "AppData" / "Local" / "ms-playwright"
    return any(ms_playwright.glob("chromium*"))


needs_chromium = pytest.mark.skipif(
    not _browser_available(),
    reason="Chromium não encontrado (rode `playwright install chromium`)",
)

PAYLOAD = {
    "meta": {"title": "Pedido", "mode": "exact"},
    "layout": {"produto": {"label": "Produto", "format_mask": "str", "alignment": "left"}},
    "data": [{"produto": "Caneta"}],
}


@needs_chromium
async def test_agenerate_pdf_starts_with_pdf_magic():
    from isis_report_lib import agenerate_pdf

    pdf = await agenerate_pdf(PAYLOAD)
    assert pdf.startswith(b"%PDF")


@needs_chromium
def test_generate_pdf_from_toon():
    pdf = generate_pdf_from_toon("meta:\n  title: T\n  mode: exact\ndados[1]:\n  - produto: Caneta")
    assert pdf.startswith(b"%PDF")


@needs_chromium
def test_generate_pdf_sync():
    assert generate_pdf(PAYLOAD).startswith(b"%PDF")
