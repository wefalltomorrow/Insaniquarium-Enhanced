#!/usr/bin/env python3
"""Attach read-only M2 debug probes after M2's guarded source patch.

No game-state writes, no new renderer, no ImGui dependency. The opt-in
recorder observes simulation, sprite draw calls, and object state.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
POPLIB = ROOT / "upstream/poplib/PopLib"
GAME = ROOT / "upstream/port/winfish"


def change(file: Path, old: str, new: str, description: str) -> None:
    text = file.read_text(encoding="utf-8-sig")
    hits = text.count(old)
    if hits != 1:
        raise RuntimeError(
            f"{description}: expected exactly one anchor, got {hits} in {file}"
        )
    file.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[ok] {description}")


def main() -> None:
    shared = ROOT / "m2/DebugTrace.hpp"
    for destination in (GAME / "M2DebugTrace.hpp", POPLIB / "m2_debug_trace.hpp"):
        if not destination.parent.is_dir():
            raise RuntimeError(f"Source checkout not generated: {destination.parent}")
        shutil.copyfile(shared, destination)

    app = POPLIB / "appbase.cpp"
    change(app, '#include "m2_frameclock.hpp"',
           '#include "m2_frameclock.hpp"\n#include "m2_debug_trace.hpp"',
           "include M2 debug recorder in the main loop")
    change(app,
           '\t\tauto plan = m2Clock.Advance(elapsed);\n'
           '\t\tgEnhancedM2Blend = plan.blend;',
           '\t\tauto plan = m2Clock.Advance(elapsed);\n'
           '\t\tgEnhancedM2Blend = plan.blend;\n'
           '\t\tif (M2Debug::Get().Active())\n'
           '\t\t\tM2Debug::Get().Begin(elapsed, plan.blend, plan.simulationTicks);',
           "inspect scheduler clock and interpolation blend")
    change(app,
           '\t\t\tif (!DoUpdateFrames()) break;\n'
           '\t\t\t++m2SimCount;',
           '\t\t\tif (!DoUpdateFrames()) break;\n'
           '\t\t\t++m2SimCount;\n'
           '\t\t\tM2Debug::Get().SimTick();',
           "count completed gameplay updates")
    change(app,
           '\t\t\tif (DrawDirtyStuff())\n'
           '\t\t\t\t++m2PresentCount;',
           '\t\t\tconst uint64_t renderStartNS = SDL_GetTicksNS();\n'
           '\t\t\tconst bool didPresent = DrawDirtyStuff();\n'
           '\t\t\tif (didPresent) ++m2PresentCount;\n'
           '\t\t\tif (M2Debug::Get().Active()) {\n'
           '\t\t\t\tconst double renderMs = double(SDL_GetTicksNS() - renderStartNS) / 1e6;\n'
           '\t\t\t\tM2Debug::Get().End(plan.simulationTicks, true, didPresent,\n'
           '\t\t\t\t\telapsed, renderMs, plan.blend);\n'
           '\t\t\t}',
           "record each actual display presentation and render duration")
    change(app,
           '\t\t\t\t\tm2SimCount / seconds, m2PresentCount / seconds);\n'
           '\t\t\t\tstd::fclose(log);',
           '\t\t\t\t\tm2SimCount / seconds, m2PresentCount / seconds);\n'
           '\t\t\t\tstd::fclose(log);\n'
           '\t\t\t\tif (M2Debug::Get().Active()) {\n'
           '\t\t\t\t\tM2Debug::Get().WindowTitle(m2SimCount / seconds, m2PresentCount / seconds);\n'
           '\t\t\t\t\tif (mSDLInterface && mSDLInterface->mWindow)\n'
           '\t\t\t\t\t\tSDL_SetWindowTitle(mSDLInterface->mWindow, M2Debug::Get().Title());\n'
           '\t\t\t\t}',
           "show game/display timing and warnings in titlebar")

    for name, kind, cel in (
        ("Fish.cpp", "Fish", "mAnimationFrameIndexFish"),
        ("Coin.cpp", "Coin", "mAnimationFrame"),
        ("Food.cpp", "Food", "m0x178"),
        ("Alien.cpp", "Alien", "mAnimIndex"),
    ):
        p = GAME / name
        classname = name[:-4]
        change(p, f'#include "{classname}.h"',
               f'#include "{classname}.h"\n#include "M2DebugTrace.hpp"',
               f"include debug recorder in {classname}")
        update_sig = ('void Fish::Update()\n{' if classname == "Fish"
                      else f'void PopLib::{classname}::Update()\n{{')
        # The SDL port converts the namespace from Sexy to PopLib.
        change(p, update_sig,
               update_sig + f'\n\tM2Debug::Get().Updated(M2Debug::{kind});',
               f"count {classname} simulation calls")
        draw_sig = ('void Fish::Draw(Graphics* g)\n{' if classname == "Fish"
                    else f'void PopLib::{classname}::Draw(Graphics* g)\n{{')
        visual_kind = ('(mType == TYPE_FISH_TYPE_PET ? M2Debug::FishPet : M2Debug::Fish)'
                       if classname == 'Fish' else 'M2Debug::' + kind)
        change(p, draw_sig, draw_sig +
               f'\n\tM2Debug::DrawGuard m2DrawGuard({visual_kind}, this, mXD, mYD, {cel});',
               f"record {classname} position, animation cel, and draw mutation")

    # Read-only probes for un-interpolated pets, missiles and shot effects.
    # FishTypePet inherits Fish::Draw and is already covered by fish drawing.
    for name, kind, x, y, cel, integer in (
        ("OtherTypePet", "OtherPet", "mXD", "mYD", "mAnimationIndex", False),
        ("Missle", "Missile", "mXD", "mYD", "m0x178", False),
        ("Shot", "ShotEffect", "mX", "mY", "m0x158", True),
    ):
        p = GAME / (name + ".cpp")
        change(p, '#include "' + name + '.h"',
               '#include "' + name + '.h"\n#include "M2DebugTrace.hpp"',
               "include extra debug probe in " + name)
        update = "void PopLib::" + name + "::Update()\n{"
        change(p, update, update +
               "\n\tM2Debug::Get().Updated(M2Debug::" + kind + ");",
               "count " + name + " simulation updates")
        draw = "void PopLib::" + name + "::Draw(Graphics* g)\n{"
        guard = "IntDrawGuard" if integer else "DrawGuard"
        change(p, draw, draw +
               "\n\tM2Debug::" + guard +
               " m2Probe(M2Debug::" + kind + ", this, " +
               x + ", " + y + ", " + cel + ");",
               "observe " + name + " rendering without changing gameplay")

    # Fish-type pets inherit Fish::Draw but have their own Update().
    # Count their simulation ticks independently from ordinary guppies.
    fish_pet = GAME / "FishTypePet.cpp"
    change(fish_pet, '#include "FishTypePet.h"',
           '#include "FishTypePet.h"\n#include "M2DebugTrace.hpp"',
           "include fish-type pet simulation probe")
    fish_pet_sig = "void PopLib::FishTypePet::Update()\n{"
    change(fish_pet, fish_pet_sig, fish_pet_sig +
           "\n\tM2Debug::Get().Updated(M2Debug::FishPet);",
           "count fish-type pet simulation calls")

    fish = GAME / "Fish.cpp"
    change(fish,
           '    g->Translate(m2DX, m2DY);\n    DrawFish(g, shouldFlip);',
           '    g->Translate(m2DX, m2DY);\n'
           '    if (gEnhancedM2Enabled && mM2HavePrev &&\n'
           '        !EnhancedM2::RenderablePosition(mXD, mYD))\n'
           '        M2Debug::Get().UnsafeFishPosition(this, mXD, mYD);\n'
           '    M2Debug::Get().RenderOffset(this, mXD, mYD,\n'
           '                                     m2DX, m2DY, gEnhancedM2Blend);\n'
           '    DrawFish(g, shouldFlip);',
           "trace visual interpolation separately from simulation coordinates")

    board = GAME / "Board.cpp"
    change(board, '#include "Board.h"',
           '#include "Board.h"\n#include "M2DebugTrace.hpp"',
           "include debug recorder in Board")
    change(board, 'void Board::Update()\n{',
           'void Board::Update()\n{\n\tM2Debug::Get().Updated(M2Debug::Board);',
           "count board simulation updates")
    change(board, 'void Board::Draw(Graphics* g)\n{',
           'void Board::Draw(Graphics* g)\n{\n\tM2Debug::Get().Drawn(M2Debug::Board, this, 0.0, 0.0, mGameUpdateCnt);',
           "count board draws vs simulation")

    graphics = POPLIB / "graphics/graphics.cpp"
    change(graphics, '#include "graphics.hpp"',
           '#include "graphics.hpp"\n#include "../m2_debug_trace.hpp"',
           "include graphics sprite probe")
    for sig, x, y, n in (
        ('void Graphics::DrawImageCel(Image *theImageStrip, int theX, int theY, int theCelCol, int theCelRow)\n{',
         "theX", "theY", "sprite cel at a point"),
        ('void Graphics::DrawImageCel(Image *theImageStrip, const Rect &theDestRect, int theCelCol, int theCelRow)\n{',
         "theDestRect.mX", "theDestRect.mY", "sprite cel in a destination rectangle"),
    ):
        new = (sig + '\n\tif (M2Debug::Get().Active() && theImageStrip)\n'
               '\t\tM2Debug::Get().SpriteCel(theImageStrip, theCelCol, theCelRow, '
               f'{x}, {y}, theImageStrip->mNumCols, theImageStrip->mNumRows, '
               'theImageStrip->mWidth, theImageStrip->mHeight, '
               'theImageStrip->mFilePath);')
        change(graphics, sig, new, f"trace {n}")
    print("[ok] M2 diagnostics are opt-in and do not modify game-state paths")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
