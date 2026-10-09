#!/usr/bin/env python3
"""Prepare latest WinFish for SaMeiers' SDL3 port without masking patch failures.

The port is pinned at 95d4aaf (September 2026), while we build WinFish
f919b3c (October 2026). WinFish independently fixed the fish-song applause
lifetime bug. SaMeiers' older three-part patch no longer matches the new source.

This script checks the *actual* upstream fix, then removes only the redundant
applause patch section from the temporary, generated port checkout. All other
game fixes remain enabled and port.sh must still pass without [FAILED] markers.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "upstream"
GAME = UPSTREAM / "external" / "winfish" / "source" / "WinFish" / "FishSongMgr.cpp"
FIXES = UPSTREAM / "port" / "fixups" / "apply-gamefixes.py"

def main() -> int:
    song = GAME.read_text(encoding="utf-8-sig", errors="strict")
    checks = {
        "heap-allocated applause song": "FishSong* aSong = new FishSong();" in song,
        "notes stored on heap object": song.count("aSong->mNoteDataVector.push_back(aNote);") >= 2,
        "applause queued via owned pointer": "AddSong(aSong);" in song,
        "no stack-based applause": "FishSong aSong;" not in song,
        "song iterator erase uses return": "anIterator = mSongList.erase(anIterator);" in song,
    }
    for label, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    if not all(checks.values()):
        print("Latest WinFish changed: cannot safely drop the older applause fixes.", file=sys.stderr)
        return 1

    code = FIXES.read_text(encoding="utf-8")
    begin = "    # --- 7. The applause song is a local, kept after it dies"
    finish = "    # --- 8. StopFishSong walks an iterator it just invalidated"
    if code.count(begin) != 1 or code.count(finish) != 1:
        print("Unexpected apply-gamefixes.py layout: refusing to alter it.", file=sys.stderr)
        return 1
    a, b = code.index(begin), code.index(finish)
    if a >= b:
        print("Gamefix markers out of order.", file=sys.stderr)
        return 1
    redundant = code[a:b]
    if redundant.count('ok &= sub("FishSongMgr.cpp",') != 3:
        print("Unexpected number of applause replacements.", file=sys.stderr)
        return 1

    updated = code[:a] + (
        "    # --- 7. Upstream WinFish has already fixed the applause song. -----\n"
        "    # Verified by the Insaniquarium Enhanced M1 source-prep script.\n\n"
    ) + code[b:]
    FIXES.write_text(updated, encoding="utf-8", newline="")
    print("Removed 3 redundant applause replacements. All other port fixes preserved.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
