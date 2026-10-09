#!/usr/bin/env python3
"""Install Insaniquarium Enhanced's async GitHub updater into generated M1 C++.

Source/version patches are checked, and changes only affect the temporary
port/winfish tree built by GitHub Actions. No PopCap update service is called.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream" / "port" / "winfish"
HERE = ROOT / "m1"
RELEASES = "https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases"


def change_one(data: str, before: str, after: str, label: str) -> str:
    n = data.count(before)
    if n != 1:
        raise ValueError(f"{label}: expected exactly one anchor, got {n}")
    print(f"[ok] {label}")
    return data.replace(before, after, 1)


def patch(name: str, changes: list[tuple[str, str, str]]) -> None:
    path = GAME / name
    text = path.read_text(encoding="utf-8-sig")
    for old, new, label in changes:
        text = change_one(text, old, new, label)
    path.write_text(text, encoding="utf-8", newline="\n")


def main(tag: str) -> None:
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+-[A-Za-z0-9-]+", tag):
        raise ValueError(f"Release tag not a supported version: {tag}")
    if not GAME.is_dir():
        raise ValueError("The portable game source hasn't been generated yet")

    for name in ("EnhancedUpdater.h", "EnhancedUpdater.cpp"):
        shutil.copyfile(HERE / name, GAME / name)
        print(f"[ok] Added {name}")

    # The updater embeds the exact release tag of this executable, not a
    # downloaded version file or a mutable GitHub branch name.
    (GAME / "EnhancedUpdaterVersion.h").write_text(
        "#pragma once\n"
        f'#define ENHANCED_VERSION_TAG "{tag}"\n',
        encoding="ascii",
    )
    print(f"[ok] Embedded release version {tag}")

    patch("OptionsDialog.cpp", [
        ('#include "OptionsDialog.h"',
         '#include "EnhancedUpdater.h"\n#include "OptionsDialog.h"',
         "include updater entry point"),
        (f'mApp->OpenURL("{RELEASES}");',
         'EnhancedUpdater::Start(mApp);',
         "replace direct Releases link with asynchronous version check"),
    ])

    # Intercept ONLY the new updater's Download/Cancel clicks, leaving the
    # original dialog manager's callbacks and game controls unchanged.
    patch("WinFishApp.cpp", [
        ('#include "WinFishApp.h"',
         '#include "EnhancedUpdater.h"\n#include "WinFishApp.h"',
         "include update polling and download handlers"),
        ('void PopLib::WinFishApp::ButtonDepress(int theId)\n{\n',
         'void PopLib::WinFishApp::ButtonDepress(int theId)\n{\n'
         '    if (theId == 2091) { // Yes / Download in Enhanced Update dialog\n'
         '        KillDialog(91);\n'
         '        EnhancedUpdater::Download(this);\n'
         '        return;\n'
         '    }\n'
         '    if (theId == 2090) { // Cancel the "Checking..." dialog\n'
         '        KillDialog(90);\n'
         '        return;\n'
         '    }\n'
         '    if (theId == 2092 || theId == 2093) { // Error / Up-to-date OK\n'
         '        KillDialog(theId - 2000);\n'
         '        return;\n'
         '    }\n',
         "route Download/Cancel decisions"),
        ('void PopLib::WinFishApp::UpdateFrames()\n{\n',
         'void PopLib::WinFishApp::UpdateFrames()\n{\n'
         '    EnhancedUpdater::Pump(this);\n',
         "poll the HTTPS worker without blocking simulation"),
    ])

    body = (GAME / "WinFishApp.cpp").read_text(encoding="utf-8")
    option = (GAME / "OptionsDialog.cpp").read_text(encoding="utf-8")
    assert "EnhancedUpdater::Pump(this);" in body
    assert "EnhancedUpdater::Start(mApp);" in option
    assert f'mApp->OpenURL("{RELEASES}");' not in option
    print("[ok] Enhanced in-game update flow patched and verified")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("tag", help="Installed build tag, e.g. v0.2.2-m1-update")
        args = parser.parse_args()
        main(args.tag)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
