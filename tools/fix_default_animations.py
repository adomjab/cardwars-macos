#!/usr/bin/env python3
"""Restore lost default clips on legacy Animation components.

When the CardWars project was recovered from the shipped game, almost every
Animation component lost its default clip (m_Animation: {fileID: 0}). Ones
set to play automatically then play nothing: the "Nice/Rare/Very Rare/
Algebraic Rare Card!" chest banners, "You Win/You Lose", hit/crit and spell
effects, tombstones, animated scenery, etc.

For every Animation component that plays automatically, has no default clip
and holds exactly one clip, this makes that clip the default. Components with
several clips (characters) are left alone; the game plays those by name.

Usage: python3 tools/fix_default_animations.py path/to/CardWars/Assets
"""

import glob
import os
import re
import sys

CLIP_RE = re.compile(r"^  - (\{fileID: 7400000, guid: [0-9a-f]{32}, type: 2\})$", re.M)


def fix_document(doc):
    if not doc.startswith("!u!111 ") or "m_Animation: {fileID: 0}" not in doc:
        return doc, False
    if "m_PlayAutomatically: 1" not in doc:
        return doc, False
    clips = CLIP_RE.findall(doc)
    if len(clips) != 1:
        return doc, False
    return doc.replace("m_Animation: {fileID: 0}", "m_Animation: " + clips[0], 1), True


def fix_file(path):
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    if "!u!111 " not in text:
        return 0
    parts = re.split(r"(?m)^(?=--- )", text)
    fixed = 0
    out = []
    for part in parts:
        if part.startswith("--- "):
            header, _, body = part.partition(" ")
            body, changed = fix_document(body)
            part = header + " " + body
            fixed += changed
        out.append(part)
    if fixed:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("".join(out))
    return fixed


def main():
    assets = sys.argv[1] if len(sys.argv) > 1 else "Assets"
    files = glob.glob(os.path.join(assets, "**", "*.prefab"), recursive=True) + \
        glob.glob(os.path.join(assets, "**", "*.unity"), recursive=True)
    total = 0
    for path in sorted(files):
        n = fix_file(path)
        if n:
            print("%3d  %s" % (n, os.path.relpath(path, assets)))
            total += n
    print("Fixed %d Animation components." % total)


if __name__ == "__main__":
    main()
