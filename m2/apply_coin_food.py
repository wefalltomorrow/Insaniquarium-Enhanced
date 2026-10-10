#!/usr/bin/env python3
"""Guarded opt-in render-only Coin and Food interpolation.

Apply after m2/apply.py, m2/apply_debug.py and m2/apply_pause_fix.py to
the generated disposable native source. Original WinFish source untouched.
"""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"

def change(path: Path, old: str, new: str, label: str) -> None:
    src = path.read_text(encoding="utf-8-sig")
    count = src.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, got {count}, in {path}")
    path.write_text(src.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[ok] {label}")

def main() -> None:
    if not (GAME / "Coin.cpp").is_file() or not (GAME / "Food.cpp").is_file():
        raise RuntimeError("Generated native port sources missing")
    shutil.copyfile(ROOT / "m2/ObjectInterpolation.hpp",
                    GAME / "M2ObjectInterpolation.hpp")
    shutil.copyfile(ROOT / "m2/RenderCoordinates.hpp",
                    GAME / "RenderCoordinates.hpp")
    shutil.copyfile(ROOT / "m2/PauseInterpolation.hpp",
                    GAME / "PauseInterpolation.hpp")

    for obj in ("Coin", "Food"):
        header = GAME / f"{obj}.h"
        source = GAME / f"{obj}.cpp"
        change(header, f"\tclass {obj} : public GameObject\n\t{{\n\tpublic:",
            f"\tclass {obj} : public GameObject\n\t{{\n\tpublic:\n"
            "\t\t// M2 visual history (not used for simulation or saves).\n"
            "\t\tdouble mM2PrevXD = 0.0, mM2PrevYD = 0.0;\n"
            "\t\tbool mM2HavePrev = false;",
            f"add {obj} render-only visual history")
        change(source, f'#include "{obj}.h"',
            f'#include "{obj}.h"\n#include "M2ObjectInterpolation.hpp"',
            f"include {obj} scoped render shift")

        original = (
            f"void PopLib::{obj}::Update()\n{{\n"
            f"\tM2Debug::Get().Updated(M2Debug::{obj});\n"
            "\tif (!mApp->mBoard || mApp->mBoard->mPause)\n"
            "\t\treturn;\n\n"
        )
        music = ("\t\tGameObject::UpdateFishSongMgr();\n" if obj == "Coin"
                 else "\t\tUpdateFishSongMgr();\n")
        update = (
            "\t// No sound/game callbacks from 60Hz presentation redraws.\n"
            "\tif (gEnhancedM2Enabled) {\n"
            "\t\tmM2PrevXD = mXD;\n"
            "\t\tmM2PrevYD = mYD;\n"
            "\t\tmM2HavePrev = true;\n"
            + music +
            "\t} else {\n"
            "\t\tmM2HavePrev = false;\n"
            "\t}\n"
        )
        change(source, original, original + update,
               f"sample {obj} before original 28ms simulation tick")
        draw_music = ("\tGameObject::UpdateFishSongMgr();" if obj == "Coin"
                      else "\tUpdateFishSongMgr();")
        next_line = ("\n\n\tint aVal = m0x19c % 8;" if obj == "Coin"
                     else "\n\tif (m0x180 != 0)")
        scope = (
            "\tif (!gEnhancedM2Enabled)\n"
            "\t\t" + draw_music.strip() + "\n"
            "\tEnhancedM2::ScopedObjectTranslation<Graphics> m2VisualShift(\n"
            "\t\tg, gEnhancedM2Enabled,\n"
            "\t\tmApp->mBoard && mApp->mBoard->mPause,\n"
            "\t\tmM2HavePrev, mM2PrevXD, mM2PrevYD,\n"
            "\t\tmXD, mYD, mX, mY, gEnhancedM2Blend,\n"
            "\t\t" + ("m0x198 ? 96.0 : 48.0" if obj == "Coin" else "48.0") + ");\n"
            "\tM2Debug::Get().ObjectMotion(M2Debug::" + obj + ", this,\n"
            "\t\tmXD, mYD, m2VisualShift.ShiftX(), m2VisualShift.ShiftY(),\n"
            "\t\tgEnhancedM2Blend, mApp->mBoard && mApp->mBoard->mPause,\n"
            "\t\tmM2HavePrev);"
        )
        change(source, draw_music + next_line, scope + next_line,
               f"translate {obj} sprite with automatic early-return restoration")
        assert "ScopedObjectTranslation<Graphics> m2VisualShift" in source.read_text(encoding="utf-8")
    print("[ok] experimental coin and food render-only interpolation patched")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, UnicodeError, AssertionError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
