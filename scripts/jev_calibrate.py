#!/usr/bin/env python3
"""Run a local Jev calibration corpus and detect verdict drift.

The corpus is a JSON file with ``cases``. Each case points at a saved diff and
an expected verdict. The harness invokes ``scripts/jev_review.py`` for each
case, reads the JSON report, and compares the verdict.

Example config (see ``calibration/jev-cases.example.json``)::

    {
      "cases": [
        {"name": "pr98", "diff": "pr98.diff", "expected": "comment", "profile": "strict"},
        {"name": "security-bad", "diff": "security-bad.diff", "expected": "block", "profile": "security"}
      ]
    }

Typical use::

    gh pr diff 98 > calibration/pr98.diff
    python scripts/jev_calibrate.py --config calibration/jev-cases.json
    python scripts/jev_calibrate.py --config calibration/jev-cases.json --dry-run
    python scripts/jev_calibrate.py --config calibration/jev-cases.json --case pr98

This harness calls the API only when not in ``--dry-run``/``--self-test`` mode.
It is intentionally not part of CI (the secret and model cost stay local).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "scripts" / "jev_review.py"
DEFAULT_CONFIG = ROOT / "calibration" / "jev-cases.json"
VERDICTS = ("approve", "comment", "block")
PROFILES = ("default", "strict", "docs", "security", "release", "all")


class CalibrationError(RuntimeError):
    """A user-facing calibration error."""


@dataclass(frozen=True)
class Case:
    name: str
    diff: Path
    expected: str
    profile: str
    model: str | None = None
    fallbacks: tuple[str, ...] = ()


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _case_from_dict(item: dict[str, Any], base: Path) -> Case:
    name = item.get("name")
    diff = item.get("diff")
    expected = item.get("expected")
    profile = item.get("profile", "strict")
    if not isinstance(name, str) or not name:
        raise CalibrationError("case is missing a non-empty 'name'")
    if not isinstance(diff, str) or not diff:
        raise CalibrationError(f"{name}: missing 'diff'")
    if expected not in VERDICTS:
        raise CalibrationError(f"{name}: 'expected' must be one of {', '.join(VERDICTS)}")
    if profile not in PROFILES:
        raise CalibrationError(f"{name}: 'profile' must be one of {', '.join(PROFILES)}")
    model = item.get("model")
    if model is not None and not isinstance(model, str):
        raise CalibrationError(f"{name}: 'model' must be a string")
    fallbacks = item.get("fallbacks", [])
    if not isinstance(fallbacks, list) or not all(isinstance(value, str) for value in fallbacks):
        raise CalibrationError(f"{name}: 'fallbacks' must be a list of strings")
    path = Path(diff)
    if not path.is_absolute():
        path = (base / path).resolve()
    return Case(name=name, diff=path, expected=expected, profile=profile, model=model, fallbacks=tuple(fallbacks))


def _load_cases(path: Path) -> list[Case]:
    if not path.exists():
        raise CalibrationError(f"config not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CalibrationError(f"config is not valid JSON: {exc}") from exc
    items = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise CalibrationError("config must contain a non-empty 'cases' list")
    cases = [_case_from_dict(item, path.parent) for item in items if isinstance(item, dict)]
    if len(cases) != len(items):
        raise CalibrationError("every case must be a JSON object")
    names = [case.name for case in cases]
    if len(names) != len(set(names)):
        raise CalibrationError("case names must be unique")
    return cases


def _review(case: Case, env_file: Path | None) -> str:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "jev-review.md"
        json_output = Path(directory) / "jev-review.json"
        command = [
            sys.executable,
            str(REVIEW),
            "--diff-file",
            str(case.diff),
            "--profile",
            case.profile,
            "--lang",
            "en",
            "--output",
            str(output),
            "--json-output",
            str(json_output),
            "--quiet",
        ]
        if case.model:
            command += ["--model", case.model]
        for fallback in case.fallbacks:
            command += ["--fallback-model", fallback]
        if env_file is not None:
            command += ["--env-file", str(env_file)]
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout).strip()
            return f"error: {message[:160]}"
        try:
            payload = json.loads(json_output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return f"error: invalid JSON report ({exc})"
        verdict = payload.get("verdict")
        return verdict if isinstance(verdict, str) else "error: no verdict"


def _self_test() -> int:
    base = Path(".")
    good = _case_from_dict(
        {"name": "x", "diff": "x.diff", "expected": "approve", "profile": "strict"},
        base,
    )
    _check(good.name == "x" and good.expected == "approve", "case parse")
    for bad in (
        {"name": "x", "diff": "x.diff", "expected": "nope"},
        {"name": "x", "diff": "x.diff", "expected": "approve", "profile": "nope"},
        {"name": "x", "expected": "approve"},
    ):
        try:
            _case_from_dict(bad, base)
        except CalibrationError:
            continue
        raise AssertionError(f"invalid case accepted: {bad}")
    print("self-test OK")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="JSON corpus (default: calibration/jev-cases.json)")
    parser.add_argument("--env-file", type=Path, help="file containing OPENCODE_API_KEY=...")
    parser.add_argument("--case", action="append", dest="cases", help="run only this case (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="validate the corpus without calling Jev")
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    parser.add_argument("--self-test", action="store_true", help="run local parser checks")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _self_test()
    try:
        cases = _load_cases(args.config)
        if args.cases:
            selected = set(args.cases)
            unknown = selected - {case.name for case in cases}
            if unknown:
                raise CalibrationError(f"unknown case(s): {', '.join(sorted(unknown))}")
            cases = [case for case in cases if case.name in selected]
        missing = [case for case in cases if not case.diff.exists()]
        if args.dry_run or missing:
            for case in cases:
                state = "present" if case.diff.exists() else "MISSING"
                print(f"{case.name}\t{case.expected}\t{case.diff}\t{state}")
            if missing:
                raise CalibrationError(f"missing diff(s): {', '.join(case.name for case in missing)}")
            return 0
        results = []
        failures = 0
        for case in cases:
            actual = _review(case, args.env_file)
            ok = actual == case.expected
            failures += 0 if ok else 1
            results.append({"name": case.name, "expected": case.expected, "actual": actual, "ok": ok})
        if args.json:
            print(json.dumps({"cases": results, "failures": failures}, ensure_ascii=False, indent=2))
        else:
            print(f"{'CASE':<28} {'EXPECTED':<10} {'ACTUAL':<12} RESULT")
            for result in results:
                print(f"{result['name']:<28} {result['expected']:<10} {result['actual']:<12} {'PASS' if result['ok'] else 'FAIL'}")
            print(f"Summary: {len(results) - failures} pass, {failures} fail")
        return 1 if failures else 0
    except (CalibrationError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
