# Contributing to isis-report-lib

Thanks for taking the time to help. This is a small, single-maintainer
library, so the fastest path is a focused issue or a small pull request.

## Ways to contribute

- **Bug reports and feature requests** — open an issue at
  <https://github.com/thepaneb/isis-report-lib/issues>. Include the library
  version (`pip show isis-report-lib`), the output format (`pdf`/`xlsx`/`csv`/
  `html`), a minimal reproducer payload (redact real data), and what you
  expected versus what happened.
- **Code and documentation** — fork the repository, create a branch, and open
  a pull request against `main`.
- **Security issues** — **do not open a public issue**. Follow
  [`SECURITY.md`](SECURITY.md) and use GitHub's private
  [Report a vulnerability](https://github.com/thepaneb/isis-report-lib/security/advisories/new)
  flow.

## Development setup

```bash
git clone https://github.com/thepaneb/isis-report-lib.git
cd isis-report-lib
pip install -e ".[dev]"
playwright install chromium   # only needed for the real-PDF tests
```

## Before opening a pull request

Run the same checks as CI:

```bash
python -m pytest tests -q -m "not browser"   # fast suite, no browser needed
python -m pytest tests -q                    # full suite (needs Chromium)
python -m pytest tests -q --cov=isis_report_lib  # coverage gate: 85%
python -m ruff check src tests fuzz
python -m ruff format --check src tests fuzz
python -m mypy src
python -m zensical build --strict             # only when docs change
bash scripts/fuzz-smoke.sh 30                 # parsers changed (Linux/macOS, needs atheris)
```

- **Tests are required for behavior changes.** Add or update cases in the
  matching file under `tests/` — see `AGENTS.md` for the mapping between
  modules and test files.
- **Keep changes focused.** One concern per pull request, with a clear
  description of the problem and the fix.
- **Update `CHANGELOG.md`** under `[Unreleased]` for user-visible changes.
- **Use Conventional Commits** (`feat:`, `fix:`, `refactor:`, `test:`,
  `docs:`, `chore:`). `main` is protected: branch → pull request → green CI →
  squash merge. Direct pushes and force pushes are disabled.

## Coding standards

- Code and docstrings in English.
- [`docs/STANDARDS.md`](docs/STANDARDS.md) is binding for architecture,
  rendering, export, signing and trust boundaries; [`AGENTS.md`](AGENTS.md)
  records the layout and the pitfalls that must not be reintroduced.
- Public API changes need both the `async` function and the synchronous
  wrapper in `src/isis_report_lib/api.py` (Golden Rule 1 in `AGENTS.md`).
- Bundled templates live in `src/isis_report_lib/templates/` and load through
  `rendering.get_jinja_env()`; never use paths relative to the current
  working directory.

## Review and licensing

The maintainer reviews every pull request; CI (lint/unit on 3.11–3.15, e2e,
fuzzing, Semgrep, CodeQL, Gitleaks, pip-audit and docs) must be green before
merge. By submitting a contribution you agree that it is licensed under the
project's MIT license (see [`LICENSE`](LICENSE)).
