"""The generated API reference must cover every public export."""

from pathlib import Path

import isis_report_lib

DOCS = Path(__file__).resolve().parents[1] / "docs" / "api.md"


def test_api_reference_lists_every_public_export() -> None:
    text = DOCS.read_text(encoding="utf-8")
    missing = [name for name in isis_report_lib.__all__ if not name.startswith("__") and f"`{name}`" not in text]
    assert not missing, f"docs/api.md is missing: {', '.join(missing)}"
