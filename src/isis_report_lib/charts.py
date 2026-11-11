"""dependency-free SVG charts for the ``chart`` section type."""

import math
from typing import Any
from xml.sax.saxutils import escape

DEFAULT_COLORS = ["#0A2F46", "#1B7A3D", "#B8860B", "#8B3A3A", "#4A6FA5", "#6B4A8B"]


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
    orientation: str = "vertical",
) -> str:
    """Bar chart as an inline SVG string (``orientation``: vertical or horizontal)."""
    if orientation not in ("vertical", "horizontal"):
        raise ValueError(f"Unknown bar orientation: {orientation!r} (expected vertical|horizontal)")
    if orientation == "horizontal":
        return _horizontal_bar_chart(labels, values, width, height, color)
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


def _horizontal_bar_chart(labels: list[str], values: list[Any], width: int, height: int, color: str) -> str:
    """Horizontal bar chart as an inline SVG string."""
    numbers = _check_series([str(label) for label in labels], values)
    labels = [str(label) for label in labels]
    left, right, row_h, gap = 120, 10, 26, 10
    plot_w = width - left - right
    span = max(numbers) if max(numbers) > 0 else 1
    plot_h = len(numbers) * (row_h + gap)
    total_h = max(height, plot_h + 20)
    parts = [f'<svg width="{width}" height="{total_h}" viewBox="0 0 {width} {total_h}" xmlns="http://www.w3.org/2000/svg" role="img">']
    for i, (label, value) in enumerate(zip(labels, numbers, strict=True)):
        y = 10 + i * (row_h + gap)
        bar_w = max((value / span) * plot_w, 2 if value else 0)
        parts.append(f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{row_h}" fill="{color}"/>')
        if value:
            parts.append(f'<text x="{left + bar_w + 4:.1f}" y="{y + 17}" font-size="11">{value:g}</text>')
        parts.append(f'<text x="{left - 6}" y="{y + 17}" text-anchor="end" font-size="11">{escape(label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def pie_chart(
    labels: list[str],
    values: list[Any],
    width: int = 600,
    height: int = 300,
    colors: list[str] | None = None,
    donut: bool = False,
) -> str:
    """Pie (or donut) chart with legend as an inline SVG string."""
    numbers = _check_series([str(label) for label in labels], values)
    labels = [str(label) for label in labels]
    total = sum(numbers)
    if total <= 0:
        raise ValueError("Pie chart needs a positive total.")
    colors = colors or DEFAULT_COLORS
    cx, cy, radius = 150, height // 2, min(140, height // 2 - 10)
    legend_x = 320
    parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img">']
    angle = -90.0
    for i, (label, value) in enumerate(zip(labels, numbers, strict=True)):
        frac = value / total
        sweep = frac * 360.0
        large = 1 if sweep > 180 else 0
        x1, y1 = cx + radius * math.cos(math.radians(angle)), cy + radius * math.sin(math.radians(angle))
        x2, y2 = cx + radius * math.cos(math.radians(angle + sweep)), cy + radius * math.sin(math.radians(angle + sweep))
        color = colors[i % len(colors)]
        parts.append(f'<path d="M {cx},{cy} L {x1:.1f},{y1:.1f} A {radius},{radius} 0 {large},1 {x2:.1f},{y2:.1f} Z" fill="{color}"/>')
        ly = 30 + i * 24
        parts.append(f'<rect x="{legend_x}" y="{ly - 12}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{legend_x + 18}" y="{ly}" font-size="12">{escape(label)} ({frac:.0%})</text>')
        angle += sweep
    if donut:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius // 2}" fill="white"/>')
    parts.append("</svg>")
    return "".join(parts)


def build_chart(spec: dict[str, Any]) -> str:
    """Build a chart SVG from a section spec: ``{kind, labels, values, ...}``."""
    kind = spec.get("kind", "bar")
    if kind == "bar":
        return bar_chart(
            spec.get("labels", []),
            spec.get("values", []),
            width=int(spec.get("width", 600)),
            height=int(spec.get("height", 300)),
            color=spec.get("color", "#0A2F46"),
            orientation=spec.get("orientation", "vertical"),
        )
    if kind in ("pie", "donut"):
        return pie_chart(
            spec.get("labels", []),
            spec.get("values", []),
            width=int(spec.get("width", 600)),
            height=int(spec.get("height", 300)),
            colors=spec.get("colors"),
            donut=(kind == "donut"),
        )
    if kind == "line":
        return line_chart(
            spec.get("labels", []),
            spec.get("values", []),
            width=int(spec.get("width", 600)),
            height=int(spec.get("height", 300)),
            color=spec.get("color", "#0A2F46"),
        )
    raise ValueError(f"Unknown chart kind: {kind!r} (expected one of bar|line|pie|donut)")
