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
    if "source_note" in meta and (not isinstance(meta["source_note"], str) or not meta["source_note"]):
        raise ValueError(f"Invalid meta.source_note (must be a non-empty string): {meta['source_note']!r}")
    if "summary_side" in meta and meta["summary_side"] not in ("top", "bottom"):
        raise ValueError(f"Invalid meta.summary_side (expected top|bottom): {meta['summary_side']!r}")
    return meta


def prepare_report(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build (dataset, layout, meta) from a normalized payload dict (shared by all outputs)."""
    from isis_report_lib.layout import (
        assign_report_footnotes,
        build_report,
        collect_footnotes,
        infer_layout,
        is_template_format,
        template_header_layout,
    )

    meta = with_meta_defaults(payload.get("meta", {}) or {})
    if "sections" in payload:
        dataset, layout, _meta = _prepare_sections(payload.get("sections", []) or [], meta)
        assign_report_footnotes(layout, dataset.get("sections", []))
        for section in dataset.get("sections", []):
            stype = section.get("type", "table")
            if stype == "table":
                section["footnotes"] = collect_footnotes(section.get("layout", {}))
            elif stype == "crosstab":
                ct = section.get("crosstab")
                section["footnotes"] = _crosstab_footnotes(ct) if ct is not None else []
            elif stype == "kpi":
                section["footnotes"] = _item_footnotes(section.get("items", []))
        return dataset, layout, meta
    data = payload.get("data", [])
    layout_raw = payload.get("layout")
    if layout_raw:
        dataset, layout = build_report(data, layout_raw)
    elif is_template_format(data):
        layout = template_header_layout(data)
        dataset = {"groups": data, "summary": None}
    else:
        layout = infer_layout(data)
        dataset = {
            "groups": [{"fields": r} if isinstance(r, dict) else {"fields": {"value": r}} for r in data],
            "summary": None,
        }
    assign_report_footnotes(layout)
    layout["footnotes"] = collect_footnotes(layout)
    return dataset, layout, meta


def _crosstab_footnotes(ct: Any) -> list[tuple[str, str]]:
    """Collect (mark, text) from crosstab row/column/measure defs in order."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for part in (getattr(ct, "row_field", {}), getattr(ct, "col_field", {}), getattr(ct, "measure_field", {})):
        note = part.get("footnote") if isinstance(part, dict) else None
        if isinstance(note, dict) and note.get("mark") and note.get("mark") not in seen:
            seen.add(note["mark"])
            found.append((note["mark"], note.get("text", "")))
    return found


def _item_footnotes(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Collect (mark, text) from KPI items in order."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in items or []:
        note = item.get("footnote") if isinstance(item, dict) else None
        if isinstance(note, dict) and note.get("mark") and note.get("mark") not in seen:
            seen.add(note["mark"])
            found.append((note["mark"], note.get("text", "")))
    return found


def _section_source(section: dict[str, Any]) -> str:
    """Validate and return a section's ``source`` note ("" when absent)."""
    source = section.get("source", "")
    if source is None or source == "":
        return ""
    if not isinstance(source, str):
        raise ValueError(f"Invalid section source (must be a string): {source!r}")
    return source


def _prepare_sections(sections: list[dict[str, Any]], meta: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build a composed document: table/text/kpi/chart sections sharing the report meta."""
    from isis_report_lib.layout import build_report

    built: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError(f"Invalid section (must be an object): {section!r}")
        stype = section.get("type", "table")
        if stype == "table":
            dataset, layout = build_report(section.get("data", []), section.get("layout", {}))
            entry: dict[str, Any] = {"type": "table", "title": section.get("title"), "dataset": dataset, "layout": layout}
            if isinstance(section.get("empty_text"), str) and section["empty_text"]:
                entry["empty_text"] = section["empty_text"]
            built.append(entry)
        elif stype == "text":
            paragraphs = section.get("paragraphs", [section["body"]] if "body" in section else [])
            if not isinstance(paragraphs, list) or not all(isinstance(p, str) for p in paragraphs):
                raise ValueError(f"Invalid text section (need paragraphs: [...]): {section!r}")
            built.append({"type": "text", "title": section.get("title"), "paragraphs": paragraphs})
        elif stype == "kpi":
            from isis_report_lib.formatting import normalize_footnote

            raw_items = section.get("items", [])
            if not isinstance(raw_items, list):
                raise ValueError(f"Invalid kpi section (need items: [...]): {section!r}")
            items = []
            for raw in raw_items:
                if not isinstance(raw, dict) or "label" not in raw:
                    raise ValueError(f"Invalid kpi item (need at least a label): {raw!r}")
                item = dict(raw)
                if "footnote" in item:
                    item["footnote"] = normalize_footnote(item["footnote"], f"kpi item {raw.get('label')!r}")
                items.append(item)
            built.append({"type": "kpi", "title": section.get("title"), "items": items})
        elif stype == "chart":
            from isis_report_lib.charts import build_chart

            chart_spec = section.get("chart")
            if not isinstance(chart_spec, dict):
                chart_spec = {}
            built.append(
                {
                    "type": "chart",
                    "title": section.get("title") or chart_spec.get("title"),
                    "svg": build_chart(chart_spec),
                    "chart": chart_spec,
                }
            )
        elif stype == "crosstab":
            from isis_report_lib.crosstab import build_crosstab

            ct = build_crosstab(section.get("data", []), section)
            built.append({"type": "crosstab", "title": section.get("title"), "crosstab": ct})
        else:
            raise ValueError(f"Unknown section type: {stype!r} (expected table|text|kpi|chart|crosstab)")
    for entry, section in zip(built, sections, strict=True):
        if not isinstance(section, dict):
            continue
        source = _section_source(section)
        if source:
            entry["source"] = source
    return {"sections": built}, {"groups": {"header": []}}, meta


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
        self._meta_locale: str = "pt-BR"
        self._page: dict[str, Any] = {}
        self._pdf_module = _pdf

    async def _fetch_data(self, payload: dict[str, Any]) -> Any:
        return payload.get("data", [])

    async def _process_data(self, data: Any, payload: dict[str, Any]) -> dict[str, Any]:
        dataset, layout, meta = prepare_report({**payload, "data": data})
        self._printed_at = meta.get("printed_at")
        self._meta_locale = meta.get("locale", "pt-BR")
        self._page = meta.get("page", {}) or {}
        return {"dataset": dataset, "layout": layout, "meta": meta}

    async def _render_html(self, data: dict[str, Any], payload: dict[str, Any]) -> str:
        from isis_report_lib.rendering import arender_report_html

        template_name = self._template_name
        if "sections" in data.get("dataset", {}) and template_name == "tabular.jinja":
            template_name = "sections.jinja"
        return await arender_report_html(
            dataset=data["dataset"],
            layout=data["layout"],
            meta=data["meta"],
            template_name=template_name,
            template_dir=self._template_dir,
        )

    async def _generate_pdf(self, html: str) -> bytes:
        from isis_report_lib.pdf import default_footer

        options = dict(self._page_pdf_options())
        # Print timestamp goes in the repeated page footer (right side);
        # an explicit footer_template always wins.
        options.setdefault("footer_template", default_footer(self._printed_at, locale=self._meta_locale))
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
