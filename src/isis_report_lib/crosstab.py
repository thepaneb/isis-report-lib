"""Dynamic pivot tables: rows x columns matrix with aggregated measures.

A crosstab declares row/column buckets plus a measure and function; the grid
shape comes from the data (unknown at design time), Totals and the grand
total are computed the same way. Empty row/column combinations show ``""``
— except ``count``/``sum``, which are faithfully ``0``.
"""

from dataclasses import dataclass, field
from typing import Any

from isis_report_lib.export import Column, Table
from isis_report_lib.formatting import format_value
from isis_report_lib.layout import AGGREGATIONS, aggregate_values

FUNCTIONS = AGGREGATIONS


@dataclass
class Crosstab:
    """Normalized pivot: headers, raw cell values, totals and display defs."""

    row_headers: list[Any] = field(default_factory=list)
    col_headers: list[Any] = field(default_factory=list)
    cells: list[list[Any]] = field(default_factory=list)
    row_totals: list[Any] = field(default_factory=list)
    col_totals: list[Any] = field(default_factory=list)
    grand_total: Any = ""
    totals: bool = True
    row_label: str = ""
    col_label: str = ""
    total_label: str = "Total"
    mask: str = "str"
    measure_field: dict[str, Any] = field(default_factory=dict)
    row_field: dict[str, Any] = field(default_factory=dict)
    col_field: dict[str, Any] = field(default_factory=dict)
    empty_text: str = ""

    @property
    def has_data(self) -> bool:
        return bool(self.row_headers and self.col_headers)


def _field_def(spec: Any, kind: str) -> dict[str, Any]:
    """Normalize a row/column/measure spec (name or {field, label, ...})."""
    if isinstance(spec, str):
        return {"field": spec, "label": spec}
    if isinstance(spec, dict) and isinstance(spec.get("field"), str):
        out = {"field": spec["field"], "label": spec.get("label", spec["field"])}
        for key in ("format_mask", "alignment", "missing_text", "substitutions", "cell_rules"):
            if key in spec:
                out[key] = spec[key]
        if "footnote" in spec:
            from isis_report_lib.formatting import normalize_footnote

            out["footnote"] = normalize_footnote(spec["footnote"], f"crosstab {kind} {spec['field']!r}")
        return out
    raise ValueError(f"Invalid crosstab {kind} (need a field name or {{field, ...}}): {spec!r}")


def _bucket_key(value: Any):
    """Sort buckets ascending: numbers before strings, ``None`` last."""
    if value is None:
        return (1, 0, "")
    if isinstance(value, (int, float)):
        return (0, 0, value)
    return (0, 1, str(value))


def _cell_value(records: list[dict[str, Any]], measure: str, func: str) -> Any:
    """Aggregate one grid cell; unobserved combos are 0 for count/sum, else blank."""
    if not records:
        return 0 if func in ("count", "sum") else ""
    return aggregate_values(records, measure, func)


def build_crosstab(data: list[Any], spec: dict[str, Any]) -> Crosstab:
    """Build a crosstab from raw records and a ``rows``/``columns``/measure spec.

    Spec keys: ``rows``, ``columns`` (field name or field def), ``measure``
    (field name or def; optional for ``count``), ``function``
    (``sum``|``count``|``avg``|``min``|``max``), ``totals`` (default True),
    ``total_label`` (default ``"Total"``), ``empty_text``.
    """
    if not isinstance(spec, dict):
        raise ValueError(f"Invalid crosstab spec (must be an object): {spec!r}")
    row_def = _field_def(spec.get("rows"), "rows")
    col_def = _field_def(spec.get("columns"), "columns")
    func = spec.get("function", "sum")
    if func not in FUNCTIONS:
        raise ValueError(f"Unknown crosstab function: {func!r} (expected one of {FUNCTIONS})")
    measure = spec.get("measure")
    if measure is None and func != "count":
        raise ValueError(f"Crosstab {func!r} needs a measure field")
    measure_def = _field_def(measure, "measure") if measure is not None else {"field": "", "label": "Count"}
    measure_def.setdefault("format_mask", "int" if func == "count" else "float")

    totals = spec.get("totals", True)
    if not isinstance(totals, bool):
        raise ValueError(f"Invalid crosstab totals (must be true/false): {spec.get('totals')!r}")

    rows = [r for r in (data or []) if isinstance(r, dict)]
    row_values = sorted({r.get(row_def["field"]) for r in rows}, key=_bucket_key)
    col_values = sorted({r.get(col_def["field"]) for r in rows}, key=_bucket_key)

    cells: list[list[Any]] = []
    row_totals: list[Any] = []
    for rv in row_values:
        row_cells = []
        band = [r for r in rows if r.get(row_def["field"]) == rv]
        for cv in col_values:
            cell_records = [r for r in band if r.get(col_def["field"]) == cv]
            row_cells.append(_cell_value(cell_records, measure_def["field"], func))
        cells.append(row_cells)
        row_totals.append(_cell_value(band, measure_def["field"], func))

    col_totals = [_cell_value([r for r in rows if r.get(col_def["field"]) == cv], measure_def["field"], func) for cv in col_values]
    grand_total = _cell_value(rows, measure_def["field"], func)

    empty_text = spec.get("empty_text", "")
    if empty_text is not None and not isinstance(empty_text, str):
        raise ValueError(f"Invalid crosstab empty_text (must be a string): {empty_text!r}")

    return Crosstab(
        row_headers=row_values,
        col_headers=col_values,
        cells=cells,
        row_totals=row_totals,
        col_totals=col_totals,
        grand_total=grand_total,
        totals=totals,
        row_label=row_def["label"],
        col_label=col_def["label"],
        total_label=spec.get("total_label", "Total"),
        mask=measure_def.get("format_mask", "str"),
        measure_field=measure_def,
        row_field=row_def,
        col_field=col_def,
        empty_text=empty_text or "",
    )


def crosstab_table(ct: Crosstab, meta: dict[str, Any] | None = None) -> Table:
    """Flatten a crosstab into an export ``Table`` (first column = row headers)."""
    meta = meta or {}
    locale = meta.get("locale", "pt-BR")
    currency = meta.get("currency")

    columns = [Column(key="__row__", label=ct.row_label or " ", mask="str", field=ct.row_field)]
    for i, header in enumerate(ct.col_headers):
        columns.append(
            Column(
                key=f"__c{i}__",
                label=str(format_value(header, ct.col_field.get("format_mask", "str"), locale, currency, ct.col_field)),
                mask=ct.mask,
                field=ct.measure_field,
            )
        )
    if ct.totals:
        columns.append(Column(key="__total__", label=ct.total_label, mask=ct.mask, field=ct.measure_field))

    table = Table(key="crosstab", columns=columns, note=ct.empty_text if not ct.has_data else "")
    for header, cells, total in zip(ct.row_headers, ct.cells, ct.row_totals, strict=True):
        record: dict[str, Any] = {"__row__": header}
        for i, value in enumerate(cells):
            record[f"__c{i}__"] = value
        if ct.totals:
            record["__total__"] = total
        table.rows.append(record)
    if ct.totals and ct.has_data:
        total_row: dict[str, Any] = {"__row__": ct.total_label}
        for i, value in enumerate(ct.col_totals):
            total_row[f"__c{i}__"] = value
        total_row["__total__"] = ct.grand_total
        table.rows.append(total_row)
        table.total_rows.add(len(table.rows) - 1)
    return table
