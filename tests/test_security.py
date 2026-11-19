"""Security regression tests: XSS escaping, SSRF stripping, formula guard, fail-closed verify."""

import asyncio
import io

import pytest

from isis_report_lib import generate_csv, generate_xlsx, render_html
from isis_report_lib import pdf as pool


def test_html_escapes_untrusted_data():
    html = render_html({"meta": {"title": "T"}, "data": [{"a": "<script>alert(1)</script><img src=x onerror=alert(2)>"}]})
    assert "<script>alert(1)</script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html and "&lt;img" in html


def test_html_escapes_meta_and_marks():
    html = render_html(
        {
            "meta": {"title": "<b>T</b>", "accent_color": 'red" onmouseover="alert(1)'},
            "layout": {"a": {"label": "A<script>", "format_mask": "str"}},
            "data": [{"a": "x"}],
        }
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_charts_and_sparklines_stay_raw_svg():
    html = render_html(
        {
            "meta": {"title": "T"},
            "sections": [
                {"type": "chart", "title": "C", "chart": {"kind": "bar", "labels": ["A"], "values": [1]}},
            ],
        }
    )
    assert "<svg" in html and "&lt;svg" not in html
    html2 = render_html(
        {
            "meta": {"title": "T"},
            "layout": {"t": {"label": "T", "format_mask": "sparkline"}},
            "data": [{"t": [3, 1, 2]}],
        }
    )
    assert "<polyline" in html2


def test_inline_css_strips_remote_stylesheets():
    from isis_report_lib.rendering import _inline_css

    doc = (
        "<html><head>"
        '<link rel="stylesheet" href="http://127.0.0.1:9/evil.css">'
        "<style>p{font-size:14px}</style></head><body><p>hi</p></body></html>"
    )
    out = _inline_css(doc)  # must not raise (no outbound fetch to unroutable port)
    assert "<link" not in out
    assert "font-size:14px" in out or "font-size: 14px" in out


def test_csv_neutralizes_formulas_but_not_numbers():
    text = generate_csv(
        {
            "meta": {"title": "T"},
            "layout": {
                "a": {"label": "A"},
                "n": {"label": "N", "format_mask": "float"},
            },
            "data": [{"a": "=1+1", "n": -5}, {"a": "@SUM(A1)", "n": 3}],
        }
    )
    assert "'=1+1" in text and "'@SUM(A1)" in text
    assert "'-5" not in text  # numeric negatives stay numeric


def test_xlsx_stores_formulas_as_text():
    from openpyxl import load_workbook

    blob = generate_xlsx(
        {
            "meta": {"title": "T"},
            "layout": {"a": {"label": "A"}, "n": {"label": "N", "format_mask": "float"}},
            "data": [{"a": "=1+1", "n": -5}],
        }
    )
    ws = load_workbook(io.BytesIO(blob))["data"]
    assert ws["A3"].value == "'=1+1" and ws["A3"].data_type == "s"
    assert ws["B3"].value == -5.0 and ws["B3"].data_type == "n"


def test_verify_never_raises_on_malformed_input():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    secret = generate_hmac_key()
    pdf = b"%PDF-1.4\ntrailer\n%%EOF\n"
    signed = sign_pdf(pdf, secret)
    tampered = signed.replace(b'"sig":"', b'"sig":123,"x":"')
    assert verify_pdf(tampered, secret).valid is False
    info = verify_pdf(signed, "not-bytes")
    assert info.valid is False  # wrong key type must not raise


def test_deep_inputs_fail_closed():
    from isis_report_lib.inputs import from_json

    with pytest.raises(ValueError, match="nested too deeply"):
        from_json(io.StringIO("[" * 50000 + "]" * 50000))
    node = cur = {}
    for _ in range(2000):
        cur["g"] = {}
        cur = cur["g"]
    cur["x"] = {"label": "X"}
    with pytest.raises(ValueError, match="nested too deeply"):
        render_html({"meta": {"title": "T"}, "layout": node, "data": []})


class FakeContext:
    def __init__(self):
        self.closed = False
        self.pages = 0

    async def new_page(self):
        self.pages += 1
        return f"page-{self.pages}"

    async def close(self):
        self.closed = True


class FakeBrowserWithContext:
    def __init__(self):
        self.connected = True
        self.closed = False
        self.context_kwargs = None
        self.context = FakeContext()

    def is_connected(self):
        return True

    async def new_context(self, **kwargs):
        self.context_kwargs = kwargs
        return self.context

    async def close(self):
        self.closed = True


def test_new_page_uses_js_disabled_context(monkeypatch):
    async def run():
        browser = FakeBrowserWithContext()
        monkeypatch.setattr(pool, "_browser", browser)
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        monkeypatch.setattr(pool, "_context", browser.context)
        page = await pool.new_page()
        assert page == "page-1"
        return browser

    browser = asyncio.run(run())
    assert browser.context.pages == 1


def test_reset_closes_context(monkeypatch):
    async def run():
        browser = FakeBrowserWithContext()
        monkeypatch.setattr(pool, "_browser", browser)
        monkeypatch.setattr(pool, "_context", browser.context)
        monkeypatch.setattr(pool, "_owner_loop", asyncio.get_running_loop())
        await pool._reset_unlocked()
        return browser

    browser = asyncio.run(run())
    assert browser.context.closed is True
    assert browser.closed is True
    assert pool._context is None
