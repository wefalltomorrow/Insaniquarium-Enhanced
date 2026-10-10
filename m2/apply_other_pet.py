#!/usr/bin/env python3
"""Render-only M2 interpolation for OtherTypePet (Stinky, Clyde, etc.).

Run after apply_debug.py and apply_coin_food.py. Keep gameplay positions,
click hitboxes, movement, AI, sound updates, saves and non-M2 mode unchanged.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"

def replace_one(source: str, original: str, replacement: str, name: str) -> str:
    count = source.count(original)
    if count != 1:
        raise RuntimeError("{}: expected one native source anchor, found {}".format(name, count))
    return source.replace(original, replacement, 1)

def patch_header(source: str) -> str:
    if "mM2HavePrev = false;" in source or "mM2PrevXD = " in source:
        raise RuntimeError("other-pet visual history is already patched")
    return replace_one(
        source,
        "\tclass OtherTypePet : public GameObject\n\t{\n\tpublic:",
        "\tclass OtherTypePet : public GameObject\n\t{\n\tpublic:\n"
        "\t\t// M2 visual-only history; never read by gameplay or Sync().\n"
        "\t\tdouble mM2PrevXD = 0.0, mM2PrevYD = 0.0;\n"
        "\t\tbool mM2HavePrev = false;",
        "other-pet visual history")

def patch_source(source: str) -> str:
    source = replace_one(source,
        '#include "OtherTypePet.h"',
        '#include "OtherTypePet.h"\n#include "M2ObjectInterpolation.hpp"',
        "other-pet scoped draw includes")

    update = (
        "void PopLib::OtherTypePet::Update()\n"
        "{\n"
        "\tM2Debug::Get().Updated(M2Debug::OtherPet);\n"
        "\tif (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
        "\t\treturn;\n\n"
        "\tUpdateCounters();"
    )
    sampled = (
        "void PopLib::OtherTypePet::Update()\n"
        "{\n"
        "\tM2Debug::Get().Updated(M2Debug::OtherPet);\n"
        "\tif (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
        "\t\treturn;\n\n"
        "\t// Original simulation rate stays 28ms; only visual history is new.\n"
        "\tif (gEnhancedM2Enabled) {\n"
        "\t\tmM2PrevXD = mXD;\n"
        "\t\tmM2PrevYD = mYD;\n"
        "\t\tmM2HavePrev = true;\n"
        "\t\tUpdateFishSongMgr();\n"
        "\t} else {\n"
        "\t\tmM2HavePrev = false;\n"
        "\t}\n"
        "\tUpdateCounters();"
    )
    source = replace_one(source, update, sampled, "other-pet sim tick sampling")
    draw = (
        "void PopLib::OtherTypePet::Draw(Graphics* g)\n"
        "{\n"
        "\tM2Debug::DrawGuard m2Probe(M2Debug::OtherPet, this, mXD, mYD, mAnimationIndex);\n"
        "\tUpdateFishSongMgr();"
    )
    smooth = (
        "void PopLib::OtherTypePet::Draw(Graphics* g)\n"
        "{\n"
        "\tM2Debug::DrawGuard m2Probe(M2Debug::OtherPet, this, mXD, mYD, mAnimationIndex);\n"
        "\tif (!gEnhancedM2Enabled)\n"
        "\t\tUpdateFishSongMgr();\n"
        "\t// Translate graphics only; on-screen motion must never move hitboxes.\n"
        "\tEnhancedM2::ScopedObjectTranslation<Graphics> m2VisualShift(\n"
        "\t\tg, gEnhancedM2Enabled,\n"
        "\t\tmApp->mBoard && mApp->mBoard->mPause,\n"
        "\t\tmM2HavePrev, mM2PrevXD, mM2PrevYD,\n"
        "\t\tmXD, mYD, mX, mY, gEnhancedM2Blend);\n"
        "\tM2Debug::Get().ObjectMotion(M2Debug::OtherPet, this,\n"
        "\t\tmXD, mYD, m2VisualShift.ShiftX(), m2VisualShift.ShiftY(),\n"
        "\t\tgEnhancedM2Blend, mApp->mBoard && mApp->mBoard->mPause,\n"
        "\t\tmM2HavePrev);"
    )
    return replace_one(source, draw, smooth, "other-pet guarded render shift")

def main() -> None:
    header = GAME / "OtherTypePet.h"
    source = GAME / "OtherTypePet.cpp"
    if not header.is_file() or not source.is_file():
        raise RuntimeError("Generated other-pet source files missing")
    if not (GAME / "M2ObjectInterpolation.hpp").is_file():
        raise RuntimeError("M2ObjectInterpolation.hpp missing; run coin/food stage first")
    updated_header = patch_header(header.read_text(encoding="utf-8-sig"))
    updated_source = patch_source(source.read_text(encoding="utf-8-sig"))
    header.write_text(updated_header, encoding="utf-8", newline="\n")
    source.write_text(updated_source, encoding="utf-8", newline="\n")
    print("[ok] OtherTypePet visuals smoothed; original sim/click/saves unchanged")

if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as exc:
        print("[FAILED] {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
