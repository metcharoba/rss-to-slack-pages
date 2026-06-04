#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/3] Build public/index.html from RSS log"
python3 scripts/build_html_from_log.py

echo "[2/3] Copy public/index.html to docs/index.html"
cp public/index.html docs/index.html

echo "[3/3] Done"
ls -lh public/index.html docs/index.html
