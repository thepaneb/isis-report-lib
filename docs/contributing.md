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

## AI-assisted contributions

AI tools are allowed. Disclose the tool/model and scope in the pull request,
review and test the output, and keep the final authorship human. Never paste
tokens, `.env.local`, private keys, customer data or private URLs into a prompt.
AI-assisted changes pass the same CI and review gates. See
[`AI_USAGE.md`](https://github.com/thepaneb/isis-report-lib/blob/main/AI_USAGE.md)
and the untrusted-content rules in
[`AGENTS.md`](https://github.com/thepaneb/isis-report-lib/blob/main/AGENTS.md).

## Local advisory reviews (Jev)

The repository ships a local, advisory diff review under `scripts/`:

```bash
python scripts/jev_review.py --diff-file pr.diff --auto-packs --lang en
python scripts/jev_review.py --diff-file pr.diff --profile strict
python scripts/jev_review.py --list-packs
python scripts/jev_review.py --self-test
```

- `--auto-packs` selects `core` plus the packs implied by changed paths
  (`quality`, `docs`, `security`, `release`).
- The default model is `jev-1.13-free`, with a paid fallback chain.
- The key comes from `OPENCODE_API_KEY` or `--env-file`; never commit it.
- Reports are written to `.jev/` (gitignored).

The **Jev review (advisory)** CI workflow runs on same-repo PRs and manual
dispatch. It uploads `.jev/jev-review.md|json` as an artifact and job summary,
and posts a compact sticky comment only when there are findings or a
`comment`/`block` verdict. It is not a required check and does not replace
tests, lint, mypy or human review. The filtered diff is sent to the OpenCode
Console; see the data-egress note in `AGENTS.md`.

Release maintainers can also run the repo-state preflight:

```bash
python scripts/release_preflight.py --version 0.17.0
python scripts/release_preflight.py --version 0.17.0 --remote
```

`--remote` checks PyPI, the GitHub Release assets, docs/security.txt and GHCR.
For calibration after a model or threshold change, use the local harness:

```bash
python scripts/jev_calibrate.py --config calibration/jev-cases.json --dry-run
python scripts/jev_calibrate.py --config calibration/jev-cases.json
```

See [`calibration/README.md`](https://github.com/thepaneb/isis-report-lib/blob/main/calibration/README.md)
for the corpus setup.

## Integrating fork PRs (maintainers)

For a code/tests/CI/dependency fork PR, create an `integrate/pr-<N>` branch in
this repository from `main`, apply the contributor's commits, and preserve the
original author:

- use `git cherry-pick` when the commits are clean, or `git commit --author=...`
  when applying the diff/conflicts; use `Co-authored-by` for additional authors;
- open an internal PR saying `Supersedes #<N>` and `Original author: @<user>`;
- merge with **Rebase and merge**, never squash (squash would replace the
  author with the maintainer);
- close the original PR with a link and credit.

The full command sequence and checklist are in
[`CONTRIBUTING.md`](https://github.com/thepaneb/isis-report-lib/blob/main/CONTRIBUTING.md#maintainer-integrating-a-fork-pr).
Never use `--admin` to bypass the code-scanning gate.

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
