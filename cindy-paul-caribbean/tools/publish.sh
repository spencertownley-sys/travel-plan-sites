#!/usr/bin/env bash
# Copy the built site (everything except tools/) into the cindy-paul-caribbean/ folder of a
# kathy-japan checkout, which is the branch GitHub Pages serves.
#   tools/publish.sh /path/to/kathy-japan-worktree
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:?usage: tools/publish.sh /path/to/kathy-japan-checkout}/cindy-paul-caribbean"
mkdir -p "$DEST"
rsync -a --delete --exclude tools/ "$SRC/" "$DEST/"
echo "copied site to $DEST"
