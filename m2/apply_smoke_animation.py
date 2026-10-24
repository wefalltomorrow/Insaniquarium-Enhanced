#!/usr/bin/env python3
"""Apply optional smoke cel crossfade after existing M2 position patches."""
from pathlib import Path
import sys
from apply_shot_interpolation import replace_once

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"
HEADER = "\t\tbool mM2HavePrevShot = false;"
UPDATE = "\t// Snapshot before the original 28ms shot update."
DRAW = "\tM2Debug::IntDrawGuard m2Probe(M2Debug::ShotEffect, this, mX, mY, m0x158);"
SYNC = "void PopLib::Shot::Sync(DataSync* theSync)\n{"

def patch(header: str, source: str) -> tuple[str, str]:
    if "mM2SmokeAnimation" in header or "DrawSmokeFrames" in source:
        raise RuntimeError("Smoke animation already applied")
    header = replace_once(header, '#include "GameObject.h"',
                          '#include "GameObject.h"\n#include "M2SmokeAnimation.hpp"\n#include "M2SmokePixels.hpp"\n#include "PopLib/graphics/memoryimage.hpp"', "Shot include")
    header = replace_once(header, HEADER, HEADER +
                          "\n\t\tEnhancedM2::SmokeAnimationHistory mM2SmokeAnimation;" +
                          "\n\t\tEnhancedM2::SmokePixelBuffer<PopLib::MemoryImage> mM2SmokePixels;", "Shot history")
    source = replace_once(source, UPDATE,
        "\t// Record only completed simulation animation state; no extra updates.\n"
        "\tmM2SmokeAnimation.Capture(gEnhancedM2Enabled && EnhancedM2::SmokeAnimationEnabled(),\n"
        "\t\tmShotType, m0x158, m0x15c, m0x164);\n" + UPDATE, "Shot update")
    source = replace_once(source, DRAW, DRAW +
        "\n\tconst bool m2SmokePaused = !mApp->mBoard || mApp->mBoard->mPause;\n"
        "\tif (m2SmokePaused || !gEnhancedM2Enabled) mM2SmokeAnimation.valid = false;", "Shot draw")
    # Reset presentation history for either serialization direction, without
    # adding bytes or changing any original Sync call.
    source = replace_once(source, SYNC, SYNC +
                          "\n\tmM2SmokeAnimation.valid = false;", "Shot sync")
    for image in ("IMAGE_SMOKETINY", "IMAGE_SMOKESMALL"):
        old = f"\t\tg->DrawImageCel({image}, 0, 0, m0x15c);"
        new = f"""\t\tauto m2SmokePlan = mM2SmokeAnimation.Plan(
\t\t\tgEnhancedM2Enabled && EnhancedM2::SmokeAnimationEnabled() &&
\t\t\tg->GetDrawMode() == Graphics::DRAWMODE_NORMAL &&
\t\t\tg->GetColor().mAlpha >= 0 && g->GetColor().mAlpha <= 255,
\t\t\tm2SmokePaused, mShotType, m0x158, m0x15c, m0x164,
\t\t\t{image}->mNumCols, {image}->mNumRows, gEnhancedM2Blend);
\t\tauto* m2SmokeImage = mM2SmokePixels.Prepare(
\t\t\tdynamic_cast<MemoryImage*>({image}), m2SmokePlan);
\t\tM2Debug::Get().SmokeAnimation(this, mShotType, m0x158, m0x15c,
\t\t\tm2SmokePlan.from, m2SmokePlan.to, m2SmokePlan.mix,
\t\t\tm2SmokePlan.transition, m2SmokePaused);
\t\tEnhancedM2::DrawSmokeFrames(g, {image}, m2SmokePlan, static_cast<Image*>(m2SmokeImage));"""
        source = replace_once(source, old, new, image)
    return header, source

def main():
    header, source = GAME / "Shot.h", GAME / "Shot.cpp"
    h, s = patch(header.read_text(encoding="utf-8-sig"), source.read_text(encoding="utf-8-sig"))
    helper = (ROOT / "m2/SmokeAnimation.hpp").read_text(encoding="utf-8")
    pixels = (ROOT / "m2/SmokePixels.hpp").read_text(encoding="utf-8").replace('"SmokeAnimation.hpp"', '"M2SmokeAnimation.hpp"')
    for path, text in [(header,h),(source,s),(GAME/"M2SmokeAnimation.hpp",helper),(GAME/"M2SmokePixels.hpp",pixels)]:
        path.write_text(text,encoding="utf-8",newline="\n")
    print("[ok] Optional smoke animation crossfade; original simulation and serialized fields preserved")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f"[FAILED] {exc}",file=sys.stderr)
        sys.exit(1)
