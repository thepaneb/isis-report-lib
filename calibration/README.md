# Jev calibration corpus

Local, advisory calibration for `scripts/jev_review.py`. It is not part of CI:
running it calls the Jev API and may use paid fallback credits.

## Build a corpus

Save public PR diffs next to a config (the `.diff` files are gitignored):

```bash
gh pr diff 98 > calibration/pr98.diff
gh pr diff 110 > calibration/pr110.diff
gh pr diff 111 > calibration/pr111.diff
gh pr diff 112 > calibration/pr112.diff
gh pr diff 113 > calibration/pr113.diff
cp calibration/jev-cases.example.json calibration/jev-cases.json
```

The `*-bad.diff` cases are local synthetic security/release regressions; create
them from the examples in the calibration notes or keep your own.

## Run

```bash
python scripts/jev_calibrate.py --config calibration/jev-cases.json --dry-run
python scripts/jev_calibrate.py --config calibration/jev-cases.json
python scripts/jev_calibrate.py --config calibration/jev-cases.json --case pr98
python scripts/jev_calibrate.py --config calibration/jev-cases.json --json
```

The key comes from `OPENCODE_API_KEY` or `--env-file`. The default model is
`jev-1.13-free`, with the paid fallback chain.

Expected verdicts are intentionally coarse (`approve` / `comment` / `block`).
If a case regresses, compare the Markdown report and the per-dimension
probabilities before changing a threshold. Re-run this after a Jev model update
or a significant change to a pack.

## Cadence

A monthly `Jev calibration reminder` workflow opens one issue when none is
already open. Run the corpus, investigate any failures and close the issue;
the reminder does not call the Jev API or need a secret.
