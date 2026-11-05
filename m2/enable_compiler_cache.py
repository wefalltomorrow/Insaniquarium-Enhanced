#!/usr/bin/env python3
"""Make pinned generated WinFish MSVC CMake project compiler-cache-compatible.

Converts /Zi compiler PDB usage to /Z7 embedded debug info. Existing /DEBUG
linker option still emits the PDB used by the crash handler. Does not
modify any game C++ logic or the pinned upstream source checkout.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
PORT_CMAKE = ROOT / "upstream/port/CMakeLists.txt"

OLD = """\t# Symbols in Release too: the crash handler in Window.cpp uses them to print
\t# a stack with file and line.
\ttarget_compile_options(${GAME_TARGET} PRIVATE /Zi)
\ttarget_link_options(${GAME_TARGET} PRIVATE /DEBUG /OPT:REF /OPT:ICF)"""

NEW = """\t# Embedded /Z7 debug information supports content-addressed caching.
\t# The existing /DEBUG link option still emits the crash-handler PDB.
\ttarget_compile_options(${GAME_TARGET} PRIVATE /Z7)
\ttarget_link_options(${GAME_TARGET} PRIVATE /DEBUG /OPT:REF /OPT:ICF)"""


def patch_source(source: str) -> str:
    count = source.count(OLD)
    if count != 1:
        raise RuntimeError(f"Expected one WinFish debug-info anchor, found {count}")
    result = source.replace(OLD, NEW, 1)
    if result.count("target_compile_options(${GAME_TARGET} PRIVATE /Z7)") != 1:
        raise RuntimeError("Missing /Z7 setting")
    if "target_link_options(${GAME_TARGET} PRIVATE /DEBUG /OPT:REF /OPT:ICF)" not in result:
        raise RuntimeError("PDB linker options were lost")
    return result


def main() -> None:
    source = PORT_CMAKE.read_text(encoding="utf-8-sig")
    PORT_CMAKE.write_text(patch_source(source), encoding="utf-8", newline="\n")
    print("[ok] WinFish /Z7 debug info and /DEBUG PDB linker retained")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
