"""Fuzz target: `.toon` parser.

Invariant under test: whatever a hostile document contains, the parser either
returns a payload dict or raises ``ValueError`` (fail-closed contract, STANDARDS
§2.2). Any other exception — ``IndexError``, ``KeyError``, ``AttributeError``,
``RecursionError`` leaking through — is a bug and aborts the fuzzer.

Run:  python fuzz/fuzz_toon.py -max_total_time=60
Seed: corpus/toon/*.toon
"""

import sys

import atheris

with atheris.instrument_imports():
    from isis_report_lib.toon import parse_toon


def TestOneInput(data: bytes) -> None:
    text = data.decode("utf-8", errors="replace")
    try:
        payload = parse_toon(text)
    except ValueError:
        return  # documented failure mode
    # A successful parse must stay a payload dict, never a bare scalar.
    if not isinstance(payload, dict):
        raise AssertionError(f"parse_toon returned {type(payload).__name__}, expected dict")


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
