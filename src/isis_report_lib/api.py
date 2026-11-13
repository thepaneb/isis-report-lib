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
    inline_css: bool = False,
) -> str:
    """Render only the intermediate HTML (async, no Playwright)."""
    from isis_report_lib.service import prepare_report

    data = _normalize_payload(payload)
    dataset, layout, meta = prepare_report(data)

    from isis_report_lib.rendering import arender_report_html

    if "sections" in data and template_name == "tabular.jinja":
        template_name = "sections.jinja"
    return await arender_report_html(
        dataset=dataset, layout=layout, meta=meta, template_name=template_name, template_dir=template_dir, inline_css=inline_css
    )


def render_html(
    payload: dict[str, Any] | ReportPayload,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    inline_css: bool = False,
) -> str:
    """Render only the intermediate HTML (sync, no Playwright)."""
    return _run(arender_html(payload, template_dir, template_name, inline_css))


def render_html_from_toon(
    text: str,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    inline_css: bool = False,
) -> str:
    """Render HTML (sync) from `.toon` text."""
    return render_html(parse_toon(text), template_dir, template_name, inline_css)


async def agenerate_xlsx(payload: dict[str, Any] | ReportPayload) -> bytes:
    """Generate an .xlsx workbook (async, no browser needed)."""
    from isis_report_lib.export import build_workbook, collect_tables
    from isis_report_lib.service import prepare_report

    dataset, layout, meta = prepare_report(_normalize_payload(payload))
    tables, summaries = collect_tables(dataset, layout)
    return build_workbook(tables, summaries, meta)


async def agenerate_many(
    payloads: list[dict[str, Any] | ReportPayload],
    pdf_options: dict[str, Any] | None = None,
    max_concurrency: int = 4,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> list[bytes]:
    """Generate several PDFs concurrently, rejoining results in input order.

    Pages share the browser pool; ``max_concurrency`` caps simultaneous pages.
    For mixed options per report, use ``asyncio.gather`` over ``agenerate_pdf`` directly.
    """
    if max_concurrency < 1:
        raise ValueError(f"max_concurrency must be >= 1, got {max_concurrency!r}")
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _one(payload: dict[str, Any] | ReportPayload) -> bytes:
        async with semaphore:
            return await agenerate_pdf(payload, pdf_options, template_dir, template_name)

    return list(await asyncio.gather(*[_one(payload) for payload in payloads]))


def generate_many(
    payloads: list[dict[str, Any] | ReportPayload],
    pdf_options: dict[str, Any] | None = None,
    max_concurrency: int = 4,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
) -> list[bytes]:
    """Generate several PDFs concurrently (sync); results come back in input order."""
    return _run(agenerate_many(payloads, pdf_options, max_concurrency, template_dir, template_name))


def generate_xlsx(payload: dict[str, Any] | ReportPayload) -> bytes:
    """Generate an .xlsx workbook (sync, no browser needed)."""
    return _run(agenerate_xlsx(payload))


async def agenerate_xlsx_from_toon(text: str) -> bytes:
    """Generate an .xlsx workbook (async) from `.toon` text."""
    return await agenerate_xlsx(parse_toon(text))


def generate_xlsx_from_toon(text: str) -> bytes:
    """Generate an .xlsx workbook (sync) from `.toon` text."""
    return _run(agenerate_xlsx_from_toon(text))


async def agenerate_csv(payload: dict[str, Any] | ReportPayload, delimiter: str = ",", bom: bool = False) -> str:
    """Generate CSV text (async, no browser needed).

    ``bom=True`` prepends a UTF-8 BOM so Excel (PT) opens accented text correctly.
    """
    from isis_report_lib.export import collect_tables, render_csv
    from isis_report_lib.service import prepare_report

    dataset, layout, meta = prepare_report(_normalize_payload(payload))
    tables, summaries = collect_tables(dataset, layout)
    text = render_csv(tables, summaries, meta, delimiter=delimiter)
    return "\ufeff" + text if bom else text


def generate_csv(payload: dict[str, Any] | ReportPayload, delimiter: str = ",", bom: bool = False) -> str:
    """Generate CSV text (sync, no browser needed)."""
    return _run(agenerate_csv(payload, delimiter, bom))


async def agenerate_csv_from_toon(text: str, delimiter: str = ",", bom: bool = False) -> str:
    """Generate CSV text (async) from `.toon` text."""
    return await agenerate_csv(parse_toon(text), delimiter, bom)


def generate_csv_from_toon(text: str, delimiter: str = ",", bom: bool = False) -> str:
    """Generate CSV text (sync) from `.toon` text."""
    return _run(agenerate_csv_from_toon(text, delimiter, bom))
