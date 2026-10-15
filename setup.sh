#!/usr/bin/env bash
# Clone CardWars at the commit the patch was made against and apply the macOS patch.
# Usage: ./setup.sh [target-dir]   (default: ./CardWars)
set -euo pipefail

UPSTREAM="https://github.com/shishkabob27/CardWars.git"
COMMIT="210255cc96cf5bc96cbccb9252763566338bad5e"
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-CardWars}"

if [ ! -d "$DEST/.git" ]; then
  git clone "$UPSTREAM" "$DEST"
fi
cd "$DEST"
git checkout "$COMMIT" 2>/dev/null || {
  echo "Pinned commit not found, using the current upstream HEAD instead." >&2
}

PATCH="$HERE/cardwars-macos.patch"
if git apply --reverse --check "$PATCH" 2>/dev/null; then
  echo "macOS patch already applied."
elif git apply --check "$PATCH" 2>/dev/null; then
  git apply --whitespace=nowarn "$PATCH"
  echo "macOS patch applied."
else
  # An older version of the patch is applied. Put the game's files back to the
  # original (Unity's Library cache and Builds/ are ignored by git, so they're
  # kept) and apply the current patch.
  echo "Updating to the current macOS patch..."
  git checkout -- .
  git clean -fdq
  git apply --whitespace=nowarn "$PATCH"
  echo "macOS patch applied."
fi
echo "Project ready at: $(pwd)"
