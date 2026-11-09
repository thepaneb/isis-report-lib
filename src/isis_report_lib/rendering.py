"""Jinja2 rendering with templates bundled in the package.

Custom templates can be supplied via ``template_dir``: the directory is
prepended to the loader, so it can override bundled templates (e.g. a custom
``tabular.jinja``) or provide new ones referenced by ``template_name``.

Every template receives: ``dataset``, ``layout``, ``meta``, plus the ``fmt``
value formatter and ``zip``.
"""

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
        _envs[key] = Environment(loader=FileSystemLoader(searchpath=searchpath), autoescape=False)
    return _envs[key]


async def arender_report_html(
    dataset: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "tabular.jinja",
    template_dir: str | Path | None = None,
) -> str:
    """Render the report HTML (async for API parity; Jinja itself is sync)."""
    from isis_report_lib.formatting import format_value

    env = get_jinja_env(template_dir)
    template = env.get_template(template_name)
    return template.render(dataset=dataset, layout=layout, meta=meta, fmt=format_value, zip=zip)


def render_report_html(
    dataset: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "tabular.jinja",
    template_dir: str | Path | None = None,
) -> str:
    """Synchronous version of the HTML rendering."""
    from isis_report_lib.formatting import format_value

    env = get_jinja_env(template_dir)
    template = env.get_template(template_name)
    return template.render(dataset=dataset, layout=layout, meta=meta, fmt=format_value, zip=zip)
