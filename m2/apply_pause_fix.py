#!/usr/bin/env python3
"""Prevent M2 render-only interpolation from oscillating behind pause dialogs.

Apply AFTER m2/apply.py and m2/apply_debug.py. Safe for the normal launcher.
Gameplay updates, widget updates, and UI rendering continue unchanged.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"


def patch(path: Path, old: str, new: str, name: str) -> None:
    src = path.read_text(encoding="utf-8-sig")
    count = src.count(old)
    if count != 1:
        raise RuntimeError(f"{name}: expected one occurrence, got {count}, in {path}")
    path.write_text(src.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[ok] {name}")


def main() -> None:
    fish = GAME / "Fish.cpp"
    board = GAME / "Board.cpp"
    if not fish.is_file() or not board.is_file():
        raise RuntimeError("Generated portable sources are not present")
    shutil.copyfile(ROOT / "m2/PauseInterpolation.hpp", GAME / "M2PauseInterpolation.hpp")

    patch(fish,
          '#include "M2DebugTrace.hpp"',
          '#include "M2DebugTrace.hpp"\n#include "M2PauseInterpolation.hpp"',
          "include independent pause guard")

    patch(fish,
          '''    int m2DX = 0, m2DY = 0;
    if (gEnhancedM2Enabled && mM2HavePrev &&
        std::abs(mXD - mM2PrevXD) < 48.0 &&''',
          '''    int m2DX = 0, m2DY = 0;
    // The application loop continues updating the Options UI while the
    // gameplay board is paused. Without a guard the interpolation alpha
    // keeps cycling between two old fish positions, making fish jitter.
    const bool m2GameplayPaused = mApp->mBoard && mApp->mBoard->mPause;
    EnhancedM2::InvalidateHistoryOnPause(
        gEnhancedM2Enabled, m2GameplayPaused, mM2HavePrev);
    if (EnhancedM2::CanInterpolate(
            gEnhancedM2Enabled, m2GameplayPaused, mM2HavePrev) &&
        std::abs(mXD - mM2PrevXD) < 48.0 &&''',
          "freeze fish rendering on paused simulation positions")

    # The moment a modal is opened/closed is useful for correlating frame
    # and sprite logs, but these diagnostic calls never advance gameplay.
    patch(board,
          'void PopLib::Board::PauseGame(bool shouldPause)\n{\n',
          '''void PopLib::Board::PauseGame(bool shouldPause)
{
    const bool m2WasPaused = mPause;
''',
          "observe board pause transitions")

    patch(board,
          '''\t}
}

void PopLib::Board::StartGame()
{''',
          '''\t}
    if (mPause != m2WasPaused)
        M2Debug::Get().PauseTransition(mPause);
}

void PopLib::Board::StartGame()
{''',
          "log tank-paused / tank-resumed state for diagnosing animations")

    src = fish.read_text(encoding="utf-8")
    assert "m2GameplayPaused" in src
    assert "InvalidateHistoryOnPause" in src
    assert "CanInterpolate" in src
    print("[ok] paused boards show stable fish positions at any display rate")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, AssertionError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
