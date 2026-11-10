"""Locale-aware value formatting (Babel/CLDR).

The locale comes from ``meta.locale`` (default ``"pt-BR"``) and drives the
``int``/``float``/``percent``/``currency``/``date`` masks. ``meta.currency``
optionally overrides the currency code (default: the locale's territory currency).
"""

import datetime
from functools import partial
from typing import Any

from babel.core import Locale, UnknownLocaleError
from babel.dates import format_date as _format_date
from babel.numbers import NumberFormatError, format_decimal, format_percent, get_territory_currencies
from babel.numbers import format_currency as _format_currency

DEFAULT_LOCALE = "pt-BR"


def normalize_locale(locale: str) -> str:
    """Accept ``pt-BR`` or ``pt_BR``; raise ``ValueError`` for unknown locales."""
    norm = locale.replace("-", "_")
    try:
        Locale.parse(norm)
    except (UnknownLocaleError, ValueError) as e:
        raise ValueError(f"Unknown locale: {locale}") from e
    return norm


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
