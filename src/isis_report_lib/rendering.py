"""Jinja2 rendering with templates bundled in the package.

Custom templates can be supplied via ``template_dir``: the directory is
prepended to the loader, so it can override bundled templates (e.g. a custom
``tabular.jinja``) or provide new ones referenced by ``template_name``.

Every template receives: ``dataset``, ``layout``, ``meta``, plus the ``fmt``
value formatter and ``cellstyle``. With ``inline_css=True`` the stylesheet is
inlined and CSS variables are resolved to literal values (email clients such
as Outlook largely ignore ``var()``).
"""

import re
from importlib import resources
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_envs: dict[str | None, Environment] = {}


def _templates_dir() -> str:
    # importlib.resources.files works with an installed package (wheel/sdist).
    return str(resources.files("isis_report_lib") / "templates")


def get_jinja_env(template_dir: str | Path | None = None) -> Environment:
    """Return a Jinja2 environment, optionally layered over a custom template dir.

    Raises:
        ValueError: if ``template_dir`` does not exist.
    """
    key = str(template_dir) if template_dir is not None else None
    if key not in _envs:
        if template_dir is not None and not Path(template_dir).is_dir():
            raise ValueError(f"Template directory not found: {template_dir}")
        searchpath = [str(template_dir), _templates_dir()] if template_dir is not None else [_templates_dir()]
        # Autoescape is ON: report data is untrusted input and the HTML output
        # is also shipped to email clients. Charts/sparklines return Markup (safe SVG).
        _envs[key] = Environment(loader=FileSystemLoader(searchpath=searchpath), autoescape=True)
    return _envs[key]


async def arender_report_html(
    dataset: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "tabular.jinja",
    template_dir: str | Path | None = None,
    inline_css: bool = False,
) -> str:
    """Render the report HTML (async for API parity; Jinja itself is sync).

    ``inline_css=True`` inlines the stylesheet into ``style`` attributes
    (email-client friendly; needs the ``email`` extra).
    """
    from isis_report_lib.formatting import cell_style, formatter_for

    env = get_jinja_env(template_dir)
    template = env.get_template(template_name)
    html = template.render(dataset=dataset, layout=layout, meta=meta, fmt=formatter_for(meta), cellstyle=cell_style, zip=zip)
    return _inline_css(html) if inline_css else html


def render_report_html(
    dataset: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "tabular.jinja",
    template_dir: str | Path | None = None,
    inline_css: bool = False,
) -> str:
    """Synchronous version of the HTML rendering (see :func:`arender_report_html`)."""
    from isis_report_lib.formatting import cell_style, formatter_for

    env = get_jinja_env(template_dir)
    template = env.get_template(template_name)
    html = template.render(dataset=dataset, layout=layout, meta=meta, fmt=formatter_for(meta), cellstyle=cell_style, zip=zip)
    return _inline_css(html) if inline_css else html


def _resolve_css_vars(html: str) -> str:
    """Replace ``var(--name[, fallback])`` with the ``:root`` value or fallback.

    Email clients (notably Outlook) ignore CSS variables, while the bundled
    templates style everything through them. Later ``:root`` blocks win, so a
    ``meta.accent_color`` override is honored.
    """
    variables: dict[str, str] = {}
    for block in re.findall(r":root\s*\{([^}]*)\}", html):
        for name, value in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", block):
            variables[name] = value.strip()

    def _replace(match: re.Match[str]) -> str:
        name, fallback = match.group(1), match.group(2)
        if name in variables:
            return variables[name]
        return fallback.strip() if fallback is not None else match.group(0)

    return re.sub(r"var\(\s*--([\w-]+)\s*(?:,\s*([^)]*))?\)", _replace, html)


def _inline_css(html: str) -> str:
    """Inline a document's stylesheet (lazy optional dependency).

    External ``<link rel=stylesheet>`` tags are stripped first: email clients
    ignore them, and fetching them would turn report rendering into a
    server-side request forgery (SSRF) vector for attacker-controlled data.
    """
    try:
        import css_inline
    except ImportError as e:
        raise ImportError("Inline CSS requires the 'email' extra: pip install isis-report-lib[email]") from e
    no_links = re.sub(r"<link\b[^>]*>", "", html, flags=re.IGNORECASE)
    return css_inline.inline(_resolve_css_vars(no_links))
