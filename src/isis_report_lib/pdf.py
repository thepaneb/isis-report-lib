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
    """Build the PDF page footer: timestamp left, page count center, brand right."""
    date_html = f"<span>Printed on {printed_at}</span>" if printed_at else "<span></span>"
    return (
        '<div style="width:100%;font-size:10px;display:flex;'
        'justify-content:space-between;align-items:center;padding:0 .4in;">'
        f"{date_html}"
        "<span>Page <span class='pageNumber'></span> of <span class='totalPages'></span></span>"
        "<span>powered by "
        '<svg width="28" height="28" viewBox="0 0 86 86" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle">'
        '<path d="M27.3331 25.9999C22.9331 27.8666 18.2665 29.3332 17.0665 29.3332C15.7332 29.3332 14.6665 30.2666 14.6665 31.4666C14.6665 33.9999 19.8665 33.0666 28.5331 29.1999C35.5998 25.9999 44.9331 25.9999 52.133 29.3332C55.733 30.9332 58.533 31.3332 59.1997 30.6666C60.7997 29.0666 60.7997 29.0666 52.3997 25.5999C43.4664 21.8666 37.1997 21.9999 27.3331 25.9999Z" fill="#0A2F46"/>'
        '<path d="M64.7998 23.8666C62.9331 24.5333 62.6664 25.1999 63.7331 25.8666C64.9331 26.5332 62.9331 29.7332 57.3331 35.9999C50.3998 43.7332 48.7998 45.0665 46.7998 43.7332C44.9332 42.5332 43.1998 43.7332 36.2665 50.5332C28.7999 58.1331 27.5999 58.7998 23.0666 58.3998C18.7999 58.1331 17.8666 57.4665 17.5999 54.6665C17.1999 51.8665 17.3333 51.7332 19.1999 53.1998C21.3333 55.0665 25.3332 54.3998 25.3332 52.1331C25.3332 49.5998 21.3333 46.9332 18.5333 47.5998C15.0666 48.5332 13.3333 53.0665 14.9333 57.3331C16.5333 61.4664 18.2666 62.6664 23.4666 62.6664C27.7332 62.6664 35.3332 57.8665 41.1999 51.4665C44.1332 48.3998 44.6665 48.2665 46.6665 49.9998C48.6665 51.7331 49.7332 50.9332 58.1331 41.3332C63.1998 35.4665 68.2664 30.7999 69.3331 31.0666C70.6664 31.1999 71.4664 29.9999 71.7331 26.9332C72.1331 22.3999 70.3997 21.5999 64.7998 23.8666Z" fill="#0A2F46"/>'
        '<path d="M27.9998 32.6666C23.9998 34.3999 19.3332 35.8666 17.7332 35.9999C13.7332 35.9999 13.5999 39.9999 17.4665 39.9999C19.0665 39.9999 23.8665 41.5999 28.1331 43.4665C33.0665 45.7332 36.7998 46.6665 38.2664 45.9999C40.2664 45.1999 40.2664 44.9332 38.6664 44.3999C37.5998 43.9999 33.9998 42.5332 30.6665 41.0665L24.6665 38.3999L29.9998 35.8666C35.3331 33.4666 35.3331 33.4666 35.9998 36.2666C37.0664 40.3999 40.6664 42.2665 43.1997 40.1332C44.3997 39.0665 45.3331 37.1999 45.3331 35.8666C45.3331 33.4666 45.5997 33.4666 49.8664 35.1999C54.133 36.9332 55.9997 36.7999 55.9997 34.5332C55.9997 32.7999 45.3331 29.3333 40.2664 29.3333C37.5998 29.4666 31.9998 30.9332 27.9998 32.6666ZM41.5998 36.2666C39.5998 38.2666 38.1331 36.7999 39.1998 33.8666C39.8664 32.1332 40.3998 31.8666 41.5998 33.0666C42.7997 34.2666 42.7997 35.0666 41.5998 36.2666ZM52.133 50.5332C49.3331 54.3998 48.2664 61.3331 50.3997 61.3331C51.5997 61.3331 60.533 50.6665 59.8663 50.2665C59.5997 49.9998 58.3997 49.1998 57.0664 48.2665C55.1997 46.7999 54.533 47.1999 52.133 50.5332Z" fill="#0A2F46"/>'
        "</svg></span></div>"
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
