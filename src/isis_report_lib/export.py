"""Tabular export to XLSX/CSV (no browser needed).

The exporters walk the same ``(dataset, layout)`` structure as the HTML
templates, so labels, numbers and totals match the PDF. Grain:

- one table per detail key (context columns repeated = analyzable sheets);
- table footers (``tfoot``) as the last row;
- group footers and the grand summary collected as ``(label, value, mask)`` rows.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Column:
    """A column: ``key`` reads values, ``label`` is the header, ``mask`` formats.

    ``field`` is the normalized layout field dict (carries ``cell_rules``,
    ``missing_text`` and ``substitutions`` for faithful display).
    """

    key: str
    label: str
    mask: str = "str"
    rules: list[dict[str, Any]] = field(default_factory=list)
    field: dict[str, Any] = field(default_factory=dict)


@dataclass
class Table:
    """One flat table with shared ``columns`` and raw ``rows`` (dicts).

    Footer (total) rows are appended to ``rows``; their indices are tracked in
    ``total_rows`` so renderers can style them (bold, top border). ``note``
    carries the ``empty_text`` message for tables with no rows; ``notes``
    carries ``(ref, text)`` footnotes plus ``("source", text)`` section notes.
    """

    key: str
    columns: list[Column] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    total_rows: set[int] = field(default_factory=set)
    note: str = ""
    notes: list[tuple[str, str]] = field(default_factory=list)


def collect_tables(
    dataset: dict[str, Any], layout: dict[str, Any], meta: dict[str, Any] | None = None
) -> tuple[list[Table], list[tuple[str, Any, str]]]:
    """Flatten (dataset, layout) into tables plus (label, value, mask) summary rows."""
    return _collect(dataset, layout, meta, default_name="data")


def _collect(
    dataset: dict[str, Any], layout: dict[str, Any], meta: dict[str, Any] | None, default_name: str
) -> tuple[list[Table], list[tuple[str, Any, str]]]:
    summaries: list[tuple[str, Any, str]] = []
    by_key: dict[str, Table] = {}

    def table_for(key: str, columns: list[Column]) -> Table:
        if key not in by_key:
            by_key[key] = Table(key=key, columns=list(columns))
        return by_key[key]

    def visit(
        items: list[dict[str, Any]],
        frag: dict[str, Any],
        context: list[tuple[Column, Any]],
    ) -> None:
        header = frag.get("header", [])
        for item in items:
            if not isinstance(item, dict):
                continue
            fields = item.get("fields", {}) or {}
            ctx = list(context) + [
                (
                    Column(
                        key=f["name"],
                        label=f["label"],
                        mask=f.get("format_mask", "str"),
                        rules=list(f.get("cell_rules", []) or []),
                        field=f,
                    ),
                    fields.get(f["name"]),
                )
                for f in header
            ]
            details = item.get("details", {}) or {}
            layouts = frag.get("details", {}) or {}
            for tkey, tlayout in layouts.items():
                table = details.get(tkey, {})
                rows = [r for r in table.get("rows", []) if isinstance(r, dict)]
                if not rows and not table.get("footer") and not table.get("empty_text"):
                    continue
                columns = _merge_columns([c for c, _ in ctx], tlayout)
                sheet = table_for(tkey, columns)
                if table.get("empty_text"):
                    sheet.note = table["empty_text"]
                _attach_notes(sheet, _notes_from_columns(columns))
                base = {c.key: v for c, v in ctx}
                for row in rows:
                    values = dict.fromkeys([c.key for c in columns])
                    values.update(base)
                    values.update(row)
                    sheet.rows.append(values)
                if table.get("footer"):
                    sheet.rows.append(dict(table["footer"]))
                    sheet.total_rows.add(len(sheet.rows) - 1)
            if item.get("groups") and frag.get("groups"):
                kids = [c for c in item["groups"] if isinstance(c, dict)]
                visit(kids, frag["groups"], ctx)
            footer = item.get("footer")
            if footer and frag.get("footer"):
                path = " / ".join(str(v) for _c, v in ctx if v not in (None, ""))
                for f in frag["footer"]:
                    value = footer.get(f["name"])
                    if value != "" and value is not None:
                        label = f"{path} / {f['label']}" if path else f["label"]
                        summaries.append((label, value, f.get("format_mask", "str")))

    top = dataset.get("groups", [])
    visit(top if isinstance(top, list) else [], layout.get("groups", {}), [])
    summary = dataset.get("summary") or {}
    for f in layout.get("summary", []) or []:
        if f["name"] in summary:
            summaries.append((f["label"], summary[f["name"]], f.get("format_mask", "str")))
    for section in dataset.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        stype = section.get("type", "table")
        if stype == "table":
            sub_tables, sub_summaries = _collect(
                section.get("dataset", {}), section.get("layout", {}), meta, section.get("title") or "table"
            )
            title = section.get("title")
            for table in sub_tables:
                key = table.key if not title or table.key == title else f"{title} - {table.key}"
                suffix, n = key, 2
                while suffix in by_key:
                    suffix, n = f"{key}_{n}", n + 1
                table.key = suffix
                _attach_notes(table, _section_notes(section))
                by_key[suffix] = table
            for label, value, mask in sub_summaries:
                summaries.append((f"{title} / {label}" if title else label, value, mask))
        elif stype == "text":
            paragraphs = [p for p in section.get("paragraphs", []) if isinstance(p, str)]
            if paragraphs:
                table = Table(
                    key=section.get("title") or "notes",
                    columns=[Column(key="text", label="Text")],
                    rows=[{"text": p} for p in paragraphs],
                )
                _attach_notes(table, _section_notes(section))
                by_key[section.get("title") or f"notes_{len(by_key)}"] = table
        elif stype == "kpi":
            rows = [{"label": i.get("label"), "value": i.get("value")} for i in section.get("items", []) if isinstance(i, dict)]
            if rows:
                table = Table(
                    key=section.get("title") or "kpi",
                    columns=[Column(key="label", label="Label"), Column(key="value", label="Value")],
                    rows=rows,
                )
                _attach_notes(table, _notes_from_field_dicts(section.get("items", [])))
                _attach_notes(table, _section_notes(section))
                by_key[section.get("title") or "kpi"] = table
        elif stype == "chart":
            spec = section.get("chart", {}) if isinstance(section.get("chart"), dict) else {}
            labels = [str(label) for label in spec.get("labels", [])]
            rows = [{"label": lb, "value": v} for lb, v in zip(labels, spec.get("values", []), strict=True)]
            if rows:
                key = section.get("title") or spec.get("title") or "chart"
                table = Table(
                    key=key,
                    columns=[Column(key="label", label="Label"), Column(key="value", label="Value")],
                    rows=rows,
                )
                _attach_notes(table, _section_notes(section))
                by_key[key] = table
        elif stype == "crosstab":
            from isis_report_lib.crosstab import build_crosstab, crosstab_table

            ct = section.get("crosstab")
            if ct is None:
                ct = build_crosstab(section.get("data", []), section)
            table = crosstab_table(ct, meta)
            if table.rows or table.note:
                title = section.get("title")
                key = title if title else table.key
                suffix, n = key, 2
                while suffix in by_key:
                    suffix, n = f"{key}_{n}", n + 1
                table.key = suffix
                _attach_notes(table, _notes_from_columns(table.columns))
                _attach_notes(table, _section_notes(section))
                by_key[suffix] = table
    if not by_key and top:
        header = layout.get("groups", {}).get("header", [])
        columns = [
            Column(
                key=f["name"],
                label=f["label"],
                mask=f.get("format_mask", "str"),
                rules=list(f.get("cell_rules", []) or []),
                field=f,
            )
            for f in header
        ]
        if columns:
            sheet = table_for(default_name, columns)
            _attach_notes(sheet, _notes_from_columns(columns))
            for item in top:
                if isinstance(item, dict):
                    fields = item.get("fields", {}) or {}
                    sheet.rows.append({c.key: fields.get(c.key) for c in columns})
    return list(by_key.values()), summaries


def _merge_columns(ctx_cols: list[Column], table_fields: list[dict[str, Any]]) -> list[Column]:
    """Context columns first, then table fields (no duplicates, order preserved)."""
    cols = list(ctx_cols)
    seen = {c.key for c in cols}
    for f in table_fields:
        if f["name"] not in seen:
            cols.append(
                Column(
                    key=f["name"],
                    label=f["label"],
                    mask=f.get("format_mask", "str"),
                    rules=list(f.get("cell_rules", []) or []),
                    field=f,
                )
            )
            seen.add(f["name"])
    return cols


def _column_mark(column: Column) -> str:
    """Footnote mark for a column ("" when the field has none)."""
    note = column.field.get("footnote") if isinstance(column.field, dict) else None
    if isinstance(note, dict) and note.get("mark"):
        return str(note["mark"])
    return ""


def _notes_from_columns(columns: list[Column]) -> list[tuple[str, str]]:
    """Ordered unique ``(mark, text)`` footnotes for a column list."""
    return _notes_from_field_dicts([c.field for c in columns])


def _notes_from_field_dicts(fields: list[Any]) -> list[tuple[str, str]]:
    """Ordered unique ``(mark, text)`` footnotes for normalized field/item dicts."""
    notes: list[tuple[str, str]] = []
    seen: set[str] = set()
    for f in fields or []:
        note = f.get("footnote") if isinstance(f, dict) else None
        if isinstance(note, dict) and note.get("mark") and note.get("mark") not in seen:
            seen.add(str(note["mark"]))
            notes.append((str(note["mark"]), str(note.get("text", ""))))
    return notes


def _section_notes(section: dict[str, Any]) -> list[tuple[str, str]]:
    """A section's ``source`` note as a ``("source", text)`` entry (or nothing)."""
    source = section.get("source", "")
    if isinstance(source, str) and source:
        return [("source", source)]
    return []


def _attach_notes(table: Table, notes: list[tuple[str, str]]) -> None:
    """Append note entries a table does not already reference."""
    known = {ref for ref, _text in table.notes}
    for ref, text in notes:
        if ref not in known:
            known.add(ref)
            table.notes.append((ref, text))


def _column_label(column: Column) -> str:
    """Header label with footnote mark suffix ("" when none)."""
    mark = _column_mark(column)
    return f"{column.label} [{mark}]" if mark else column.label


def _require_openpyxl():
    """Import openpyxl lazily so it stays an optional dependency."""
    try:
        import openpyxl

        return openpyxl
    except ImportError as e:
        raise ImportError("XLSX export requires the 'xlsx' extra: pip install isis-report-lib[xlsx]") from e


def _guard_formula(value: Any, raw: Any) -> Any:
    """Neutralize spreadsheet formula injection (OWASP CSV Injection).

    A text cell starting with ``= + - @`` (or tab/CR) is evaluated as a
    formula by Excel/Sheets. Prefixing with ``'`` forces text display
    (hidden by Excel, visible in plain-text readers). Numeric raw values are
    never touched, so negative numbers keep rendering as-is.
    """
    if isinstance(value, str) and not isinstance(raw, (int, float)) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _native_value(value: Any, mask: str) -> Any:
    """Convert to an Excel-native value (numbers/dates stay numeric)."""
    if value is None:
        return None
    if mask == "sparkline":
        from isis_report_lib.formatting import sparkline_text

        return sparkline_text(value)
    if mask == "bool":
        if isinstance(value, str):
            return "Yes" if value.strip().lower() in {"true", "yes", "y", "1"} else "No"
        return "Yes" if value else "No"
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value
    if mask == "int":
        try:
            return int(value)
        except (ValueError, TypeError):
            return value
    if mask in ("float", "percent", "currency"):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    return value


def _number_format(mask: str, currency_symbol: str | None = None) -> str | None:
    if mask == "int":
        return "#,##0"
    if mask == "float":
        return "#,##0.00"
    if mask == "percent":
        return "0.00%"
    if mask == "currency":
        return f'"{currency_symbol or "$"}"#,##0.00'
    if mask == "date":
        return "yyyy-mm-dd"
    return None


def _apply_data_bars(ws: Any, header_row: int, table: Table) -> None:
    """Native Excel data bars for columns whose field sets ``data_bar: true``."""
    from openpyxl.formatting.rule import DataBarRule

    if not table.rows:
        return
    for col, column in enumerate(table.columns, start=1):
        if not isinstance(column.field, dict) or column.field.get("data_bar") is not True:
            continue
        raw_values = [record.get(column.key) for record in table.rows]
        numbers = [float(v) for v in raw_values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(numbers) < 1 or min(numbers) >= max(numbers):
            continue
        letter = ws.cell(row=header_row, column=col).column_letter
        first, last = header_row + 1, header_row + len(table.rows)
        ws.conditional_formatting.add(
            f"{letter}{first}:{letter}{last}",
            DataBarRule(start_type="num", start_value=min(numbers), end_type="num", end_value=max(numbers), color="FF0A2F46"),
        )


def _sheet_name(base: str, used: set[str]) -> str:
    """Sanitize an Excel sheet name (≤31 chars, no \\ / * ? : [ ]) and dedupe."""
    clean = "".join(c if c not in "\\/*?:[]" else "-" for c in base).strip() or "Sheet"
    name, i = clean[:31], 2
    while name in used:
        suffix = f"_{i}"
        name, i = clean[: 31 - len(suffix)] + suffix, i + 1
    used.add(name)
    return name


def _argb(spec: str) -> str:
    """Normalize a ``#rrggbb``/``rrggbb`` color to openpyxl's ``AARRGGBB`` (opaque)."""
    hexpart = spec.lstrip("#")
    if len(hexpart) == 3:
        hexpart = "".join(c * 2 for c in hexpart)
    return f"FF{hexpart}" if len(hexpart) == 6 else hexpart


def build_workbook(
    tables: list[Table],
    summaries: list[tuple[str, Any, str]],
    meta: dict[str, Any] | None = None,
) -> bytes:
    """Build an .xlsx workbook (returned as bytes) from collected tables."""
    _require_openpyxl()  # friendly error when the optional dependency is missing

    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.workbook import Workbook

    meta = meta or {}
    currency_symbol = _currency_symbol(meta)

    wb = Workbook()
    used: set[str] = set()
    first = True

    def new_sheet(name: str):
        nonlocal first
        sheet = wb.active if first else wb.create_sheet()
        if sheet is None:
            raise RuntimeError("openpyxl returned no worksheet")
        first = False
        sheet.title = _sheet_name(name, used)
        return sheet

    from isis_report_lib.formatting import cell_style_dict, field_text, scale_fill

    header_font = Font(bold=True, color=_argb("FFFFFF"))
    header_fill = PatternFill("solid", fgColor=_argb("0A2F46"))
    bold = Font(bold=True)
    note_font = Font(italic=True, color=_argb("6B7280"))
    thin_top = Border(top=Side(style="thin"))
    wrap = Alignment(vertical="center", wrap_text=False)

    def apply_cell_style(cell, raw_value: Any, column) -> None:
        """Layer conditional formatting over the cell (no-op without matching rules)."""
        style = cell_style_dict(raw_value, {"cell_rules": column.rules})
        if style:
            cell.font = Font(
                color=_argb(style["color"]) if style.get("color") else cell.font.color,
                bold=bool(style.get("bold", cell.font.bold or False)),
                italic=bool(style.get("italic", cell.font.italic or False)),
            )
        if style.get("background"):
            cell.fill = PatternFill("solid", fgColor=_argb(style["background"]))
        elif (fill := scale_fill(raw_value, column.field)) is not None:
            cell.fill = PatternFill("solid", fgColor=_argb(fill))

    if not tables and not summaries:
        ws = new_sheet(meta.get("title") or "Report")
        ws["A1"] = meta.get("title") or "Report"
        return _workbook_bytes(wb)

    for table in tables:
        ws = new_sheet(table.key)
        widths: list[int] = []
        row_idx = 1
        if meta.get("title"):
            ws.cell(row=row_idx, column=1, value=meta["title"]).font = Font(bold=True, size=14)
            row_idx += 1
        if meta.get("sub_title"):
            ws.cell(row=row_idx, column=1, value=meta["sub_title"])
            row_idx += 1
        header_row = row_idx
        for col, column in enumerate(table.columns, start=1):
            header_label = _column_label(column)
            cell = ws.cell(row=row_idx, column=col, value=header_label)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = wrap
            widths.append(len(header_label))
        # Print polish: repeat the header on every printed page, freeze below
        # it and offer column filters.
        if table.columns:
            first_col = ws.cell(row=header_row, column=1).column_letter
            last_col = ws.cell(row=header_row, column=len(table.columns)).column_letter
            ws.print_title_rows = f"{header_row}:{header_row}"
            ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
            ws.auto_filter.ref = f"{first_col}{header_row}:{last_col}{header_row}"
        if not table.rows and table.note:
            row_idx += 1
            cell = ws.cell(row=row_idx, column=1, value=table.note)
            cell.font = note_font
            if widths:
                widths[0] = max(widths[0], len(table.note))
        for pos, record in enumerate(table.rows):
            row_idx += 1
            is_total = pos in table.total_rows
            for col, column in enumerate(table.columns, start=1):
                raw = record.get(column.key)
                mapped = field_text(raw, column.field)
                value = mapped if mapped is not None else (None if raw is None else _native_value(raw, column.mask))
                value = _guard_formula(value, raw)
                cell = ws.cell(row=row_idx, column=col, value=value)
                if is_total:
                    cell.font = bold
                    cell.border = thin_top
                apply_cell_style(cell, raw, column)
                number_format = _number_format(column.mask, currency_symbol)
                if number_format and isinstance(value, (int, float)):
                    cell.number_format = number_format
                cell.alignment = wrap
                widths.append(len(str(value if value is not None else "")))
        for col, width in enumerate(widths, start=1):
            ws.column_dimensions[ws.cell(row=header_row, column=col).column_letter].width = min(max(width + 2, 10), 50)
        _apply_data_bars(ws, header_row, table)

    if summaries:
        ws = new_sheet("Summary")
        row_idx = 1
        if meta.get("title"):
            ws.cell(row=row_idx, column=1, value=meta["title"]).font = Font(bold=True, size=14)
            row_idx += 1
        ws.cell(row=row_idx, column=1, value="Item").font = header_font
        ws.cell(row=row_idx, column=1).fill = header_fill
        ws.cell(row=row_idx, column=2, value="Value").font = header_font
        ws.cell(row=row_idx, column=2).fill = header_fill
        widths = [4, 5]
        for label, value, mask in summaries:
            row_idx += 1
            ws.cell(row=row_idx, column=1, value=label)
            native = _native_value(value, mask)
            cell = ws.cell(row=row_idx, column=2, value=native)
            number_format = _number_format(mask, currency_symbol)
            if number_format and isinstance(native, (int, float)):
                cell.number_format = number_format
            widths[0] = max(widths[0], len(str(label)))
            widths[1] = max(widths[1], len(str(native if native is not None else "")))
        ws.column_dimensions["A"].width = min(widths[0] + 2, 60)
        ws.column_dimensions["B"].width = min(widths[1] + 2, 30)

    note_rows: list[tuple[str, str, str]] = []
    if meta.get("source_note"):
        note_rows.append(("", "source", meta["source_note"]))
    for table in tables:
        for ref, text in table.notes:
            note_rows.append((table.key, ref, text))
    if note_rows:
        ws = new_sheet("Notes")
        ws.cell(row=1, column=1, value="Table").font = header_font
        ws.cell(row=1, column=1).fill = header_fill
        ws.cell(row=1, column=2, value="Ref").font = header_font
        ws.cell(row=1, column=2).fill = header_fill
        ws.cell(row=1, column=3, value="Note").font = header_font
        ws.cell(row=1, column=3).fill = header_fill
        widths = [5, 3, 4]
        for row_idx, (table_key, ref, text) in enumerate(note_rows, start=2):
            ws.cell(row=row_idx, column=1, value=table_key)
            ws.cell(row=row_idx, column=2, value=ref)
            ws.cell(row=row_idx, column=3, value=text)
            widths[0] = max(widths[0], len(table_key))
            widths[1] = max(widths[1], len(ref))
            widths[2] = max(widths[2], len(text))
        ws.column_dimensions["A"].width = min(widths[0] + 2, 40)
        ws.column_dimensions["B"].width = min(widths[1] + 2, 12)
        ws.column_dimensions["C"].width = min(widths[2] + 2, 80)

    return _workbook_bytes(wb)


def _workbook_bytes(wb) -> bytes:
    import io

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _currency_symbol(meta: dict[str, Any]) -> str:
    from isis_report_lib.formatting import default_currency, normalize_locale

    try:
        locale = normalize_locale(meta.get("locale", "pt-BR"))
    except ValueError:
        return "$"
    code = meta.get("currency") or default_currency(locale)
    try:
        from babel.numbers import get_currency_symbol

        return get_currency_symbol(code, locale=locale)
    except Exception:  # noqa: BLE001 - fall back to a plain dollar sign
        return "$"


def render_csv(
    tables: list[Table],
    summaries: list[tuple[str, Any, str]],
    meta: dict[str, Any] | None = None,
    delimiter: str = ",",
) -> str:
    """Render tables + summary as CSV text (locale-formatted values)."""
    import csv as csv_module
    import io
    from functools import partial

    from isis_report_lib.formatting import format_value

    meta = meta or {}
    fmt = partial(format_value, locale=meta.get("locale", "pt-BR"), currency=meta.get("currency"))
    out = io.StringIO()
    writer = csv_module.writer(out, delimiter=delimiter, lineterminator="\n")
    if meta.get("title"):
        writer.writerow([f"# {meta['title']}"])
    if meta.get("source_note"):
        writer.writerow([f"# [source] {meta['source_note']}"])
    for table in tables:
        writer.writerow([f"# table: {table.key}"])
        writer.writerow([_column_label(c) for c in table.columns])
        if not table.rows and table.note:
            writer.writerow([f"# {table.note}"])
        for row in table.rows:
            writer.writerow([_guard_formula(_cell_text(row, c, fmt), row.get(c.key)) for c in table.columns])
        for ref, text in table.notes:
            writer.writerow([f"# [{ref}] {text}"])
    if summaries:
        writer.writerow(["# summary"])
        writer.writerow(["Item", "Value"])
        for label, value, mask in summaries:
            writer.writerow([label, _guard_formula(fmt(value, mask), value)])
    return out.getvalue()


def _cell_text(row: dict[str, Any], column: Column, fmt: Any) -> str:
    """Render one CSV cell (SVG sparklines become block art)."""
    from isis_report_lib.formatting import sparkline_text

    if column.mask == "sparkline":
        return sparkline_text(row.get(column.key))
    return fmt(row.get(column.key), column.mask, field=column.field)
