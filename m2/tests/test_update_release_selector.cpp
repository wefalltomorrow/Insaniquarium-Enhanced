#include "../M2ReleaseSelector.hpp"
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

static void Verify(bool condition, const char* description) {
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", description);
        std::exit(1);
    }
}

static std::string Release(const std::string& tag, const std::string& published,
                           const std::string& asset, bool draft = false) {
    const std::string prefix =
        "https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/download/";
    return "{\"tag_name\":\"" + tag + "\",\"draft\":" + (draft ? "true" : "false")
         + ",\"published_at\":\"" + published + "\",\"assets\":[{\"browser_download_url\":\""
         + prefix + tag + "/" + asset + "\"}]}";
}

int main() {
    const std::string prefix =
        "https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/download/";
    // The live GitHub response listed shot-smoke before missile-interp even
    // though missile-interp had a later published_at. Never assume order.
    const std::vector<std::string> releases = {
        Release("m2-shot-smoke-20261013", "2026-10-13T10:47:17Z",
                "InsaniquariumEnhanced-M2ShotSmoke-Win64.zip"),
        Release("m2-missile-interp-20261013", "2026-10-13T11:44:41Z",
                "InsaniquariumEnhanced-M2MissileInterp-Win64.zip"),
        Release("v0.2.2-m1-update", "2026-10-13T23:00:00Z",
                "InsaniquariumEnhanced-M1-Win64.zip"),
        Release("m2-future-20261014", "2026-10-14T10:00:00Z",
                "InsaniquariumEnhanced-M2Future-Win64.zip", true),
        Release("m2-invalid-20261015", "2026-10-15T10:00:00Z",
                "InsaniquariumEnhanced-M2Invalid.zip"),
    };
    auto selected = M2ReleaseSelector::Latest(releases, prefix, "m2-shot-smoke-20261013");
    Verify(selected.found, "M2 release present");
    Verify(selected.tag == "m2-missile-interp-20261013",
           "choose latest published M2 and skip draft/M1/non-Win64");
    Verify(selected.newer, "installed earlier M2 should offer update");
    Verify(selected.download.find("M2MissileInterp-Win64.zip") != std::string::npos,
           "asset belongs to selected release");
    auto current = M2ReleaseSelector::Latest(releases, prefix, selected.tag);
    Verify(current.found && !current.newer, "latest installed should be up to date");

    // Never downgrade if GitHub lists the installed build after a newer first
    // item or if its release date sorts before a different name.
    const std::vector<std::string> outOfOrder = {releases[1], releases[0]};
    current = M2ReleaseSelector::Latest(outOfOrder, prefix, "m2-missile-interp-20261013");
    Verify(!current.newer, "out-of-order release list cannot offer downgrade");

    const std::vector<std::string> wrongUrl = {
        "{\"tag_name\":\"m2-bad-20261013\",\"draft\":false,"
        "\"published_at\":\"2026-10-15T00:00:00Z\","
        "\"assets\":[{\"browser_download_url\":"
        "\"https://evil.example/releases/download/m2-bad-20261013/x-Win64.zip\"}]}",
        Release("m2-good-20261012", "2026-10-12T10:00:00Z",
                "InsaniquariumEnhanced-M2Good-Win64.zip")
    };
    selected = M2ReleaseSelector::Latest(wrongUrl, prefix, "m2-good-20261012");
    Verify(selected.found && selected.tag == "m2-good-20261012",
           "reject foreign-host asset URLs");
    Verify(!selected.newer, "existing compatible release remains up to date");
    selected = M2ReleaseSelector::Latest({}, prefix, "m2-missile-interp-20261013");
    Verify(!selected.found, "empty API response does not claim latest");
    std::puts("PASS M2 latest published x64 release selection");
}
