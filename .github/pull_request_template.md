## Summary

<!-- What problem does this PR solve, and how? Link the issue if there is one. -->

## Checklist

- [ ] Tests cover the change (or the PR explains why none are needed)
- [ ] `python -m pytest tests -q -m "not browser"` passes
- [ ] `python -m ruff check src tests` and `python -m mypy src` pass
- [ ] Docs updated when behavior or the public API changed
- [ ] `CHANGELOG.md` updated under `[Unreleased]` for user-visible changes
- [ ] `python scripts/gen_api_docs.py --check` passes (public API/docstrings)
- [ ] `python -m zensical build --strict` passes when `docs/` changed

## Notes

<!-- Breaking changes, migration steps, screenshots, or anything reviewers should know. -->
