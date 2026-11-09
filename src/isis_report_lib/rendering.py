"""Renderização Jinja2 com templates embutidos no pacote."""

from importlib import resources
from typing import Any

from jinja2 import Environment, FileSystemLoader

_env: Environment | None = None


def _templates_dir() -> str:
    # importlib.resources.files funciona com pacote instalado (wheel/sdist)
    return str(resources.files("isis_report_lib") / "templates")


def get_jinja_env() -> Environment:
    """Retorna (singleton) o Environment Jinja2 apontando p/ os templates do pacote."""
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(searchpath=_templates_dir()), autoescape=False)
    return _env


async def arender_report_html(
    ds_items: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "relatorio_tabular.jinja",
) -> str:
    """Renderiza o HTML do relatório (async p/ compatibilidade; Jinja é síncrono)."""
    from isis_report_lib.formatting import format_value

    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(ds_items=ds_items, layout=layout, meta=meta, fmt=format_value, zip=zip)


def render_report_html(
    ds_items: dict[str, Any],
    layout: dict[str, Any],
    meta: dict[str, Any],
    template_name: str = "relatorio_tabular.jinja",
) -> str:
    """Versão síncrona da renderização do HTML."""
    from isis_report_lib.formatting import format_value

    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(ds_items=ds_items, layout=layout, meta=meta, fmt=format_value, zip=zip)
