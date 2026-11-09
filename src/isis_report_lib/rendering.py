"""Jinja2 rendering with templates bundled in the package."""

from importlib import resources
from typing import Any

from jinja2 import Environment, FileSystemLoader

_env: Environment | None = None


def _templates_dir() -> str:
    # importlib.resources.files works with an installed package (wheel/sdist).
    return str(resources.files("isis_report_lib") / "templates")


def get_jinja_env() -> Environment:
    """Return the (singleton) Jinja2 environment pointing at the package templates."""
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(searchpath=_templates_dir()), autoescape=False)
    return _env


async def arender_report_html(
    dataset: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "tabular.jinja",
) -> str:
    """Render the report HTML (async for API parity; Jinja itself is sync)."""
    from isis_report_lib.formatting import format_value

    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(dataset=dataset, layout=layout, meta=meta, fmt=format_value, zip=zip)


def render_report_html(
    dataset: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "tabular.jinja",
) -> str:
    """Synchronous version of the HTML rendering."""
    from isis_report_lib.formatting import format_value

    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(dataset=dataset, layout=layout, meta=meta, fmt=format_value, zip=zip)
