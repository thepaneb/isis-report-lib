"""API pública da lib (sync + async)."""

import asyncio
from typing import Any

from isis_report_lib.models import ReportPayload
from isis_report_lib.service import TabularReportService
from isis_report_lib.toon import parse_toon


def _normalize_payload(payload: dict[str, Any] | ReportPayload) -> dict[str, Any]:
    if isinstance(payload, ReportPayload):
        return payload.model_dump()
    return dict(payload)


def _run(coro):
    """Executa a coroutine e encerra o browser do loop efêmero (evita vazar Chromium).

    A API async reutiliza o pool entre chamadas; a sync abre/fecha por chamada.
    """
    from isis_report_lib.pdf import close_owned_browser

    async def _scoped():
        try:
            return await coro
        finally:
            await close_owned_browser()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_scoped())
    # Há um loop ativo (ex.: Jupyter): executa em thread separada p/ não travar.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(_scoped())).result()


async def agenerate_pdf(
    payload: dict[str, Any] | ReportPayload,
    pdf_options: dict[str, Any] | None = None,
) -> bytes:
    """Gera PDF (async) a partir de payload dict/ReportPayload."""
    service = TabularReportService(pdf_options=pdf_options)
    return await service.execute(_normalize_payload(payload))


def generate_pdf(
    payload: dict[str, Any] | ReportPayload,
    pdf_options: dict[str, Any] | None = None,
) -> bytes:
    """Gera PDF (sync) a partir de payload dict/ReportPayload."""
    return _run(agenerate_pdf(payload, pdf_options))


async def agenerate_pdf_from_toon(
    text: str,
    pdf_options: dict[str, Any] | None = None,
) -> bytes:
    """Gera PDF (async) a partir de texto `.toon`."""
    return await agenerate_pdf(parse_toon(text), pdf_options)


def generate_pdf_from_toon(
    text: str,
    pdf_options: dict[str, Any] | None = None,
) -> bytes:
    """Gera PDF (sync) a partir de texto `.toon`."""
    return _run(agenerate_pdf_from_toon(text, pdf_options))


async def arender_html(payload: dict[str, Any] | ReportPayload) -> str:
    """Renderiza só o HTML intermediário (async, sem Playwright)."""
    from isis_report_lib.layout import convert_data, convert_layout, infer_layout

    data = _normalize_payload(payload)
    raw = data.get("data", [])
    layout_raw = data.get("layout")
    meta = data.get("meta", {})
    if layout_raw:
        layout = convert_layout(layout_raw)
        ds_items = convert_data(raw, layout_raw)
    else:
        from isis_report_lib.layout import is_template_format

        layout = infer_layout(raw)
        if is_template_format(raw):
            ds_items = {"groups": raw}
        else:
            ds_items = {"groups": [{"fields": r} if isinstance(r, dict) else {"fields": {"value": r}} for r in raw]}

    from isis_report_lib.rendering import arender_report_html

    return await arender_report_html(ds_items=ds_items, layout=layout, meta=meta)


def render_html(payload: dict[str, Any] | ReportPayload) -> str:
    """Renderiza só o HTML intermediário (sync, sem Playwright)."""
    return _run(arender_html(payload))


def render_html_from_toon(text: str) -> str:
    """Renderiza HTML (sync) a partir de texto `.toon`."""
    return render_html(parse_toon(text))
