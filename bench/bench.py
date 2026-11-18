"""Benchmarks: build + render + export timings for growing datasets.

Usage: ``python bench/bench.py [--rows N] [--no-pdf]``. ``--check`` runs the
fixed ``bench_budgets.json`` workload and fails when a median exceeds its
smoke-level budget (CI perf gate).
"""

import argparse
import json
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
    parser.add_argument("--check", action="store_true", help="fail when a median exceeds bench_budgets.json")
    args = parser.parse_args()

    if args.check:
        return check_budgets()

    payload = make_payload(args.orders, args.rows // max(args.orders, 1))
    detail_rows = sum(len(o["items"]) for o in payload["data"][0]["orders"])
    print(f"detail rows: {detail_rows}")
    print(f"render_html : {timed(render_html, payload, repeats=args.repeats):8.3f}s (median)")
    print(f"generate_csv: {timed(generate_csv, payload, repeats=args.repeats):8.3f}s (median)")
    print(f"generate_xlsx: {timed(generate_xlsx, payload, repeats=args.repeats):8.3f}s (median)")
    if not args.no_pdf:
        print(f"generate_pdf: {timed(generate_pdf, payload, repeats=args.repeats):8.3f}s (median)")
    return 0


def check_budgets() -> int:
    """Run the fixed budget workload; return 1 listing every overrun."""
    config = json.loads(Path(__file__).parent.joinpath("bench_budgets.json").read_text(encoding="utf-8"))
    cfg_args = config["args"]
    payload = make_payload(cfg_args["orders"], cfg_args["rows"] // max(cfg_args["orders"], 1))
    steps = [
        ("render_html", render_html),
        ("generate_csv", generate_csv),
        ("generate_xlsx", generate_xlsx),
        ("generate_pdf", generate_pdf),
    ]
    failures = []
    for name, fn in steps:
        elapsed = timed(fn, payload, repeats=cfg_args["repeats"])
        budget = config["budgets"][name]
        status = "OK " if elapsed <= budget else "OVER"
        print(f"{name:13} {elapsed:8.3f}s / budget {budget:6.1f}s  [{status}]")
        if elapsed > budget:
            failures.append(f"{name}: {elapsed:.3f}s > budget {budget:.1f}s")
    if failures:
        print("budget exceeded:\n- " + "\n- ".join(failures))
        return 1
    print("all perf budgets met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
