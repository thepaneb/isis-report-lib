"""Fuzz target: JSON/CSV payload intake through the report pipeline.

Invariant under test: a payload assembled from untrusted bytes either renders
or raises ``ValueError``. The envelope gate (``prepare_report``) plus the field
normalizers must reject garbage rather than crash, so ``RecursionError`` and
friends escaping here are real defects.

Run:  python fuzz/fuzz_payload.py -max_total_time=60
Seed: corpus/payload/*.json
"""

import json
import sys

import atheris

with atheris.instrument_imports():
    from isis_report_lib.service import prepare_report


def TestOneInput(data: bytes) -> None:
    text = data.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        return  # not our input shape

    payload = parsed if isinstance(parsed, dict) else {"data": parsed}
    try:
        dataset, layout, meta = prepare_report(payload)
    except ValueError:
        return  # documented failure mode
    except RecursionError:
        raise AssertionError("RecursionError leaked past prepare_report") from None
    if not all(isinstance(part, dict) for part in (dataset, layout, meta)):
        raise AssertionError("prepare_report must return three dicts")


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
