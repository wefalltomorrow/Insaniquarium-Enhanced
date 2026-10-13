#pragma once
// Select the most recently *published* compatible experimental M2 release.
// GitHub's releases listing is not guaranteed to be ordered by published_at.
// Keep this helper separate from stable M1.2's semantic-version updater.
#include <regex>
#include <string>
#include <vector>

namespace M2ReleaseSelector {
struct Selection {
    bool found = false;
    bool newer = false;
    std::string tag, download, published;
};

inline std::string Field(const std::string& json, const std::regex& pattern) {
    std::smatch match;
    return std::regex_search(json, match, pattern) ? match[1].str() : "";
}

inline bool EndsWith(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

inline Selection Latest(
    const std::vector<std::string>& releases,
    const std::string& officialAssetPrefix,
    const std::string& installedTag) {
    static const std::regex tagPattern(R"re("tag_name"\s*:\s*"([^"]+)")re");
    static const std::regex timePattern(
        R"re("published_at"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z)")re");
    static const std::regex downloadPattern(
        R"re("browser_download_url"\s*:\s*"([^"]+)")re");
    static const std::regex draftPattern(R"re("draft"\s*:\s*true)re");
    static const std::regex validTag(R"re(^m2-[a-z0-9][a-z0-9-]*-[0-9]{8}$)re");

    Selection best;
    std::string installedPublished;
    bool installedSeen = false;

    for (const std::string& item : releases) {
        if (std::regex_search(item, draftPattern)) continue;
        const std::string tag = Field(item, tagPattern);
        if (!std::regex_match(tag, validTag)) continue;
        const std::string published = Field(item, timePattern);
        if (published.empty()) continue;

        std::string asset;
        const auto begin = std::sregex_iterator(
            item.begin(), item.end(), downloadPattern);
        for (auto it = begin; it != std::sregex_iterator(); ++it) {
            const std::string candidate = (*it)[1].str();
            if (candidate.rfind(officialAssetPrefix, 0) != 0) continue;
            if (!EndsWith(candidate, "-Win64.zip")) continue;
            // The URL path must refer to this exact release, not another tag.
            if (candidate.rfind(officialAssetPrefix + tag + "/", 0) != 0) continue;
            asset = candidate;
            break;
        }
        if (asset.empty()) continue;

        if (tag == installedTag) {
            installedSeen = true;
            installedPublished = published;
        }
        if (!best.found || published > best.published ||
            (published == best.published && tag > best.tag)) {
            best.found = true;
            best.tag = tag;
            best.download = asset;
            best.published = published;
        }
    }

    if (!best.found) return best;
    // When the installed release is present, never offer an older publication.
    // If absent from the most recent 20, present the latest published M2
    // rather than silently claiming the installed build is up to date.
    best.newer = installedSeen ? best.published > installedPublished
                              : best.tag != installedTag;
    return best;
}
}  // namespace M2ReleaseSelector
