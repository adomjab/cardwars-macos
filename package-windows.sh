#!/usr/bin/env bash
# Zip the Windows build for sharing (upload CardWars-Windows.zip to the same
# GitHub Release as CardWars-macOS.zip; install-windows.ps1 downloads it).
# Usage: ./package-windows.sh [--server http://YOUR-IP/] [path/to/game-folder]
#   --server  sets the game server the shared game connects to
# Default folder: ./CardWars/Builds/Windows/CardWars
set -euo pipefail

SERVER=""
GAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    --server) SERVER="${2:-}"; shift 2 ;;
    --server=*) SERVER="${1#--server=}"; shift ;;
    -h|--help) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) GAME="$1"; shift ;;
  esac
done
GAME="${GAME:-CardWars/Builds/Windows/CardWars}"
if [ ! -f "$GAME/CardWars.exe" ] || [ ! -d "$GAME/CardWars_Data" ]; then
  echo "Windows build not found in $GAME. Run ./build-windows.sh first." >&2
  exit 1
fi

SETTINGS="$GAME/CardWars_Data/StreamingAssets/server_settings.json"
if [ -n "$SERVER" ]; then
  case "$SERVER" in
    http://*) ;;
    https://*) echo "The game can't use https. Use http://..." >&2; exit 1 ;;
    *) SERVER="http://$SERVER" ;;
  esac
  case "$SERVER" in */) ;; *) SERVER="$SERVER/" ;; esac
  printf '{\n    "type" : "server_settings",\n    "server_url" : "%s"\n}\n' "$SERVER" > "$SETTINGS"
fi
CURRENT="$(sed -n 's/.*"server_url" *: *"\([^"]*\)".*/\1/p' "$SETTINGS")"
echo "Game server in this package: $CURRENT"
if curl -fsS -m 5 "$CURRENT" >/dev/null 2>&1; then
  echo "  (reachable)"
else
  echo "  WARNING: that server isn't answering right now." >&2
fi

BLUEPRINTS="$GAME/CardWars_Data/StreamingAssets/Blueprints"
for f in db_Schedule.json db_GachaSchedule.json db_IAP.json db_Leaders.json db_Spells.json db_Characters.json; do
  if curl -fsSL -m 30 -o "$BLUEPRINTS/$f.new" "https://raw.githubusercontent.com/adomjab/cardwars-macos/main/gamedata/$f"; then
    mv "$BLUEPRINTS/$f.new" "$BLUEPRINTS/$f"
  else
    rm -f "$BLUEPRINTS/$f.new"
    echo "  WARNING: couldn't download $f; keeping the game's copy." >&2
  fi
done
echo "Event schedules, gem prices and fixes: up to date"

OUT="$(pwd)/CardWars-Windows.zip"
rm -f "$OUT"
# Plain zip without Mac metadata (no __MACOSX or ._ files) for Windows.
(cd "$(dirname "$GAME")" && zip -qrX "$OUT" "$(basename "$GAME")" -x '*.DS_Store')

echo "Created: $OUT ($(du -h "$OUT" | cut -f1))"
echo "Upload it to the same GitHub Release as CardWars-macOS.zip (see SHARING.md)."
