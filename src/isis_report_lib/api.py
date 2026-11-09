"""Public API of the library (sync + async)."""

import asyncio
from pathlib import Path
from typing import Any

from isis_report_lib.models import ReportPayload
from isis_report_lib.service import TabularReportService
from isis_report_lib.toon import parse_toon


def _normalize_payload(payload: dict[str, Any] | ReportPayload) -> dict[str, Any]:
    if isinstance(payload, ReportPayload):
        return payload.model_dump()
    return dict(payload)


def _run(coro):
    """Run a coroutine and shut down the ephemeral loop's browser (avoids leaking Chromium).

    The async API reuses the pool across calls; the sync API opens/closes per call.
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
    # A loop is already running (e.g. Jupyter): run in a separate thread to avoid blocking.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(_scoped())).result()


async def agenerate_pdf(
    payload: dict[str, Any] | ReportPayload,
    pdf_options: dict[str, Any] | None = None,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> bytes:
    """Generate a PDF (async) from a dict/ReportPayload payload.

    Custom layouts: point ``template_dir`` at a directory with your own
    ``.jinja`` files and pick one via ``template_name``.
    """
    service = TabularReportService(pdf_options=pdf_options, template_dir=template_dir, template_name=template_name)
    return await service.execute(_normalize_payload(payload))


def generate_pdf(
    payload: dict[str, Any] | ReportPayload,
    pdf_options: dict[str, Any] | None = None,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> bytes:
    """Generate a PDF (sync) from a dict/ReportPayload payload."""
    return _run(agenerate_pdf(payload, pdf_options, template_dir, template_name))


async def agenerate_pdf_from_toon(
    text: str,
    pdf_options: dict[str, Any] | None = None,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> bytes:
    """Generate a PDF (async) from `.toon` text."""
    return await agenerate_pdf(parse_toon(text), pdf_options, template_dir, template_name)


def generate_pdf_from_toon(
    text: str,
    pdf_options: dict[str, Any] | None = None,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> bytes:
    """Generate a PDF (sync) from `.toon` text."""
    return _run(agenerate_pdf_from_toon(text, pdf_options, template_dir, template_name))


async def arender_html(
    payload: dict[str, Any] | ReportPayload,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> str:
    """Render only the intermediate HTML (async, no Playwright)."""
    from isis_report_lib.layout import convert_data, convert_layout, infer_layout, is_template_format

    data = _normalize_payload(payload)
    raw = data.get("data", [])
    layout_raw = data.get("layout")
    from isis_report_lib.service import with_meta_defaults

    meta = with_meta_defaults(data.get("meta", {}))
    if layout_raw:
        layout = convert_layout(layout_raw)
        dataset = convert_data(raw, layout_raw)
    else:
        layout = infer_layout(raw)
        if is_template_format(raw):
            dataset = {"groups": raw}
        else:
            dataset = {"groups": [{"fields": r} if isinstance(r, dict) else {"fields": {"value": r}} for r in raw]}

    from isis_report_lib.rendering import arender_report_html

    return await arender_report_html(dataset=dataset, layout=layout, meta=meta, template_name=template_name, template_dir=template_dir)


def render_html(
    payload: dict[str, Any] | ReportPayload,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> str:
    """Render only the intermediate HTML (sync, no Playwright)."""
    return _run(arender_html(payload, template_dir, template_name))


def render_html_from_toon(
    text: str,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> str:
    """Render HTML (sync) from `.toon` text."""
    return render_html(parse_toon(text), template_dir, template_name)
