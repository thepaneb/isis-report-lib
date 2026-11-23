#!/usr/bin/env bash
# Time-boxed fuzzing of every target. The committed seeds under fuzz/corpus/
# stay read-only; libFuzzer writes new units to a scratch dir so a local run
# never dirties the repo.
#
# Usage: bash scripts/fuzz-smoke.sh [seconds]   (default 25)
set -uo pipefail
cd "$(dirname "$0")/.."

seconds="${1:-25}"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

failed=0
for target in toon payload layout; do
  echo "=== fuzz_${target} (${seconds}s) ==="
  out="${scratch}/${target}"
  mkdir -p "$out"
  if ! python "fuzz/fuzz_${target}.py" "$out" "fuzz/corpus/${target}" \
      -max_total_time="$seconds" -print_final_stats=1 -rss_limit_mb=2048; then
    echo "FAILED: fuzz_${target}"
    failed=1
  fi
done
exit "$failed"
