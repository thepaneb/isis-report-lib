"""Report generation pipeline: Fetch -> Process -> HTML -> PDF."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, final

logger = logging.getLogger("isis_report_lib")


def with_meta_defaults(meta: dict[str, Any]) -> dict[str, Any]:
    """Fill display metadata the payload did not provide (e.g. print timestamp)."""
    meta = dict(meta)
    if not meta.get("printed_at"):
        meta["printed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return meta


class BaseReportService(ABC):
    """Defines the report lifecycle; ``execute`` enforces the step order."""

    @final
    async def execute(self, payload: dict[str, Any]) -> bytes:
        service_name = self.__class__.__name__
        try:
            logger.info("Starting report processing: %s", service_name)
            raw_data = await self._fetch_data(payload)
            processed_data = await self._process_data(raw_data, payload)
            html_content = await self._render_html(processed_data, payload)
            pdf_bytes = await self._generate_pdf(html_content)
            logger.info("Report %s generated successfully.", service_name)
            return pdf_bytes
        except Exception:
            logger.exception("Pipeline failed for service %s", service_name)
            raise

    @abstractmethod
    async def _fetch_data(self, payload: dict[str, Any]) -> Any:
        """Retrieve raw data from the payload."""

    @abstractmethod
    async def _process_data(self, data: Any, payload: dict[str, Any]) -> Any:
        """Apply layout conversion / data shaping."""

    @abstractmethod
    async def _render_html(self, data: Any, payload: dict[str, Any]) -> str:
        """Render the Jinja2 template."""

    @abstractmethod
    async def _generate_pdf(self, html: str) -> bytes:
        """Convert HTML to PDF."""


class TabularReportService(BaseReportService):
    """Default tabular implementation of the pipeline."""

    def __init__(
        self,
        pdf_options: dict[str, Any] | None = None,
        template_dir: str | Path | None = None,
        template_name: str = "tabular.jinja",
    ) -> None:
        from isis_report_lib import pdf as _pdf

        self._pdf_options = pdf_options or {}
        self._template_dir = template_dir
        self._template_name = template_name
        self._printed_at: str | None = None
        self._page: dict[str, Any] = {}
        self._pdf_module = _pdf

    async def _fetch_data(self, payload: dict[str, Any]) -> Any:
        return payload.get("data", [])

    async def _process_data(self, data: Any, payload: dict[str, Any]) -> dict[str, Any]:
        from isis_report_lib.layout import build_report, infer_layout, is_template_format, template_header_layout

        meta = with_meta_defaults(payload.get("meta", {}))
        self._printed_at = meta.get("printed_at")
        self._page = meta.get("page", {}) or {}
        layout_raw = payload.get("layout")

        if layout_raw:
            dataset, layout = build_report(data, layout_raw)
        elif is_template_format(data):
            layout = template_header_layout(data)
            dataset = {"groups": data, "summary": None}
        else:
            layout = infer_layout(data)
            # The template iterates over `row.fields`, so raw records must be wrapped.
            dataset = {
                "groups": [{"fields": r} if isinstance(r, dict) else {"fields": {"value": r}} for r in data],
                "summary": None,
            }
        return {"dataset": dataset, "layout": layout, "meta": meta}

    async def _render_html(self, data: dict[str, Any], payload: dict[str, Any]) -> str:
        from isis_report_lib.rendering import arender_report_html

        return await arender_report_html(
            dataset=data["dataset"],
            layout=data["layout"],
            meta=data["meta"],
            template_name=self._template_name,
            template_dir=self._template_dir,
        )

    async def _generate_pdf(self, html: str) -> bytes:
        from isis_report_lib.pdf import default_footer

        options = dict(self._page_pdf_options())
        # Print timestamp goes in the repeated page footer (right side);
        # an explicit footer_template always wins.
        options.setdefault("footer_template", default_footer(self._printed_at))
        return await self._pdf_module.get_pdf_from_html(html, **options)

    def _page_pdf_options(self) -> dict[str, Any]:
        """Translate ``meta.page`` to ``page.pdf`` kwargs; explicit ``pdf_options`` win."""
        from isis_report_lib.pdf import DEFAULT_MARGIN

        page = self._page or {}
        options: dict[str, Any] = {"format": page.get("size", "A4")}
        if page.get("orientation") == "landscape":
            options["landscape"] = True
        elif page.get("orientation") not in (None, "portrait"):
            raise ValueError(f"Invalid page orientation: {page.get('orientation')!r}")
        margins = page.get("margins") or {}
        options["margin"] = {key: margins.get(key, DEFAULT_MARGIN[key]) for key in ("top", "bottom", "left", "right")}
        options.update(self._pdf_options)
        return options
