#!/usr/bin/env bash
# One-line installer for Card Wars on macOS. Friends run:
#   curl -fsSL https://raw.githubusercontent.com/adomjab/cardwars-macos/main/install.sh | bash
set -euo pipefail

REPO="adomjab/cardwars-macos"
URL="https://github.com/$REPO/releases/latest/download/CardWars-macOS.zip"
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

# Shared game data: yearly event schedules (the game's own ended in 2025) and
# the gem prices, so Mac and Windows players get the same.
echo "==> Adding events, gem prices and fixes..."
BLUEPRINTS="$DEST/CardWars.app/Contents/Resources/Data/StreamingAssets/Blueprints"
for f in db_Schedule.json db_GachaSchedule.json db_IAP.json db_Leaders.json db_Spells.json; do
  curl -fsSL -o "$TMP/$f" "https://raw.githubusercontent.com/$REPO/main/gamedata/$f"
  cp "$TMP/$f" "$BLUEPRINTS/$f" 2>/dev/null || sudo cp "$TMP/$f" "$BLUEPRINTS/$f"
  # A copy downloaded by the old server's content updates would win; remove it.
  rm -f "$HOME/Library/Application Support/shishkabob/Card Wars/Contents/Blueprints/$f"
done

# The app isn't notarized by Apple; clear the download flag so macOS opens it,
# and re-sign it after the change above.
xattr -cr "$DEST/CardWars.app" 2>/dev/null || sudo xattr -cr "$DEST/CardWars.app"
codesign --force --deep --sign - "$DEST/CardWars.app" 2>/dev/null || sudo codesign --force --deep --sign - "$DEST/CardWars.app"

echo "==> Done! Card Wars is in your Applications folder."
open "$DEST/CardWars.app"
