"""dependency-free SVG charts for the ``chart`` section type."""

from typing import Any
from xml.sax.saxutils import escape


def _check_series(labels: list[str], values: list[float]) -> list[float]:
    if not labels or not values:
        raise ValueError("Chart needs non-empty labels and values.")
    if len(labels) != len(values):
        raise ValueError(f"Chart labels ({len(labels)}) and values ({len(values)}) must match in length.")
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError) as e:
        raise ValueError(f"Chart values must be numeric: {e}") from e


def bar_chart(
    labels: list[str],
    values: list[Any],
    width: int = 600,
    height: int = 300,
    color: str = "#0A2F46",
) -> str:
    """Vertical bar chart as an inline SVG string."""
    numbers = _check_series([str(label) for label in labels], values)
    labels = [str(label) for label in labels]
    top, bottom = 22, height - 30
    span = max(numbers) if max(numbers) > 0 else 1
    n = len(numbers)
    slot = width / n
    bar_w = min(slot * 0.6, 60)
    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img">']
    for i, (label, value) in enumerate(zip(labels, numbers, strict=True)):
        bar_h = max((value / span) * (bottom - top), 2 if value else 0)
        x = slot * i + (slot - bar_w) / 2
        y = bottom - bar_h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}"/>')
        if value:
            parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" text-anchor="middle" font-size="11">{value:g}</text>')
        parts.append(f'<text x="{slot * i + slot / 2:.1f}" y="{height - 8}" text-anchor="middle" font-size="11">{escape(label)}</text>')
    parts.append(f'<line x1="0" y1="{bottom}" x2="{width}" y2="{bottom}" stroke="#999"/>')
    parts.append("</svg>")
    return "".join(parts)


def line_chart(
    labels: list[str],
    values: list[Any],
    width: int = 600,
    height: int = 300,
    color: str = "#0A2F46",
) -> str:
    """Line chart with dots as an inline SVG string."""
    numbers = _check_series([str(label) for label in labels], values)
    labels = [str(label) for label in labels]
    top, bottom, left, right = 22, height - 30, 40, width - 10
    lo, hi = min(0, min(numbers)), max(numbers)
    span = (hi - lo) or 1
    n = len(numbers)
    step = (right - left) / (n - 1) if n > 1 else 0

    def x(i: int) -> float:
        return left + step * i

    def y(v: float) -> float:
        return bottom - (v - lo) / span * (bottom - top)

    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img">']
    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(numbers))
    parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
    for i, (label, value) in enumerate(zip(labels, numbers, strict=True)):
        parts.append(f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="3" fill="{color}"/>')
        parts.append(f'<text x="{x(i):.1f}" y="{y(value) - 8:.1f}" text-anchor="middle" font-size="11">{value:g}</text>')
        parts.append(f'<text x="{x(i):.1f}" y="{height - 8}" text-anchor="middle" font-size="11">{escape(label)}</text>')
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#999"/>')
    parts.append("</svg>")
    return "".join(parts)


def build_chart(spec: dict[str, Any]) -> str:
    """Build a chart SVG from a section spec: ``{kind, labels, values, ...}``."""
    kind = spec.get("kind", "bar")
    builders = {"bar": bar_chart, "line": line_chart}
    if kind not in builders:
        raise ValueError(f"Unknown chart kind: {kind!r} (expected one of {sorted(builders)})")
    return builders[kind](
        spec.get("labels", []),
        spec.get("values", []),
        width=int(spec.get("width", 600)),
        height=int(spec.get("height", 300)),
        color=spec.get("color", "#0A2F46"),
    )
