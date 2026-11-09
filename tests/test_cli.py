"""CLI tests (real rendering; PDF generation mocked except one browser e2e)."""

import json

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
    monkeypatch.setattr(cli, "generate_pdf_from_toon", lambda text, opts: b"%PDF-mock")
    assert main(["generate", str(src), "-o", str(dst)]) == 0
    assert dst.read_bytes() == b"%PDF-mock"
    out, _ = capsys.readouterr()
    assert str(dst) in out


def test_generate_json_default_output_mocked(tmp_path, monkeypatch):
    from isis_report_lib import cli

    src = _write(tmp_path, "in.json", json.dumps(PAYLOAD))
    seen = {}

    def fake_generate(payload, opts):
        seen["payload"] = payload
        seen["opts"] = opts
        return b"%PDF-mock"

    monkeypatch.setattr(cli, "generate_pdf", fake_generate)
    assert main(["generate", str(src), "--page-format", "Letter"]) == 0
    assert src.with_suffix(".pdf").read_bytes() == b"%PDF-mock"
    assert seen["payload"]["meta"]["title"] == "Order"
    assert seen["opts"] == {"format": "Letter"}


def test_generate_propagates_failure_as_exit_1(tmp_path, monkeypatch, capsys):
    from isis_report_lib import cli

    src = _write(tmp_path, "in.toon", TOON)

    def boom(text, opts):
        raise RuntimeError("browser exploded")

    monkeypatch.setattr(cli, "generate_pdf_from_toon", boom)
    assert main(["generate", str(src)]) == 1
    _, err = capsys.readouterr()
    assert "browser exploded" in err


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
