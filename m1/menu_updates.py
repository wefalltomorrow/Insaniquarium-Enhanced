#!/usr/bin/env python3
"""Apply M1 Windows Options menu changes to the port-generated WinFish C++.

Runs after SaMeiers' compatibility/port feature scripts. Source changes are
checked against expected upstream text so changed upstream releases fail
loudly rather than silently omit a requested UI change.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
OPTIONS = ROOT / "upstream" / "port" / "winfish" / "OptionsDialog.cpp"
RELEASES = "https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases"


def change_one(src: str, old: str, new: str, description: str) -> str:
    if src.count(old) != 1:
        raise RuntimeError(f"{description}: expected one match, got {src.count(old)}")
    print(f"[ok] {description}")
    return src.replace(old, new, 1)


def main() -> int:
    if not OPTIONS.is_file():
        raise RuntimeError(f"Generated OptionsDialog.cpp missing: {OPTIONS}")
    data = OPTIONS.read_text(encoding="utf-8-sig")

    # Keep the legacy widget allocated: the original source still owns it in
    # AddedToManager/RemovedFromManager/destructor. It must never be visible.
    data = change_one(
        data,
        'mRegisterButton = MakeDialogButton(0, this, "Register", NULL);',
        'mRegisterButton = MakeDialogButton(0, this, "Register", NULL);\n'
        '\tmRegisterButton->SetVisible(false);',
        "hide obsolete Register button",
    )

    # A direct link opens the project's current releases in the browser;
    # do NOT invoke PopCap's obsolete update-check service.
    data = change_one(
        data,
        "mApp->DoUpdateCheckDialog();",
        f'mApp->OpenURL("{RELEASES}");',
        "route Check Updates to Enhanced GitHub releases",
    )

    # The SDL3 port abbreviated Hardware Acceleration to HA because it
    # overlaps Auto Collect when both are arranged in a two-column row.
    # Put Auto Collect on a dedicated third row instead.
    data = change_one(
        data,
        'g->DrawString("HA", m3DCB',
        'g->DrawString("Hardware Acceleration", m3DCB',
        "restore full Hardware Acceleration label",
    )
    data = change_one(
        data,
        'mAutoCollectCB->Resize(mX + 161, mY + 172, 45, 46);',
        'mAutoCollectCB->Resize(mX + 33, mY + 216, 45, 46);',
        "move Auto Collect below Hardware Acceleration",
    )

    # Register disappearing removes a 34px row from GetPreferredHeight().
    # Preserve the previous dialog dimensions, leaving room for the added
    # dedicated checkbox row without pushing it into the action buttons.
    data = change_one(
        data, "int aPrefHght = 362;", "int aPrefHght = 396;",
        "preserve dialog vertical space in gameplay",
    )
    data = change_one(
        data, "aPrefHght = 328;", "aPrefHght = 362;",
        "preserve dialog vertical space on main menu",
    )

    # Verify we edited the generated port output (not pristine WinFish).
    for required in (
        "mAutoCollectCB->Resize(mX + 33, mY + 216, 45, 46);",
        'g->DrawString("Hardware Acceleration", m3DCB',
        f'mApp->OpenURL("{RELEASES}");',
        'mRegisterButton->SetVisible(false);',
    ):
        if required not in data:
            raise RuntimeError(f"Required generated menu change absent: {required}")
    OPTIONS.write_text(data, encoding="utf-8", newline="\n")
    print("[ok] M1 Options menu changes verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        raise SystemExit(1)
