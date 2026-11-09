"""Value formatting for template output (int/float/date/str masks)."""

from typing import Any


def format_value(value: Any, format_mask: str) -> str:
    """Format a value according to the layout mask.

    - ``int``: thousand-separated (``1234`` -> ``"1.234"``)
    - ``float``: pt-BR with 2 decimals (``1234.5`` -> ``"1.234,50"``)
    - ``date``: passed through as string
    - anything else: ``str(value)``; ``None`` -> ``""``
    """
    if value is None:
        return ""
    if format_mask == "int":
        try:
            return f"{int(value):,}".replace(",", ".")
        except (ValueError, TypeError):
            return str(value)
    if format_mask == "float":
        try:
            return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return str(value)
    if format_mask == "date":
        return str(value)
    if format_mask == "percent":
        try:
            return f"{float(value) * 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " %"
        except (ValueError, TypeError):
            return str(value)
    if format_mask == "currency":
        try:
            return "R$ " + f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return str(value)
    if format_mask == "bool":
        if isinstance(value, str):
            return "Yes" if value.strip().lower() in {"true", "yes", "y", "1", "sim"} else "No"
        return "Yes" if value else "No"
    return str(value)
