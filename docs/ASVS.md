# OWASP ASVS 4.0.3 — Applicability Mapping

Scope: `isis_report_lib` as a **library** (no network listeners, no auth,
no sessions, no user management). Evaluation context: embedded use —
integrators pass dict/JSON/`.toon` payloads and ship PDF/XLSX/CSV/HTML
artifacts. Findings marked **L1** are the Level 1 bar; **L2/L3** notes show
where the project already meets higher levels. This is a self-assessment
against the public standard, not a certification.

Conventions: **Pass** (control implemented + tested), **Partial** (meets the
intent with documented limits), **N/A** (no such surface in this project).

## V1 — Architecture, Design and Threat Modeling

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 1.1.4 | L1L2 | Pass | Trust boundaries, components and data flows: `STANDARDS.md` §1–§3, `README.md` Security, this file |
| 1.1.5 | L1L2 | Pass | Architecture and connected services: `STANDARDS.md` §1 (pipeline, module map, Chromium pool) |
| 1.1.7 | L1L2 | Pass | `STANDARDS.md` + `AGENTS.md` are the secure-coding checklist; enforced by CI gates |
| 1.5.4 | L1L2 | Pass | Output encoding at the interpreter: Jinja `autoescape=True` at render time (`rendering.py`) |
| 1.7.1 | L1L2 | Partial | stdlib logging is used consistently, but there is no central log format/syslog — the host application owns log routing |
| 1.10.1 | L1L2 | Pass | git + protected `main` + mandatory PR review + `gate` check |
| 1.11.1 | L1L2 | Pass | Components documented by security function (`STANDARDS.md` §1.2) |
| 1.14.3 | L2L3 | Pass | `pip-audit` gate and Dependabot warn/upgrade on outdated components |
| V1.2/V1.3/V1.4 (auth/session/access) | — | N/A | no identities, sessions or access decisions exist in the library |
| V1.6 (key lifecycle) | — | Partial | keys are bytes-in/never-logged with `key_id` rotation support; vault storage is the deployer's duty (documented in `STANDARDS.md` §3.3) |
| V1.8/V1.9 (data classification, encrypted comms) | — | N/A with note | the library neither classifies caller data nor opens connections; TLS/secret storage are deployer duties |

## V5 — Validation, Sanitization and Encoding

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 5.1.3 | L1L2 | Pass | Positive validation of layout/operators/masks (allow-listed values, fail-closed `ValueError`); free-text *data* is output-encoded instead of restricted |
| 5.1.4 | L1L2 | Partial | `pydantic` models + per-field schema checks; raw dict payloads are validated incrementally at build, not against the full JSON Schema (`payload_schema()` available) |
| 5.2.4 | L1L2 | Pass | No `eval`/`exec`/`pickle`/dynamic import (grep-verified; `ruff` S-gates it) |
| 5.2.5 | L1L2 | Pass | Autoescaped `SandboxedEnvironment`; sandbox violations raise fail-closed `ValueError` (`tests/test_security.py`) |
| 5.2.6 | L1L2 | Pass | `_inline_css` strips `<link>` stylesheets — rendering performs no server-side fetch (verified: remote `evil.css` hit the local listener before the fix, zero after) |
| 5.2.7 | L1L2 | Pass | SVG is generated, never user-supplied: numeric/geometry interpolation only, colors allow-listed/escaped, JS disabled at render |
| 5.3.1/5.3.2 | L1L2 | Pass | Context-correct HTML escaping; locales/Unicode preserved via Babel (`tests/test_formatting.py`) |
| 5.3.3 | L1L2 | Pass | Stored-XSS regression tests (`<script>`/event handlers render inert) |
| 5.3.9 | L1L2 | Pass | `FileSystemLoader` blocks `..`/absolute templates (tested); no file inclusion surface |
| 5.5.3 | L1L2 | Pass | JSON parsed with `json` only (no `eval`); RecursionError → `ValueError`; custom `.toon` parser depth-guarded |
| 5.2.2 | L1L2 | Partial | No length quotas on payloads by design; nesting depth is bounded, unbounded *size* is the deployer's limit to set |
| V5.1.1/5.1.2/5.1.5, 5.2.1, 5.2.3, 5.2.8, 5.3.4–5.3.8, 5.3.10, 5.4.x, 5.5.2 | — | N/A | no HTTP params/redirects/WYSIWYG/mail/SQL/LDAP/OS-shell/XPath/XML parsing in scope |

## V6 — Stored Cryptography

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 6.2.1 | L1L2 | Pass | Verification fails closed to `invalid` (no padding-oracle class: nothing is decrypted) |
| 6.2.2 | L2L3 | Pass | Only stdlib HMAC-SHA256 and `cryptography` Ed25519; no custom crypto (`signing.py`) |
| 6.2.7 | L2 | Pass | Envelope (hash + metadata incl. `key_id`) is signed; tampering breaks verification |
| 6.2.8 | L2 | Pass | `hmac.compare_digest` for HMAC; Ed25519 verify is constant-time in `cryptography` |
| 6.3.1 | L1L2 | Pass | `secrets.token_bytes` for HMAC keys |
| 6.4.1/6.4.2 | L2L3 | Partial | Library never persists keys and never logs them; vault/HSM storage and rotation procedures are the deployer's duty |
| V6.1.x/6.2.3–6.2.6 | — | N/A | no at-rest PII encryption, cipher modes, or nonces in scope (seal only, no confidentiality claim) |

## V7 — Error Handling and Logging

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 7.1.1/7.1.2 | L1L2 | Pass | Secrets/keys/PII never logged; tracebacks carry code, not payload values |
| 7.3.1 | L1L2 | Partial | No user-controlled content reaches log sinks (static messages only); no dedicated log-encoding layer |
| 7.4.1 | L1L2 | Pass | `verify_*` returns generic `invalid` verdicts; CLI exits `0/1/2` without internals |
| 7.4.2 | L1L2 | Pass | Fail-closed `ValueError` + `ImportError` hints across inputs, layout, export, signing |
| V7.2/V7.3.3/V7.3.4 | — | N/A | no authentication/access decisions or centralized log pipeline in the library |

## V8/V9/V11 — Data Protection, Communications, Business Logic

Mostly **N/A**: no caches, sessions, browser storage, listeners, TLS endpoints,
or multi-step business flows in the library. Deliberate Partial: no input-size
quotas (12.1.1, deployer limit) and no outbound allow-list (12.6.1 — outbound
fetch only exists via operator-authored templates; data cannot trigger it).

## V10 — Malicious Code

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 10.1.1 | L3 | Partial | `ruff` S-rules + `pip-audit` + `mypy` + 99% tests run in CI; no dedicated SAST scanner yet (follow-up: semgrep) |
| 10.2.3 | L3 | Partial | Mandatory review on every PR to protected `main`; no hardcoded secrets/keys (verified); no automated secret scanning |
| 10.3.2 | L1L2L3 | Pass | No auto-update; no remote code execution (JS off, no link fetch, no dynamic imports); releases via OIDC trusted publishing |

## V12 — Files and Resources

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 12.1.1 | L1L2 | Partial | No quotas by design; recursion guards bound nesting; giant-payload limits are the deployer's call |
| 12.3.1/12.3.2/12.3.5 | L1L2 | Pass | Template names cannot escape the template dir (tested); user metadata never touches filesystem APIs |
| 12.3.3 | L1L2 | Pass | No remote file inclusion: `<link>` stripped, no URL-driven includes |
| 12.3.6 | L1L2 | Pass | No unverified CDN/remote libraries in output; JS disabled |
| 12.6.1 | L1L2L3 | Partial | No generic allow-list framework; effective posture is deny-by-default (no fetch in render paths) |

## V13 — API and Web Service

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 13.2.2 | L1L2 | Partial | `payload_schema()` + `pydantic` models published; raw dict payloads validated incrementally rather than against the full schema |
| Rest of V13 | — | N/A | no HTTP API, sessions, cookies, CORS, GraphQL, or XML in the library |

## V14 — Configuration

| Req | Lvl | Verdict | Evidence |
|---|---|---|---|
| 14.1.3 | L2L3 | Partial | JS off, autoescape, sandbox, minimal browser flags per framework guidance; host/server hardening is the deployer's duty |
| 14.2.1 | L1L2 | Pass | `pip-audit` runs on every CI build |
| 14.2.4 | L2L3 | Pass | PyPI only + Dependabot; Actions SHA-pinned |
| 14.2.5 | L2L3 | Partial | No checked-in SBOM artifact; dependency set fully declared in `pyproject.toml` (CycloneDX export is a follow-up) |
| 14.3.2 | L1L2 | Pass | No debug mode, verbose errors, or tracebacks in outputs exist |
| Rest of V14 | — | N/A | no HTTP headers/CORS/server surface in the library |

## Gaps accepted (deliberate, tracked)

1. No input-size quotas — recursion is bounded, volume is a deployer limit.
2. No SBOM artifact — full dependency declaration + Dependabot + pip-audit instead.
3. No dedicated SAST scanner — `ruff` S-rules + review + tests; semgrep is the planned next gate.
4. Secrets management (vault/HSM/rotation runbooks) lives with the deployer; the library only guarantees never-log/never-persist and `key_id`-tagged seals.
5. Outbound network from Chromium (remote fonts/images in operator templates) has no allow-list; data-driven fetch is eliminated.
