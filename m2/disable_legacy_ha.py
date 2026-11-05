#!/usr/bin/env python3
"""Remove obsolete hardware-acceleration UI and disable unsafe SDL3 mode resets.

Runs after the M1 menu and updater patches and before the M2 timing patch.
The SDL3 renderer chooses its GPU driver independently of the legacy Is3D bit.
The old checkbox could trigger InitSDLInterface() a second time, invalidating
textures and widget state. Preserve normal fullscreen and M2 update timing.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream" / "port" / "winfish"
FRAMEWORK = ROOT / "upstream" / "poplib" / "PopLib"


def replace_once(path: Path, before: str, after: str, purpose: str) -> None:
    data = path.read_text(encoding="utf-8-sig")
    count = data.count(before)
    if count != 1:
        raise RuntimeError(f"{purpose}: expected one source anchor, got {count} in {path}")
    path.write_text(data.replace(before, after, 1), encoding="utf-8", newline="\n")
    print(f"[ok] {purpose}")


def main() -> None:
    options = GAME / "OptionsDialog.cpp"
    game = GAME / "WinFishApp.cpp"
    framework = FRAMEWORK / "appbase.cpp"
    for file in (options, game, framework):
        if not file.is_file():
            raise RuntimeError(f"Generated source not found: {file}")

    replace_once(
        options,
        '\tm3DCB = MakeCheckbox(9, this, mApp->Is3DAccelerated());',
        '\tm3DCB = MakeCheckbox(9, this, false);\n'
        '\tm3DCB->SetVisible(false); // SDL3 selects the GPU renderer itself.',
        "hide obsolete and unsafe HA checkbox",
    )
    replace_once(
        options,
        '\tg->DrawString("Hardware Acceleration", m3DCB->mX - mX + 43, m3DCB->mY - mY + 24);\n',
        '',
        "remove unused HA menu label",
    )
    replace_once(
        options,
        '\tmAutoCollectCB->Resize(mX + 33, mY + 216, 45, 46);',
        '\tmAutoCollectCB->Resize(mX + 33, mY + 172, 45, 46);',
        "move Auto Collect up into the available menu row",
    )
    replace_once(
        options,
        '\tint aPrefHght = 396;',
        '\tint aPrefHght = 362;',
        "remove redundant HA menu row from in-game height",
    )
    replace_once(
        options,
        '\tif (!mBackButton->mVisible)\n\t\taPrefHght = 362;',
        '\tif (!mBackButton->mVisible)\n\t\taPrefHght = 328;',
        "restore main menu dialog height",
    )

    # Do not forward the old checkbox value to SwitchScreenMode.
    # Fullscreen/windowed changes must still work through normal SDL handling.
    replace_once(
        game,
        'SwitchScreenMode(!aDia->mFullscreenCB->IsChecked(), aDia->m3DCB->IsChecked());',
        'SwitchScreenMode(!aDia->mFullscreenCB->IsChecked(), false);'
        ' // No legacy 3D mode switch in SDL3.',
        "prevent Options OK from switching the obsolete 3D mode",
    )

    # A previously persisted Is3D=true value must not recreate the same fault
    # on the next launch. Ignore the old setting rather than changing users'
    # registry keys (which other PopCap games may share).
    original_init = """\
\t\t// Enable 3d setting
\t\tbool is3D = false;
\t\tbool is3DOptionSet = RegistryReadBoolean("Is3D", &is3D);
\t\tif (is3DOptionSet)
\t\t{
\t\t\tif (mAutoEnable3D)
\t\t\t{
\t\t\t\tmAutoEnable3D = false;
\t\t\t\tmTest3D = true;
\t\t\t}

\t\t\tif (is3D)
\t\t\t\tmTest3D = true;

\t\t\tmSDLInterface->mIs3D = is3D;
\t\t}"""
    replacement_init = """\
\t\t// SDL3 already creates a GPU renderer. The old Is3D registry value
\t\t// only selects an obsolete framework flag and must be ignored.
\t\tmSDLInterface->mIs3D = false;
\t\tmTest3D = false;
\t\tmAutoEnable3D = false;"""
    replace_once(framework, original_init, replacement_init,
                 "ignore persisted legacy acceleration setting")

    # Also block the old Shift+F8 3D toggle, or any stray caller, without
    # touching the regular window/fullscreen toggle.
    content = framework.read_text(encoding="utf-8")
    begin = 'void AppBase::Set3DAcclerated(bool is3D, bool reinit)\n{\n'
    next_method = '\nSharedImageRef AppBase::GetSharedImage('
    if content.count(begin) != 1 or content.count(next_method) != 1:
        raise RuntimeError("Cannot locate unique Set3DAcclerated method boundaries")
    left = content.index(begin)
    right = content.index(next_method, left)
    old_method = content[left:right]
    if ('InitSDLInterface()' not in old_method or
            'ReInitImages()' not in old_method or
            'mSDLInterface->mIs3D = is3D;' not in old_method):
        raise RuntimeError("Unexpected legacy 3D mode implementation; refusing patch")
    replacement = """\
void AppBase::Set3DAcclerated(bool /*is3D*/, bool /*reinit*/)
{
\t// Deliberately inert in Insaniquarium Enhanced's SDL3 build.
\t// Reinitialising the renderer here invalidates live textures/widgets.
\tif (mSDLInterface != nullptr)
\t\tmSDLInterface->mIs3D = false;
\tmUserChanged3DSetting = false;
}
"""
    framework.write_text(content[:left] + replacement + content[right:],
                         encoding="utf-8", newline="\n")
    print("[ok] disable legacy 3D mode reinitialisation from all callers")

    assert 'm3DCB->SetVisible(false);' in options.read_text(encoding="utf-8")
    assert 'SwitchScreenMode(!aDia->mFullscreenCB->IsChecked(), false);' in game.read_text(encoding="utf-8")
    print("[ok] legacy HA toggle removed, persisted setting ignored, SDL3 stays intact")


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError, AssertionError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
