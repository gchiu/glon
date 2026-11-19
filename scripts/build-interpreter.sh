#!/usr/bin/env bash
# Build the pinned native Glon CLI from gchiu/rebol-substrate-experiment.
#
# Usage:
#   scripts/build-interpreter.sh [COMMIT] [DEST]
#
# COMMIT defaults to interpreter.json's commit.
# DEST defaults to .tools/glon-eng.
# GLON_ENGINEERING_REPO may override the clone URL/path (useful offline).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT="${1:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["commit"])' "$ROOT/interpreter.json")}"
DEST="${2:-$ROOT/.tools/glon-eng}"
REPO_URL="${GLON_ENGINEERING_REPO:-https://github.com/gchiu/rebol-substrate-experiment.git}"

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
git clone --filter=blob:none --no-checkout "$REPO_URL" "$DEST"
git -C "$DEST" checkout --detach "$COMMIT"
make -C "$DEST" glon MODULES=file

test -x "$DEST/glon" || { echo "build-interpreter: $DEST/glon was not produced" >&2; exit 1; }
echo "$DEST/glon"
