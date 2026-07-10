#!/usr/bin/env bash
set -e
cd "/c/Users/fyz/WorkBuddy/2026-07-07-10-35-32"
"./.venv/Scripts/pyinstaller.exe" --onefile --windowed --name StockPulse \
  --add-data "index.html;." \
  --hidden-import webview --collect-all webview app.py 2>&1 | tail -5
echo "=== copy ==="
cp "dist/StockPulse.exe" "/c/Users/fyz/Desktop/StockPulse.exe"
cp "index.html" "/c/Users/fyz/Desktop/StockPulse-preview.html"
echo "ALL_DONE"
ls -lh "/c/Users/fyz/Desktop/StockPulse.exe"
