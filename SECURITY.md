# Security Policy

## Supported versions

Only the latest PyPI release is supported with security fixes. Pin
`isis-report-lib==x.y.z` and upgrade on release notes marked `Security`.

## Reporting a vulnerability

**Do not open a public issue for a suspected vulnerability.**
Use **GitHub Security Advisories → Report a vulnerability** on
[`thepaneb/isis-report-lib`](https://github.com/thepaneb/isis-report-lib/security/advisories/new)
(private by default: the report is visible only to maintainers until fixed).

Please include:

- affected version(s) (`pip show isis-report-lib`) and install extras used
- output format involved (`pdf` / `xlsx` / `csv` / `html`) and how the
  payload was built (dict / `.toon` / `from_csv` / `from_json` / dataframe)
- a minimal reproducer payload (redact real data) and the observed vs.
  expected behavior
- your assessment of impact (who must be attacker-controlled: data, layout,
  template, key material?)

## What happens next

- Acknowledgement within 5 business days.
- If confirmed, a fix is developed on a private branch, covered by a
  regression test, and released as a patch/minor version noting `Security`
  in `CHANGELOG.md` — crediting the reporter unless anonymity is requested.
- Severity is triaged with CVSS as a guide, scoped to the library's threat
  model (`docs/ASVS.md`): data is untrusted, templates are code, keys are
  operator-managed.

## Scope notes

- The signing API is a tamper-evident *seal*, not Adobe PAdES: it proves
  origin/integrity to `verify_pdf` holders without CAs or timestamps.
- Report *data* is untrusted by design and is escaped, never executed;
  report *templates* are code — only load them from sources you trust
  (see `docs/STANDARDS.md` §3).
