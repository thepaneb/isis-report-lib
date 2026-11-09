"""Shared Playwright browser pool (singleton) reused across generations.

Call :func:`close_browser` when shutting down long-lived processes. The pool
is bound to an event loop: state owned by a foreign/closed loop is abandoned,
never awaited (cross-loop close hangs on Linux).
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


def default_footer(printed_at: str | None = None) -> str:
    """Build the PDF page footer: page count on the left, print timestamp on the right."""
    date_html = f"<span>Printed on {printed_at}</span>" if printed_at else "<span></span>"
    return (
        '<div style="width:100%;font-size:10px;display:flex;'
        'justify-content:space-between;align-items:center;padding:0 .4in;">'
        "<span>Page <span class='pageNumber'></span> of <span class='totalPages'></span></span>"
        f"{date_html}</div>"
    )


DEFAULT_FOOTER = default_footer()
DEFAULT_MARGIN = {"top": ".2in", "bottom": ".5in", "left": ".2in", "right": ".2in"}


def _browser_usable() -> bool:
    """True when the browser exists, belongs to the current loop and is connected."""
    if _browser is None:
        return False
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover - always called with a running loop
        return False
    if _owner_loop is not running:
        return False
    try:
        return _browser.is_connected()
    except Exception:
        return False


async def _reset_unlocked() -> None:
    """Close and clear the browser/Playwright without acquiring the lock (caller holds it).

    Critical rule: never await objects owned by another event loop (it can hang
    forever on Linux, even under ``wait_for``). Foreign/closed-loop state is
    abandoned; only same-loop state is closed, with a timeout.
    """

    async def _close_quietly(coro, label: str) -> None:
        try:
            await asyncio.wait_for(coro, timeout=10)
        except Exception:
            logger.warning("Failed to close %s during pool reset; abandoning.", label)

    global _playwright_ctx, _playwright, _browser, _owner_loop
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover - always called with a running loop
        running = None
    same_loop = running is not None and _owner_loop is running

    if _browser is not None:
        if same_loop:
            await _close_quietly(_browser.close(), "browser")
        else:
            logger.warning("Abandoning browser from another event loop without closing (avoids deadlock).")
        _browser = None
    if _playwright_ctx is not None:
        if same_loop:
            await _close_quietly(_playwright_ctx.__aexit__(None, None, None), "playwright")
        _playwright_ctx = None
        _playwright = None
    _owner_loop = None


async def ensure_browser(headless: bool = True) -> None:
    """Ensure the shared browser is started (idempotent).

    If the browser belongs to a different/closed event loop (e.g. test suites
    creating one loop per test), it is recreated on the current loop.
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


def ensure_browser_sync(headless: bool = True) -> None:
    """Start the browser synchronously (schedules a task if a loop is already running)."""
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
    """Return a new Page from the shared browser (close it with ``await page.close()``)."""
    await ensure_browser()
    assert _browser is not None
    return await _browser.new_page()


async def get_pdf_from_html(html: str, **kwargs: Any) -> bytes:
    """Render HTML to PDF via the shared browser pool.

    Accepted kwargs: ``format`` (default ``"A4"``), ``display_header_footer``,
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
    """Close the shared browser and shut down Playwright."""
    global _playwright_ctx, _playwright, _browser, _owner_loop
    async with _lock:
        await _reset_unlocked()


async def close_owned_browser() -> None:
    """Close the browser only if it belongs to the current loop.

    Internal use by the sync API: each ``generate_pdf`` runs on an ephemeral
    loop (``asyncio.run``), so the browser must be shut down at the end of the
    call to avoid leaking Chromium processes. Never touches another loop's
    browser (the async API keeps the pool reusable).
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover - coroutine body needs a running loop
        return
    if _owner_loop is not None and _owner_loop is running:
        await close_browser()
