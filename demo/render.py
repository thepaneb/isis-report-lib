#!/usr/bin/env python3
"""Render the demo payload to PDF, HTML, XLSX and CSV.

    python demo/render.py
    python demo/render.py --no-pdf   # skip Chromium

The generated files land in demo/out/ (gitignored).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from isis_report_lib import generate_csv, generate_pdf, generate_xlsx, render_html

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def load_payload() -> dict:
    """Read the demo payload from JSON."""
    return json.loads((HERE / "payload.json").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-pdf", action="store_true", help="skip the PDF (no Chromium needed)")
    args = parser.parse_args(argv)

    payload = load_payload()
    OUT.mkdir(exist_ok=True)

    (OUT / "report.html").write_text(render_html(payload), encoding="utf-8")
    (OUT / "report.xlsx").write_bytes(generate_xlsx(payload))
    (OUT / "report.csv").write_text(generate_csv(payload, bom=True), encoding="utf-8")
    if not args.no_pdf:
        (OUT / "report.pdf").write_bytes(generate_pdf(payload))

    for path in sorted(OUT.iterdir()):
        print(f"{path.relative_to(HERE)}  {path.stat().st_size:>9,} bytes")
    if not args.no_pdf:
        print("\nOpen demo/out/report.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
