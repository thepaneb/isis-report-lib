"""Hierarchical layout and data conversion into the template-ready format.

Input is the "raw" layout::

    {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "orders": {
            "order": {"label": "Order", "format_mask": "int", "alignment": "right"},
            "items": {
                "qty": {"label": "Qty", "format_mask": "int", "alignment": "right", "aggregate": "sum"},
            },
        },
    }

Keys whose value is a dict **without** ``label`` are treated as nested groups.
Keys starting with ``$`` are reserved level options (``$print_when``, ``$order_by``).

Report parameters (Phase 1 + running balances):

- field ``"aggregate"``: ``sum`` | ``count`` | ``avg`` | ``min`` | ``max`` — computed
  over sibling rows into group ``footer``\\ s, detail ``tfoot`` and the grand ``summary``.
- field ``"visible": false`` — drop the column; ``"visible_when": {condition}`` —
  drop it unless any/all rows match (``"scope": "any"``, default, or ``"all"``).
- ``"$print_when": {condition}`` — keep only matching rows at that level.
- ``"$order_by": [{"field": ..., "direction": "asc"|"desc"}]`` (or ``"field"``/``"-field"``
  shorthands) — sort rows at that level.
- field ``"running_balance": "<source field>"`` — cumulative sum of the source
  field in row order (new ``balance``-style columns, e.g. bank statements).

Conditions: ``{"field": name, "equals"|"not_equals"|"in"|"not_in"|"gt"|"gte"|"lt"|"lte": value}``
or ``{"field": name, "is_null"|"not_null": true}``.
"""

from typing import Any

AGGREGATIONS = ("sum", "count", "avg", "min", "max")


def format_field(name: str, field_def: dict[str, Any]) -> dict[str, Any]:
    """Normalize a field definition with defaults (label=name, alignment=left)."""
    out: dict[str, Any] = {
        "name": name,
        "label": field_def.get("label", name),
        "format_mask": field_def.get("format_mask", "str"),
        "alignment": field_def.get("alignment", "left"),
    }
    if field_def.get("cell_rules"):
        out["cell_rules"] = field_def["cell_rules"]
    return out


def convert_layout(layout_raw: dict[str, Any]) -> dict[str, Any]:
    """Convert the hierarchical layout into the render-ready format."""
    header: list[dict[str, Any]] = []
    groups: dict[str, Any] | None = None

    for key, value in layout_raw.items():
        if isinstance(value, dict) and "label" in value:
            header.append(format_field(key, value))
        elif isinstance(value, dict):
            field_header: list[dict[str, Any]] = []
            detail: list[dict[str, Any]] = []
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict) and "label" in sub_value:
                    field_header.append(format_field(sub_key, sub_value))
                elif isinstance(sub_value, dict):
                    for inner_key, inner_value in sub_value.items():
                        if isinstance(inner_value, dict) and "label" in inner_value:
                            detail.append(format_field(inner_key, inner_value))
            if groups is None:
                groups = {}
            groups["header"] = field_header
            if detail:
                groups["detail"] = detail

    result: dict[str, Any] = {"groups": {"header": header}}
    if groups:
        result["groups"]["groups"] = groups
    return result


def is_template_format(data: list[Any]) -> bool:
    """True when data is already in template format (records with ``fields``)."""
    return bool(data and isinstance(data[0], dict) and "fields" in data[0])


def convert_data(data_raw: list[dict[str, Any]], layout_raw: dict[str, Any]) -> dict[str, Any]:
    """Convert raw data + raw layout into the template's ``{"groups": [...]}``."""
    if is_template_format(data_raw):
        return {"groups": data_raw}

    group_keys: dict[str, Any] = {}
    for k, v in layout_raw.items():
        if isinstance(v, dict) and "label" not in v:
            group_keys[k] = v

    items: list[dict[str, Any]] = []
    for record in data_raw:
        fields: dict[str, Any] = {}
        groups: list[dict[str, Any]] = []

        for key, value in record.items():
            if key in group_keys:
                sub_layout = group_keys[key]
                detail_key = next(
                    (sk for sk, sv in sub_layout.items() if isinstance(sv, dict) and "label" not in sv),
                    None,
                )
                for sub_item in value:
                    sub_fields = {sk: sub_item[sk] for sk in sub_layout if sk != detail_key and sk in sub_item}
                    detail = sub_item.get(detail_key, []) if detail_key else []
                    group_entry: dict[str, Any] = {"fields": sub_fields}
                    if detail:
                        group_entry["detail"] = detail
                    groups.append(group_entry)
            else:
                fields[key] = value

        item: dict[str, Any] = {"fields": fields}
        if groups:
            item["groups"] = groups
        items.append(item)

    return {"groups": items}


def infer_layout(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Infer a simple (header-only) layout from the first data row."""
    if not data:
        return {"groups": {"header": []}}

    sample = data[0] if isinstance(data[0], dict) else {}
    header: list[dict[str, Any]] = []
    for key, value in sample.items():
        if isinstance(value, list):
            continue
        dtype = "str"
        alignment = "left"
        if isinstance(value, bool):
            dtype = "str"
        elif isinstance(value, int):
            dtype = "int"
            alignment = "right"
        elif isinstance(value, float):
            dtype = "float"
            alignment = "right"
        header.append({"name": key, "label": key.replace("_", " ").title(), "format_mask": dtype, "alignment": alignment})

    return {"groups": {"header": header}}


# ---------------------------------------------------------------------------
# Phase 1 engine: parameters, conditions, ordering, aggregations.
# ---------------------------------------------------------------------------


def _is_field_def(value: Any) -> bool:
    return isinstance(value, dict) and "label" in value


def _is_group_node(value: Any) -> bool:
    return isinstance(value, dict) and "label" not in value


def split_layout_node(node: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Split a layout level into (field defs, child group nodes, $options)."""
    fields: dict[str, Any] = {}
    groups: dict[str, Any] = {}
    options: dict[str, Any] = {}
    for key, value in node.items():
        if key.startswith("$"):
            options[key[1:]] = value
        elif _is_field_def(value):
            fields[key] = value
        elif _is_group_node(value):
            groups[key] = value
        # scalar junk is ignored
    return fields, groups, options


def evaluate_condition(row: dict[str, Any], condition: dict[str, Any]) -> bool:
    """Evaluate a ``$print_when``/``visible_when`` condition against a row."""
    from isis_report_lib.formatting import match_rule

    field = condition.get("field")
    if not isinstance(field, str):
        raise ValueError(f"Condition needs a field name: {condition!r}")
    value = row.get(field) if isinstance(row, dict) else None
    return match_rule(value, condition)


def filter_rows(rows: list[dict[str, Any]], print_when: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Keep rows matching the ``$print_when`` condition (all rows when absent)."""
    if not print_when:
        return list(rows)
    if not isinstance(print_when, dict) or "field" not in print_when:
        raise ValueError(f"Invalid $print_when condition: {print_when!r}")
    return [r for r in rows if isinstance(r, dict) and evaluate_condition(r, print_when)]


def _field_value(row: dict[str, Any], field: str) -> Any:
    return row.get(field) if isinstance(row, dict) else None


def _sort_key(field: str):
    def key(row: dict[str, Any]):
        value = _field_value(row, field)
        # None sorts last; numbers before strings; mixed types never compare directly.
        if value is None:
            return (1, 0, "")
        if isinstance(value, (int, float)):
            return (0, 0, value)
        return (0, 1, str(value))

    return key


def sort_rows(rows: list[dict[str, Any]], order_by: Any) -> list[dict[str, Any]]:
    """Sort rows per ``$order_by`` (list of {field, direction} or "field"/"-field").

    Null values always sort last, regardless of direction.
    """
    if not order_by:
        return list(rows)
    specs = order_by if isinstance(order_by, list) else [order_by]
    result = list(rows)
    for spec in reversed(specs):  # stable sort: last key has lowest priority
        if isinstance(spec, dict):
            field, direction = spec.get("field"), spec.get("direction", "asc")
        elif isinstance(spec, str):
            field, direction = (spec[1:], "desc") if spec.startswith("-") else (spec, "asc")
        else:
            raise ValueError(f"Invalid $order_by spec: {spec!r}")
        if not isinstance(field, str):
            raise ValueError(f"Invalid $order_by spec (needs a field name): {spec!r}")
        if direction not in ("asc", "desc"):
            raise ValueError(f"Invalid sort direction: {direction!r}")
        result.sort(key=_sort_key(field))
        if direction == "desc":
            non_null = [r for r in result if _field_value(r, field) is not None]
            nulls = [r for r in result if _field_value(r, field) is None]
            result = non_null[::-1] + nulls
    return result


def field_visible(field_def: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    """Decide column visibility (``visible`` / ``visible_when`` with any/all scope)."""
    if field_def.get("visible") is False:
        return False
    condition = field_def.get("visible_when")
    if not condition:
        return True
    if not isinstance(condition, dict) or "field" not in condition:
        raise ValueError(f"Invalid visible_when condition: {condition!r}")
    scope = condition.get("scope", "any")
    if scope not in ("any", "all"):
        raise ValueError(f"Invalid visible_when scope: {scope!r}")
    matches = [evaluate_condition(r, condition) for r in rows if isinstance(r, dict)]
    return any(matches) if scope == "any" else all(matches)


def aggregate_values(rows: list[dict[str, Any]], field: str, func: str) -> Any:
    """Aggregate a field over sibling rows. Returns ``""`` when there is nothing to show."""
    if func not in AGGREGATIONS:
        raise ValueError(f"Unknown aggregate: {func!r} (expected one of {AGGREGATIONS})")
    if func == "count":
        return sum(1 for r in rows if isinstance(r, dict))
    numbers: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            numbers.append(float(row[field]))
        except (KeyError, TypeError, ValueError):
            continue
    if not numbers:
        return ""
    if func == "sum":
        return sum(numbers)
    if func == "avg":
        return sum(numbers) / len(numbers)
    if func == "min":
        return min(numbers)
    return max(numbers)


def build_report(data_raw: list[dict[str, Any]], layout_raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build (dataset, layout) with parameters applied (filtering, sorting, totals).

    Layout shape mirrors ``convert_layout`` with ``footer`` lists added wherever
    aggregates are declared, plus top-level ``summary`` when declared there.
    """
    rows = sort_rows(filter_rows(data_raw, layout_raw.get("$print_when")), layout_raw.get("$order_by"))
    items = [_convert_item(record, layout_raw) for record in rows]
    inner = _build_layout(layout_raw, rows)
    collected, summary_defs = _collect_summary(rows, layout_raw)
    summary: dict[str, Any] | None = collected or None
    layout: dict[str, Any] = {"groups": inner}
    if summary_defs:
        layout["summary"] = [format_field(f, summary_defs[f]) for f in summary_defs]
    return {"groups": items, "summary": summary}, layout


def _collect_summary(rows: list[dict[str, Any]], node: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Grand totals: aggregates declared at any level, computed over all rows at that path."""
    field_defs, group_nodes, _options = split_layout_node(node)
    summary: dict[str, Any] = {}
    defs: dict[str, Any] = {}
    for f, d in field_defs.items():
        if d.get("aggregate"):
            value = aggregate_values(rows, f, d["aggregate"])
            if value != "" and value is not None:
                summary[f] = value
                defs[f] = d
    for gkey, sub in group_nodes.items():
        kids: list[dict[str, Any]] = []
        for r in rows:
            kids.extend([c for c in (r.get(gkey, []) or []) if isinstance(c, dict)])
        sub_summary, sub_defs = _collect_summary(kids, sub)
        for f, v in sub_summary.items():
            if f not in summary:
                summary[f] = v
                defs[f] = sub_defs[f]
    return summary, defs


def _meaningful(values: dict[str, Any]) -> dict[str, Any] | None:
    """Return the dict only if at least one computed value is displayable."""
    if values and any(v != "" and v is not None for v in values.values()):
        return values
    return None


def _visible_fields(field_defs: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    return [k for k, v in field_defs.items() if field_visible(v, rows)]


def template_header_layout(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Header-only layout for data already in template format (records with ``fields``)."""
    sample = data[0].get("fields", {}) if data and isinstance(data[0], dict) else {}
    if not isinstance(sample, dict):
        sample = {}
    return {"groups": {"header": [format_field(k, {}) for k in sample]}}


def _has_nested_groups(sub_node: dict[str, Any]) -> bool:
    """True when the sub-layout declares a deeper group level (vs. a flat row list)."""
    return any(_is_group_node(v) for k, v in sub_node.items() if not k.startswith("$"))


def _convert_item(record: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Convert one raw record (recursive): fields, groups, detail tables + footers.

    A group key whose sub-layout declares deeper groups becomes nested ``groups``
    entries; a group key over a flat row list becomes a ``details`` table.
    Multiple tables per item are supported (e.g. products + fees).
    """
    field_defs, group_nodes, _options = split_layout_node(node)
    fields = {k: record.get(k) for k in field_defs if k in record}

    groups: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    footer_funcs: dict[str, str] = {}
    footer_rows: dict[str, list[dict[str, Any]]] = {}
    for key, sub_node in group_nodes.items():
        children = record.get(key, []) or []
        children = [c for c in children if isinstance(c, dict)]
        children = sort_rows(filter_rows(children, sub_node.get("$print_when")), sub_node.get("$order_by"))
        sub_fields, _sub_groups, _sub_options = split_layout_node(sub_node)
        children = _apply_running_balance(children, sub_fields)
        if _has_nested_groups(sub_node):
            for f, d in sub_fields.items():
                if d.get("aggregate") and f not in footer_funcs:
                    footer_funcs[f] = d["aggregate"]
                    footer_rows[f] = children
            for child in children:
                groups.append(_convert_item(child, sub_node))
        else:
            table: dict[str, Any] = {"rows": children}
            table_footer = _meaningful(
                {f: aggregate_values(children, f, d["aggregate"]) for f, d in sub_fields.items() if d.get("aggregate")}
            )
            if table_footer is not None:
                table["footer"] = table_footer
            if children:
                details[key] = table

    item: dict[str, Any] = {"fields": fields}
    if groups:
        item["groups"] = groups
    if details:
        item["details"] = details
    computed_footer = _meaningful({f: aggregate_values(footer_rows[f], f, func) for f, func in footer_funcs.items()})
    if computed_footer is not None:
        item["footer"] = computed_footer
    return item


def _apply_running_balance(rows: list[dict[str, Any]], field_defs: dict[str, Any]) -> list[dict[str, Any]]:
    """Fill ``running_balance`` columns with the cumulative sum of their source field.

    Spec form: ``"running_balance": "<source field>"`` (starts at zero) or
    ``"running_balance": {"of": "<source field>", "start": <opening balance>}``.
    Rows are copied so user-supplied dicts are never mutated. Non-numeric source
    values count as zero.
    """
    specs: dict[str, tuple[str, float]] = {}
    for key, value in field_defs.items():
        spec = value.get("running_balance") if isinstance(value, dict) else None
        if isinstance(spec, str):
            specs[key] = (spec, 0.0)
        elif isinstance(spec, dict) and spec.get("of"):
            try:
                specs[key] = (spec["of"], float(spec.get("start", 0) or 0))
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid running_balance start for {key!r}: {spec!r}") from e
        elif spec is not None:
            raise ValueError(f"Invalid running_balance spec for {key!r}: {spec!r}")
    if not specs or not rows:
        return rows
    out: list[dict[str, Any]] = []
    balances: dict[str, float] = {}
    for row in rows:
        row = dict(row) if isinstance(row, dict) else row
        out.append(row)
        if not isinstance(row, dict):
            continue
        for key, (source, start) in specs.items():
            if key not in balances:
                balances[key] = start
            try:
                delta = float(row.get(source, 0) or 0)
            except (TypeError, ValueError):
                delta = 0.0
            balances[key] = balances[key] + delta
            row[key] = balances[key]
    return out


def _build_layout(node: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the render-ready layout fragment for one level (visibility-aware).

    Mirrors the data shape: ``header`` (own fields), ``groups`` (child fragment),
    ``details`` (leaf table columns per key), ``footer`` (child-level aggregate
    fields). Group keys with deeper nesting share a single child fragment built
    from the first nested key (documented limitation).
    """
    field_defs, group_nodes, _options = split_layout_node(node)
    visible = _visible_fields(field_defs, rows)
    header = [format_field(k, field_defs[k]) for k in visible]

    child_rows: dict[str, list[dict[str, Any]]] = {}
    for gkey in group_nodes:
        kids: list[dict[str, Any]] = []
        for r in rows:
            kids.extend([c for c in (r.get(gkey, []) or []) if isinstance(c, dict)])
        child_rows[gkey] = kids

    footer: list[dict[str, Any]] = []
    seen: set[str] = set()
    for gkey, sub in group_nodes.items():
        if not _has_nested_groups(sub):
            continue
        sub_fields, _sg, _so = split_layout_node(sub)
        for f in _visible_fields(sub_fields, child_rows[gkey]):
            if sub_fields[f].get("aggregate") and f not in seen:
                seen.add(f)
                footer.append(format_field(f, sub_fields[f]))

    child_layout = None
    nested_key = next((k for k, v in group_nodes.items() if _has_nested_groups(v)), None)
    if nested_key is not None:
        child_layout = _build_layout(group_nodes[nested_key], child_rows[nested_key])

    details: dict[str, Any] = {}
    for gkey, sub in group_nodes.items():
        if _has_nested_groups(sub):
            continue
        sub_fields, _sg, _so = split_layout_node(sub)
        details[gkey] = [format_field(k, sub_fields[k]) for k in _visible_fields(sub_fields, child_rows[gkey])]

    fragment: dict[str, Any] = {"header": header}
    if child_layout is not None:
        fragment["groups"] = child_layout
    if details:
        fragment["details"] = details
    if footer:
        fragment["footer"] = footer
    return fragment
