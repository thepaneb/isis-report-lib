#!/usr/bin/env bash
# Regenerate every hash-pinned lock from its .in file.
#
# These locks are what CI installs (`pip install --require-hashes -r ...`), so
# every tool we run in workflows is pinned to an exact version *and* hash.
# Run this after bumping a tool (or when Dependabot bumps an .in) and commit
# both the .in and the regenerated .txt.
#
# Requirements: uv (https://docs.astral.sh/uv/).
set -euo pipefail

cd "$(dirname "$0")/.."

compile() {
  local src="$1" out="$2"
  echo "==> $src -> $out"
  uv pip compile "$src" \
    --universal \
    --python-version 3.11 \
    --generate-hashes \
    --no-header \
    --quiet \
    --output-file "$out"
}

for name in ci audit publish guarddog sbom fuzz; do
  compile ".github/requirements/requirements-$name.in" ".github/requirements/requirements-$name.txt"
done

compile "docs/requirements-docs.in" "docs/requirements-docs.txt"
compile "docker/requirements.in" "docker/requirements.txt"

echo "Done. Review the diff, then commit."
