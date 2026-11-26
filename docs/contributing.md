# Contributing

isis-report-lib is a small, single-maintainer library. Bug reports, focused
pull requests and documentation fixes are all welcome.

## Get the software

```bash
pip install isis-report-lib
playwright install chromium   # required to generate PDFs
```

The full user guide, API reference and examples live in the
[user guide](guide.md) and the [project README](https://github.com/thepaneb/isis-report-lib#readme).

## Report a bug or ask for a feature

Open an issue at <https://github.com/thepaneb/isis-report-lib/issues>. Include:

- the library version (`pip show isis-report-lib`) and extras in use;
- the output format (`pdf` / `xlsx` / `csv` / `html`);
- a minimal reproducer payload (redact real data) and the observed versus
  expected behavior.

For **security vulnerabilities**, do not open a public issue: use the private
[GitHub Security Advisory](https://github.com/thepaneb/isis-report-lib/security/advisories/new)
flow described in [`SECURITY.md`](https://github.com/thepaneb/isis-report-lib/blob/main/SECURITY.md).

## Contribute code or documentation

Pull requests against `main` are the contribution mechanism:

1. Fork the repository and create a branch (`feat/...`, `fix/...`, `docs/...`).
2. Add or update tests for behavior changes.
3. Run the checks below.
4. Open a pull request; CI must be green and the maintainer reviews before
   the squash merge.

> **Fork PRs and code scanning:** docs/config-only fork PRs are handled
> automatically. Fork PRs that change code, tests, CI or dependencies are
> intentionally blocked by the code-scanning rule (fork-generated SARIF is not
> trusted); the maintainer integrates those from a same-repo branch. Open an
> issue first for anything beyond docs/config.

```bash
pip install -e ".[dev]"
python -m pytest tests -q -m "not browser"
python -m ruff check src tests demo fuzz
python -m ruff format --check src tests demo fuzz
python -m mypy src
```

See [`CONTRIBUTING.md`](https://github.com/thepaneb/isis-report-lib/blob/main/CONTRIBUTING.md)
for the full checklist (full test suite, coverage gate, fuzzing and docs
builds). Coding standards and the security/trust model are binding in
[`STANDARDS.md`](STANDARDS.md); the layout and pitfalls are in
[`AGENTS.md`](https://github.com/thepaneb/isis-report-lib/blob/main/AGENTS.md).

By submitting a contribution you agree that it is licensed under the
project's MIT license.
