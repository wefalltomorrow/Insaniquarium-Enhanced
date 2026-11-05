#!/usr/bin/env python3
"""Keep shot-effect sound/game callbacks on original 28ms ticks in M2.

The pinned WinFish Shot::Draw invokes GameObject::UpdateFishSongMgr().
M2 renders at ~60Hz while updates run at ~35.7Hz, so repeated draws
must not run this callback. Non-M2 behaviour is intentionally unchanged.
Runs after apply_debug.py, including its shot motion probe.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish/Shot.cpp"

UPDATE = (
    "void PopLib::Shot::Update()\n"
    "{\n"
    "\tM2Debug::Get().Updated(M2Debug::ShotEffect);\n"
    "\tif (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
    "\t\treturn;\n\n"
    "\tGameObject::UpdateCounters();"
)
UPDATE_FIXED = (
    'extern "C" bool gEnhancedM2Enabled;\n\n'
    "void PopLib::Shot::Update()\n"
    "{\n"
    "\tM2Debug::Get().Updated(M2Debug::ShotEffect);\n"
    "\tif (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
    "\t\treturn;\n\n"
    "\t// Original sound/game callback must not run on M2 redraws.\n"
    "\tif (gEnhancedM2Enabled)\n"
    "\t\tGameObject::UpdateFishSongMgr();\n"
    "\tGameObject::UpdateCounters();"
)
DRAW = (
    "void PopLib::Shot::Draw(Graphics* g)\n"
    "{\n"
    "\tM2Debug::IntDrawGuard m2Probe(M2Debug::ShotEffect, this, mX, mY, m0x158);\n"
    "\tM2Debug::Get().ObjectMotion(M2Debug::ShotEffect, this, mX, mY, "
    "0, 0, 0.0, mApp->mBoard && mApp->mBoard->mPause, false);\n"
    "\tGameObject::UpdateFishSongMgr();"
)
DRAW_FIXED = DRAW.replace(
    "\tGameObject::UpdateFishSongMgr();",
    "\tif (!gEnhancedM2Enabled)\n"
    "\t\tGameObject::UpdateFishSongMgr();"
)


def patch(source: str) -> str:
    if source.count(UPDATE) != 1 or source.count(DRAW) != 1:
        raise RuntimeError("Expected exactly one audited Shot update/draw pair")
    if "extern \"C\" bool gEnhancedM2Enabled;" in source:
        raise RuntimeError("Shot M2 callback patch appears to be present already")
    if source.count("GameObject::UpdateFishSongMgr();") != 1:
        raise RuntimeError("Unexpected additional shot callbacks; re-audit upstream")
    result = source.replace(UPDATE, UPDATE_FIXED, 1).replace(DRAW, DRAW_FIXED, 1)
    if result.count("GameObject::UpdateFishSongMgr();") != 2:
        raise RuntimeError("Shot callback count after patch is incorrect")
    return result


def main() -> int:
    if not GAME.is_file():
        raise RuntimeError("Generated native Shot.cpp missing")
    source = GAME.read_text(encoding="utf-8-sig")
    GAME.write_text(patch(source), encoding="utf-8", newline="\n")
    print("[ok] Shot callback runs on the original simulation tick in M2")
    print("[ok] Non-M2 shot drawing and all gameplay positions preserved")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, RuntimeError) as exc:
        print("[FAILED] {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
