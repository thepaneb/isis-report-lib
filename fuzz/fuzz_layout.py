"""Fuzz target: layout definitions (field specs, rules, aggregates).

Layout comes from the "schema" trust zone: validated strictly, never executed.
This target feeds hand-built-but-mutated layouts (from a fuzzed structured
buffer) through ``build_report`` and asserts the same contract: data out or
``ValueError``, never an internal exception.

Run:  python fuzz/fuzz_layout.py -max_total_time=60
Seed: corpus/layout/*.json
"""

import json
import sys

import atheris

with atheris.instrument_imports():
    from isis_report_lib.layout import build_report

DATA = [
    {"name": "a", "total": 1, "status": "ok", "when": "2024-01-01", "items": [{"x": 1}, {"x": 2}]},
    {"name": "b", "total": -5, "status": "cancelled", "when": "2024-02-02", "items": []},
]


def _build_layout(text: str) -> dict:
    try:
        raw = json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        return {}
    if not isinstance(raw, dict):
        return {}
    layout = {}
    for name, spec in raw.items():
        if not isinstance(name, str):
            continue
        if isinstance(spec, dict):
            layout[name] = spec
        else:
            layout[name] = {"label": str(spec)[:40]}
    return layout


def TestOneInput(data: bytes) -> None:
    layout = _build_layout(data.decode("utf-8", errors="replace"))
    try:
        dataset, normalized = build_report(DATA, layout)
    except ValueError:
        return  # documented failure mode
    except RecursionError:
        raise AssertionError("RecursionError leaked past build_report") from None
    if not isinstance(dataset, dict) or not isinstance(normalized, dict):
        raise AssertionError("build_report must return dicts")


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
