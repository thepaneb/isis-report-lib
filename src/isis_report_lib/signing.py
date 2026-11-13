"""Tamper-evident report signing and verification (v1).

Model: the SHA-256 of the issued PDF bytes plus metadata is signed and stored
in a ``%ISIS-SIGNATURE {json}`` block appended after the PDF ``%%EOF`` marker
(readers ignore trailing data). Verification strips the block(s), re-hashes
the original bytes and checks the signature — any modification invalidates it.

Two modes:

- ``hmac-sha256`` (stdlib only): signer and verifier share a secret
  (self-validation, e.g. a company portal checking its own reports).
- ``ed25519`` (needs the ``sign`` extra): anyone holding the public key can
  verify (third-party validation), no shared secret.

This is a *seal*, not Adobe PAdES: it proves origin + integrity to anyone
running :func:`verify_pdf`, without CAs or timestamp authorities.
"""

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

MARKER = b"%ISIS-SIGNATURE "
SIGNATURE_VERSION = 1


@dataclass
class SignatureInfo:
    """Verification outcome (``valid`` plus machine-readable details)."""

    valid: bool
    reason: str
    alg: str | None = None
    sha256: str | None = None
    key_id: str | None = None
    issued_at: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def generate_hmac_key(nbytes: int = 32) -> bytes:
    """Generate a random shared secret for ``hmac-sha256`` signatures."""
    return secrets.token_bytes(nbytes)


def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    """Generate ``(private_pem, public_pem)`` for ``ed25519`` signatures."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as e:
        raise ImportError("Ed25519 signatures require the 'sign' extra: pip install isis-report-lib[sign]") from e

    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _split_blocks(signed: bytes) -> tuple[bytes, list[dict[str, Any]]]:
    """Split (original bytes, [envelopes]) at the first ``%%EOF`` line end."""
    match = re.search(rb"%%EOF[^\n]*\n?", signed)
    if not match:
        raise ValueError("Not a PDF (missing %%EOF marker): cannot sign or verify.")
    original = signed[: match.end()]
    envelopes = []
    for line in signed[match.end() :].split(b"\n"):
        line = line.strip()
        if not line.startswith(MARKER):
            continue
        try:
            envelope = json.loads(line[len(MARKER) :].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"Corrupt signature block: {e}") from e
        if isinstance(envelope, dict):
            envelopes.append(envelope)
    return original, envelopes


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sign_bytes(message: bytes, key: bytes, alg: str) -> str:
    if alg == "hmac-sha256":
        return hmac.new(key, message, hashlib.sha256).hexdigest()
    if alg == "ed25519":
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError as e:
            raise ImportError("Ed25519 signatures require the 'sign' extra: pip install isis-report-lib[sign]") from e
        private = serialization.load_pem_private_key(key, password=None)
        if not isinstance(private, Ed25519PrivateKey):
            raise ValueError("Ed25519 signatures need an Ed25519 private key (PEM).")
        return private.sign(message).hex()
    raise ValueError(f"Unknown signature algorithm: {alg!r} (expected hmac-sha256|ed25519)")


def _verify_bytes(message: bytes, signature_hex: str, key: bytes, alg: str) -> bool:
    if alg == "hmac-sha256":
        expected = hmac.new(key, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_hex)
    if alg == "ed25519":
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except ImportError as e:
            raise ImportError("Ed25519 signatures require the 'sign' extra: pip install isis-report-lib[sign]") from e
        public = serialization.load_pem_public_key(key)
        if not isinstance(public, Ed25519PublicKey):
            raise ValueError("Ed25519 verification needs an Ed25519 public key (PEM).")
        try:
            public.verify(bytes.fromhex(signature_hex), message)
        except (InvalidSignature, ValueError):
            return False
        return True
    raise ValueError(f"Unknown signature algorithm: {alg!r} (expected hmac-sha256|ed25519)")


def sign_pdf(
    pdf: bytes,
    key: bytes,
    *,
    alg: str = "hmac-sha256",
    key_id: str | None = None,
    issued_at: str | None = None,
) -> bytes:
    """Append a signature block to PDF bytes (original bytes are untouched).

    ``key`` is the HMAC secret or the Ed25519 private key in PEM form.
    Re-signing an already signed file is allowed (latest block wins).
    """
    if alg not in ("hmac-sha256", "ed25519"):
        raise ValueError(f"Unknown signature algorithm: {alg!r} (expected hmac-sha256|ed25519)")
    original, _envelopes = _split_blocks(pdf)  # validates the %%EOF marker
    envelope: dict[str, Any] = {
        "v": SIGNATURE_VERSION,
        "alg": alg,
        "sha256": hashlib.sha256(original).hexdigest(),
        "issued_at": issued_at or datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if key_id is not None:
        envelope["key_id"] = key_id
    envelope["sig"] = _sign_bytes(_canonical(envelope), key, alg)
    return pdf + b"\n" + MARKER + json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def verify_pdf(signed: bytes, key: bytes, *, alg: str = "hmac-sha256") -> SignatureInfo:
    """Verify the latest signature block of a (possibly) signed PDF.

    ``key`` is the HMAC secret or the Ed25519 public key in PEM form.
    Never raises for malformed input — check ``.valid`` and ``.reason``.
    """
    try:
        original, envelopes = _split_blocks(signed)
    except ValueError as e:
        return SignatureInfo(valid=False, reason=str(e))
    if not envelopes:
        return SignatureInfo(valid=False, reason="no signature block found")
    envelope = envelopes[-1]
    for name in ("v", "alg", "sha256", "sig"):
        if name not in envelope:
            return SignatureInfo(valid=False, reason=f"signature block is missing {name!r}", details={"envelope": envelope})
    if envelope["v"] != SIGNATURE_VERSION:
        return SignatureInfo(valid=False, reason=f"unsupported signature version: {envelope['v']!r}")
    if envelope["alg"] != alg:
        return SignatureInfo(
            valid=False, reason=f"algorithm mismatch: block is {envelope['alg']!r}, verifying with {alg!r}", alg=envelope["alg"]
        )
    if hashlib.sha256(original).hexdigest() != envelope["sha256"]:
        return SignatureInfo(
            valid=False, reason="content hash mismatch: file was modified after signing", alg=alg, sha256=envelope["sha256"]
        )
    body = {k: v for k, v in envelope.items() if k != "sig"}
    try:
        ok = _verify_bytes(_canonical(body), envelope["sig"], key, alg)
    except (ImportError, ValueError) as e:
        return SignatureInfo(valid=False, reason=str(e), alg=alg)
    if not ok:
        return SignatureInfo(valid=False, reason="signature mismatch: wrong key or tampered envelope", alg=alg)
    return SignatureInfo(
        valid=True,
        reason="ok",
        alg=alg,
        sha256=envelope["sha256"],
        key_id=envelope.get("key_id"),
        issued_at=envelope.get("issued_at"),
    )
