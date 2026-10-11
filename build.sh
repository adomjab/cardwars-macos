#!/usr/bin/env bash
# Build CardWars.app with Unity 2017.4.40f1 on a Mac.
# Usage: ./build.sh [project-dir]   (default: ./CardWars)
# Override the editor path with UNITY=/path/to/Unity.app/Contents/MacOS/Unity
set -euo pipefail

PROJECT="$(cd "${1:-CardWars}" && pwd)"
UNITY="${UNITY:-/Applications/Unity/Hub/Editor/2017.4.40f1/Unity.app/Contents/MacOS/Unity}"
OUT="$PROJECT/Builds/macOS/CardWars.app"

if [ ! -x "$UNITY" ]; then
  echo "Unity 2017.4.40f1 not found at: $UNITY" >&2
  echo "Install it via Unity Hub (unityhub://2017.4.40f1/6e14067f8a9a) or set UNITY=..." >&2
  exit 1
fi

"$UNITY" -batchmode -quit -nographics \
  -projectPath "$PROJECT" \
  -buildTarget OSXUniversal \
  -executeMethod MacBuild.BuildMacOS \
  -buildOutput "$OUT" \
  -logFile "$PROJECT/Builds/build-macos.log"

# Ad-hoc sign so Gatekeeper / Apple Silicon (Rosetta) will launch it locally.
xattr -cr "$OUT" || true
codesign --force --deep --sign - "$OUT"

echo "Built: $OUT"
