"""Email polish tests: inlined HTML must be email-client safe (no browser needed)."""

import pytest

css_inline = pytest.importorskip("css_inline", reason="needs the 'email' extra")

assert css_inline  # re-export for linters: the import itself is the skip gate


def _sample(accent=None, locale=None):
    from isis_report_lib import render_html

    meta = {"title": "T"}
    if accent is not None:
        meta["accent_color"] = accent
    if locale is not None:
        meta["locale"] = locale
    return render_html({"meta": meta, "data": [{"a": 1}]}, inline_css=True)


def test_inline_css_resolves_css_vars():
    html = _sample()
    assert "var(" not in html
    assert "#0A2F46" in html  # brand color resolved to a literal


def test_inline_css_honors_accent_color():
    html = _sample(accent="#123456")
    assert "var(" not in html
    assert "#123456" in html


def test_html_lang_from_locale():
    from isis_report_lib import render_html

    assert '<html lang="pt-BR"' in render_html({"meta": {"title": "T", "locale": "pt-BR"}, "data": []})
    assert '<html lang="en"' in render_html({"meta": {"title": "T"}, "data": []})
    assert '<html lang="pt-BR"' in _sample(locale="pt-BR")


def test_color_scheme_meta():
    assert 'name="color-scheme" content="light"' in _sample()


def test_resolve_css_vars_unit():
    from isis_report_lib.rendering import _resolve_css_vars

    assert _resolve_css_vars("<style>:root{--a: red;}</style><p>x</p>") == "<style>:root{--a: red;}</style><p>x</p>"
    assert "color:red" in _resolve_css_vars('<style>:root{--a: red;}</style><p style="color:var(--a)">x</p>')
    # fallback when undefined, later :root wins, bare var() kept
    assert "color:blue" in _resolve_css_vars('<p style="color:var(--missing, blue)">x</p>')
    html = _resolve_css_vars('<style>:root{--a: red;}</style><style>:root{--a: green;}</style><p style="color:var(--a)">')
    assert "color:green" in html
    assert "var(--a)" in _resolve_css_vars('<p style="color:var(--a)">x</p>')
