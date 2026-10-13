#!/usr/bin/env python3
"""Guarded M2-only sprite interpolation for upward-moving shot smoke.

Patch generated native port after shot sound-cadence stage and coin/food's
M2ObjectInterpolation.hpp deployment. Only shot types 6 and 7 move in
pinned WinFish, rising 2px per 28ms game tick. Simulation, sound and saves
remain untouched.
"""
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"

HEADER_ANCHOR = "\tclass Shot : public GameObject\n\t{\n\tpublic:"
HEADER_PATCH = (
    HEADER_ANCHOR + "\n"
    "\t\t// M2-only render history (never saved or used for game simulation).\n"
    "\t\tdouble mM2PrevShotX = 0.0, mM2PrevShotY = 0.0;\n"
    "\t\tbool mM2HavePrevShot = false;"
)
INCLUDE_ANCHOR = '#include "Shot.h"'
INCLUDE_PATCH = '#include "Shot.h"\n#include "M2ObjectInterpolation.hpp"'
UPDATE_ANCHOR = (
    "\t// Original sound/game callback must not run on M2 redraws.\n"
    "\tif (gEnhancedM2Enabled)\n"
    "\t\tGameObject::UpdateFishSongMgr();\n"
    "\tGameObject::UpdateCounters();"
)
UPDATE_PATCH = (
    "\t// Snapshot before the original 28ms shot update.\n"
    "\tif (gEnhancedM2Enabled) {\n"
    "\t\tmM2PrevShotX = mX;\n"
    "\t\tmM2PrevShotY = mY;\n"
    "\t\tmM2HavePrevShot = true;\n"
    "\t\tGameObject::UpdateFishSongMgr();\n"
    "\t} else {\n"
    "\t\tmM2HavePrevShot = false;\n"
    "\t}\n"
    "\tGameObject::UpdateCounters();"
)
DRAW_ANCHOR = (
    "\tM2Debug::Get().ObjectMotion(M2Debug::ShotEffect, this, mX, mY, "
    "0, 0, 0.0, mApp->mBoard && mApp->mBoard->mPause, false);\n"
    "\tif (!gEnhancedM2Enabled)\n"
    "\t\tGameObject::UpdateFishSongMgr();\n"
    "\tif (m0x164 != 0)\n"
    "\t\treturn;\n\n"
    "\tg->SetColorizeImages(true);"
)
DRAW_PATCH = (
    "\tif (!gEnhancedM2Enabled)\n"
    "\t\tGameObject::UpdateFishSongMgr();\n"
    "\tif (m0x164 != 0)\n"
    "\t\treturn;\n\n"
    "\t// Visual translation only: preserve simulation mX/mY and hitboxes.\n"
    "\tconst bool m2MovingSmoke = (mShotType == 6 || mShotType == 7);\n"
    "\tEnhancedM2::ScopedObjectTranslation<Graphics> m2ShotShift(\n"
    "\t\tg, gEnhancedM2Enabled && m2MovingSmoke,\n"
    "\t\tmApp->mBoard && mApp->mBoard->mPause,\n"
    "\t\tmM2HavePrevShot, mM2PrevShotX, mM2PrevShotY,\n"
    "\t\tmX, mY, mX, mY, gEnhancedM2Blend, 4.0);\n"
    "\tM2Debug::Get().ObjectMotion(M2Debug::ShotEffect, this, mX, mY,\n"
    "\t\tm2ShotShift.ShiftX(), m2ShotShift.ShiftY(),\n"
    "\t\tgEnhancedM2Blend, mApp->mBoard && mApp->mBoard->mPause,\n"
    "\t\tmM2HavePrevShot && m2MovingSmoke);\n\n"
    "\tg->SetColorizeImages(true);"
)

def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one source anchor, found {count}")
    return source.replace(old, new, 1)

def patch(header: str, source: str) -> tuple[str, str]:
    if "mM2PrevShotX" in header or "m2ShotShift" in source:
        raise RuntimeError("Shot interpolation already applied")
    header = replace_once(header, HEADER_ANCHOR, HEADER_PATCH, "Shot.h")
    source = replace_once(source, INCLUDE_ANCHOR, INCLUDE_PATCH, "Shot.cpp include")
    source = replace_once(source, UPDATE_ANCHOR, UPDATE_PATCH, "Shot::Update")
    source = replace_once(source, DRAW_ANCHOR, DRAW_PATCH, "Shot::Draw")
    return header, source

def main() -> int:
    header = GAME / "Shot.h"
    source = GAME / "Shot.cpp"
    required = GAME / "M2ObjectInterpolation.hpp"
    if not header.is_file() or not source.is_file() or not required.is_file():
        raise RuntimeError("Generated native Shot sources and M2 interpolation header required")
    new_header, new_source = patch(
        header.read_text(encoding="utf-8-sig"),
        source.read_text(encoding="utf-8-sig"),
    )
    header.write_text(new_header, encoding="utf-8", newline="\n")
    source.write_text(new_source, encoding="utf-8", newline="\n")
    print("[ok] M2 moving smoke types 6/7 use render-only smoothing")
    print("[ok] Gameplay position, audio, animation cells and non-M2 mode preserved")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        raise SystemExit(1)
