#!/usr/bin/env python3
"""Guarded experimental 60 Hz presentation with original 28 ms game ticks.

Applies only to CI's throwaway source checkout. Default gameplay is unchanged.
Set INSANIQUARIUM_M2_60FPS=1 for the experiment.

This is a *first gameplay test*: fish receive render-only positional
interpolation; other effects/objects still have their original tick cadence.
Never claim that all animations have been interpolated.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
POPLIB = ROOT / "upstream/poplib/PopLib"
GAME = ROOT / "upstream/port/winfish"

def change(path: Path, original: str, replacement: str, name: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    count = text.count(original)
    if count != 1:
        raise RuntimeError(f"{name}: expected one match, found {count} in {path.name}")
    path.write_text(text.replace(original, replacement, 1), encoding="utf-8", newline="\n")
    print(f"[ok] {name}")

def main() -> None:
    if not (GAME / "Fish.cpp").is_file() or not (POPLIB / "appbase.cpp").is_file():
        raise RuntimeError("Run the port source generator before M2 patches.")

    shutil.copyfile(ROOT / "m2/FrameClock.hpp", POPLIB / "m2_frameclock.hpp")

    app = POPLIB / "appbase.cpp"
    change(app, '#include "appbase.hpp"', '#include "appbase.hpp"\n#include "m2_frameclock.hpp"\n#include <cstdio>', "include independent scheduler")

    change(app,
        'AppBase *PopLib::gAppBase = nullptr;',
        '''AppBase *PopLib::gAppBase = nullptr;

// Shared, render-only state. Fish Draw() may read these, but game simulation
// continues using its untouched mX/mY and mXD/mYD coordinates.
extern "C" {
bool gEnhancedM2Enabled = false;
double gEnhancedM2Blend = 1.0;
}''',
        "export isolated render interpolation state")

    old = '''\tif (mLoadingFailed)
\t\tShutdown();

\tbool isVSynched'''
    new = '''\tif (mLoadingFailed)
\t\tShutdown();

\t// M2 experimental path. The original PopLib vsync-update mode must NOT
\t// be used here: it calls DoUpdateFrames on every presentation frame,
\t// causing approximately 1.7x-speed gameplay on 60 Hz monitors.
\tstatic const bool m2Requested = [] {
\t\tconst char* value = SDL_getenv("INSANIQUARIUM_M2_60FPS");
\t\treturn value != nullptr && value[0] == '1' && value[1] == '\\0';
\t}();
\tstatic bool m2Started = false;
\tstatic uint64_t m2PreviousNS = 0;
\tstatic uint64_t m2StatsStartNS = 0;
\tstatic unsigned m2SimCount = 0, m2PresentCount = 0;
\tstatic EnhancedM2::FrameClock m2Clock;

\tbool m2CanRun = m2Requested && mLoaded && !mShutdown &&
\t\t(!mLoadingThreadStarted || mLoadingThreadCompleted) &&
\t\t!mPaused && !mMinimized && !mStepMode && !gScreenSaverActive &&
\t\tmUpdateMultiplier == 1.0 &&
\t\tmWidgetManager != nullptr && mSDLInterface != nullptr;
\tif (m2CanRun) {
\t\tuint64_t now = SDL_GetTicksNS();
\t\tif (!m2Started) {
\t\t\tm2Clock.Reset();
\t\t\tm2PreviousNS = now;
\t\t\tm2StatsStartNS = now;
\t\t\tm2SimCount = m2PresentCount = 0;
\t\t\tm2Started = true;
\t\t}
\t\tgEnhancedM2Enabled = true;
\t\tdouble elapsed = static_cast<double>(now - m2PreviousNS) / 1000000.0;
\t\tm2PreviousNS = now;
\t\tauto plan = m2Clock.Advance(elapsed);
\t\tgEnhancedM2Blend = plan.blend;

\t\t// The ONLY location that advances gameplay. Maximum 3 catch-up ticks
\t\t// prevent unbounded fast-forward after a stall or breakpoint.
\t\tfor (int i = 0; i < plan.simulationTicks && !mShutdown; ++i) {
\t\t\tif (!DoUpdateFrames()) break;
\t\t\t++m2SimCount;
\t\t\tProcessSafeDeleteList();
\t\t}
\t\tif (plan.present && !mShutdown) {
\t\t\t// Full redraw is intentionally provisional. Fish interpolation is
\t\t\t// isolated to rendering, with gameplay co-ordinates unchanged.
\t\t\tmWidgetManager->MarkAllDirty();
\t\t\tmHasPendingDraw = true;
\t\t\tif (DrawDirtyStuff())
\t\t\t\t++m2PresentCount;
\t\t}
\t\tif (now - m2StatsStartNS >= 5000000000ULL) {
\t\t\tdouble seconds = static_cast<double>(now - m2StatsStartNS) / 1e9;
\t\t\tFILE* log = std::fopen("M2Timing.log", "a");
\t\t\tif (log != nullptr) {
\t\t\t\tstd::fprintf(log, "sim=%.2f Hz, present=%.2f Hz, mode=M2 experimental\\n",
\t\t\t\t\tm2SimCount / seconds, m2PresentCount / seconds);
\t\t\t\tstd::fclose(log);
\t\t\t}
\t\t\tm2StatsStartNS = now;
\t\t\tm2SimCount = m2PresentCount = 0;
\t\t}
\t\tmUpdateAppState = UPDATESTATE_PROCESS_DONE;
\t\t// Don't spin at 100% CPU while waiting for the next deadline.
\t\tif (!plan.present && plan.simulationTicks == 0 && allowSleep)
\t\t\tSDL_Delay(1);
\t\treturn true;
\t}
\tif (m2Requested) {
\t\tm2Started = false;
\t\tgEnhancedM2Enabled = false;
\t\tgEnhancedM2Blend = 1.0;
\t}

\tbool isVSynched'''
    change(app,old,new,"separate fixed-tick simulation from 60 Hz presentation")

    fishh = GAME / "Fish.h"
    change(fishh,
        '\tclass Fish : public GameObject\n\t{\n\tpublic:',
        '''\tclass Fish : public GameObject
\t{
\tpublic:
\t\t// M2 visual history; these fields are never used for simulation/saves.
\t\tdouble mM2PrevXD = 0.0, mM2PrevYD = 0.0;
\t\tbool mM2HavePrev = false;''',
        "add render-only fish previous position")

    fish = GAME / "Fish.cpp"
    change(fish, '#include "Fish.h"',
        '''#include "Fish.h"
#include <cmath>
extern "C" bool gEnhancedM2Enabled;
extern "C" double gEnhancedM2Blend;''',
        "include interpolation symbols")

    change(fish,
        '''    if (mApp->mBoard == NULL || mApp->mBoard->mPause)
        return;
    Board* aBoard = mApp->mBoard;''',
        '''    if (mApp->mBoard == NULL || mApp->mBoard->mPause)
        return;
    if (gEnhancedM2Enabled) {
        mM2PrevXD = mXD;
        mM2PrevYD = mYD;
        mM2HavePrev = true;
        // Originally called during Fish::Draw; avoid running sound/game
        // logic twice when there are more presentations than sim ticks.
        UpdateFishSongMgr();
    }
    Board* aBoard = mApp->mBoard;''',
        "sample previous fish position once per simulation tick")

    change(fish,
        '''void Fish::Draw(Graphics* g)
{
    UpdateFishSongMgr();''',
        '''void Fish::Draw(Graphics* g)
{
    if (!gEnhancedM2Enabled)
        UpdateFishSongMgr();''',
        "avoid extra music/game updates during interpolation redraws")

    change(fish,
        '''    DrawFish(g, shouldFlip);

    if (mName.size() > 0)
        DrawName(g, false);''',
        '''    int m2DX = 0, m2DY = 0;
    if (gEnhancedM2Enabled && mM2HavePrev &&
        std::abs(mXD - mM2PrevXD) < 48.0 &&
        std::abs(mYD - mM2PrevYD) < 48.0)
    {
        // Graphics is already translated to the fixed simulation mX/mY.
        // Offset only its drawing transform; clicks/collision/saves stay
        // entirely on the original 28 ms positions.
        double rx = mM2PrevXD + (mXD - mM2PrevXD) * gEnhancedM2Blend;
        double ry = mM2PrevYD + (mYD - mM2PrevYD) * gEnhancedM2Blend;
        m2DX = static_cast<int>(std::lround(rx)) - mX;
        m2DY = static_cast<int>(std::lround(ry)) - mY;
    }
    g->Translate(m2DX, m2DY);
    DrawFish(g, shouldFlip);

    if (mName.size() > 0)
        DrawName(g, false);
    g->Translate(-m2DX, -m2DY);''',
        "interpolate fish sprite drawing only")

    change(fish,
        '''    mX = newX;
    mXD = newX;
    mY = newY;
    mYD = newY;''',
        '''    mX = newX;
    mXD = newX;
    mY = newY;
    mYD = newY;
    // Teleports/spawns must not interpolate from an unrelated old position.
    mM2HavePrev = false;''',
        "reset visual history on fish teleport")

    board = GAME / "Board.cpp"
    change(board, '#include "Board.h"',
        '''#include "Board.h"
extern "C" bool gEnhancedM2Enabled;''',
        "declare visual-mode guard in board")

    change(board,
        '''\tif (mAlienTimer == 225)
\t\tPlaySample(SOUND_SONAR_ID, 3, 1.0);''',
        '''\tif (mAlienTimer == 225)
\t{
\t\t// Vanilla played sonar from Draw(); duplicate draws on M2 must not
\t\t// duplicate the audio for the same simulation update.
\t\tstatic Board* lastBoard = nullptr;
\t\tstatic int lastUpdate = -1;
\t\tif (!gEnhancedM2Enabled || lastBoard != this || lastUpdate != mGameUpdateCnt) {
\t\t\tlastBoard = this;
\t\t\tlastUpdate = mGameUpdateCnt;
\t\t\tPlaySample(SOUND_SONAR_ID, 3, 1.0);
\t\t}
\t}''',
        "guard sonar sound from duplicate redraw")

    print("[ok] M2 opt-in simulation/presentation paths patched")
    
if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
