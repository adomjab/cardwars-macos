#!/usr/bin/env bash
# Build the Windows version of Card Wars on a Mac with Unity 2017.4.40f1.
# Needs the editor's "Windows Build Support" module (Unity Hub > Installs >
# 2017.4.40f1 > Add modules).
# Usage: ./build-windows.sh [project-dir]   (default: ./CardWars)
# Override the editor path with UNITY=/path/to/Unity.app/Contents/MacOS/Unity
set -euo pipefail

PROJECT="$(cd "${1:-CardWars}" && pwd)"
UNITY="${UNITY:-/Applications/Unity/Hub/Editor/2017.4.40f1/Unity.app/Contents/MacOS/Unity}"
OUT="$PROJECT/Builds/Windows/CardWars/CardWars.exe"
LOG="$PROJECT/Builds/build-windows.log"

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

# The module lives next to Unity.app in PlaybackEngines.
ENGINES="$(dirname "$(dirname "$(dirname "$(dirname "$UNITY")")")")/PlaybackEngines"
if [ ! -d "$ENGINES/WindowsStandaloneSupport" ]; then
  echo "Unity's Windows Build Support module isn't installed." >&2
  echo "Add it in Unity Hub: Installs > 2017.4.40f1 > ... > Add modules > Windows Build Support." >&2
  exit 1
fi

# Start from an empty folder so files from an older build don't end up in the zip.
rm -rf "$(dirname "$OUT")"
mkdir -p "$PROJECT/Builds"

if ! ${ARCH_PREFIX[@]+"${ARCH_PREFIX[@]}"} "$UNITY" -batchmode -quit -nographics \
  -projectPath "$PROJECT" \
  -buildTarget Win64 \
  -executeMethod MacBuild.BuildWindows \
  -buildOutput "$OUT" \
  -logFile "$LOG"; then
  echo "Build failed. Details: $LOG" >&2
  exit 1
fi
if [ ! -f "$OUT" ]; then
  echo "Build failed (no CardWars.exe). Details: $LOG" >&2
  exit 1
fi

echo "Built: $OUT"
