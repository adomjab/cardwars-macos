#!/usr/bin/env bash
# Build CardWars.app with Unity 2017.4.40f1 on a Mac.
# Usage: ./build.sh [project-dir]   (default: ./CardWars)
# Override the editor path with UNITY=/path/to/Unity.app/Contents/MacOS/Unity
set -euo pipefail

PROJECT="$(cd "${1:-CardWars}" && pwd)"
UNITY="${UNITY:-/Applications/Unity/Hub/Editor/2017.4.40f1/Unity.app/Contents/MacOS/Unity}"
OUT="$PROJECT/Builds/macOS/CardWars.app"

# Unity 2017.4 and the games it builds are Intel-only. On Apple Silicon (M1/M2/...)
# they run through Rosetta 2, so make sure it is installed and launch Unity under it.
ARCH_PREFIX=()
if [ "$(uname -m)" = "arm64" ]; then
  if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
    echo "Installing Rosetta 2 (needed to run Unity 2017 on Apple Silicon)..."
    softwareupdate --install-rosetta --agree-to-license
  fi
  ARCH_PREFIX=(arch -x86_64)
fi

if [ ! -x "$UNITY" ]; then
  echo "Unity 2017.4.40f1 not found at: $UNITY" >&2
  echo "Install it via Unity Hub (unityhub://2017.4.40f1/6e14067f8a9a) or set UNITY=..." >&2
  exit 1
fi

${ARCH_PREFIX[@]+"${ARCH_PREFIX[@]}"} "$UNITY" -batchmode -quit -nographics \
  -projectPath "$PROJECT" \
  -buildTarget OSXUniversal \
  -executeMethod MacBuild.BuildMacOS \
  -buildOutput "$OUT" \
  -logFile "$PROJECT/Builds/build-macos.log"

# Ad-hoc sign so Gatekeeper / Apple Silicon (Rosetta) will launch it locally.
xattr -cr "$OUT" || true
codesign --force --deep --sign - "$OUT"

echo "Built: $OUT"
