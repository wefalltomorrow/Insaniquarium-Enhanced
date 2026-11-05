#!/usr/bin/env python3
"""M2-only, render-only missile interpolation with conservative movement guards.

Applies after m2/apply_debug.py and m2/apply_coin_food.py to generated
(disposable) native source. Leaves stable M1.2, collision, simulation,
animation cels and save format untouched. Missile movement was measured
at <=2.5px per axis per adjacent 28ms tick; shifts >=8px are rejected.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"

HEADER_ANCHOR = "\tclass Missle : public GameObject\n\t{\n\tpublic:"
HEADER_PATCH = (
    HEADER_ANCHOR + "\n"
    "\t\t// M2 visual-only position history; excluded from save/sync.\n"
    "\t\tdouble mM2PrevXD = 0.0, mM2PrevYD = 0.0;\n"
    "\t\tbool mM2HavePrev = false;"
)
INCLUDE_ANCHOR = '#include "Missle.h"'
INCLUDE_PATCH = '#include "Missle.h"\n#include "M2ObjectInterpolation.hpp"'
UPDATE_ANCHOR = (
    "\tM2Debug::Get().Updated(M2Debug::Missile);\n"
    "    if (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
    "        return;\n\n"
    "    UpdateCounters();"
)
UPDATE_PATCH = (
    "\tM2Debug::Get().Updated(M2Debug::Missile);\n"
    "    if (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
    "        return;\n\n"
    "    // Snapshot before the original 28ms gameplay update.\n"
    "    if (gEnhancedM2Enabled) {\n"
    "        mM2PrevXD = mXD;\n"
    "        mM2PrevYD = mYD;\n"
    "        mM2HavePrev = true;\n"
    "        // Avoid invoking this game/sound callback on every 60Hz redraw.\n"
    "        UpdateFishSongMgr();\n"
    "    } else {\n"
    "        mM2HavePrev = false;\n"
    "    }\n"
    "    UpdateCounters();"
)
DRAW_ANCHOR = (
    "\tM2Debug::DrawGuard m2Probe(M2Debug::Missile, this, mXD, mYD, m0x178);\n"
    "\tM2Debug::Get().ObjectMotion(M2Debug::Missile, this, mXD, mYD, "
    "0, 0, 0.0, mApp->mBoard && mApp->mBoard->mPause, false);\n"
    "    UpdateFishSongMgr();\n"
    "    bool doMirror ="
)
DRAW_PATCH = (
    "\tM2Debug::DrawGuard m2Probe(M2Debug::Missile, this, mXD, mYD, m0x178);\n"
    "    if (!gEnhancedM2Enabled)\n"
    "        UpdateFishSongMgr();\n"
    "    // Translation belongs to Graphics only. Missile state, hitboxes and\n"
    "    // save data retain the original simulation coordinates.\n"
    "    EnhancedM2::ScopedObjectTranslation<Graphics> m2VisualShift(\n"
    "        g, gEnhancedM2Enabled,\n"
    "        mApp->mBoard && mApp->mBoard->mPause,\n"
    "        mM2HavePrev, mM2PrevXD, mM2PrevYD,\n"
    "        mXD, mYD, mX, mY, gEnhancedM2Blend, 8.0);\n"
    "    M2Debug::Get().ObjectMotion(M2Debug::Missile, this, mXD, mYD,\n"
    "        m2VisualShift.ShiftX(), m2VisualShift.ShiftY(),\n"
    "        gEnhancedM2Blend, mApp->mBoard && mApp->mBoard->mPause,\n"
    "        mM2HavePrev);\n"
    "    bool doMirror ="
)

def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one audited anchor, found {count}")
    return source.replace(old, new, 1)

def patch(header: str, source: str) -> tuple[str, str]:
    if "mM2PrevXD" in header or "m2VisualShift" in source:
        raise RuntimeError("M2 missile smoothing appears already applied")
    header = replace_once(header, HEADER_ANCHOR, HEADER_PATCH, "Missle.h")
    source = replace_once(source, INCLUDE_ANCHOR, INCLUDE_PATCH, "Missle.cpp include")
    source = replace_once(source, UPDATE_ANCHOR, UPDATE_PATCH, "Missle::Update")
    source = replace_once(source, DRAW_ANCHOR, DRAW_PATCH, "Missle::Draw")
    return header, source

def main() -> int:
    header, source = GAME / "Missle.h", GAME / "Missle.cpp"
    required = GAME / "M2ObjectInterpolation.hpp"
    if not header.is_file() or not source.is_file() or not required.is_file():
        raise RuntimeError("Generated native missile files and interpolation header required")
    out_header, out_source = patch(
        header.read_text(encoding="utf-8-sig"),
        source.read_text(encoding="utf-8-sig"))
    header.write_text(out_header, encoding="utf-8", newline="\n")
    source.write_text(out_source, encoding="utf-8", newline="\n")
    print("[ok] M2 missiles: bounded draw-only interpolation; no simulation changes")
    print("[ok] M2 sound callbacks on original ticks; legacy draw path preserved")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        raise SystemExit(1)
