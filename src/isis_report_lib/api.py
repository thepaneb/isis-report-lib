"""Public API of the library (sync + async)."""

import asyncio
import platform

# Use selector event loop on Windows to avoid socketpair issues
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from pathlib import Path
from typing import Any

from isis_report_lib.models import ReportPayload
from isis_report_lib.service import TabularReportService
from isis_report_lib.toon import parse_toon


def _normalize_payload(payload: dict[str, Any] | ReportPayload) -> dict[str, Any]:
    if isinstance(payload, ReportPayload):
        # Full dump keeps declared defaults (e.g. mode="exact"); None only
        # ever means "unset" at the structural level, so drop those keys to
        # match raw-dict behavior exactly (no "sections" key, no None metas).
        dumped = payload.model_dump()
        meta = {key: value for key, value in dumped.get("meta", {}).items() if value is not None}
        normalized = {key: value for key, value in dumped.items() if value is not None}
        normalized["meta"] = meta
        return normalized
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
    allowed_hosts: list[str] | None = None,
    limits: dict[str, int] | None = None,
) -> bytes:
    """Generate a PDF (async) from a dict/ReportPayload payload.

    Custom layouts: point ``template_dir`` at a directory with your own
    ``.jinja`` files and pick one via ``template_name``. Outbound http(s) is
    denied by default; pass ``allowed_hosts`` (bare hostnames) to opt in.
    ``limits`` is the operator quota cap (``None`` = defaults, ``{}`` = off);
    payload ``meta.limits`` may only tighten it.
    """
    service = TabularReportService(
        pdf_options=pdf_options,
        template_dir=template_dir,
        template_name=template_name,
        allowed_hosts=allowed_hosts,
        limits=limits,
    )
    return await service.execute(_normalize_payload(payload))


def generate_pdf(
    payload: dict[str, Any] | ReportPayload,
    pdf_options: dict[str, Any] | None = None,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    allowed_hosts: list[str] | None = None,
    limits: dict[str, int] | None = None,
) -> bytes:
    """Generate a PDF (sync) from a dict/ReportPayload payload."""
    return _run(agenerate_pdf(payload, pdf_options, template_dir, template_name, allowed_hosts, limits))


async def agenerate_pdf_from_toon(
    text: str,
    pdf_options: dict[str, Any] | None = None,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    allowed_hosts: list[str] | None = None,
    limits: dict[str, int] | None = None,
) -> bytes:
    """Generate a PDF (async) from `.toon` text."""
    return await agenerate_pdf(parse_toon(text), pdf_options, template_dir, template_name, allowed_hosts, limits)


def generate_pdf_from_toon(
    text: str,
    pdf_options: dict[str, Any] | None = None,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    allowed_hosts: list[str] | None = None,
    limits: dict[str, int] | None = None,
) -> bytes:
    """Generate a PDF (sync) from `.toon` text."""
    return _run(agenerate_pdf_from_toon(text, pdf_options, template_dir, template_name, allowed_hosts, limits))


async def arender_html(
    payload: dict[str, Any] | ReportPayload,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    inline_css: bool = False,
    limits: dict[str, int] | None = None,
) -> str:
    """Render only the intermediate HTML (async, no Playwright)."""
    from isis_report_lib.service import prepare_report

    data = _normalize_payload(payload)
    dataset, layout, meta = prepare_report(data, limits=limits)

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
    limits: dict[str, int] | None = None,
) -> str:
    """Render only the intermediate HTML (sync, no Playwright)."""
    return _run(arender_html(payload, template_dir, template_name, inline_css, limits))


def render_html_from_toon(
    text: str,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    inline_css: bool = False,
    limits: dict[str, int] | None = None,
) -> str:
    """Render HTML (sync) from `.toon` text."""
    return render_html(parse_toon(text), template_dir, template_name, inline_css, limits)


async def agenerate_xlsx(payload: dict[str, Any] | ReportPayload, limits: dict[str, int] | None = None) -> bytes:
    """Generate an .xlsx workbook (async, no browser needed)."""
    from isis_report_lib.export import build_workbook, collect_tables
    from isis_report_lib.service import prepare_report

    dataset, layout, meta = prepare_report(_normalize_payload(payload), limits=limits)
    tables, summaries = collect_tables(dataset, layout, meta)
    return build_workbook(tables, summaries, meta)


async def agenerate_many(
    payloads: list[dict[str, Any] | ReportPayload],
    pdf_options: dict[str, Any] | None = None,
    max_concurrency: int = 4,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    allowed_hosts: list[str] | None = None,
    limits: dict[str, int] | None = None,
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
            return await agenerate_pdf(payload, pdf_options, template_dir, template_name, allowed_hosts, limits)

    return list(await asyncio.gather(*[_one(payload) for payload in payloads]))


def generate_many(
    payloads: list[dict[str, Any] | ReportPayload],
    pdf_options: dict[str, Any] | None = None,
    max_concurrency: int = 4,
    template_dir: str | Path | None = None,
    template_name: str = "tabular.jinja",
    allowed_hosts: list[str] | None = None,
    limits: dict[str, int] | None = None,
) -> list[bytes]:
    """Generate several PDFs concurrently (sync); results come back in input order."""
    return _run(agenerate_many(payloads, pdf_options, max_concurrency, template_dir, template_name, allowed_hosts, limits))


def generate_xlsx(payload: dict[str, Any] | ReportPayload, limits: dict[str, int] | None = None) -> bytes:
    """Generate an .xlsx workbook (sync, no browser needed)."""
    return _run(agenerate_xlsx(payload, limits))


async def agenerate_xlsx_from_toon(text: str, limits: dict[str, int] | None = None) -> bytes:
    """Generate an .xlsx workbook (async) from `.toon` text."""
    return await agenerate_xlsx(parse_toon(text), limits)


def generate_xlsx_from_toon(text: str, limits: dict[str, int] | None = None) -> bytes:
    """Generate an .xlsx workbook (sync) from `.toon` text."""
    return _run(agenerate_xlsx_from_toon(text, limits))


async def agenerate_csv(
    payload: dict[str, Any] | ReportPayload,
    delimiter: str = ",",
    bom: bool = False,
    limits: dict[str, int] | None = None,
) -> str:
    """Generate CSV text (async, no browser needed).

    ``bom=True`` prepends a UTF-8 BOM so Excel (PT) opens accented text correctly.
    """
    from isis_report_lib.export import collect_tables, render_csv
    from isis_report_lib.service import prepare_report

    dataset, layout, meta = prepare_report(_normalize_payload(payload), limits=limits)
    tables, summaries = collect_tables(dataset, layout, meta)
    text = render_csv(tables, summaries, meta, delimiter=delimiter)
    return "\ufeff" + text if bom else text


def generate_csv(
    payload: dict[str, Any] | ReportPayload,
    delimiter: str = ",",
    bom: bool = False,
    limits: dict[str, int] | None = None,
) -> str:
    """Generate CSV text (sync, no browser needed)."""
    return _run(agenerate_csv(payload, delimiter, bom, limits))


async def agenerate_csv_from_toon(text: str, delimiter: str = ",", bom: bool = False, limits: dict[str, int] | None = None) -> str:
    """Generate CSV text (async) from `.toon` text."""
    return await agenerate_csv(parse_toon(text), delimiter, bom, limits)


def generate_csv_from_toon(text: str, delimiter: str = ",", bom: bool = False, limits: dict[str, int] | None = None) -> str:
    """Generate CSV text (sync) from `.toon` text."""
    return _run(agenerate_csv_from_toon(text, delimiter, bom, limits))


async def arender_text(
    payload: dict[str, Any] | ReportPayload,
    *,
    sanitize: bool = True,
    limits: dict[str, int] | None = None,
) -> str:
    """Render a visible-only, sanitized plain-text export (async, no browser).

    Intended for LLM/RAG ingestion. Only fields visible in the report are
    included (``visible: false`` is dropped by the normal layout builder); the
    text starts with a ``REPORT DATA`` preamble and end delimiter, and control,
    format, surrogate and private-use characters are stripped by default.
    Set ``sanitize=False`` only for exact debugging output.
    """
    from isis_report_lib.text import sanitize_text, wrap_report_text

    text = await agenerate_csv(payload, limits=limits)
    return wrap_report_text(sanitize_text(text) if sanitize else text)


def render_text(
    payload: dict[str, Any] | ReportPayload,
    *,
    sanitize: bool = True,
    limits: dict[str, int] | None = None,
) -> str:
    """Render a visible-only, sanitized plain-text export (sync, no browser).

    See :func:`arender_text` for the safety properties and the data boundary.
    """
    return _run(arender_text(payload, sanitize=sanitize, limits=limits))


async def arender_text_from_toon(
    text: str,
    *,
    sanitize: bool = True,
    limits: dict[str, int] | None = None,
) -> str:
    """Render a visible-only, sanitized plain-text export (async) from `.toon`."""
    return await arender_text(parse_toon(text), sanitize=sanitize, limits=limits)


def render_text_from_toon(
    text: str,
    *,
    sanitize: bool = True,
    limits: dict[str, int] | None = None,
) -> str:
    """Render a visible-only, sanitized plain-text export (sync) from `.toon`."""
    return _run(arender_text_from_toon(text, sanitize=sanitize, limits=limits))
