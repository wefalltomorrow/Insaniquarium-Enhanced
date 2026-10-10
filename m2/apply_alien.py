#!/usr/bin/env python3
"""Experimental draw-only alien movement interpolation (M2 only).

Runs on generated native port AFTER apply_coin_food.py. Keeps collision,
targeting, hitboxes, updates, sound logic and saved game coordinates at the
original 28ms simulation tick. Does not change stable M1.2 builds.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"

def change(file: Path, old: str, new: str, label: str) -> None:
    src = file.read_text(encoding="utf-8-sig")
    count = src.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source anchor, got {count}: {file}")
    file.write_text(src.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[ok] {label}")

def main() -> None:
    header = GAME / "Alien.h"
    source = GAME / "Alien.cpp"
    if not header.is_file() or not source.is_file():
        raise RuntimeError("Generated Alien.h/Alien.cpp are missing")
    if not (GAME / "M2ObjectInterpolation.hpp").is_file():
        raise RuntimeError("Coin/Food stage must copy M2ObjectInterpolation.hpp first")
    change(header, "\tclass Alien : public GameObject\n\t{\n\tpublic:",
           "\tclass Alien : public GameObject\n\t{\n\tpublic:\n"
           "\t\t// Visual-only coordinates, never saved or used by collision logic.\n"
           "\t\tdouble mM2PrevXD = 0.0, mM2PrevYD = 0.0;\n"
           "\t\tbool mM2HavePrev = false;",
           "add alien visual history")
    change(source, '#include "Alien.h"',
           '#include "Alien.h"\n#include "M2ObjectInterpolation.hpp"',
           "include scoped alien sprite interpolation")
    original = "\tGameObject::UpdateCounters();"
    replacement = (
        "\t// Only advance sound/game-related callbacks on 28ms simulation ticks.\n"
        "\tif (gEnhancedM2Enabled) {\n"
        "\t\tmM2PrevXD = mXD;\n"
        "\t\tmM2PrevYD = mYD;\n"
        "\t\tmM2HavePrev = true;\n"
        "\t\tUpdateFishSongMgr();\n"
        "\t} else {\n"
        "\t\tmM2HavePrev = false;\n"
        "\t}\n"
        + original
    )
    change(source, original, replacement, "sample alien position on sim tick")
    original = "\tUpdateFishSongMgr();\n\tif (mVX < 0.0)"
    replacement = (
        "\tif (!gEnhancedM2Enabled)\n"
        "\t\tUpdateFishSongMgr();\n"
        "\tEnhancedM2::ScopedObjectTranslation<Graphics> m2VisualShift(\n"
        "\t\tg, gEnhancedM2Enabled,\n"
        "\t\tmApp->mBoard && mApp->mBoard->mPause,\n"
        "\t\tmM2HavePrev, mM2PrevXD, mM2PrevYD,\n"
        "\t\tmXD, mYD, mX, mY, gEnhancedM2Blend);\n"
        "\tM2Debug::Get().ObjectMotion(M2Debug::Alien, this,\n"
        "\t\tmXD, mYD, m2VisualShift.ShiftX(), m2VisualShift.ShiftY(),\n"
        "\t\tgEnhancedM2Blend, mApp->mBoard && mApp->mBoard->mPause,\n"
        "\t\tmM2HavePrev);\n"
        "\tif (mVX < 0.0)"
    )
    change(source, original, replacement,
           "apply RAII alien sprite shift with pause/teleport guards")
    print("[ok] M2 alien draw interpolates without changing gameplay")

if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        raise SystemExit(1)
