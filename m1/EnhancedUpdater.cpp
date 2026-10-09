// Insaniquarium Enhanced: nonblocking GitHub release checker (Windows x64).
// The worker only handles HTTPS + JSON. All dialogs are created on game thread.
#include "EnhancedUpdater.h"
#include "EnhancedUpdaterVersion.h"
#include "WinFishApp.h"
#include <PopLib/widget/dialog.hpp>
#include <PopLib/widget/dialogbutton.hpp>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#pragma comment(lib, "winhttp.lib")

#include <chrono>
#include <cstdio>
#include <future>
#include <regex>
#include <string>
#include <vector>

namespace {
constexpr int kChecking = 90;
constexpr int kUpdateAvailable = 91;
constexpr size_t kMaxResponseBytes = 1024 * 1024;
constexpr const char* kAssetPrefix =
    "https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/download/";
constexpr const char* kCurrentVersion = ENHANCED_VERSION_TAG;

struct Version {
    int major = -1, minor = -1, patch = -1;
    bool Valid() const { return major >= 0 && minor >= 0 && patch >= 0; }
};
Version ParseVersion(const std::string& value) {
    Version v;
    if (std::sscanf(value.c_str(), "v%d.%d.%d", &v.major, &v.minor, &v.patch) != 3)
        return {};
    return v;
}
bool IsNewer(const Version& a, const Version& b) {
    if (a.major != b.major) return a.major > b.major;
    if (a.minor != b.minor) return a.minor > b.minor;
    return a.patch > b.patch;
}

struct CheckResult {
    bool success = false;
    bool newer = false;
    std::string tag, download, error;
};

class HttpHandle {
    HINTERNET h = nullptr;
public:
    explicit HttpHandle(HINTERNET h) : h(h) {}
    ~HttpHandle() { if (h) WinHttpCloseHandle(h); }
    HttpHandle(const HttpHandle&) = delete;
    HttpHandle& operator=(const HttpHandle&) = delete;
    operator HINTERNET() const { return h; }
};

std::string FetchJson(std::string& error) {
    HttpHandle session(WinHttpOpen(
        L"InsaniquariumEnhanced-Updater/1.0",
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0));
    if (!session) { error = "Couldn't initialise HTTPS."; return {}; }
    WinHttpSetTimeouts(session, 5000, 5000, 8000, 8000);

    HttpHandle connection(WinHttpConnect(session, L"api.github.com",
                                         INTERNET_DEFAULT_HTTPS_PORT, 0));
    if (!connection) { error = "Couldn't connect to GitHub."; return {}; }

    HttpHandle request(WinHttpOpenRequest(
        connection, L"GET",
        L"/repos/wefalltomorrow/Insaniquarium-Enhanced/releases?per_page=20",
        nullptr, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
        WINHTTP_FLAG_SECURE));
    if (!request) { error = "Couldn't create GitHub request."; return {}; }

    const wchar_t* headers =
        L"Accept: application/vnd.github+json\r\n"
        L"X-GitHub-Api-Version: 2022-11-28\r\n";
    if (!WinHttpAddRequestHeaders(request, headers, (DWORD)-1,
                                  WINHTTP_ADDREQ_FLAG_ADD) ||
        !WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0) ||
        !WinHttpReceiveResponse(request, nullptr)) {
        error = "Couldn't retrieve releases. Check your connection.";
        return {};
    }

    DWORD status = 0, bytes = sizeof(status);
    if (!WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE |
                            WINHTTP_QUERY_FLAG_NUMBER,
                            WINHTTP_HEADER_NAME_BY_INDEX, &status, &bytes,
                            WINHTTP_NO_HEADER_INDEX) || status != 200) {
        error = status == 403 ? "GitHub rate limit reached. Try again later."
                              : "GitHub release check failed.";
        return {};
    }

    std::string body;
    char buffer[8192];
    for (;;) {
        DWORD received = 0;
        if (!WinHttpReadData(request, buffer, sizeof(buffer), &received)) {
            error = "Failed reading the GitHub response.";
            return {};
        }
        if (!received) break;
        if (body.size() + received > kMaxResponseBytes) {
            error = "GitHub response too large.";
            return {};
        }
        body.append(buffer, received);
    }
    return body;
}

// Split only the top-level release objects. Strings, escaped quotes, and
// nested "assets" arrays cannot disrupt this bracket scan.
std::vector<std::string> ReleaseObjects(const std::string& data) {
    std::vector<std::string> objects;
    bool quoted = false, escaped = false;
    int depth = 0;
    size_t start = 0;
    for (size_t i = 0; i < data.size(); ++i) {
        char c = data[i];
        if (escaped) { escaped = false; continue; }
        if (quoted && c == '\\') { escaped = true; continue; }
        if (c == '"') { quoted = !quoted; continue; }
        if (quoted) continue;
        if (c == '{') {
            if (!depth) start = i;
            ++depth;
        } else if (c == '}') {
            if (!depth) return {};
            if (--depth == 0) objects.push_back(data.substr(start, i - start + 1));
        }
    }
    if (quoted || depth != 0) return {};
    return objects;
}

std::string ExtractField(const std::string& data, const std::regex& pattern) {
    std::smatch found;
    return std::regex_search(data, found, pattern) ? found[1].str() : "";
}

CheckResult Check() {
    CheckResult result;
    std::string error;
    std::string json = FetchJson(error);
    if (json.empty()) {
        result.error = error.empty() ? "No release data received." : error;
        return result;
    }

    static const std::regex tagPattern(R"re("tag_name"\s*:\s*"([^"]+)")re");
    static const std::regex urlPattern(R"re("browser_download_url"\s*:\s*"([^"]+)")re");
    static const std::regex draftPattern(R"re("draft"\s*:\s*true)re");
    Version best{};
    auto versions = ReleaseObjects(json);
    if (versions.empty()) {
        result.error = "GitHub returned unexpected release data.";
        return result;
    }

    // GitHub /releases/latest excludes pre-releases. Iterate the releases API
    // instead and choose the highest published semantic version with a x64 ZIP.
    for (const std::string& item : versions) {
        if (std::regex_search(item, draftPattern)) continue;
        std::string tag = ExtractField(item, tagPattern);
        Version v = ParseVersion(tag);
        if (!v.Valid() || (best.Valid() && !IsNewer(v, best))) continue;

        std::string asset;
        auto begin = std::sregex_iterator(item.begin(), item.end(), urlPattern);
        for (auto it = begin; it != std::sregex_iterator(); ++it) {
            std::string url = (*it)[1].str();
            if (url.rfind(kAssetPrefix, 0) != 0) continue;
            if (url.find("-Win64.zip") == std::string::npos) continue;
            asset = url;
            break;
        }
        if (asset.empty()) continue;
        best = v;
        result.tag = tag;
        result.download = asset;
    }

    if (!best.Valid()) {
        result.error = "No compatible Windows x64 release found.";
        return result;
    }
    Version current = ParseVersion(kCurrentVersion);
    if (!current.Valid()) {
        result.error = "Installed build version is invalid.";
        return result;
    }
    result.newer = IsNewer(best, current);
    result.success = true;
    return result;
}

std::future<CheckResult> pending;
std::string latestDownload;

} // namespace

void EnhancedUpdater::Start(PopLib::WinFishApp* app) {
    if (!app || pending.valid()) return;
    latestDownload.clear();
    pending = std::async(std::launch::async, Check);
    app->DoDialog(kChecking, true, "Checking for Updates",
                  "Checking GitHub for a newer build...",
                  "Cancel", PopLib::Dialog::BUTTONS_FOOTER);
}

void EnhancedUpdater::Pump(PopLib::WinFishApp* app) {
    if (!app || !pending.valid() ||
        pending.wait_for(std::chrono::seconds(0)) != std::future_status::ready)
        return;

    CheckResult r = pending.get();
    // User cancelled or closed the checking dialog: suppress the result.
    if (!app->GetDialog(kChecking)) return;
    app->KillDialog(kChecking);

    if (!r.success) {
        app->DoDialog(kUpdateAvailable + 1, true, "Update Check Failed",
                      r.error + "\n\nPlease try again later.",
                      "OK", PopLib::Dialog::BUTTONS_FOOTER);
        return;
    }
    if (!r.newer) {
        app->DoDialog(kUpdateAvailable + 2, true, "Up to Date",
                      "You have the latest Insaniquarium Enhanced build.\n\nInstalled: "
                          + std::string(kCurrentVersion),
                      "OK", PopLib::Dialog::BUTTONS_FOOTER);
        return;
    }

    latestDownload = r.download;
    PopLib::Dialog* d = app->DoDialog(
        kUpdateAvailable, true, "Update Available",
        "Installed: " + std::string(kCurrentVersion)
            + "\nAvailable: " + r.tag
            + "\n\nDownload the new build?",
        "", PopLib::Dialog::BUTTONS_YES_NO);
    if (d && d->mYesButton && d->mNoButton) {
        d->mYesButton->mLabel = "Download";
        d->mNoButton->mLabel = "Later";
    }
}

void EnhancedUpdater::Download(PopLib::WinFishApp* app) {
    if (!app || latestDownload.empty()) return;
    const std::string url = latestDownload;
    latestDownload.clear();
    app->OpenURL(url);
}
