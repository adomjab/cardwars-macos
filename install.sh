#!/usr/bin/env bash
# One-line installer for Card Wars on macOS. Friends run:
#   curl -fsSL https://raw.githubusercontent.com/adomjab/aseprite-builder/claude/cardwars-macos-compat-jeh7xi/cardwars-macos/install.sh | bash
set -euo pipefail

REPO="adomjab/aseprite-builder"
TAG="${CARDWARS_TAG:-cardwars-macos}"
URL="https://github.com/$REPO/releases/download/$TAG/CardWars-macOS.zip"
DEST="/Applications"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Card Wars for macOS installer"

# Apple Silicon Macs need Rosetta 2 to run this Intel game.
if [ "$(uname -m)" = "arm64" ] && ! arch -x86_64 /usr/bin/true 2>/dev/null; then
  echo "==> Installing Rosetta 2 (you may be asked for your password)..."
  softwareupdate --install-rosetta --agree-to-license
fi

echo "==> Downloading the game (this can take a few minutes)..."
curl -fL --progress-bar -o "$TMP/CardWars-macOS.zip" "$URL"

echo "==> Unpacking..."
ditto -x -k "$TMP/CardWars-macOS.zip" "$TMP"

if [ -d "$DEST/CardWars.app" ]; then
  echo "==> Replacing the old version (your save is kept; it lives outside the app)"
  rm -rf "$DEST/CardWars.app" 2>/dev/null || sudo rm -rf "$DEST/CardWars.app"
fi
mv "$TMP/CardWars.app" "$DEST/" 2>/dev/null || sudo mv "$TMP/CardWars.app" "$DEST/"

# The app isn't notarized by Apple; clear the download flag so macOS opens it.
xattr -cr "$DEST/CardWars.app" 2>/dev/null || sudo xattr -cr "$DEST/CardWars.app"

echo "==> Done! Card Wars is in your Applications folder."
open "$DEST/CardWars.app"
