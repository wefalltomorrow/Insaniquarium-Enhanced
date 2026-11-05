#!/usr/bin/env python3
"""Give fish-type pets the same M2 draw-only history as ordinary Fish.

FishTypePet overrides Fish::Update, but inherits Fish::Draw. The M2 visual
history and once-per-tick sound callback in Fish::Update are otherwise never
executed for fish-type pets. Gameplay, AI, collision and saves stay unchanged.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"

ANCHOR = (
    "void PopLib::FishTypePet::Update()\n"
    "{\n"
    "\tM2Debug::Get().Updated(M2Debug::FishPet);\n"
    "\tif (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
    "\t\treturn;\n\n"
    "\tGameObject::UpdateCounters();"
)
REPLACEMENT = (
    'extern "C" bool gEnhancedM2Enabled;\n\n'
    "void PopLib::FishTypePet::Update()\n"
    "{\n"
    "\tM2Debug::Get().Updated(M2Debug::FishPet);\n"
    "\tif (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n"
    "\t\treturn;\n\n"
    "\t// FishTypePet bypasses Fish::Update but inherits its 60Hz Draw path.\n"
    "\t// Sample previous position and run the sound/game callback ONCE per\n"
    "\t// original 28ms simulation tick, never during repeated M2 redraws.\n"
    "\tif (gEnhancedM2Enabled) {\n"
    "\t\tmM2PrevXD = mXD;\n"
    "\t\tmM2PrevYD = mYD;\n"
    "\t\tmM2HavePrev = true;\n"
    "\t\tUpdateFishSongMgr();\n"
    "\t} else {\n"
    "\t\tmM2HavePrev = false;\n"
    "\t}\n"
    "\tGameObject::UpdateCounters();"
)

def patch(text: str) -> str:
    count = text.count(ANCHOR)
    if count != 1:
        raise RuntimeError("Expected exactly one FishTypePet::Update source anchor; got {}".format(count))
    return text.replace(ANCHOR, REPLACEMENT, 1)

def main() -> None:
    path = GAME / "FishTypePet.cpp"
    if not path.is_file():
        raise RuntimeError("Generated FishTypePet.cpp is missing")
    original = path.read_text(encoding="utf-8-sig")
    updated = patch(original)
    path.write_text(updated, encoding="utf-8", newline="\n")
    print("[ok] Fish-type pet 28ms history + sound callback; render/gameplay coordinates unchanged")

if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as exc:
        print("[FAILED] {}".format(exc), file=sys.stderr)
        raise SystemExit(1)
