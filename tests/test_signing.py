"""Signing tests: HMAC + Ed25519 round-trips, tampering, CLI (no browser needed)."""

import pytest

PDF = b"%PDF-1.4\n%\xe2\xe3\n1 0 obj<</>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def test_hmac_roundtrip_with_metadata():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    secret = generate_hmac_key()
    assert len(secret) == 32
    signed = sign_pdf(PDF, secret, key_id="portal-1")
    assert signed.startswith(PDF)
    assert b"%ISIS-SIGNATURE " in signed
    info = verify_pdf(signed, secret)
    assert info.valid is True and info.reason == "ok"
    assert info.alg == "hmac-sha256" and info.key_id == "portal-1"
    assert info.issued_at and info.sha256


def test_hmac_tampered_content_fails():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    secret = generate_hmac_key()
    signed = sign_pdf(PDF, secret)
    tampered = signed.replace(b"Root 1 0 R", b"Root 2 0 R")
    info = verify_pdf(tampered, secret)
    assert info.valid is False
    assert "modified" in info.reason


def test_hmac_wrong_key_fails():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    signed = sign_pdf(PDF, generate_hmac_key())
    assert verify_pdf(signed, generate_hmac_key()).valid is False


def test_verify_unsigned_and_garbage():
    from isis_report_lib.signing import generate_hmac_key, verify_pdf

    assert verify_pdf(PDF, generate_hmac_key()).reason == "no signature block found"
    assert verify_pdf(b"not a pdf", generate_hmac_key()).valid is False
    assert verify_pdf(PDF + b"\n%ISIS-SIGNATURE {broken", generate_hmac_key()).valid is False
    broken = PDF + b'\n%ISIS-SIGNATURE {"v": 1}\n'
    assert "missing" in verify_pdf(broken, generate_hmac_key()).reason


def test_verify_algorithm_mismatch_and_unknown_alg():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    secret = generate_hmac_key()
    signed = sign_pdf(PDF, secret)
    assert "mismatch" in verify_pdf(signed, secret, alg="ed25519").reason
    with pytest.raises(ValueError, match="Unknown signature algorithm"):
        sign_pdf(PDF, secret, alg="rot13")
    assert verify_pdf(signed, secret, alg="rot13").valid is False  # never raises: reports mismatch


def test_sign_bytes_unknown_algorithm():
    from isis_report_lib import signing

    with pytest.raises(ValueError, match="Unknown signature algorithm"):
        signing._sign_bytes(b"msg", b"key", "rot13")


def test_sign_rejects_non_pdf():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf

    with pytest.raises(ValueError, match="missing %%EOF"):
        sign_pdf(b"hello", generate_hmac_key())


def test_resign_keeps_latest_envelope():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    secret = generate_hmac_key()
    twice = sign_pdf(sign_pdf(PDF, secret, key_id="first"), secret, key_id="second")
    info = verify_pdf(twice, secret)
    assert info.valid is True and info.key_id == "second"


def test_ed25519_roundtrip_and_wrong_key():
    ed = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")

    from isis_report_lib.signing import generate_ed25519_keypair, sign_pdf, verify_pdf

    assert ed  # the import itself is the skip gate
    private_pem, public_pem = generate_ed25519_keypair()
    assert private_pem.startswith(b"-----BEGIN PRIVATE KEY-----")
    signed = sign_pdf(PDF, private_pem, alg="ed25519")
    info = verify_pdf(signed, public_pem, alg="ed25519")
    assert info.valid is True and info.alg == "ed25519"
    other_pub = generate_ed25519_keypair()[1]
    assert verify_pdf(signed, other_pub, alg="ed25519").valid is False


def test_ed25519_rejects_wrong_key_kinds():
    pytest.importorskip("cryptography")

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

    from isis_report_lib.signing import generate_ed25519_keypair, sign_pdf, verify_pdf

    rsa_priv = generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    with pytest.raises(ValueError, match="Ed25519 private key"):
        sign_pdf(PDF, rsa_priv, alg="ed25519")
    rsa_pub = (
        generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    private_pem, _public_pem = generate_ed25519_keypair()
    signed = sign_pdf(PDF, private_pem, alg="ed25519")
    assert verify_pdf(signed, rsa_pub, alg="ed25519").valid is False  # wrong key kind -> invalid, never raises


def test_ed25519_missing_extra(monkeypatch):
    import sys

    from isis_report_lib import signing

    monkeypatch.setitem(sys.modules, "cryptography", None)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives", None)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives.serialization", None)
    monkeypatch.setitem(sys.modules, "cryptography.exceptions", None)
    with pytest.raises(ImportError, match="pip install isis-report-lib\\[sign\\]"):
        signing.generate_ed25519_keypair()


def test_cli_keygen_sign_verify(tmp_path, capsys):
    from isis_report_lib.cli import main

    secret = tmp_path / "secret.key"
    assert main(["keygen", "-o", str(secret)]) == 0
    assert len(secret.read_bytes()) == 32
    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    assert main(["sign", str(src), "--key-file", str(secret), "--key-id", "k1"]) == 0
    signed = tmp_path / "in.signed.pdf"
    assert signed.exists()
    assert main(["verify", str(signed), "--key-file", str(secret)]) == 0
    out, _ = capsys.readouterr()
    assert "VALID" in out
    assert main(["verify", str(signed), "--key-file", str(secret), "--json"]) == 0
    out, _ = capsys.readouterr()
    assert '"valid": true' in out and '"key_id": "k1"' in out


def test_cli_verify_detects_tampering(tmp_path, capsys):
    from isis_report_lib.cli import main

    secret = tmp_path / "secret.key"
    assert main(["keygen", "-o", str(secret)]) == 0
    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    assert main(["sign", str(src), "--key-file", str(secret)]) == 0
    signed = tmp_path / "in.signed.pdf"
    raw = bytearray(signed.read_bytes())
    raw[10] ^= 0xFF
    signed.write_bytes(bytes(raw))
    assert main(["verify", str(signed), "--key-file", str(secret)]) == 1
    out, _err = capsys.readouterr()
    assert "INVALID" in out


def test_cli_sign_missing_key_file(tmp_path, capsys):
    from isis_report_lib.cli import main

    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    assert main(["sign", str(src), "--key-file", str(tmp_path / "nope.key")]) == 2
    _, err = capsys.readouterr()
    assert "Key file not found" in err


def test_cli_sign_missing_input_file(tmp_path, capsys):
    from isis_report_lib.cli import main

    secret = tmp_path / "secret.key"
    assert main(["keygen", "-o", str(secret)]) == 0
    assert main(["sign", str(tmp_path / "nope.pdf"), "--key-file", str(secret)]) == 2
    _, err = capsys.readouterr()
    assert "Input file not found" in err


def test_cli_verify_missing_input_file(tmp_path, capsys):
    from isis_report_lib.cli import main

    secret = tmp_path / "secret.key"
    assert main(["keygen", "-o", str(secret)]) == 0
    assert main(["verify", str(tmp_path / "nope.pdf"), "--key-file", str(secret)]) == 2
    _, err = capsys.readouterr()
    assert "Input file not found" in err


def test_cli_key_read_oserror(tmp_path, monkeypatch, capsys):
    from pathlib import Path

    from isis_report_lib.cli import main

    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    secret = tmp_path / "secret.key"
    assert main(["keygen", "-o", str(secret)]) == 0
    real_read_bytes = Path.read_bytes

    def boom(self):
        if str(self) == str(secret):
            raise PermissionError("denied")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", boom)
    assert main(["sign", str(src), "--key-file", str(secret)]) == 2
    _, err = capsys.readouterr()
    assert "Cannot read key file" in err


def test_cli_keygen_ed25519_with_public_out(tmp_path, capsys):
    pytest.importorskip("cryptography")

    from isis_report_lib.cli import main
    from isis_report_lib.signing import verify_pdf

    priv = tmp_path / "private.pem"
    pub = tmp_path / "public.pem"
    assert main(["keygen", "--kind", "ed25519", "-o", str(priv), "--public-out", str(pub)]) == 0
    assert priv.read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")
    assert pub.read_bytes().startswith(b"-----BEGIN PUBLIC KEY-----")
    src = tmp_path / "in.pdf"
    src.write_bytes(PDF)
    assert main(["sign", str(src), "--key-file", str(priv), "--alg", "ed25519"]) == 0
    signed = tmp_path / "in.signed.pdf"
    assert main(["verify", str(signed), "--key-file", str(pub), "--alg", "ed25519"]) == 0
    assert verify_pdf(signed.read_bytes(), pub.read_bytes(), alg="ed25519").valid is True
    capsys.readouterr()


def test_cli_keygen_public_out_only_for_ed25519(tmp_path, capsys):
    from isis_report_lib.cli import main

    secret = tmp_path / "secret.key"
    assert main(["keygen", "-o", str(secret), "--public-out", str(tmp_path / "pub.pem")]) == 2
    _, err = capsys.readouterr()
    assert "--public-out only applies to ed25519" in err


def test_cli_keygen_ed25519_missing_extra(tmp_path, monkeypatch, capsys):
    import sys

    from isis_report_lib.cli import main

    monkeypatch.setitem(sys.modules, "cryptography", None)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives", None)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives.asymmetric.ed25519", None)
    assert main(["keygen", "--kind", "ed25519", "-o", str(tmp_path / "priv.pem")]) == 2
    _, err = capsys.readouterr()
    assert "sign" in err and "extra" in err


def test_sign_ed25519_missing_extra(monkeypatch):
    import sys

    from isis_report_lib import signing

    monkeypatch.setitem(sys.modules, "cryptography", None)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives", None)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives.asymmetric.ed25519", None)
    with pytest.raises(ImportError, match="pip install isis-report-lib\\[sign\\]"):
        signing.sign_pdf(PDF, b"x", alg="ed25519")


def test_verify_ed25519_missing_extra_is_invalid(monkeypatch):
    import sys

    pytest.importorskip("cryptography")

    from isis_report_lib import signing

    private_pem, public_pem = signing.generate_ed25519_keypair()
    signed = signing.sign_pdf(PDF, private_pem, alg="ed25519")
    monkeypatch.setitem(sys.modules, "cryptography", None)
    monkeypatch.setitem(sys.modules, "cryptography.exceptions", None)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives", None)
    info = signing.verify_pdf(signed, public_pem, alg="ed25519")
    assert info.valid is False
    assert "sign" in info.reason and "extra" in info.reason


def test_verify_unknown_algorithm_envelope():
    import hashlib
    import json

    from isis_report_lib.signing import verify_pdf

    digest = hashlib.sha256(PDF).hexdigest()
    body = {"v": 1, "alg": "rot13", "sha256": digest}
    block = b"\n%ISIS-SIGNATURE " + json.dumps({**body, "sig": "00"}).encode() + b"\n"
    info = verify_pdf(PDF + block, b"secret", alg="rot13")
    assert info.valid is False
    assert "Unknown signature algorithm" in info.reason


def test_verify_unsupported_version():
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    signed = sign_pdf(PDF, generate_hmac_key())
    tampered = signed.replace(b'"v":1', b'"v":99')
    assert b'"v":99' in tampered
    assert "unsupported signature version" in verify_pdf(tampered, generate_hmac_key()).reason


def test_sign_then_generate_end_to_end():
    """A real generated PDF signs and verifies (needs the wheel-built package? no, local)."""
    from isis_report_lib import generate_pdf
    from isis_report_lib.signing import generate_hmac_key, sign_pdf, verify_pdf

    pdf = generate_pdf({"meta": {"title": "T"}, "data": [{"a": 1}]})
    secret = generate_hmac_key()
    assert verify_pdf(sign_pdf(pdf, secret), secret).valid is True
