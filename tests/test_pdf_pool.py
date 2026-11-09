"""Unit tests for the Playwright pool state machine (no real browser).

The foreign-loop abandon paths are covered with fakes: they only manipulate
module globals, never a live Chromium process.
"""

import asyncio

import pytest

from isis_report_lib import pdf as pool


@pytest.fixture(autouse=True)
def _isolated_pool(monkeypatch):
    monkeypatch.setattr(pool, "_browser", None)
    monkeypatch.setattr(pool, "_playwright", None)
    monkeypatch.setattr(pool, "_playwright_ctx", None)
    monkeypatch.setattr(pool, "_owner_loop", None)
    yield


class FakeBrowser:
    def __init__(self, connected=True):
        self.connected = connected
        self.closed = False

    def is_connected(self):
        return self.connected

    async def close(self):
        self.closed = True


class ExplodingBrowser(FakeBrowser):
    async def close(self):
        raise RuntimeError("boom")


class BrokenConnectionBrowser(FakeBrowser):
    def is_connected(self):
        raise RuntimeError("dead transport")


def test_browser_usable_when_nothing_started():
    assert pool._browser_usable() is False


def test_browser_usable_rejects_foreign_loop(monkeypatch):
    monkeypatch.setattr(pool, "_browser", FakeBrowser())
    monkeypatch.setattr(pool, "_owner_loop", object())
    assert pool._browser_usable() is False


def test_browser_usable_rejects_broken_connection(monkeypatch):
    async def check():
        monkeypatch.setattr(pool, "_browser", BrokenConnectionBrowser())
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        return pool._browser_usable()

    assert asyncio.run(check()) is False


def test_browser_usable_accepts_healthy_browser(monkeypatch):
    async def check():
        monkeypatch.setattr(pool, "_browser", FakeBrowser())
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        return pool._browser_usable()

    assert asyncio.run(check()) is True


def test_reset_closes_same_loop_browser(monkeypatch):
    async def run():
        browser = FakeBrowser()
        monkeypatch.setattr(pool, "_browser", browser)
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        await pool._reset_unlocked()
        return browser

    browser = asyncio.run(run())
    assert browser.closed is True
    assert pool._browser is None
    assert pool._owner_loop is None


def test_reset_abandons_foreign_loop_browser(monkeypatch):
    async def run():
        browser = FakeBrowser()
        monkeypatch.setattr(pool, "_browser", browser)
        monkeypatch.setattr(pool, "_owner_loop", object())
        await pool._reset_unlocked()
        return browser

    browser = asyncio.run(run())
    assert browser.closed is False
    assert pool._browser is None


def test_reset_survives_close_failure(monkeypatch):
    async def run():
        monkeypatch.setattr(pool, "_browser", ExplodingBrowser())
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        await pool._reset_unlocked()

    asyncio.run(run())
    assert pool._browser is None


def test_close_owned_browser_without_owner_is_noop():
    asyncio.run(pool.close_owned_browser())


def test_ensure_browser_sync_returns_early_when_started(monkeypatch):
    monkeypatch.setattr(pool, "_browser", FakeBrowser())
    pool.ensure_browser_sync()
