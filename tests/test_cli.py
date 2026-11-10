"""CLI tests (real rendering; PDF generation mocked except one browser e2e)."""

import json
from pathlib import Path

import pytest

from isis_report_lib.cli import main

PAYLOAD = {
    "meta": {"title": "Order", "mode": "exact"},
    "layout": {"product": {"label": "Product", "format_mask": "str", "alignment": "left"}},
    "data": [{"product": "Pen"}],
}

TOON = "meta:\n  title: Order\n  mode: exact\ndata[1]:\n  - product: Pen\n"


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_render_toon_to_stdout(tmp_path, capsys):
    src = _write(tmp_path, "in.toon", TOON)
    assert main(["render", str(src)]) == 0
    out, _ = capsys.readouterr()
    assert "Pen" in out and "<html" in out


def test_render_json_to_file(tmp_path):
    src = _write(tmp_path, "in.json", json.dumps(PAYLOAD))
    dst = tmp_path / "out.html"
    assert main(["render", str(src), "-o", str(dst)]) == 0
    assert "Pen" in dst.read_text(encoding="utf-8")


def test_render_explicit_format_overrides_extension(tmp_path, capsys):
    src = _write(tmp_path, "in.txt", TOON)
    assert main(["render", str(src), "--input-format", "toon"]) == 0
    out, _ = capsys.readouterr()
    assert "Pen" in out


def test_render_unknown_extension_fails(tmp_path, capsys):
    src = _write(tmp_path, "in.txt", TOON)
    assert main(["render", str(src)]) == 2
    _, err = capsys.readouterr()
    assert "Cannot guess" in err


def test_render_missing_file_fails(capsys):
    assert main(["render", "nope.toon"]) == 2
    _, err = capsys.readouterr()
    assert "not found" in err


def test_render_invalid_json_fails(tmp_path, capsys):
    src = _write(tmp_path, "in.json", "{broken")
    assert main(["render", str(src)]) == 2
    _, err = capsys.readouterr()
    assert "Invalid JSON" in err


def test_generate_toon_mocked(tmp_path, monkeypatch, capsys):
    from isis_report_lib import cli

    src = _write(tmp_path, "in.toon", TOON)
    dst = tmp_path / "out.pdf"
    seen = {}

    def fake_generate(payload, *args):
        seen["payload"] = payload
        return b"%PDF-mock"

    monkeypatch.setattr(cli, "generate_pdf", fake_generate)
    assert main(["generate", str(src), "-o", str(dst)]) == 0
    assert dst.read_bytes() == b"%PDF-mock"
    assert seen["payload"]["data"] == [{"product": "Pen"}]
    out, _ = capsys.readouterr()
    assert str(dst) in out


def test_generate_json_default_output_mocked(tmp_path, monkeypatch):
    from isis_report_lib import cli

    src = _write(tmp_path, "in.json", json.dumps(PAYLOAD))
    seen = {}

    def fake_generate(payload, opts, *args):
        seen["payload"] = payload
        seen["opts"] = opts
        return b"%PDF-mock"

    monkeypatch.setattr(cli, "generate_pdf", fake_generate)
    assert main(["generate", str(src), "--page-format", "Letter"]) == 0
    assert src.with_suffix(".pdf").read_bytes() == b"%PDF-mock"
    assert seen["payload"]["meta"]["title"] == "Order"
    assert seen["opts"] == {"format": "Letter"}


def test_generate_invalid_json_fails(tmp_path, capsys):
    src = _write(tmp_path, "in.json", "{broken")
    assert main(["generate", str(src)]) == 2
    _, err = capsys.readouterr()
    assert "Invalid JSON" in err


def test_render_propagates_failure_as_exit_1(tmp_path, monkeypatch, capsys):
    from isis_report_lib import cli

    src = _write(tmp_path, "in.toon", TOON)

    def boom(*args):
        raise RuntimeError("jinja exploded")

    monkeypatch.setattr(cli, "render_html", boom)
    assert main(["render", str(src)]) == 1
    _, err = capsys.readouterr()
    assert "jinja exploded" in err


def test_generate_propagates_failure_as_exit_1(tmp_path, monkeypatch, capsys):
    from isis_report_lib import cli

    src = _write(tmp_path, "in.toon", TOON)

    def boom(*args):
        raise RuntimeError("browser exploded")

    monkeypatch.setattr(cli, "generate_pdf", boom)
    assert main(["generate", str(src)]) == 1
    _, err = capsys.readouterr()
    assert "browser exploded" in err


def test_render_with_template_flags(tmp_path, capsys):
    tpl = tmp_path / "custom.jinja"
    tpl.write_text("<html><body>CUSTOM:{{ meta.title }}</body></html>", encoding="utf-8")
    src = _write(tmp_path, "in.toon", TOON)
    assert main(["render", str(src), "--template-dir", str(tmp_path), "--template-name", "custom.jinja"]) == 0
    out, _ = capsys.readouterr()
    assert "CUSTOM:Order" in out


def test_render_locale_override(tmp_path, capsys):
    # Without layout the value is still formatted via the inferred layout.
    src = _write(tmp_path, "in.toon", "meta:\n  title: T\n  mode: exact\ndata[1]:\n  - total: 4000\n")
    assert main(["render", str(src), "--locale", "en-US"]) == 0
    out, _ = capsys.readouterr()
    assert "4,000" in out
    # With layout the locale drives number grouping.
    float_payload = {
        "meta": {"title": "Order", "mode": "exact"},
        "layout": {"total": {"label": "Total", "format_mask": "float", "alignment": "right"}},
        "data": [{"total": 4000}],
    }
    src_json = _write(tmp_path, "in.json", json.dumps(float_payload))
    assert main(["render", str(src_json), "--locale", "en-US"]) == 0
    out, _ = capsys.readouterr()
    assert "4,000.00" in out


def test_generate_header_footer_flags_mocked(tmp_path, monkeypatch, capsys):
    from isis_report_lib import cli

    header = _write(tmp_path, "header.html", "<div>HEADER</div>")
    footer = _write(tmp_path, "footer.html", "<div>FOOTER</div>")
    src = _write(tmp_path, "in.toon", TOON)
    seen = {}

    def fake_generate(payload, opts, *args):
        seen["opts"] = opts
        return b"%PDF-mock"

    monkeypatch.setattr(cli, "generate_pdf", fake_generate)
    assert main(["generate", str(src), "--header-template", str(header), "--footer-template", str(footer)]) == 0
    assert seen["opts"]["header_template"] == "<div>HEADER</div>"
    assert seen["opts"]["footer_template"] == "<div>FOOTER</div>"
    assert seen["opts"]["format"] == "A4"
    capsys.readouterr()


def test_generate_missing_header_file_fails(tmp_path, capsys):
    src = _write(tmp_path, "in.toon", TOON)
    assert main(["generate", str(src), "--header-template", str(tmp_path / "nope.html")]) == 2
    _, err = capsys.readouterr()
    assert "Header template file not found" in err


def test_read_text_file_oserror_becomes_value_error(tmp_path, monkeypatch, capsys):
    src = _write(tmp_path, "in.toon", TOON)
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(OSError("disk gone")))
    assert main(["render", str(src)]) == 2
    _, err = capsys.readouterr()
    assert "Cannot read" in err


@pytest.mark.browser
def test_generate_e2e_real_pdf(tmp_path):
    from isis_report_lib.pdf import close_browser

    src = _write(tmp_path, "in.toon", TOON)
    dst = tmp_path / "out.pdf"
    try:
        assert main(["generate", str(src), "-o", str(dst)]) == 0
        assert dst.read_bytes().startswith(b"%PDF")
    finally:
        import asyncio

        asyncio.run(close_browser())
