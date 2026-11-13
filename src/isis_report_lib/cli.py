"""Command-line interface: ``isis-report generate`` and ``isis-report render``."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from isis_report_lib.api import generate_csv, generate_pdf, generate_xlsx, render_html
from isis_report_lib.inputs import from_csv
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
        choices=["auto", "json", "toon", "csv"],
        default="auto",
        help="Input format (default: guessed from the file extension).",
    )
    gen.add_argument(
        "--format",
        choices=["auto", "pdf", "xlsx", "csv", "html"],
        default="auto",
        help="Output format (default: guessed from -o, else pdf).",
    )
    gen.add_argument("--page-format", default="A4", help="PDF page format (default: A4).")
    gen.add_argument("--locale", default=None, help="Override meta locale (e.g. en-US, pt-BR).")
    gen.add_argument("--bom", action="store_true", help="Prepend a UTF-8 BOM to CSV output (for Excel).")
    gen.add_argument("--inline-css", action="store_true", help="Inline CSS into style attributes (email-friendly HTML).")
    gen.add_argument("--delimiter", default=",", help="CSV delimiter for input and output (default: ',').")
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
        choices=["auto", "json", "toon", "csv"],
        default="auto",
        help="Input format (default: guessed from the file extension).",
    )
    ren.add_argument("--template-dir", type=Path, default=None, help="Directory with custom .jinja templates.")
    ren.add_argument("--template-name", default="tabular.jinja", help="Template file to render (default: tabular.jinja).")
    ren.add_argument("--locale", default=None, help="Override meta locale (e.g. en-US, pt-BR).")
    ren.add_argument("--inline-css", action="store_true", help="Inline CSS into style attributes (email-friendly HTML).")
    ren.add_argument("--delimiter", default=",", help="CSV delimiter for input (default: ',').")
    ren.set_defaults(func=_cmd_render)

    sch = sub.add_parser("schema", help="Print the report payload JSON Schema.")
    sch.add_argument("-o", "--output", type=Path, default=None, help="Output file (default: stdout).")
    sch.set_defaults(func=_cmd_schema)

    return parser


def _detect_format(path: Path, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".toon":
        return "toon"
    if suffix == ".csv":
        return "csv"
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


def _apply_locale(payload: dict[str, Any], locale: str | None) -> dict[str, Any]:
    """Override ``meta.locale`` when ``--locale`` is given."""
    if locale is None:
        return payload
    meta = dict(payload.get("meta") or {})
    meta["locale"] = locale
    return {**payload, "meta": meta}


def _load_payload(path: Path, fmt: str, delimiter: str = ",") -> tuple[dict[str, Any], bool]:
    """Return (payload dict, True). Raises FileNotFoundError / ValueError with friendly messages."""
    if fmt == "csv":
        try:
            return from_csv(path, delimiter=delimiter), True
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file not found: {path}") from None
    text = _read_text_file(path, "Input")
    assert text is not None
    if fmt == "json":
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from None
        return (loaded if isinstance(loaded, dict) else {"data": loaded}), True
    return parse_toon(text), True


def _cmd_generate(args: argparse.Namespace) -> int:
    try:
        fmt = _detect_format(args.input, args.input_format)
        payload, _is_json = _load_payload(args.input, fmt, args.delimiter)
        payload = _apply_locale(payload, args.locale)
        output_format = _detect_output_format(args)
        pdf_options: dict[str, Any] = {"format": args.page_format}
        header = _read_text_file(args.header_template, "Header template")
        if header is not None:
            pdf_options["header_template"] = header
        footer = _read_text_file(args.footer_template, "Footer template")
        if footer is not None:
            pdf_options["footer_template"] = footer
        output = args.output or args.input.with_suffix(f".{output_format}")
        if output_format == "pdf":
            result = generate_pdf(payload, pdf_options, args.template_dir, args.template_name)
            output.write_bytes(result)
        elif output_format == "xlsx":
            output.write_bytes(generate_xlsx(payload))
        elif output_format == "csv":
            output.write_text(generate_csv(payload, delimiter=args.delimiter, bom=args.bom), encoding="utf-8")
        else:  # html
            output.write_text(render_html(payload, args.template_dir, args.template_name, args.inline_css), encoding="utf-8")
    except (FileNotFoundError, ValueError) as e:
        print(f"isis-report: error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 - report any generation failure as exit 1
        print(f"isis-report: failed to generate report: {e}", file=sys.stderr)
        return 1
    print(str(output))
    return 0


def _detect_output_format(args: argparse.Namespace) -> str:
    """Resolve the output format: explicit --format wins, else the -o extension."""
    if args.format != "auto":
        return args.format
    if args.output:
        suffix = args.output.suffix.lower().lstrip(".")
        if suffix in ("pdf", "xlsx", "csv", "html"):
            return suffix
        raise ValueError(f"Cannot guess output format from extension {args.output.suffix!r}; use --format.")
    return "pdf"


def _cmd_render(args: argparse.Namespace) -> int:
    try:
        fmt = _detect_format(args.input, args.input_format)
        payload, _is_json = _load_payload(args.input, fmt, args.delimiter)
        payload = _apply_locale(payload, args.locale)
        html = render_html(payload, args.template_dir, args.template_name, args.inline_css)
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


def _cmd_schema(args: argparse.Namespace) -> int:
    from isis_report_lib.inputs import payload_schema

    text = json.dumps(payload_schema(), indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(str(args.output))
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
