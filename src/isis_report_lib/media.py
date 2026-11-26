"""Validation for inline report media (data-URI images and watermarks).

Report payloads are untrusted input. Images therefore arrive **only** as
``data:image/...;base64`` URIs: the library never reads a path or fetches a
URL from the payload. The decoded bytes are capped and their magic signature
must match the declared MIME type (defense in depth against a mislabelled
polyglot). SVG is deliberately rejected: it is a document format with script
and external-reference surface, not a safe report image.
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import Any

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_WATERMARK_LENGTH = 200

_IMAGE_RE = re.compile(r"^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/]+={0,2})$")
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_WATERMARK_KEYS = ("text", "opacity", "color", "angle", "size")


def _magic_ok(mime: str, raw: bytes) -> bool:
    if mime == "image/png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/jpeg":
        return raw.startswith(b"\xff\xd8\xff")
    if mime == "image/gif":
        return raw.startswith((b"GIF87a", b"GIF89a"))
    if mime == "image/webp":
        return len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
    return False


def normalize_image_src(value: Any, field: str = "image") -> str:
    """Validate a ``data:image/...;base64`` URI and return it unchanged.

    ``field`` names the payload location in the error message (e.g.
    ``meta.logo`` or ``image section src``).
    """
    if not isinstance(value, str) or not value.startswith("data:"):
        raise ValueError(f"Invalid {field} (must be a data:image/...;base64 URI): {value!r}")
    match = _IMAGE_RE.match(value)
    if not match:
        raise ValueError(f"Invalid {field} (expected data:image/png|jpeg|webp|gif;base64,...): {value[:48]!r}")
    mime, payload = match.group(1), match.group(2)
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"Invalid {field} (base64 payload is malformed): {e}") from e
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError(f"Invalid {field} ({len(raw)} decoded bytes; max {MAX_IMAGE_BYTES})")
    if not _magic_ok(mime, raw):
        raise ValueError(f"Invalid {field} (decoded bytes do not match {mime})")
    return value


def _number(value: Any, field: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid {field} (must be a number between {minimum} and {maximum}): {value!r}")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"Invalid {field} (must be between {minimum} and {maximum}): {value!r}")
    return number


def normalize_watermark(value: Any) -> dict[str, Any] | None:
    """Normalize ``meta.watermark`` to a validated dict (or ``None``).

    Accepted forms: a string (the text, with defaults) or an object with
    ``text`` and optional ``opacity`` (0–1), ``color`` (``#rgb``/``#rrggbb``),
    ``angle`` (-90–90 degrees) and ``size`` (12–200 px). Unknown keys fail
    closed, like the rest of ``meta``.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = {"text": value}
    if not isinstance(value, dict):
        raise ValueError(f"Invalid meta.watermark (must be a string or object): {value!r}")
    unknown = sorted(set(value) - set(_WATERMARK_KEYS))
    if unknown:
        raise ValueError(f"Unknown meta.watermark key: {unknown[0]!r} (expected {'|'.join(_WATERMARK_KEYS)})")
    text = value.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"Invalid meta.watermark.text (must be a non-empty string): {text!r}")
    if len(text) > MAX_WATERMARK_LENGTH:
        raise ValueError(f"Invalid meta.watermark.text (max {MAX_WATERMARK_LENGTH} characters): {len(text)}")
    color = value.get("color", "#000000")
    if not isinstance(color, str) or not _HEX_COLOR_RE.match(color):
        raise ValueError(f"Invalid meta.watermark.color (expected #rgb or #rrggbb): {color!r}")
    return {
        "text": text,
        "opacity": _number(value.get("opacity", 0.08), "meta.watermark.opacity", minimum=0.0, maximum=1.0),
        "color": color,
        "angle": _number(value.get("angle", -30), "meta.watermark.angle", minimum=-90.0, maximum=90.0),
        "size": int(_number(value.get("size", 80), "meta.watermark.size", minimum=12.0, maximum=200.0)),
    }
