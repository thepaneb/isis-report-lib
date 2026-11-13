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
        raise ValueError(f"Unknown locale: {locale}") from e
    return norm


@lru_cache(maxsize=32)
def default_currency(normalized_locale: str) -> str:
    """Return the locale territory's currency code (``USD`` fallback)."""
    try:
        territory = Locale.parse(normalized_locale).territory
        codes = get_territory_currencies(territory) if territory else []
        return codes[0] if codes else "USD"
    except UnknownLocaleError as e:
        raise ValueError(f"Unknown locale: {normalized_locale}") from e


def format_value(value: Any, format_mask: str, locale: str = DEFAULT_LOCALE, currency: str | None = None) -> str:
    """Format a value according to the mask and locale.

    Masks: ``str`` · ``int`` · ``float`` · ``percent`` (fraction, e.g. ``0.09`` → ``9%``) ·
    ``currency`` · ``bool`` (``Yes``/``No``) · ``date`` (``date``/``datetime`` objects are
    localized; strings pass through). ``None`` → ``""``.
    """
    if value is None:
        return ""
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


CONDITION_OPS = ("equals", "not_equals", "in", "not_in", "gt", "gte", "lt", "lte", "is_null", "not_null")

STYLE_KEYS = ("color", "background", "bold", "italic")


def match_rule(value: Any, rule: dict[str, Any]) -> bool:
    """Match a single value against ``{operator: expected, ...}`` (other keys ignored)."""
    for op in CONDITION_OPS:
        if op not in rule:
            continue
        expected = rule[op]
        if op == "equals":
            return bool(value == expected)
        if op == "not_equals":
            return bool(value != expected)
        if op == "in":
            return value in expected
        if op == "not_in":
            return value not in expected
        if op == "is_null":
            return value is None
        if op == "not_null":
            return value is not None
        try:
            if op == "gt":
                return bool(value > expected)
            if op == "gte":
                return bool(value >= expected)
            if op == "lt":
                return bool(value < expected)
            if op == "lte":
                return bool(value <= expected)
        except TypeError:
            return False
    raise ValueError(f"Rule has no known operator: {rule!r}")


def cell_style_dict(value: Any, field_def: dict[str, Any]) -> dict[str, Any]:
    """First matching ``cell_rules`` entry as a style dict ({} when none match).

    Rule form: ``{"lt": 0, "color": "#C00000", "bold": True}`` — one comparison
    operator plus any of ``color``/``background``/``bold``/``italic``.
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
    """First matching ``cell_rules`` entry as inline CSS ("" when none match)."""
    style = cell_style_dict(value, field_def)
    parts = []
    if style.get("color"):
        parts.append(f"color:{style['color']}")
    if style.get("background"):
        parts.append(f"background:{style['background']}")
    if style.get("bold"):
        parts.append("font-weight:bold")
    if style.get("italic"):
        parts.append("font-style:italic")
    return ";".join(parts)
