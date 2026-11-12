"""Payload builders from external data sources (pandas, CSV, JSON).

These helpers convert foreign shapes into the library's payload dicts, ready
for ``generate_pdf`` / ``generate_xlsx`` / ``generate_csv``::

    from isis_report_lib.inputs import from_dataframe
    generate_pdf(from_dataframe(df, meta={"title": "Sales"}))
"""

import csv as csv_module
import json
from pathlib import Path
from typing import Any


def _require_pandas():
    """Import pandas lazily so it stays an optional dependency."""
    try:
        import pandas

        return pandas
    except ImportError as e:
        raise ImportError("DataFrame input requires the 'pandas' extra: pip install isis-report-lib[pandas]") from e


def _clean_value(value: Any, pd: Any) -> Any:
    """Normalize one cell: NaN/NaT/None -> None, pandas Timestamp -> datetime."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    timestamp_type = getattr(pd, "Timestamp", None)
    if timestamp_type is not None and isinstance(value, timestamp_type):
        return value.to_pydatetime()
    return value


def from_dataframe(df: Any, meta: dict[str, Any] | None = None, layout: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a payload from a ``pandas.DataFrame`` (columns become fields)."""
    pd = _require_pandas()
    records = [{str(key): _clean_value(value, pd) for key, value in row.items()} for row in df.to_dict("records")]
    return _with_meta_layout({"data": records}, meta, layout)


def from_csv(
    source: str | Path | Any,
    meta: dict[str, Any] | None = None,
    layout: dict[str, Any] | None = None,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> dict[str, Any]:
    """Build a payload from a CSV file (path or file object) with light type coercion."""
    from isis_report_lib.toon import ToonParser

    coerce = ToonParser._convert_value
    close = False
    if isinstance(source, (str, Path)):
        handle = open(source, encoding=encoding, newline="")
        close = True
    else:
        handle = source
    try:
        records = [
            {k: coerce(v) if isinstance(v, str) else v for k, v in row.items()}
            for row in csv_module.DictReader(handle, delimiter=delimiter)
        ]
    finally:
        if close:
            handle.close()
    return _with_meta_layout({"data": records}, meta, layout)


def from_json(
    source: str | Path | Any,
    meta: dict[str, Any] | None = None,
    layout: dict[str, Any] | None = None,
    encoding: str = "utf-8",
) -> dict[str, Any]:
    """Build a payload from JSON: a list becomes ``data``; a full payload dict passes through."""
    if isinstance(source, (str, Path)):
        with open(source, encoding=encoding) as handle:
            loaded = json.load(handle)
    elif hasattr(source, "read"):
        loaded = json.load(source)
    else:
        loaded = source
    if isinstance(loaded, dict):
        payload = dict(loaded)
        if meta:
            payload["meta"] = {**(payload.get("meta") or {}), **meta}
        if layout is not None:
            payload["layout"] = layout
        return payload
    if isinstance(loaded, list):
        return _with_meta_layout({"data": loaded}, meta, layout)
    raise ValueError(f"JSON input must be a list or a payload object, got {type(loaded).__name__}")


def payload_schema() -> dict[str, Any]:
    """Return the JSON Schema of the report payload (for editors and validation)."""
    from isis_report_lib.models import ReportPayload

    return ReportPayload.model_json_schema()


def _with_meta_layout(payload: dict[str, Any], meta: dict[str, Any] | None, layout: dict[str, Any] | None) -> dict[str, Any]:
    if meta is not None:
        payload["meta"] = meta
    if layout is not None:
        payload["layout"] = layout
    return payload
