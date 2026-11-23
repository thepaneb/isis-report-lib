"""Report generation pipeline: Fetch -> Process -> HTML -> PDF."""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, final

logger = logging.getLogger("isis_report_lib")

_LIMIT_KEYS = ("max_rows", "max_bytes")


def with_meta_defaults(meta: dict[str, Any]) -> dict[str, Any]:
    """Fill display metadata the payload did not provide (e.g. print timestamp)."""
    meta = dict(meta)
    if not meta.get("printed_at"):
        meta["printed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if meta.get("source_note") is not None and (not isinstance(meta["source_note"], str) or not meta["source_note"]):
        raise ValueError(f"Invalid meta.source_note (must be a non-empty string): {meta['source_note']!r}")
    if meta.get("summary_side") is not None and meta["summary_side"] not in ("top", "bottom"):
        raise ValueError(f"Invalid meta.summary_side (expected top|bottom): {meta['summary_side']!r}")
    if "limits" in meta and meta["limits"] is not None:
        meta["limits"] = _normalize_limits(meta["limits"])
    return meta


def _normalize_limits(limits: Any) -> dict[str, int]:
    """Validate ``meta.limits`` (fail closed: unknown keys and non-positive ints raise)."""
    if not isinstance(limits, dict):
        raise ValueError(f"Invalid meta.limits (must be an object): {limits!r}")
    for key in limits:
        if key not in _LIMIT_KEYS:
            raise ValueError(f"Unknown meta.limits key: {key!r} (expected max_rows|max_bytes)")
    out: dict[str, int] = {}
    for key in _LIMIT_KEYS:
        value = limits.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"Invalid meta.limits.{key} (must be a positive integer): {value!r}")
        out[key] = value
    return out


def _count_data_records(data: Any) -> int:
    """Count record objects in a data tree (every dict under lists counts, at any depth).

    Iterative (no recursion limit): a hostile payload nests arbitrarily deep.
    """
    count = 0
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            count += 1
            stack.extend(node.values())
    return count


def _count_payload_records(payload: dict[str, Any]) -> int:
    """Records driving row rendering: tabular ``data`` or table/crosstab ``data`` + kpi ``items``.

    Sections are dicts here (the ReportPayload gate rejects anything else).
    """
    if "sections" in payload:
        sections = payload.get("sections", []) or []
        total = 0
        for section in sections:
            stype = section.get("type", "table")
            if stype in ("table", "crosstab"):
                total += _count_data_records(section.get("data", []))
            elif stype == "kpi":
                total += _count_data_records(section.get("items", []))
        return total
    return _count_data_records(payload.get("data", []))


def _check_payload_quotas(payload: dict[str, Any], meta: dict[str, Any]) -> None:
    """Enforce opt-in ``meta.limits`` before any expensive shaping (fail fast on DoS-sized input)."""
    limits = meta.get("limits") or {}
    max_rows = limits.get("max_rows")
    max_bytes = limits.get("max_bytes")
    if max_rows is None and max_bytes is None:
        return
    if max_bytes is not None:
        size = len(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))
        if size > max_bytes:
            raise ValueError(f"Payload is {size} bytes, exceeding meta.limits.max_bytes={max_bytes}")
    if max_rows is not None:
        total = _count_payload_records(payload)
        if total > max_rows:
            raise ValueError(f"Payload has {total} data records, exceeding meta.limits.max_rows={max_rows}")


def _validate_payload_shape(payload: Any) -> None:
    """Validate the payload envelope against ReportPayload (fail closed).

    Deep layout/field rules stay incremental (layout.py, formatting.py); this
    gate ensures the top-level shape and meta keys are known before any work.
    """
    from pydantic import ValidationError

    from isis_report_lib.models import ReportPayload

    if not isinstance(payload, dict):
        raise ValueError(f"Invalid payload (must be an object): {type(payload).__name__}")
    try:
        ReportPayload.model_validate(payload)
    except ValidationError as e:
        details = "; ".join(
            f"{'.'.join(str(part) for part in err['loc']) or 'payload'}: {err['msg']}" for err in e.errors(include_url=False)[:3]
        )
        more = f" (+{e.error_count() - 3} more)" if e.error_count() > 3 else ""
        problems = "problem" if e.error_count() == 1 else "problems"
        raise ValueError(f"Invalid payload ({e.error_count()} {problems}): {details}{more}") from e


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

    _validate_payload_shape(payload)
    meta = with_meta_defaults(payload.get("meta", {}) or {})
    _check_payload_quotas(payload, meta)
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
    try:
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
    except RecursionError as e:
        raise ValueError("Report layout is nested too deeply to build") from e
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
        allowed_hosts: list[str] | None = None,
    ) -> None:
        from isis_report_lib import pdf as _pdf
        from isis_report_lib.pdf import validate_allowed_hosts

        self._pdf_options = pdf_options or {}
        self._template_dir = template_dir
        self._template_name = template_name
        self._allowed_hosts = validate_allowed_hosts(allowed_hosts)
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
        return await self._pdf_module.get_pdf_from_html(html, allowed_hosts=self._allowed_hosts, **options)

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
