# Security policy

This is the stable entry point on the docs site. The canonical policy is
[`SECURITY.md`](https://github.com/thepaneb/isis-report-lib/blob/main/SECURITY.md).

## Reporting a vulnerability

**Do not open a public issue for a suspected vulnerability.** Use GitHub
Security Advisories → **Report a vulnerability**:

<https://github.com/thepaneb/isis-report-lib/security/advisories/new>

Reports are private by default and visible only to maintainers until fixed.

Machine-readable: <https://thepaneb.github.io/isis-report-lib/security.txt>
(RFC 9116 root fallback).

Include the affected version (`pip show isis-report-lib`), the output format
(`pdf` / `xlsx` / `csv` / `html`), how the payload was built, a minimal
reproducer (redact real data), and your impact assessment.

## Supported versions

Only the latest PyPI release is supported with security fixes. Pin
`isis-report-lib==x.y.z` and upgrade on release notes marked `Security`.

## What happens next

- Acknowledgement within **5 business days**.
- If confirmed, a fix is developed privately, covered by a regression test, and
  released as a patch/minor version noting `Security` in `CHANGELOG.md`;
  the reporter is credited unless anonymity is requested.
- Severity is triaged with CVSS, scoped to the threat model in
  [`docs/ASVS.md`](https://github.com/thepaneb/isis-report-lib/blob/main/docs/ASVS.md):
  data is untrusted, templates are code, keys are operator-managed.

## Scope notes

- The signing API is a tamper-evident **seal**, not Adobe PAdES.
- Report data is untrusted by design and is escaped, never executed; templates
  are code and must come from trusted sources.
- Error messages and logs name fields/paths and expected types, never payload
  values.

## AI-assisted use and report ingestion

The library does **not** use AI at runtime. Reports are data, not instructions.
If you feed a generated PDF/HTML/XLSX/CSV to an LLM or agent, treat it as
untrusted input: hidden or invisible text, template content and post-processing
can carry instructions. `render_text`/`arender_text` provide a visible-only,
sanitized text export; use it with clear delimiters and a system prompt that
treats the report as data; never let the document trigger tools or reveal
secrets.

AI-assisted contributions follow
[`AI_USAGE.md`](https://github.com/thepaneb/isis-report-lib/blob/main/AI_USAGE.md)
and
[`AGENTS.md`](https://github.com/thepaneb/isis-report-lib/blob/main/AGENTS.md).
