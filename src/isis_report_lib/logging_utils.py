"""Log encoding helpers (ASVS 7.3.1).

The library never logs report data, payload bodies or secrets. When a log line
carries a value that may come from the caller (a host name, a service label),
it must go through :func:`log_value`. The package logger additionally installs
:class:`LogEncodingFilter` as a safety net: every formatted message is
single-line, with CR/LF, ANSI/control characters and Unicode line separators
escaped before it reaches a handler.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER_NAME = "isis_report_lib"
_MAX_FIELD = 200
_installed = False


def _escape(text: str) -> str:
    """Escape line breaks and non-printable characters, never backslashes."""
    out: list[str] = []
    for char in text:
        if char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif char.isprintable():
            out.append(char)
        else:
            code = ord(char)
            out.append(f"\\x{code:02x}" if code <= 0xFF else f"\\u{code:04x}")
    return "".join(out)


def log_value(value: Any, *, max_length: int = _MAX_FIELD) -> str:
    """Encode one caller-controlled value for a single-line log field.

    Escapes CR/LF/tabs, ANSI and other non-printable characters (including
    Unicode line/paragraph separators) and truncates to ``max_length``. The
    result contains no raw line breaks, so it cannot forge a second log line.

    Use it for identifiers and host/label values only — never for keys,
    passwords, payload bodies or other secrets.
    """
    encoded = _escape(str(value))
    if len(encoded) > max_length:
        encoded = encoded[: max_length - 3] + "..."
    return encoded


class LogEncodingFilter(logging.Filter):
    """Encode control characters in every record's formatted message."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # malformed %-args: leave logging to report it
            return True
        encoded = _escape(message)
        if encoded != message:
            record.msg = encoded
            record.args = ()
        return True


def get_logger() -> logging.Logger:
    """Return the package logger, installing the encoding filter once."""
    global _installed
    logger = logging.getLogger(_LOGGER_NAME)
    if not _installed:
        logger.addFilter(LogEncodingFilter())
        _installed = True
    return logger
