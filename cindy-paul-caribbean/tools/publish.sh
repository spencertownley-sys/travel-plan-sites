#!/usr/bin/env bash
# Copy the built site (everything except tools/) into the cindy-paul-caribbean/ folder of a
# kathy-japan checkout, which is the branch GitHub Pages serves.
#   tools/publish.sh /path/to/kathy-japan-checkout
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:?usage: tools/publish.sh /path/to/kathy-japan-checkout}/cindy-paul-caribbean"
python3 - "$SRC" "$DEST" <<'PY'
import os, shutil, sys
src, dest = sys.argv[1], sys.argv[2]
if os.path.isdir(dest):
    shutil.rmtree(dest)
shutil.copytree(src, dest, ignore=shutil.ignore_patterns("tools", "__pycache__", ".tilecache"))
print("copied site to", dest)
PY
