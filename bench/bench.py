"""Benchmarks: build + render + export timings for growing datasets.

Usage: ``python bench/bench.py [--rows N] [--no-pdf]``. Not a CI gate — run
manually and record notable numbers in this directory's notes.
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from isis_report_lib import (  # noqa: E402
    generate_csv,
    generate_pdf,
    generate_xlsx,
    render_html,
)


def make_payload(n_orders: int, items_per_order: int) -> dict:
    orders = []
    for o in range(n_orders):
        orders.append(
            {
                "order": o,
                "total": o * 100.0,
                "items": [{"qty": i, "unit_price": 10.0 * i, "line_total": 10.0 * i} for i in range(items_per_order)],
            }
        )
    return {
        "meta": {"title": "Bench", "mode": "exact"},
        "layout": {
            "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
            "orders": {
                "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
                "total": {"label": "Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
                "items": {
                    "qty": {"label": "Qty", "format_mask": "int", "alignment": "right", "aggregate": "sum"},
                    "unit_price": {"label": "Unit", "format_mask": "float", "alignment": "right"},
                    "line_total": {"label": "Line", "format_mask": "float", "alignment": "right"},
                },
            },
        },
        "data": [{"company": "ACME", "orders": orders}],
    }


def timed(fn, *args, repeats: int = 3):
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn(*args)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark report generation.")
    parser.add_argument("--rows", type=int, default=1000, help="detail rows per order group")
    parser.add_argument("--orders", type=int, default=10, help="number of orders")
    parser.add_argument("--no-pdf", action="store_true", help="skip PDF (needs Chromium)")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    payload = make_payload(args.orders, args.rows // max(args.orders, 1))
    detail_rows = sum(len(o["items"]) for o in payload["data"][0]["orders"])
    print(f"detail rows: {detail_rows}")
    print(f"render_html : {timed(render_html, payload, repeats=args.repeats):8.3f}s (median)")
    print(f"generate_csv: {timed(generate_csv, payload, repeats=args.repeats):8.3f}s (median)")
    print(f"generate_xlsx: {timed(generate_xlsx, payload, repeats=args.repeats):8.3f}s (median)")
    if not args.no_pdf:
        print(f"generate_pdf: {timed(generate_pdf, payload, repeats=args.repeats):8.3f}s (median)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
