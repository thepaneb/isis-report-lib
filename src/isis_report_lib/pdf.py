"""Pool singleton de browser Playwright (extraído do POC isis_report).

Reuso do Chromium entre gerações; chame :func:`close_browser` ao encerrar
testes/scripts longos.
"""

import asyncio
import logging
from typing import Any

from playwright.async_api import Browser, Playwright, async_playwright

logger = logging.getLogger("isis_report_lib")

_playwright_ctx = None
_playwright: Playwright | None = None
_browser: Browser | None = None
_owner_loop: asyncio.AbstractEventLoop | None = None
_lock = asyncio.Lock()

DEFAULT_FOOTER = (
    '<div style="width:100%;text-align:center;font-size:10px;">'
    "Página <span class='pageNumber'></span> de <span class='totalPages'></span></div>"
)
DEFAULT_MARGIN = {"top": ".2in", "bottom": ".5in", "left": ".2in", "right": ".2in"}


def _browser_usable() -> bool:
    """True se o browser existe, pertence ao loop atual e está conectado."""
    if _browser is None:
        return False
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        return False
    if _owner_loop is not running:
        return False
    try:
        return _browser.is_connected()
    except Exception:
        return False


async def _reset_unlocked() -> None:
    """Fecha e limpa o browser/Playwright sem adquirir o lock (chamador já o detém).

    Regra crítica: nunca se dá ``await`` em objetos de outro event loop (pode
    bloquear para sempre no Linux, mesmo com ``wait_for``). Estado de loop
    alheio/encerrado é apenas abandonado; o caso mesmo-loop fecha com timeout.
    """

    async def _close_quietly(coro, label: str) -> None:
        try:
            await asyncio.wait_for(coro, timeout=10)
        except Exception:
            logger.warning("Falha ao fechar %s durante reset do pool; abandonando.", label)

    global _playwright_ctx, _playwright, _browser, _owner_loop
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    same_loop = running is not None and _owner_loop is running

    if _browser is not None:
        if same_loop:
            await _close_quietly(_browser.close(), "browser")
        else:
            logger.warning("Abandonando browser de outro event loop sem fechar (evita deadlock).")
        _browser = None
    if _playwright_ctx is not None:
        if same_loop:
            await _close_quietly(_playwright_ctx.__aexit__(None, None, None), "playwright")
        _playwright_ctx = None
        _playwright = None
    _owner_loop = None


async def ensure_browser(headless: bool = True) -> None:
    """Garante o browser compartilhado iniciado (idempotente).

    Se o browser pertence a um event loop diferente/encerrado (ex.: suítes
    de teste que criam um loop por teste), ele é recriado no loop atual.
    """
    global _playwright_ctx, _playwright, _browser, _owner_loop
    async with _lock:
        if _browser_usable():
            return
        await _reset_unlocked()
        _playwright_ctx = async_playwright()
        _playwright = await _playwright_ctx.__aenter__()
        _browser = await _playwright.chromium.launch(headless=headless)
        _owner_loop = asyncio.get_running_loop()


_ensure_browser = ensure_browser  # alias p/ compatibilidade com o POC


def ensure_browser_sync(headless: bool = True) -> None:
    """Garante o browser de forma síncrona (agenda task se houver loop ativo)."""
    if _browser is not None:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(ensure_browser(headless=headless))
        else:
            loop.run_until_complete(ensure_browser(headless=headless))
    except RuntimeError:
        asyncio.run(ensure_browser(headless=headless))


async def new_page():
    """Retorna uma nova Page do browser compartilhado (feche com ``await page.close()``)."""
    await _ensure_browser()
    assert _browser is not None
    return await _browser.new_page()


async def get_pdf_from_html(html: str, **kwargs: Any) -> bytes:
    """Renderiza HTML em PDF via browser compartilhado.

    kwargs aceitos: ``format`` (default ``"A4"``), ``display_header_footer``,
    ``header_template``, ``footer_template``, ``margin``.
    """
    page = await new_page()
    try:
        await page.set_content(html)
        return await page.pdf(
            format=kwargs.get("format", "A4"),
            display_header_footer=kwargs.get("display_header_footer", True),
            header_template=kwargs.get("header_template", ""),
            footer_template=kwargs.get("footer_template", DEFAULT_FOOTER),
            margin=kwargs.get("margin", DEFAULT_MARGIN),
        )
    finally:
        await page.close()


async def close_browser() -> None:
    """Fecha o browser compartilhado e encerra o Playwright."""
    global _playwright_ctx, _playwright, _browser, _owner_loop
    async with _lock:
        await _reset_unlocked()


async def close_owned_browser() -> None:
    """Fecha o browser somente se pertencer ao loop atual.

    Uso interno da API síncrona: cada ``generate_pdf`` roda em um loop
    efêmero (``asyncio.run``), então o browser deve ser encerrado ao final
    da chamada para não vazar processos Chromium. Nunca toca em browser
    de outro loop (a API async mantém o pool reutilizável).
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _owner_loop is not None and _owner_loop is running:
        await close_browser()
