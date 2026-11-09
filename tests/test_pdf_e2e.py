"""Teste fim-a-fim com browser real. Requer `playwright install chromium`.

Pulados automaticamente se o Chromium não estiver instalado.

Todos os testes são async e compartilham o loop de sessão
(`asyncio_default_test_loop_scope = "session"` no pyproject): o pool do
Playwright é preso ao event loop, então trocar de loop entre testes causa
close cross-loop, que trava no Linux.
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
    reason="Chromium não encontrado (rode `playwright install chromium`)",
)

PAYLOAD = {
    "meta": {"title": "Pedido", "mode": "exact"},
    "layout": {"produto": {"label": "Produto", "format_mask": "str", "alignment": "left"}},
    "data": [{"produto": "Caneta"}],
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
    pdf = await agenerate_pdf_from_toon("meta:\n  title: T\n  mode: exact\ndados[1]:\n  - produto: Caneta")
    assert pdf.startswith(b"%PDF")


@needs_chromium
async def test_agenerate_pdf_reuses_shared_browser():
    # Segundo uso no mesmo loop: exercita o reuso do pool sem recriar o browser.
    assert (await agenerate_pdf(PAYLOAD)).startswith(b"%PDF")
    assert (await agenerate_pdf(PAYLOAD)).startswith(b"%PDF")
