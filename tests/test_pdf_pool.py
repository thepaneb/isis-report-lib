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
    monkeypatch.setattr(pool, "_context", None)
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
    async def check():
        monkeypatch.setattr(pool, "_browser", FakeBrowser())
        monkeypatch.setattr(pool, "_owner_loop", object())
        return pool._browser_usable()

    assert asyncio.run(check()) is False


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


def test_is_host_allowed_non_network_schemes():
    assert pool.is_host_allowed("data:image/png;base64,AAA", None) is True
    assert pool.is_host_allowed("blob:https://example.com/uuid", []) is True
    assert pool.is_host_allowed("file:///etc/hosts", None) is True
    assert pool.is_host_allowed("about:blank", None) is True


def test_is_host_allowed_default_deny():
    assert pool.is_host_allowed("http://example.com/x.png", None) is False
    assert pool.is_host_allowed("https://example.com/", []) is False
    assert pool.is_host_allowed("http://127.0.0.1:9/x", None) is False


def test_is_host_allowed_listed_host_exact_match():
    assert pool.is_host_allowed("https://fonts.example.com/css", ["fonts.example.com"]) is True
    assert pool.is_host_allowed("https://Fonts.Example.COM/css", ["fonts.example.com"]) is True
    assert pool.is_host_allowed("http://example.com./x", ["example.com"]) is True
    # no subdomain wildcards: parent does not cover children and vice versa
    assert pool.is_host_allowed("https://fonts.example.com/css", ["example.com"]) is False
    assert pool.is_host_allowed("https://example.com/", ["fonts.example.com"]) is False
    assert pool.is_host_allowed("https://evil.com/?next=example.com", ["example.com"]) is False


def test_validate_allowed_hosts_rejects_garbage():
    for bad in (
        "example.com",
        123,
        [123],
        [""],
        ["   "],
        ["https://example.com"],
        ["http://example.com"],
        ["example.com/path"],
        ["example.com:8080"],
        ["*.example.com"],
        [".example.com"],
        ["exa mple.com"],
        ["user@example.com"],
        ["[::1]"],
    ):
        with pytest.raises(ValueError, match="allowed_hosts"):
            pool.validate_allowed_hosts(bad)


def test_validate_allowed_hosts_normalizes():
    assert pool.validate_allowed_hosts(None) is None
    assert pool.validate_allowed_hosts([]) == []
    assert pool.validate_allowed_hosts([" Example.COM. "]) == ["example.com"]
    assert pool.validate_allowed_hosts(("a.example", "b.example")) == ["a.example", "b.example"]


class FakeRequest:
    def __init__(self, url):
        self.url = url


class FakeRoute:
    def __init__(self, url):
        self.request = FakeRequest(url)
        self.continued = False
        self.aborted = False

    async def continue_(self):
        self.continued = True

    async def abort(self):
        self.aborted = True


def test_guard_outbound_continues_listed_and_aborts_rest():
    async def run():
        allowed = ["fonts.example.com"]
        listed = FakeRoute("https://fonts.example.com/css?family=x")
        await pool._guard_outbound(listed, allowed)
        unlisted = FakeRoute("http://evil.example.net/steal?d=1")
        await pool._guard_outbound(unlisted, allowed)
        inline = FakeRoute("data:image/png;base64,AAA")
        await pool._guard_outbound(inline, allowed)
        denied = FakeRoute("https://example.com/x.png")
        await pool._guard_outbound(denied, None)
        return listed, unlisted, inline, denied

    listed, unlisted, inline, denied = asyncio.run(run())
    assert listed.continued and not listed.aborted
    assert unlisted.aborted and not unlisted.continued
    assert inline.continued and not inline.aborted
    assert denied.aborted and not denied.continued


class FakeGuardedPage:
    def __init__(self):
        self.routes: list[tuple[str, object]] = []
        self.html = ""

    async def route(self, pattern, handler):
        self.routes.append((pattern, handler))

    async def set_content(self, html):
        self.html = html

    async def pdf(self, **kwargs):
        assert "allowed_hosts" not in kwargs  # policy is enforced via routes, not passed to Chromium
        return b"%PDF-mock"

    async def close(self):
        pass


class FakeGuardedContext:
    def __init__(self, page):
        self._page = page

    async def new_page(self):
        return self._page


def test_get_pdf_from_html_registers_route_guard(monkeypatch):
    async def run():
        page = FakeGuardedPage()
        monkeypatch.setattr(pool, "_browser", FakeBrowser())
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        monkeypatch.setattr(pool, "_context", FakeGuardedContext(page))
        pdf = await pool.get_pdf_from_html("<html></html>", allowed_hosts=["example.com"])
        assert pdf == b"%PDF-mock"
        return page

    page = asyncio.run(run())
    assert len(page.routes) == 1
    pattern, handler = page.routes[0]
    assert pattern == "**/*"

    async def exercise():
        listed = FakeRoute("https://example.com/a.png")
        await handler(listed)
        unlisted = FakeRoute("http://evil.test/a.png")
        await handler(unlisted)
        return listed, unlisted

    listed, unlisted = asyncio.run(exercise())
    assert listed.continued and not listed.aborted
    assert unlisted.aborted and not unlisted.continued


def test_get_pdf_from_html_rejects_bad_policy(monkeypatch):
    async def run():
        monkeypatch.setattr(pool, "_browser", FakeBrowser())
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        monkeypatch.setattr(pool, "_context", FakeGuardedContext(FakeGuardedPage()))
        with pytest.raises(ValueError, match="allowed_hosts"):
            await pool.get_pdf_from_html("<html></html>", allowed_hosts=["https://example.com"])

    asyncio.run(run())
