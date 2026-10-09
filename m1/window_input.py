#!/usr/bin/env python3
"""Optional SDL3 Windows presentation/input improvements for Insaniquarium Enhanced.

Patches the temporary, reproducibly fetched PopLib checkout. No upstream
repository is modified, and M0/M1 baseline releases remain unchanged.

- Request a high-pixel-density SDL window on Windows so OS DPI scaling does
  not bitmap-stretch the compositor.
- Alt+Enter toggles fullscreen on the *existing* SDL window, retaining the
  renderer, textures, native cursor and coordinate mapping.
- Both paths retain SDL logical presentation and 4:3 letterboxing.
These are input/window improvements, NOT native 4K game rendering.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
POPLIB = ROOT / "upstream" / "poplib"
WINDOW = POPLIB / "PopLib" / "graphics" / "sdlinterface.cpp"
APP = POPLIB / "PopLib" / "appbase.cpp"

def replace_once(path: Path, before: str, after: str, label: str) -> None:
    data = path.read_text(encoding="utf-8")
    if data.count(after) == 1 and before not in data:
        print(f"[already] {label}")
        return
    count = data.count(before)
    if count != 1:
        raise RuntimeError(f"{label}: expected one insertion anchor, got {count}")
    path.write_text(data.replace(before, after, 1), encoding="utf-8", newline="\n")
    print(f"[ok] {label}")

def main() -> int:
    replace_once(
        WINDOW,
        "\tint aWindowFlags = IsWindowed ? SDL_WINDOW_RESIZABLE : SDL_WINDOW_FULLSCREEN;\n",
        "\tint aWindowFlags = IsWindowed ? SDL_WINDOW_RESIZABLE : SDL_WINDOW_FULLSCREEN;\n"
        "#ifdef _WIN32\n"
        "\t// Let SDL manage native DPI / per-monitor pixel density. Input is\n"
        "\t// still mapped into the game's 640x480 logical coordinate space.\n"
        "\taWindowFlags |= SDL_WINDOW_HIGH_PIXEL_DENSITY;\n"
        "#endif\n",
        "high-DPI SDL window",
    )
    replace_once(
        APP,
        "\t\t\tSDL_Keycode key = event.key.key;\n\n\t\t\tmLastUserInputTick",
        "\t\t\tSDL_Keycode key = event.key.key;\n\n"
        "\t\t\t// Native Alt+Enter: switch the existing SDL window instead of\n"
        "\t\t\t// destroying/recreating the renderer (which can lose textures).\n"
        "\t\t\tif (key == SDLK_RETURN && (event.key.mod & SDL_KMOD_ALT) != 0 &&\n"
        "\t\t\t    mSDLInterface != nullptr && mSDLInterface->mWindow != nullptr)\n"
        "\t\t\t{\n"
        "\t\t\t\tif (isDown && !event.key.repeat)\n"
        "\t\t\t\t{\n"
        "\t\t\t\t\tSDL_Window* window = mSDLInterface->mWindow;\n"
        "\t\t\t\t\tbool wasFullscreen = (SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN) != 0;\n"
        "\t\t\t\t\tif (SDL_SetWindowFullscreen(window, !wasFullscreen))\n"
        "\t\t\t\t\t{\n"
        "\t\t\t\t\t\tmIsWindowed = wasFullscreen;\n"
        "\t\t\t\t\t\tmIsPhysWindowed = wasFullscreen;\n"
        "\t\t\t\t\t\tRegistryWriteInteger(\"ScreenMode\", wasFullscreen ? 0 : 1);\n"
        "\t\t\t\t\t\tmSDLInterface->UpdateViewport();\n"
        "\t\t\t\t\t\tmWidgetManager->MarkAllDirty();\n"
        "\t\t\t\t\t\tClearUpdateBacklog();\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t\telse\n"
        "\t\t\t\t\t\tSDL_Log(\"Alt+Enter fullscreen toggle failed: %s\", SDL_GetError());\n"
        "\t\t\t\t}\n"
        "\t\t\t\tbreak; // Do not send the fullscreen shortcut to the game.\n"
        "\t\t\t}\n\n"
        "\t\t\tmLastUserInputTick",
        "in-place fullscreen toggle",
    )
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        raise SystemExit(1)
