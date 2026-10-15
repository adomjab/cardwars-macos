#!/usr/bin/env bash
# Zip a built CardWars.app for sharing (upload the zip to a GitHub Release).
# Usage: ./package.sh [--server http://YOUR-IP/] [path/to/CardWars.app]
#   --server  sets the game server the shared app connects to
# Default app: ./CardWars/Builds/macOS/CardWars.app, or /Applications/CardWars.app
set -euo pipefail

SERVER=""
APP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --server) SERVER="${2:-}"; shift 2 ;;
    --server=*) SERVER="${1#--server=}"; shift ;;
    -h|--help) sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) APP="$1"; shift ;;
  esac
done

if [ -z "$APP" ]; then
  for candidate in "CardWars/Builds/macOS/CardWars.app" "/Applications/CardWars.app"; do
    if [ -d "$candidate" ]; then APP="$candidate"; break; fi
  done
fi
if [ -z "$APP" ] || [ ! -d "$APP" ]; then
  echo "CardWars.app not found. Pass its path: ./package.sh /path/to/CardWars.app" >&2
  exit 1
fi

SETTINGS="$APP/Contents/Resources/Data/StreamingAssets/server_settings.json"
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

# Shared game data from main/gamedata: yearly event schedules (tools/make_events.py)
# and the cheaper 1.12.8 gem prices.
BLUEPRINTS="$APP/Contents/Resources/Data/StreamingAssets/Blueprints"
for f in db_Schedule.json db_GachaSchedule.json db_IAP.json; do
  if curl -fsSL -m 30 -o "$BLUEPRINTS/$f.new" "https://raw.githubusercontent.com/adomjab/cardwars-macos/main/gamedata/$f"; then
    mv "$BLUEPRINTS/$f.new" "$BLUEPRINTS/$f"
  else
    rm -f "$BLUEPRINTS/$f.new"
    echo "  WARNING: couldn't download $f; keeping the app's copy." >&2
  fi
done
echo "Event schedules and gem prices: up to date"

OUT="$(pwd)/CardWars-macOS.zip"

# Clean extended attributes and re-sign so the copy we ship is consistent.
xattr -cr "$APP" || true
codesign --force --deep --sign - "$APP"

# ditto keeps the app bundle's symlinks and metadata intact (plain zip can break them).
rm -f "$OUT"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$OUT"

echo "Created: $OUT ($(du -h "$OUT" | cut -f1))"
echo "Upload it to a new GitHub Release (see SHARING.md)."
