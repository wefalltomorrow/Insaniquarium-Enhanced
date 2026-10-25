#!/usr/bin/env python3
"""Add Escape to open/close the existing in-game Options pause menu.

Patch after the M2/game/debug updates. Hook SDL3's real key-down dispatch so
the shortcut works regardless of which child widget currently has focus.
No change to simulation, animation, save data or rendering.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"
FRAMEWORK = ROOT / "upstream/poplib/PopLib"


def patch(file: Path, before: str, after: str, description: str) -> None:
    src = file.read_text(encoding="utf-8-sig")
    count = src.count(before)
    if count != 1:
        raise RuntimeError(
            f"{description}: expected one anchor, found {count} in {file}"
        )
    file.write_text(src.replace(before, after, 1), encoding="utf-8", newline="\n")
    print("[ok]", description)


def main() -> None:
    game = GAME / "WinFishApp.cpp"
    engine = FRAMEWORK / "appbase.cpp"
    if not game.exists() or not engine.exists():
        raise RuntimeError("Portable game and PopLib source not generated")

    shutil.copyfile(ROOT / "m2/EscapePolicy.hpp",
                    GAME / "M2EscapePolicy.hpp")

    patch(game,
          '#include "WinFishApp.h"',
          '#include "WinFishApp.h"\n#include "M2EscapePolicy.hpp"',
          "include M2 escape-key decision policy")

    # A function implemented in the port's game module and linked from
    # PopLib's SDL3 event code, avoiding any framework/game header cycle.
    # Esc on the top Options dialog closes it (not "Back to Main Menu").
    # Esc during an active tank opens the same modal as the Options button.
    # All other dialogs, title screens and secondary views are unaffected.
    anchor = '''namespace PopLib
{
\tbool gUnkBool01 = false;'''
    handler = '''bool EnhancedM2HandleEscape(PopLib::AppBase* base)
{
    if (!base) return false;
    auto* app = static_cast<PopLib::WinFishApp*>(base);

    const bool hasDialog = !app->mDialogList.empty();
    const bool optionsTop = hasDialog &&
        app->mDialogList.back()->mId == PopLib::DIALOG_OPTIONS;

    const bool otherScreen = app->mTitleScreen ||
        app->mGameSelector || app->mStoreScreen ||
        app->mPetsScreen || app->mSimFishScreen ||
        app->mSimSetupScreen || app->mHatchScreen ||
        app->mInterludeScreen || app->mTankScreen ||
        app->mHelpScreen || app->mStoryScreen ||
        app->mBonusScreen || app->IsScreenSaver();

    const auto action = EnhancedM2::DecideEscape(
        app->mBoard != nullptr,
        app->mBoard && app->mBoard->mVisible,
        app->mBoard && app->mBoard->mPause,
        otherScreen, hasDialog, optionsTop);

    if (action == EnhancedM2::EscapeAction::CloseOptions) {
        // Cancel/discard unapplied fullscreen/checkbox edits. The existing
        // KillDialog logic restores focus and unpauses the board.
        app->KillDialog(PopLib::DIALOG_OPTIONS);
        return true;
    }
    if (action == EnhancedM2::EscapeAction::OpenOptions) {
        app->DoOptionsDialog(false);
        return true;
    }
    return false;
}

namespace PopLib
{
\tbool gUnkBool01 = false;'''
    patch(game, anchor, handler, "route Escape to the existing Options menu")

    patch(engine,
          '#include "m2_debug_trace.hpp"',
          '#include "m2_debug_trace.hpp"\n'
          '// The WinFish-specific Escape action is defined in the game module.\n'
          'extern bool EnhancedM2HandleEscape(PopLib::AppBase* app);',
          "declare game-owned Esc action in SDL3 event loop")

    before = '''\t\t\tif (isDown && mDebugKeysEnabled && DebugKeyDown(key))
\t\t\t\tbreak;'''
    after = '''\t\t\tif (isDown && key == SDLK_ESCAPE) {
\t\t\t\t// One key press = one toggle; holding Esc must not repeatedly
\t\t\t\t// open and close the pause menu or dismiss a second modal.
\t\t\t\tif (event.key.repeat) break;
\t\t\t\tif (EnhancedM2HandleEscape(this)) break;
\t\t\t}

\t\t\tif (isDown && mDebugKeysEnabled && DebugKeyDown(key))
\t\t\t\tbreak;'''
    patch(engine, before, after, "capture one SDL3 Escape key-down event")

    content = game.read_text(encoding="utf-8")
    assert "EnhancedM2HandleEscape" in content
    assert "app->DoOptionsDialog(false)" in content
    assert "app->KillDialog(PopLib::DIALOG_OPTIONS)" in content
    print("[ok] Escape opens/closes pause menu with repeat and modal safety")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, UnicodeError, AssertionError) as exc:
        print("[FAILED]", exc, file=sys.stderr)
        sys.exit(1)
