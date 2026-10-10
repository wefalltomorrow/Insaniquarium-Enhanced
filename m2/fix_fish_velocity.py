#!/usr/bin/env python3
"""Initialise both directions of the newly spawned WinFish guppy velocity.

The pinned WinFish Fish::Init() sets mVX in only the random negative branch.
When the positive branch is selected, mVX previously contained whatever bits
were left in uninitialised instance storage. This patch gives that branch the
intended positive 0.1 velocity while leaving the negative path unchanged.

Only patches the throwaway, port-generated M2 source tree. It does NOT touch
simulation rate, older releases, saved games or upstream submodules.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
FISH = ROOT / "upstream/port/winfish/Fish.cpp"

OLD = """    mPrevVX = 1.0;
    if (Rand(2))
    {
        mVX = -0.1;
        mPrevVX = -1.0;
    }"""

NEW = """    mVX = 0.1;
    mPrevVX = 1.0;
    if (Rand(2))
    {
        mVX = -0.1;
        mPrevVX = -1.0;
    }"""


def patch_source(source: str) -> str:
    count = source.count(OLD)
    if count != 1:
        raise RuntimeError(
            f"Fish::Init initial velocity anchor expected once, found {count}"
        )
    patched = source.replace(OLD, NEW, 1)
    if patched.count(NEW) != 1:
        raise RuntimeError("Fish::Init initial velocity verification failed")
    return patched


def main() -> None:
    if not FISH.is_file():
        raise RuntimeError(f"Generated Fish.cpp missing: {FISH}")
    source = FISH.read_text(encoding="utf-8-sig")
    patched = patch_source(source)
    FISH.write_text(patched, encoding="utf-8", newline="\n")
    print("[ok] Fish::Init positive initial velocity is +0.1")
    print("[ok] Negative random direction remains -0.1")
    print("[ok] Other fish movement logic remains untouched")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
