"""Command-line interface: ``isis-report generate`` and ``isis-report render``."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from isis_report_lib.api import generate_pdf, render_html
from isis_report_lib.toon import parse_toon


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="isis-report",
        description="Generate tabular PDF reports from JSON or .toon files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a PDF report.")
    gen.add_argument("input", type=Path, help="Input file (.json or .toon).")
    gen.add_argument("-o", "--output", type=Path, default=None, help="Output PDF path (default: <input>.pdf).")
    gen.add_argument(
        "--input-format",
        choices=["auto", "json", "toon"],
        default="auto",
        help="Input format (default: guessed from the file extension).",
    )
    gen.add_argument("--page-format", default="A4", help="PDF page format (default: A4).")
    gen.add_argument("--locale", default=None, help="Override meta locale (e.g. en-US, pt-BR).")
    gen.add_argument("--template-dir", type=Path, default=None, help="Directory with custom .jinja templates.")
    gen.add_argument("--template-name", default="tabular.jinja", help="Template file to render (default: tabular.jinja).")
    gen.add_argument("--header-template", type=Path, default=None, help="HTML file for the PDF header.")
    gen.add_argument("--footer-template", type=Path, default=None, help="HTML file for the PDF footer.")
    gen.set_defaults(func=_cmd_generate)

    ren = sub.add_parser("render", help="Render the intermediate HTML (no browser needed).")
    ren.add_argument("input", type=Path, help="Input file (.json or .toon).")
    ren.add_argument("-o", "--output", type=Path, default=None, help="Output HTML path (default: stdout).")
    ren.add_argument(
        "--input-format",
        choices=["auto", "json", "toon"],
        default="auto",
        help="Input format (default: guessed from the file extension).",
    )
    ren.add_argument("--template-dir", type=Path, default=None, help="Directory with custom .jinja templates.")
    ren.add_argument("--template-name", default="tabular.jinja", help="Template file to render (default: tabular.jinja).")
    ren.add_argument("--locale", default=None, help="Override meta locale (e.g. en-US, pt-BR).")
    ren.set_defaults(func=_cmd_render)

    return parser


def _detect_format(path: Path, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    if path.suffix.lower() == ".json":
        return "json"
    if path.suffix.lower() == ".toon":
        return "toon"
    raise ValueError(f"Cannot guess input format from extension {path.suffix!r}; use --input-format.")


def _read_text_file(path: Path | None, label: str) -> str | None:
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"{label} file not found: {path}") from None
    except OSError as e:
        raise ValueError(f"Cannot read {label} file {path}: {e}") from None


def _apply_locale(payload: dict | str, locale: str | None) -> dict | str:
    """Override ``meta.locale`` when ``--locale`` is given (dict payloads only)."""
    if locale is None or not isinstance(payload, dict):
        return payload
    meta = dict(payload.get("meta") or {})
    meta["locale"] = locale
    return {**payload, "meta": meta}


def _load_payload(path: Path, fmt: str) -> tuple[dict | str, bool]:
    """Return (payload, is_json). Raises FileNotFoundError / ValueError with friendly messages."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {path}") from None
    if fmt == "json":
        try:
            return json.loads(text), True
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from None
    return text, False


def _cmd_generate(args: argparse.Namespace) -> int:
    try:
        fmt = _detect_format(args.input, args.input_format)
        payload, is_json = _load_payload(args.input, fmt)
        if not is_json:
            payload = parse_toon(payload)
        payload = _apply_locale(payload, args.locale)
        pdf_options: dict[str, Any] = {"format": args.page_format}
        header = _read_text_file(args.header_template, "Header template")
        if header is not None:
            pdf_options["header_template"] = header
        footer = _read_text_file(args.footer_template, "Footer template")
        if footer is not None:
            pdf_options["footer_template"] = footer
        pdf = generate_pdf(payload, pdf_options, args.template_dir, args.template_name)
    except (FileNotFoundError, ValueError) as e:
        print(f"isis-report: error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - report any generation failure as exit 1
        print(f"isis-report: failed to generate PDF: {e}", file=sys.stderr)
        return 1
    output = args.output or args.input.with_suffix(".pdf")
    output.write_bytes(pdf)
    print(str(output))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    try:
        fmt = _detect_format(args.input, args.input_format)
        payload, is_json = _load_payload(args.input, fmt)
        if not is_json:
            payload = parse_toon(payload)
        payload = _apply_locale(payload, args.locale)
        html = render_html(payload, args.template_dir, args.template_name)
    except (FileNotFoundError, ValueError) as e:
        print(f"isis-report: error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - report any rendering failure as exit 1
        print(f"isis-report: failed to render HTML: {e}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(html, encoding="utf-8")
        print(str(args.output))
    else:
        print(html)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
