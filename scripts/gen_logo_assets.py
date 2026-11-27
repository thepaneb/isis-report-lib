#!/usr/bin/env python3
"""Generate the documentation logo assets from the inline SVG in base.jinja.

The report template keeps the mark inline so standalone HTML/PDF files do not
need an external image. Documentation, the README tile and the favicon are
generated from that same source:

    python scripts/gen_logo_assets.py
    python scripts/gen_logo_assets.py --check   # CI drift check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "src" / "isis_report_lib" / "templates" / "base.jinja"
ASSETS = ROOT / "docs" / "assets"


def render() -> dict[Path, str]:
    text = BASE.read_text(encoding="utf-8")
    match = re.search(r'<svg width="86" height="86" viewBox="0 0 86 86".*?</svg>', text, re.DOTALL)
    if match is None:
        raise SystemExit(f"logo SVG not found in {BASE}")
    svg = match.group(0)
    inner_match = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.DOTALL)
    if inner_match is None:
        raise SystemExit(f"could not read the logo SVG in {BASE}")
    inner = inner_match.group(1).strip()

    logo = (
        '<svg width="86" height="86" viewBox="0 0 86 86" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="isis-logo-title">\n'
        '  <title id="isis-logo-title">isis-report-lib</title>\n'
        f"{inner}\n"
        "</svg>\n"
    )
    white_mark = inner.replace('fill="#0A2F46"', 'fill="#FFFFFF"')
    tile = (
        '<svg width="86" height="86" viewBox="0 0 86 86" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="isis-logo-tile-title">\n'
        '  <title id="isis-logo-tile-title">isis-report-lib</title>\n'
        '  <rect width="86" height="86" rx="18" fill="#FFFFFF"/>\n'
        f"{inner}\n"
        "</svg>\n"
    )
    favicon = (
        '<svg width="86" height="86" viewBox="0 0 86 86" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="isis-favicon-title">\n'
        '  <title id="isis-favicon-title">isis-report-lib</title>\n'
        '  <rect width="86" height="86" rx="18" fill="#0A2F46"/>\n'
        f"{white_mark}\n"
        "</svg>\n"
    )
    return {
        ASSETS / "logo.svg": logo,
        ASSETS / "logo-tile.svg": tile,
        ASSETS / "favicon.svg": favicon,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail when docs assets are stale")
    args = parser.parse_args(argv)
    assets = render()
    if args.check:
        stale = [
            path.relative_to(ROOT) for path, content in assets.items() if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print("logo assets are stale: " + ", ".join(str(path) for path in stale), file=sys.stderr)
            print("run python scripts/gen_logo_assets.py", file=sys.stderr)
            return 1
        print("logo assets are up to date")
        return 0
    for path, content in assets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
