"""Inline media validation: data-URI images, logos and watermarks."""

import base64

import pytest

from isis_report_lib import generate_csv, media, render_html

PNG_1PX = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


def _data_uri(mime: str, raw: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


@pytest.mark.parametrize(
    ("mime", "raw"),
    [
        ("image/png", base64.b64decode(PNG_1PX.split(",", 1)[1])),
        ("image/jpeg", b"\xff\xd8\xff\xe0" + b"\x00" * 8),
        ("image/gif", b"GIF89a" + b"\x00" * 8),
        ("image/webp", b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 4),
    ],
)
def test_normalize_image_accepts_supported_types(mime: str, raw: bytes) -> None:
    uri = _data_uri(mime, raw)
    assert media.normalize_image_src(uri) == uri


@pytest.mark.parametrize(
    ("value", "match"),
    [
        ("https://example.com/logo.png", "must be a data"),
        ("data:image/svg+xml;base64,PHN2Zz4=", "expected data:image"),
        ("data:image/png;base64,!!!!", "expected data:image"),
        (_data_uri("image/png", b"GIF89a" + b"\x00" * 8), "do not match"),
        ("data:image/png;base64,", "expected data:image"),
    ],
)
def test_normalize_image_rejects_bad_sources(value: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        media.normalize_image_src(value)


def test_normalize_image_rejects_oversized_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media, "MAX_IMAGE_BYTES", 8)
    uri = _data_uri("image/png", b"\x89PNG\r\n\x1a\nx")
    with pytest.raises(ValueError, match="decoded bytes"):
        media.normalize_image_src(uri)


def test_normalize_image_rejects_bad_base64_padding() -> None:
    with pytest.raises(ValueError, match="malformed"):
        media.normalize_image_src("data:image/png;base64,AAAAA")


def test_magic_check_rejects_unknown_mime() -> None:
    assert media._magic_ok("image/bmp", b"\x00") is False


def test_normalize_watermark_defaults_and_overrides() -> None:
    assert media.normalize_watermark(None) is None
    assert media.normalize_watermark("DRAFT") == {
        "text": "DRAFT",
        "opacity": 0.08,
        "color": "#000000",
        "angle": -30.0,
        "size": 80,
    }
    assert media.normalize_watermark({"text": "CONFIDENTIAL", "opacity": 0.1, "color": "#f00", "angle": -45, "size": 120}) == {
        "text": "CONFIDENTIAL",
        "opacity": 0.1,
        "color": "#f00",
        "angle": -45.0,
        "size": 120,
    }


@pytest.mark.parametrize(
    ("value", "match"),
    [
        ({"opacity": 0.1}, "watermark.text"),
        ({"text": ""}, "watermark.text"),
        ({"text": "x", "opacity": 2}, "watermark.opacity"),
        ({"text": "x", "color": "red"}, "watermark.color"),
        ({"text": "x", "angle": 100}, "watermark.angle"),
        ({"text": "x", "size": 4}, "watermark.size"),
        ({"text": "x", "size": True}, "watermark.size"),
        ({"text": "x", "extra": 1}, "Unknown meta.watermark key"),
        ({"text": "x" * 201}, "max 200 characters"),
        (123, "string or object"),
    ],
)
def test_normalize_watermark_rejects_bad_values(value: object, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        media.normalize_watermark(value)


def test_render_html_with_logo_and_watermark() -> None:
    html = render_html(
        {
            "meta": {
                "title": "T",
                "company": "ACME",
                "logo": PNG_1PX,
                "watermark": {"text": "DRAFT", "opacity": 0.1, "color": "#ff0000", "angle": -45, "size": 120},
            },
            "data": [],
        }
    )
    assert 'class="brand-logo"' in html
    assert 'src="data:image/png;base64,' in html
    assert "ACME" in html
    assert 'class="watermark"' in html
    assert "DRAFT" in html
    assert "--wm-color: #ff0000" in html
    assert "--wm-angle: -45.0deg" in html


def test_render_html_rejects_bad_logo_and_watermark() -> None:
    with pytest.raises(ValueError, match="meta.logo"):
        render_html({"meta": {"title": "T", "logo": "https://example.com/logo.png"}, "data": []})
    with pytest.raises(ValueError, match="meta.watermark.color"):
        render_html({"meta": {"title": "T", "watermark": {"text": "X", "color": "red"}}, "data": []})


def test_image_section_renders_figure() -> None:
    html = render_html(
        {
            "meta": {"title": "T"},
            "sections": [
                {
                    "type": "image",
                    "title": "Logo",
                    "src": PNG_1PX,
                    "alt": "ACME logo",
                    "caption": "Figure 1",
                    "width": 120,
                    "align": "right",
                }
            ],
        }
    )
    assert "<figure" in html
    assert 'src="data:image/png;base64,' in html
    assert 'alt="ACME logo"' in html
    assert 'width="120"' in html
    assert "text-align: right" in html
    assert "Figure 1" in html


def test_image_section_tolerates_null_alt_and_caption() -> None:
    html = render_html({"meta": {"title": "T"}, "sections": [{"type": "image", "src": PNG_1PX, "alt": None, "caption": None}]})
    assert '<figure class="report-image"' in html
    assert 'alt=""' in html
    assert "<figcaption>" not in html


@pytest.mark.parametrize(
    ("section", "match"),
    [
        ({"type": "image", "src": "file:///etc/passwd"}, "image section src"),
        ({"type": "image"}, "image section src"),
        ({"type": "image", "src": PNG_1PX, "align": "up"}, "image section align"),
        ({"type": "image", "src": PNG_1PX, "width": True}, "image section width"),
        ({"type": "image", "src": PNG_1PX, "alt": 1}, "image section alt"),
        ({"type": "image", "src": PNG_1PX, "caption": 1}, "image section caption"),
    ],
)
def test_image_section_rejects_bad_values(section: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        render_html({"meta": {"title": "T"}, "sections": [section]})


def test_image_section_exports_as_note() -> None:
    text = generate_csv(
        {
            "meta": {"title": "T"},
            "sections": [{"type": "image", "title": "Logo", "src": PNG_1PX, "alt": "ACME logo"}],
        }
    )
    assert "# table: Logo" in text
    assert "ACME logo" in text
