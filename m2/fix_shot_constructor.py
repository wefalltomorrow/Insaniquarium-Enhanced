#!/usr/bin/env python3
"""Fix WinFish Shot(int,int,int) using mShotType before assignment (M2 only).

The original WinFish constructor tests mShotType when choosing initial
animation delay before assigning the constructor's theType argument.
Another Insaniquarium mod found the same issue in the retail executable.
Keep both RNG branches as written; initialise the actual requested type
before their condition. Do not touch other constructors, gameplay timing,
simulation coordinates, or shot rendering.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish/Shot.cpp"

CONSTRUCTOR_START = "Shot::Shot(int theX, int theY, int theType)"
ORIGINAL = (
    "\tmX = theX;\n"
    "\tmY = theY;\n"
    "\tmType = TYPE_SHOT;\n"
    "\tm0x158 = 0;\n"
    "\tm0x15c = 0;\n"
    "\tif (mShotType == 0 || mShotType == 2)\n"
    "\t\tm0x164 = 0;\n"
    "\telse\n"
    "\t\tm0x164 = mApp->mSeed->Next() % 3;\n\n"
    "\tmMouseVisible = false;\n"
    "\tmShotType = theType;\n"
)
FIXED = (
    "\tmX = theX;\n"
    "\tmY = theY;\n"
    "\tmType = TYPE_SHOT;\n"
    "\tm0x158 = 0;\n"
    "\tm0x15c = 0;\n"
    "\t// The requested shot type must be defined before choosing the delay.\n"
    "\t// Keep the game's original type-dependent RNG behaviour.\n"
    "\tmShotType = theType;\n"
    "\tif (mShotType == 0 || mShotType == 2)\n"
    "\t\tm0x164 = 0;\n"
    "\telse\n"
    "\t\tm0x164 = mApp->mSeed->Next() % 3;\n\n"
    "\tmMouseVisible = false;\n"
)

def patch(source: str) -> str:
    if source.count(CONSTRUCTOR_START) != 1:
        raise RuntimeError("Expected one three-argument Shot constructor")
    index = source.index(CONSTRUCTOR_START)
    end = source.find("\n}", index)
    if end == -1:
        raise RuntimeError("Shot constructor end not found")
    body = source[index:end]
    if body.count(ORIGINAL) != 1:
        raise RuntimeError("Shot constructor no longer matches audited upstream")
    if source.count(ORIGINAL) != 1:
        raise RuntimeError("Shot constructor sequence appears outside expected scope")
    fixed = body.replace(ORIGINAL, FIXED, 1)
    if fixed.count("mShotType = theType;") != 1:
        raise RuntimeError("Expected exactly one shot-type assignment")
    if fixed.index("mShotType = theType;") >= fixed.index("if (mShotType == 0 || mShotType == 2)"):
        raise RuntimeError("Shot type still read before assignment")
    return source[:index] + fixed + source[end:]

def main() -> int:
    if not GAME.is_file():
        raise RuntimeError("Generated native Shot.cpp missing")
    original = GAME.read_text(encoding="utf-8-sig")
    changed = patch(original)
    GAME.write_text(changed, encoding="utf-8", newline="\n")
    print("[ok] Shot kind initialised before type-dependent first-frame delay")
    print("[ok] Original random-delay branch and other Shot constructors preserved")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError) as exc:
        print("[FAILED] {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
