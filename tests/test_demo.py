"""The runnable demo payload must stay valid and render."""

import json
from pathlib import Path

from isis_report_lib import render_html

DEMO = Path(__file__).resolve().parents[1] / "demo"


def test_demo_payload_renders() -> None:
    payload = json.loads((DEMO / "payload.json").read_text(encoding="utf-8"))
    html = render_html(payload)
    assert "Quarterly Board Pack" in html
    assert "Contents" in html
    assert "Revenue by product" in html
    assert "Revenue by region" in html
    assert "DRAFT" in html
    assert "<svg" in html
