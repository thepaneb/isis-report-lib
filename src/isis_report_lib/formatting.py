"""Locale-aware value formatting (Babel/CLDR).

The locale comes from ``meta.locale`` (default ``"pt-BR"``) and drives the
``int``/``float``/``percent``/``currency``/``date`` masks. ``meta.currency``
optionally overrides the currency code (default: the locale's territory currency).
"""

import datetime
from functools import lru_cache, partial
from typing import Any

from babel.core import Locale, UnknownLocaleError
from babel.dates import format_date as _format_date
from babel.numbers import NumberFormatError, format_decimal, format_percent, get_territory_currencies
from babel.numbers import format_currency as _format_currency

DEFAULT_LOCALE = "pt-BR"


@lru_cache(maxsize=32)
def normalize_locale(locale: str) -> str:
    """Accept ``pt-BR`` or ``pt_BR``; raise ``ValueError`` for unknown locales."""
    norm = locale.replace("-", "_")
    try:
        Locale.parse(norm)
    except (UnknownLocaleError, ValueError) as e:
        raise ValueError(f"Unknown locale: {locale!r}") from e
    return norm


@lru_cache(maxsize=32)
def default_currency(normalized_locale: str) -> str:
    """Return the locale territory's currency code (``USD`` fallback)."""
    try:
        territory = Locale.parse(normalized_locale).territory
        codes = get_territory_currencies(territory) if territory else []
        return codes[0] if codes else "USD"
    except UnknownLocaleError as e:
        raise ValueError(f"Unknown locale: {normalized_locale!r}") from e


def field_text(value: Any, field: dict[str, Any] | None) -> str | None:
    """Mapped display text via ``substitutions``/``missing_text``, else None.

    ``substitutions`` maps raw values (exact match, then ``str(value)`` match)
    to display strings; a ``None`` value with no substitution falls back to
    ``missing_text`` (default: unmapped, i.e. None). Non-dict ``substitutions``
    is a schema error.
    """
    if not isinstance(field, dict):
        return None
    if "substitutions" in field:
        subs = field["substitutions"]
        if not isinstance(subs, dict):
            raise ValueError(f"Invalid substitutions (must be an object): {subs!r}")
        try:
            if value in subs:
                return str(subs[value])
        except TypeError:
            pass
        if value is not None and str(value) in subs:
            return str(subs[str(value)])
    if value is None and "missing_text" in field:
        missing = field["missing_text"]
        return "" if missing is None else str(missing)
    return None


def format_value(
    value: Any,
    format_mask: str,
    locale: str = DEFAULT_LOCALE,
    currency: str | None = None,
    field: dict[str, Any] | None = None,
) -> str:
    """Format a value according to the mask and locale.

    Masks: ``str`` · ``int`` · ``float`` · ``percent`` (fraction, e.g. ``0.09`` → ``9%``) ·
    ``currency`` · ``bool`` (``Yes``/``No``) · ``date`` (``date``/``datetime`` objects are
    localized; strings pass through) · ``sparkline`` (list of numbers → inline
    SVG nanoplot; ``spark_kind`` ``line``|``bar`` and ``spark_color`` field options).
    ``None`` → ``""``.

    ``field`` (the layout field definition) applies ``substitutions`` first,
    then ``missing_text`` for ``None`` — see :func:`field_text`. Templates pass
    the current field; direct callers may omit it (previous behavior).
    """
    mapped = field_text(value, field)
    if mapped is not None:
        return mapped
    if value is None:
        return ""
    if format_mask == "sparkline":
        from isis_report_lib.charts import sparkline

        options = field if isinstance(field, dict) else {}
        return sparkline(
            value,
            kind=options.get("spark_kind", "line"),
            color=options.get("spark_color", "#0A2F46"),
        )
    norm = normalize_locale(locale)
    if format_mask == "int":
        try:
            return format_decimal(int(value), format="#,##0", locale=norm)
        except (ValueError, TypeError, NumberFormatError):
            return str(value)
    if format_mask == "float":
        try:
            return format_decimal(float(value), format="#,##0.00", locale=norm)
        except (ValueError, TypeError, NumberFormatError):
            return str(value)
    if format_mask == "percent":
        try:
            return format_percent(float(value), format="#,##0.00%", locale=norm)
        except (ValueError, TypeError, NumberFormatError):
            return str(value)
    if format_mask == "currency":
        code = currency or default_currency(norm)
        try:
            return _format_currency(float(value), code, locale=norm)
        except (ValueError, TypeError, NumberFormatError):
            return str(value)
    if format_mask == "bool":
        if isinstance(value, str):
            return "Yes" if value.strip().lower() in {"true", "yes", "y", "1", "sim"} else "No"
        return "Yes" if value else "No"
    if format_mask == "date":
        if isinstance(value, (datetime.date, datetime.datetime)):
            return _format_date(value, locale=norm)
        return str(value)
    return str(value)


def formatter_for(meta: dict[str, Any]):
    """Build the ``fmt(value, mask)`` helper bound to the payload's locale/currency."""
    return partial(
        format_value,
        locale=meta.get("locale", DEFAULT_LOCALE),
        currency=meta.get("currency"),
    )


CONDITION_OPS = (
    "equals",
    "not_equals",
    "in",
    "not_in",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "contains",
    "is_null",
    "not_null",
)

STYLE_KEYS = ("color", "background", "bold", "italic")

FOOTNOTE_MARKS = ("*", "†", "‡", "§", "‖", "¶")


def normalize_footnote(spec: Any, where: str) -> dict[str, Any]:
    """Normalize a footnote to ``{"mark": str | None, "text": str}``.

    Shorthand: a plain string is the note text (mark auto-assigned later).
    Explicit form: ``{"text": ..., "mark": ...}`` (mark optional). Marks are
    validated and auto-assigned by :func:`assign_footnote_marks`.
    """
    if isinstance(spec, str):
        if not spec:
            raise ValueError(f"Invalid empty footnote for {where}")
        return {"mark": None, "text": spec}
    if isinstance(spec, dict):
        unknown = [k for k in spec if k not in ("mark", "text")]
        if unknown:
            raise ValueError(f"Invalid footnote keys {unknown!r} for {where}")
        text = spec.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"Invalid footnote text for {where}: {spec!r}")
        mark = spec.get("mark")
        if mark is not None and (not isinstance(mark, str) or not mark):
            raise ValueError(f"Invalid footnote mark for {where}: {spec!r}")
        return {"mark": mark, "text": text}
    raise ValueError(f"Invalid footnote for {where} (need text or {{mark, text}}): {spec!r}")


def assign_footnote_marks(fields: list[dict[str, Any]], state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fill auto marks (``*†‡§‖¶`` then numbers) in a normalized field list.

    ``state`` carries ``{"used": set, "by_text": dict, "auto": int}`` across
    calls so numbering is deterministic in render order. Same text reuses its
    mark; an explicit mark colliding with another text raises ``ValueError``.
    """
    if state is None:
        state = {"used": set(), "by_text": {}, "auto": 0}
    for f in fields:
        note = f.get("footnote") if isinstance(f, dict) else None
        if not isinstance(note, dict):
            continue
        mark, text = note.get("mark"), note.get("text")
        if text in state["by_text"]:
            mark = state["by_text"][text]
            if note.get("mark") is not None and note["mark"] != mark:
                raise ValueError(f"Conflicting footnote marks for the same note: {text!r}")
        else:
            if mark is None:
                while True:
                    n = state["auto"]
                    candidate = FOOTNOTE_MARKS[n] if n < len(FOOTNOTE_MARKS) else str(n - len(FOOTNOTE_MARKS) + 1)
                    state["auto"] += 1
                    if candidate not in state["used"]:
                        mark = candidate
                        break
            elif mark in state["used"]:
                raise ValueError(f"Duplicate footnote mark {mark!r} for different notes")
            state["by_text"][text] = mark
        note["mark"] = mark
        state["used"].add(mark)
    return state


def _parse_hex_color(spec: Any, where: str) -> tuple[int, int, int]:
    if not isinstance(spec, str) or not spec.startswith("#"):
        raise ValueError(f"Invalid color for {where} (need #rrggbb): {spec!r}")
    hexpart = spec[1:]
    if len(hexpart) == 3:
        hexpart = "".join(c * 2 for c in hexpart)
    if len(hexpart) != 6:
        raise ValueError(f"Invalid color for {where} (need #rrggbb): {spec!r}")
    try:
        return int(hexpart[0:2], 16), int(hexpart[2:4], 16), int(hexpart[4:6], 16)
    except ValueError as e:
        raise ValueError(f"Invalid color for {where} (need #rrggbb): {spec!r}") from e


def normalize_color_scale(spec: Any, where: str) -> dict[str, str]:
    """Validate a ``color_scale`` (``{min, max}`` #rrggbb colors)."""
    if not isinstance(spec, dict):
        raise ValueError(f"Invalid color_scale for {where} (need {{min, max}} colors): {spec!r}")
    unknown = [k for k in spec if k not in ("min", "max")]
    if unknown or "min" not in spec or "max" not in spec:
        raise ValueError(f"Invalid color_scale for {where} (need {{min, max}} colors): {spec!r}")
    _parse_hex_color(spec["min"], where)
    _parse_hex_color(spec["max"], where)
    return {"min": spec["min"], "max": spec["max"]}


def color_scale_fill(value: float, low: float, high: float, min_color: str, max_color: str) -> str:
    """Interpolate a ``#rrggbb`` fill between min/max colors (clamped)."""
    lo_rgb, hi_rgb = _parse_hex_color(min_color, "color_scale"), _parse_hex_color(max_color, "color_scale")
    t = 0.5 if high == low else min(1.0, max(0.0, (value - low) / (high - low)))
    mixed = tuple(round(lo + (hi - lo) * t) for lo, hi in zip(lo_rgb, hi_rgb, strict=True))
    return f"#{mixed[0]:02X}{mixed[1]:02X}{mixed[2]:02X}"


SPARK_BLOCKS = (" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")


def sparkline_text(value: Any) -> str:
    """Unicode block-art nanoplot (``""`` when there is no data).

    Text-safe fallback for CSV/XLSX, where inline SVG cannot be embedded.
    """
    from isis_report_lib.charts import _spark_numbers

    numbers = _spark_numbers(value)
    if not numbers:
        return ""
    lo, hi = min(numbers), max(numbers)
    span = (hi - lo) or 1.0
    return "".join(SPARK_BLOCKS[1 + int((v - lo) / span * 7)] for v in numbers)


def match_rule(value: Any, rule: dict[str, Any]) -> bool:
    """Match a value against every comparison operator in the rule (AND).

    Operators: ``equals`` · ``not_equals`` · ``in`` · ``not_in`` ·
    ``gt`` · ``gte`` · ``lt`` · ``lte`` · ``between`` (``[lo, hi]``,
    inclusive) · ``contains`` (substring of the stringified value) ·
    ``is_null`` · ``not_null``. Style keys (``color`` …) and unknown keys
    are ignored here (``cell_style_dict`` rejects the latter). A rule with
    no comparison operator matches everything (catch-all default).
    """
    matched = False
    for op in CONDITION_OPS:
        if op not in rule:
            continue
        matched = True
        expected = rule[op]
        if op == "equals":
            if not value == expected:
                return False
        elif op == "not_equals":
            if not value != expected:
                return False
        elif op == "in":
            try:
                if value not in expected:
                    return False
            except TypeError:
                return False
        elif op == "not_in":
            try:
                if value in expected:
                    return False
            except TypeError:
                return False
        elif op == "is_null":
            if value is not None:
                return False
        elif op == "not_null":
            if value is None:
                return False
        elif op == "between":
            try:
                lo, hi = expected
            except (TypeError, ValueError) as e:
                raise ValueError(f"'between' needs a [lo, hi] pair: {rule!r}") from e
            try:
                if not lo <= value <= hi:
                    return False
            except TypeError:
                return False
        elif op == "contains":
            if not isinstance(expected, str):
                raise ValueError(f"'contains' needs a string needle: {rule!r}")
            if value is None or expected not in str(value):
                return False
        else:  # gt / gte / lt / lte
            try:
                if op == "gt":
                    ok = bool(value > expected)
                elif op == "gte":
                    ok = bool(value >= expected)
                elif op == "lt":
                    ok = bool(value < expected)
                else:
                    ok = bool(value <= expected)
            except TypeError:
                return False
            if not ok:
                return False
    if not matched:
        raise ValueError(f"Rule has no known operator: {rule!r}")
    return True


def cell_style_dict(value: Any, field_def: dict[str, Any]) -> dict[str, Any]:
    """First matching ``cell_rules`` entry as a style dict ({} when none match).

    Rule form: ``{"gte": 1000, "lt": 5000, "color": "#C00000", "bold": True}``
    — all comparison operators in the rule must hold (AND); a rule with no
    comparison operator is a catch-all default. Style keys are any of
    ``color``/``background``/``bold``/``italic``.
    """
    for rule in field_def.get("cell_rules", []) or []:
        if not isinstance(rule, dict):
            raise ValueError(f"Invalid cell rule (must be an object): {rule!r}")
        unknown = [k for k in rule if k not in CONDITION_OPS + STYLE_KEYS]
        if unknown:
            raise ValueError(f"Invalid cell rule keys {unknown!r}: {rule!r}")
        if not any(k in CONDITION_OPS for k in rule) or match_rule(value, rule):
            return {k: rule[k] for k in STYLE_KEYS if k in rule}
    return {}


def cell_style(value: Any, field_def: dict[str, Any]) -> str:
    """First matching ``cell_rules`` entry as inline CSS ("" when none match).

    A ``color_scale`` gradient fill applies when no rule set a background and
    the field carries a computed ``color_domain`` (see ``layout``).
    """
    style = cell_style_dict(value, field_def)
    parts = []
    if style.get("color"):
        parts.append(f"color:{style['color']}")
    background = style.get("background") or scale_fill(value, field_def)
    if background:
        parts.append(f"background:{background}")
    if style.get("bold"):
        parts.append("font-weight:bold")
    if style.get("italic"):
        parts.append("font-style:italic")
    return ";".join(parts)


def scale_fill(value: Any, field_def: dict[str, Any] | None) -> str | None:
    """Gradient fill for ``color_scale`` fields with a ``color_domain`` (else None)."""
    if not isinstance(field_def, dict):
        return None
    scale = field_def.get("color_scale")
    domain = field_def.get("color_domain")
    if not isinstance(scale, dict) or not isinstance(domain, (list, tuple)) or len(domain) != 2:
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    try:
        return color_scale_fill(number, float(domain[0]), float(domain[1]), scale["min"], scale["max"])
    except (TypeError, ValueError, KeyError):
        return None
