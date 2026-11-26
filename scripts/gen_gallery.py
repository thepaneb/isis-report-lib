#!/usr/bin/env python3
"""Generate the committed gallery artifacts under `docs/assets/gallery/`.

The payloads come from `examples/board_pack.py` (composed sections + a
hierarchical statement), so the gallery always shows the same examples users
can run. PDF/HTML/XLSX/CSV come from the public API; the PNG covers are
screenshots of the intermediate HTML in print media.

    python scripts/gen_gallery.py
"""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

from isis_report_lib import generate_csv, generate_pdf, generate_xlsx, render_html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "gallery"


def _example_payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    module = runpy.run_path(str(ROOT / "examples" / "board_pack.py"), run_name="gallery_example")
    return module["BOARD_PACK"], module["STATEMENT"]


def _screenshot(html: str, path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1754})
        page.emulate_media(media="print")
        page.set_content(html, wait_until="load")
        page.screenshot(path=str(path), full_page=True)
        browser.close()
    print(f"{path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


def _write(name: str, data: bytes | str) -> None:
    path = OUT / name
    if isinstance(data, str):
        if name.endswith(".html"):
            # Jinja control lines leave indentation-only lines; keep the
            # committed artifact clean for `git diff --check`.
            data = "\n".join(line.rstrip() for line in data.splitlines()) + "\n"
        path.write_text(data, encoding="utf-8", newline="\n")
    else:
        path.write_bytes(data)
    print(f"{path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    board_pack, statement = _example_payloads()

    board_html = render_html(board_pack)
    _write("board-pack.pdf", generate_pdf(board_pack))
    _write("board-pack.html", board_html)
    _write("board-pack.xlsx", generate_xlsx(board_pack))
    _write("board-pack.csv", generate_csv(board_pack, bom=True))
    _screenshot(board_html, OUT / "board-pack.png")

    statement_html = render_html(statement)
    _write("statement.pdf", generate_pdf(statement))
    _screenshot(statement_html, OUT / "statement.png")


if __name__ == "__main__":
    main()
