# Contributing to isis-report-lib

Thanks for taking the time to help. This is a small, single-maintainer
library, so the fastest path is a focused issue or a small pull request.

## Ways to contribute

- **Questions and ideas** — use
  [Discussions](https://github.com/thepaneb/isis-report-lib/discussions) to ask
  how to model a report, share a payload, or discuss a proposal before opening
  an issue.
- **Bug reports and feature requests** — open an issue at
  <https://github.com/thepaneb/isis-report-lib/issues>. The forms ask for the
  library version (`pip show isis-report-lib`), the output format
  (`pdf`/`xlsx`/`csv`/`html`), a minimal reproducer payload (redact real data),
  and what you expected versus what happened.
- **Good first issues** — look for the
  [`good first issue`](https://github.com/thepaneb/isis-report-lib/labels/good%20first%20issue)
  label; each one lists the files to touch and the acceptance criteria.
- **Code and documentation** — fork the repository, create a branch, and open
  a pull request against `main`.
- **Security issues** — **do not open a public issue**. Follow
  [`SECURITY.md`](SECURITY.md) and use GitHub's private
  [Report a vulnerability](https://github.com/thepaneb/isis-report-lib/security/advisories/new)
  flow.

## Fork pull requests and code scanning

Fork → branch → pull request is the normal path. One CI constraint is worth
knowing before you start:

- **Docs/config-only changes** (Markdown, docs assets, `zensical.toml`) are
  handled automatically: a trusted workflow adds the required empty
  code-scanning analyses, and the normal CI gate applies.
- **Code, tests, CI or dependency changes** from a fork are intentionally
  blocked by the code-scanning ruleset, because fork-generated SARIF cannot be
  trusted. The maintainer integrates those through a branch in this repository
  (credit preserved) or asks for a split. Open an issue first for anything
  beyond docs/config so we can agree on the path.

## Maintainer: integrating a fork PR

Fork PRs that change code, tests, CI or dependencies cannot upload the
code-scanning SARIF (the token is read-only). Integrate them from a branch in
this repository and **never use `--admin` to bypass the gate**.

```bash
# 1. Fetch the contributor's head and start from main
git fetch origin pull/<N>/head:pr-<N>
git switch -c integrate/pr-<N> origin/main

# Tip: copy the author identity from the PR head
git log -1 --format='%an <%ae>' pr-<N>

# 2a. Preserve the original commits (author is kept)
git cherry-pick <sha>...      # or: git rebase --onto origin/main <base> pr-<N>

# 2b. If merge commits/conflicts make cherry-pick impractical, apply the diff
#     and commit it with the original author:
git diff --binary origin/main...pr-<N> | git apply
git add -A
git commit --author="Original Author <email>" -m "<original title>" \
  -m "Supersedes #<N>."
# Multiple authors: keep the primary author and add
# `Co-authored-by: Name <email>` trailers.
```

```bash
# 3. Push the integration branch and open the internal PR
git push -u origin integrate/pr-<N>
gh pr create --base main --head integrate/pr-<N> \
  --title "<original title>" \
  --body "Supersedes #<N>. Original author: @<user>. ..."

# 4. After the full gate is green, merge with rebase (NOT squash)
gh pr merge <internal> --rebase --delete-branch

# 5. Close the fork PR and credit the author
gh pr close <N> --comment "Integrated in #<internal> with the original authorship preserved."
```

Why rebase: a squash would make the maintainer the author of the final commit;
a rebase keeps the contributor's commit author. The maintainer remains the
committer and the internal PR opener.

Integration checklist:

- [ ] The integration branch lives in this repository, based on `main`.
- [ ] `git show --format='%an <%ae>'` shows the contributor, not the maintainer.
- [ ] The internal PR says `Supersedes #<N>` and `Original author: @<user>`.
- [ ] The full CI/SARIF gate is green; there is no admin bypass.
- [ ] The merge is **Rebase and merge**, not squash.
- [ ] The original fork PR is closed with a link and credit.

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
python -m ruff check src tests demo fuzz
python -m ruff format --check src tests demo fuzz
python -m mypy src
python -m zensical build --strict             # only when docs change
python scripts/gen_api_docs.py --check        # public API/docstring changes
python scripts/gen_gallery.py                 # only when gallery artifacts change
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
