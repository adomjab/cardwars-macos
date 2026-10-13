#!/usr/bin/env bash
# Zip a built CardWars.app for sharing (upload the zip to a GitHub Release).
# Usage: ./package.sh [path/to/CardWars.app]
# Default app: ./CardWars/Builds/macOS/CardWars.app, or /Applications/CardWars.app
set -euo pipefail

APP="${1:-}"
if [ -z "$APP" ]; then
  for candidate in "CardWars/Builds/macOS/CardWars.app" "/Applications/CardWars.app"; do
    if [ -d "$candidate" ]; then APP="$candidate"; break; fi
  done
fi
if [ -z "$APP" ] || [ ! -d "$APP" ]; then
  echo "CardWars.app not found. Pass its path: ./package.sh /path/to/CardWars.app" >&2
  exit 1
fi

OUT="$(pwd)/CardWars-macOS.zip"

# Clean extended attributes and re-sign so the copy we ship is consistent.
xattr -cr "$APP" || true
codesign --force --deep --sign - "$APP"

# ditto keeps the app bundle's symlinks and metadata intact (plain zip can break them).
rm -f "$OUT"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$OUT"

echo "Created: $OUT ($(du -h "$OUT" | cut -f1))"
echo "Upload it to a GitHub Release with the tag 'cardwars-macos' (see SHARING.md)."
