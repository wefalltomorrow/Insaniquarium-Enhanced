#!/usr/bin/env python3
"""Select published M2 prereleases, not stable semantic versions, in-game.

Apply ONLY on the disposable generated Windows M2 source after
m1/apply_updater.py. Stable M1.2 source/workflow is never modified.
The embedded installed tag must match this build's actual published tag.
"""
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "upstream/port/winfish"
START = "CheckResult Check() {\n"
END = "\nstd::future<CheckResult> pending;"
REPLACEMENT = r"""CheckResult Check() {
    CheckResult result;
    std::string error;
    std::string json = FetchJson(error);
    if (json.empty()) {
        result.error = error.empty() ? "No release data received." : error;
        return result;
    }
    auto releases = ReleaseObjects(json);
    if (releases.empty()) {
        result.error = "GitHub returned unexpected release data.";
        return result;
    }
    // Match only published M2 release tags and their genuine project Win64
    // ZIP assets. GitHub release API order is not publication order.
    auto latest = M2ReleaseSelector::Latest(releases, kAssetPrefix, kCurrentVersion);
    if (!latest.found) {
        result.error = "No published M2 Windows x64 release found.";
        return result;
    }
    result.success = true;
    result.newer = latest.newer;
    result.tag = latest.tag;
    result.download = latest.download;
    return result;
}
"""

def patch(source: str, version_header: str, public_tag: str) -> tuple[str, str]:
    if not re.fullmatch(r"m2-[a-z0-9][a-z0-9-]*-[0-9]{8}", public_tag):
        raise RuntimeError("Expected an experimental published M2 release tag")
    if source.count(START) != 1 or source.count(END) != 1:
        raise RuntimeError("Unexpected updater source shape")
    if '#include "M2ReleaseSelector.hpp"' in source:
        raise RuntimeError("M2 updater already patched")
    anchor = '#include "EnhancedUpdaterVersion.h"'
    if source.count(anchor) != 1:
        raise RuntimeError("EnhancedUpdaterVersion header include not unique")
    source = source.replace(anchor, anchor + '\n#include "M2ReleaseSelector.hpp"', 1)
    begin = source.index(START)
    end = source.index(END, begin)
    if source.count('Version best{};', begin, end) != 1:
        raise RuntimeError("M1 semantic-release selector changed; source re-audit required")
    source = source[:begin] + REPLACEMENT + source[end:]
    matches = re.findall(r'^#define ENHANCED_VERSION_TAG "([^"]+)"$', version_header, re.M)
    if len(matches) != 1 or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+-[A-Za-z0-9-]+", matches[0]):
        raise RuntimeError("Unexpected generated updater version header")
    version_header = version_header.replace(
        f'#define ENHANCED_VERSION_TAG "{matches[0]}"',
        f'#define ENHANCED_VERSION_TAG "{public_tag}"', 1)
    return source, version_header

def main(tag: str) -> int:
    source = GAME / "EnhancedUpdater.cpp"
    version = GAME / "EnhancedUpdaterVersion.h"
    if not source.is_file() or not version.is_file():
        raise RuntimeError("Run m1/apply_updater.py before M2 channel override")
    updated_source, updated_header = patch(
        source.read_text(encoding="utf-8-sig"),
        version.read_text(encoding="utf-8-sig"), tag)
    if not (ROOT / "m2/M2ReleaseSelector.hpp").is_file():
        raise RuntimeError("M2 release selector header missing")
    shutil.copyfile(ROOT / "m2/M2ReleaseSelector.hpp",
                    GAME / "M2ReleaseSelector.hpp")
    source.write_text(updated_source, encoding="utf-8", newline="\n")
    version.write_text(updated_header, encoding="utf-8", newline="\n")
    print(f"[ok] M2 channel updates now compare published tags, current={tag}")
    print("[ok] Only verified GitHub M2 Win64 ZIPs accepted; stable M1.2 unchanged")
    return 0

if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise RuntimeError("Usage: apply_updater_channel.py m2-release-tag-YYYYMMDD")
        raise SystemExit(main(sys.argv[1]))
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        raise SystemExit(1)
