"""Formatação de valores exibidos nos templates (máscaras int/float/date/str)."""

from typing import Any


def format_value(value: Any, format_mask: str) -> str:
    """Formata um valor conforme a máscara do layout.

    - ``int``: milhar com ponto (``1234`` -> ``"1.234"``)
    - ``float``: padrão pt-BR com 2 casas (``1234.5`` -> ``"1.234,50"``)
    - ``date``: repassa como string
    - demais: ``str(value)``; ``None`` -> ``""``
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
    return str(value)
