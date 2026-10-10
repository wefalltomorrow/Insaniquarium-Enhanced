#pragma once
// M2 development-only instrumentation. Engine-agnostic C++17/C++14, no SDL
// calls and no writes to game state. Enable with INSANIQUARIUM_M2_DEBUG=1.
// The normal build incurs only a cheap disabled flag check.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <set>
#include <limits>
#include <string>
#include <utility>

namespace M2Debug {
enum Kind { Board = 0, Fish = 1, Coin = 2, Food = 3, Alien = 4, Kinds = 5 };
inline const char* Name(Kind k) {
    static const char* names[] = {"board", "fish", "coin", "food", "alien"};
    return names[static_cast<int>(k)];
}
struct ObjectState {
    double x = 0, y = 0;
    int cel = 0;
    unsigned long long tick = 0, frame = 0;
    bool valid = false;
};

class Recorder {
    bool active = false, opened = false;
    FILE* frames = nullptr;
    FILE* objects = nullptr;
    FILE* sprites = nullptr;
    FILE* interp = nullptr;
    FILE* invalidSprites = nullptr;
    FILE* skippedSprites = nullptr;
    FILE* events = nullptr;
    unsigned long long frame = 0, ticks = 0;
    unsigned long long totalEvents = 0;
    // Separate file budgets: object-heavy scenes must not exhaust the other CSVs.
    unsigned long long objectRows = 0, spriteRows = 0, interpRows = 0;
    unsigned long long lastReportedTick = 0, invalidRows = 0, skippedRows = 0;
    unsigned update[Kinds] = {}, draw[Kinds] = {};
    unsigned spriteCount = 0, invalidSpriteCount = 0, skippedSpriteCount = 0, celChanges = 0;
    unsigned currentWarnings = 0;
    unsigned perFrameObjects = 0, perFrameSprites = 0;
    unsigned lastSecondWarnings = 0;
    double lastFrameMs = 0, lastSimRate = 0, lastPresentRate = 0;
    std::map<std::pair<int, uintptr_t>, ObjectState> observations;
    std::set<uintptr_t> reportedUnsafeFish;
    char title[256] = {};
    static constexpr unsigned kObjectsPerFrame = 160;
    static constexpr unsigned kSpritesPerFrame = 220;
    static constexpr unsigned long long kTraceRowLimit = 350000;

    static FILE* Open(const char* name, const char* header) {
        FILE* f = std::fopen(name, "w");
        if (f) {
            std::setvbuf(f, nullptr, _IOFBF, 64 * 1024);
            std::fputs(header, f);
        }
        return f;
    }

    void LogEvent(const char* severity, const char* issue, double a = 0,
                  double b = 0, bool countWarning = true) {
        if (countWarning) ++currentWarnings;
        if (!events || totalEvents >= 20000) return;
        std::fprintf(events, "%llu,%llu,%s,%s,%.4f,%.4f\n",
                     frame, ticks, severity, issue, a, b);
        ++totalEvents;
    }

public:
    Recorder() {
        const char* e = std::getenv("INSANIQUARIUM_M2_DEBUG");
        active = e && e[0] == '1' && e[1] == '\0';
        std::snprintf(title, sizeof(title), "Insaniquarium Enhanced M2 [Debug]");
    }
    ~Recorder() {
        if (frames) std::fclose(frames);
        if (objects) std::fclose(objects);
        if (sprites) std::fclose(sprites);
        if (interp) std::fclose(interp);
        if (invalidSprites) std::fclose(invalidSprites);
        if (skippedSprites) std::fclose(skippedSprites);
        if (events) std::fclose(events);
    }
    bool Active() const { return active; }
    // Full object/interpolation detail for the first ~167 seconds at 60 FPS.
    // Later, sample every third presentation frame so the 350k-row
    // per-stream budgets cover longer sessions without growing huge logs.
    // Warning detection and per-frame totals ALWAYS run at full cadence.
    static bool SampleDetailFrame(unsigned long long presentFrame) {
        return presentFrame < 10000ULL || (presentFrame % 3ULL) == 0ULL;
    }
    void Start() {
        if (!active || opened) return;
        opened = true;
        frames = Open("M2DebugFrames.csv",
            "frame,scheduledTicks,actualTicksSincePreviousPresent,totalSimTicks,presentRequested,presented,elapsedMs,renderMs,blend,updatesBoard,updatesFish,updatesCoin,updatesFood,updatesAlien,drawsBoard,drawsFish,drawsCoin,drawsFood,drawsAlien,spriteCels,invalidCels,celChanges,warnings,expectedSkippedCels\n");
        objects = Open("M2DebugObjects.csv",
            "frame,gameTick,kind,objectId,simulationX,simulationY,animationCel,changedCel,simMoved,repeatDraw,simTicksSinceLastDraw\n");
        sprites = Open("M2DebugSprites.csv",
            "frame,gameTick,imageId,celColumn,celRow,drawX,drawY\n");
        interp = Open("M2DebugInterpolation.csv",
            "frame,gameTick,objectId,simulationX,simulationY,renderX,renderY,offsetX,offsetY,blend\n");
        invalidSprites = Open("M2DebugInvalidSprites.csv",
            "frame,gameTick,imageId,assetPath,imageWidth,imageHeight,sheetCols,sheetRows,requestedCol,requestedRow,drawX,drawY\n");
        skippedSprites = Open("M2DebugSkippedSprites.csv",
            "frame,gameTick,imageId,assetPath,imageWidth,imageHeight,sheetCols,sheetRows,requestedCol,requestedRow,drawX,drawY\n");
        events = Open("M2DebugEvents.csv",
            "frame,gameTick,severity,event,valueA,valueB\n");
        LogEvent("INFO", "debug_enabled", 0, 0, false);
        if (!frames || !objects || !sprites || !interp || !invalidSprites || !skippedSprites || !events)
            LogEvent("ERROR", "unable_to_open_some_debug_logs");
    }

    void Begin(double elapsedMs, double blend, int simSteps) {
        if (!active) return;
        Start();
        lastFrameMs = elapsedMs;
        if (elapsedMs > 65.0)
            LogEvent("WARN", "long_scheduler_gap_ms", elapsedMs, simSteps);
        if (blend < -0.0001 || blend > 1.0001)
            LogEvent("ERROR", "invalid_interpolation_factor", blend);
        if (observations.size() > 10000) observations.clear();
    }
    void PauseTransition(bool isPaused) {
        if (!active) return;
        LogEvent("INFO", isPaused ? "tank_paused" : "tank_resumed",
                 isPaused ? 1.0 : 0.0, 0.0, false);
    }
    void SimTick() { if (active) ++ticks; }
    void Updated(Kind kind) {
        if (active) ++update[kind];
    }
    void Drawn(Kind kind, const void* object, double x, double y, int cel) {
        if (!active) return;
        ++draw[kind];
        auto key = std::make_pair(static_cast<int>(kind),
                                  reinterpret_cast<uintptr_t>(object));
        ObjectState& previous = observations[key];
        const bool repeated = previous.valid && previous.tick == ticks;
        const bool changedCel = previous.valid && previous.cel != cel;
        const bool moved = previous.valid &&
            (std::abs(previous.x - x) > 0.005 || std::abs(previous.y - y) > 0.005);
        const unsigned long long since =
            previous.valid ? ticks - previous.tick : 0;
        if (changedCel) ++celChanges;
        if (repeated && changedCel)
            LogEvent("WARN", "animation_cel_changed_without_game_tick",
                     static_cast<double>(kind), static_cast<double>(cel));
        if (repeated && moved)
            LogEvent("WARN", "simulation_position_changed_without_game_tick",
                     static_cast<double>(kind), static_cast<double>(since));
        if (objects && SampleDetailFrame(frame) && objectRows < kTraceRowLimit &&
            perFrameObjects++ < kObjectsPerFrame) {
            std::fprintf(objects, "%llu,%llu,%s,%llu,%.4f,%.4f,%d,%u,%u,%u,%llu\n",
                         frame, ticks, Name(kind),
                         static_cast<unsigned long long>(key.second),
                         x, y, cel, changedCel, moved, repeated, since);
            ++objectRows;
        }
        previous = {x, y, cel, ticks, frame, true};
    }

    void UnsafeFishPosition(const void* object, double x, double y) {
        if (!active || reportedUnsafeFish.size() >= 1024) return;
        const uintptr_t id = reinterpret_cast<uintptr_t>(object);
        if (reportedUnsafeFish.insert(id).second) {
            const double bound = static_cast<double>(std::numeric_limits<int>::max());
            LogEvent("WARN", "fish_position_outside_safe_render_range",
                     (!std::isfinite(x) || std::abs(x) > bound) ? 1.0 : 0.0,
                     (!std::isfinite(y) || std::abs(y) > bound) ? 1.0 : 0.0);
        }
    }

    void RenderOffset(const void* object, double simX, double simY,
                      double dx, double dy, double blend) {
        if (!active) return;
        if (!std::isfinite(dx) || !std::isfinite(dy))
            LogEvent("ERROR", "nonfinite_fish_render_offset", dx, dy);
        if (std::abs(dx) > 50.0 || std::abs(dy) > 50.0)
            LogEvent("WARN", "large_fish_interpolation_offset", dx, dy);
        if (interp && SampleDetailFrame(frame) && interpRows < kTraceRowLimit && perFrameObjects < kObjectsPerFrame) {
            std::fprintf(interp, "%llu,%llu,%llu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.5f\n",
                         frame, ticks, static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(object)),
                         simX, simY, simX + dx, simY + dy, dx, dy, blend);
            ++interpRows;
        }
    }

    void SpriteCel(const void* image, int col, int row, int x, int y,
                   int maxCols, int maxRows, int width, int height,
                   const std::string& assetPath) {
        if (!active) return;
        ++spriteCount;
        if (col < 0 || row < 0 || col >= maxCols || row >= maxRows) {
            // Original graphics code intentionally ignores negative cels.
            // Meryl's blinking overlay and the first chomp-effect frame
            // both use -1 as a normal "do not draw" sentinel.
            // The old graphics engine ignores these out-of-sheet calls:
            // - Negative first cels are hidden startup frames for shot FX.
            // - Laser shots have a 15-tick lifetime but only 10 drawable
            //   animation columns; their trailing frames remain invisible.
            // Neither case should be clamped to a visible sprite frame.
            const bool hiddenFirstCel = col == -1 && row == 0 &&
                (assetPath == "images/merylblink" ||
                 assetPath == "images/chomp" ||
                 assetPath == "images/smoketiny" ||
                 assetPath == "images/smokesmall" ||
                 assetPath == "images/explosion" ||
                 assetPath == "images/explosiontiny" ||
                 assetPath == "images/explosionsmall");
            const bool hiddenLaserTail =
                assetPath == "images/lasers" &&
                maxCols == 10 && maxRows == 6 &&
                col >= 10 && col <= 13 && row >= 0 && row < 6;
            // Single-index DrawImageCel maps the terminal index 17/17 or
            // 10/10 to (col=0,row=1); old Graphics rejects it without draw.
            // Warp::Draw and HatchScreen are the confirmed callers. Match
            // exact image paths and sheet shape; leave other errors visible.
            const bool hiddenWarpFinal = col == 0 && row == 1 &&
                maxCols == 17 && maxRows == 1 &&
                (assetPath == "images/warphole" || assetPath == "images/warpglow");
            const bool hiddenEggFinal = col == 0 && row == 1 &&
                maxCols == 10 && maxRows == 1 && assetPath == "images/eggcrack2";
            const bool expectedSkip = hiddenFirstCel || hiddenLaserTail ||
                                      hiddenWarpFinal || hiddenEggFinal;
            if (expectedSkip)
                ++skippedSpriteCount;
            else {
                ++invalidSpriteCount;
                if (invalidSpriteCount <= 3)
                    LogEvent("WARN", "invalid_sprite_cel", col, row);
            }
            FILE* detail = expectedSkip ? skippedSprites : invalidSprites;
            unsigned long long& count = expectedSkip ? skippedRows : invalidRows;
            if (detail && count < 50000) {
                std::string safePath = assetPath.empty() ? "<unnamed image>" : assetPath;
                for (char& ch : safePath)
                    if (ch == '"' || ch == '\r' || ch == '\n' || ch == ',')
                        ch = '_';
                std::fprintf(detail,
                    "%llu,%llu,%llu,%s,%d,%d,%d,%d,%d,%d,%d,%d\n",
                    frame, ticks,
                    static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(image)),
                    safePath.c_str(), width, height, maxCols, maxRows,
                    col, row, x, y);
                ++count;
            }
        }
        if (sprites && spriteRows < kTraceRowLimit &&
            perFrameSprites++ < kSpritesPerFrame && (frame % 2) == 0) {
            std::fprintf(sprites, "%llu,%llu,%llu,%d,%d,%d,%d\n",
                         frame, ticks,
                         static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(image)),
                         col, row, x, y);
            ++spriteRows;
        }
    }
    void DrawMutation(Kind kind, const void* object, double beforeX, double beforeY,
                      int beforeCel, double afterX, double afterY, int afterCel) {
        if (!active) return;
        if (std::abs(beforeX-afterX) > 0.001 ||
            std::abs(beforeY-afterY) > 0.001 || beforeCel != afterCel) {
            LogEvent("WARN", "draw_mutated_game_state",
                     static_cast<double>(kind), static_cast<double>(beforeCel != afterCel));
            (void)object;
        }
    }
    void End(int simSteps, bool requested, bool presented, double elapsed,
             double renderMs, double blend) {
        if (!active) return;
        if (renderMs > 25.0)
            LogEvent("WARN", "slow_render_ms", renderMs);
        if (frames)
            std::fprintf(frames,
                "%llu,%d,%llu,%llu,%u,%u,%.4f,%.4f,%.6f,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n",
                frame, simSteps, ticks - lastReportedTick, ticks,
                requested, presented, elapsed,
                renderMs, blend, update[Board], update[Fish], update[Coin],
                update[Food], update[Alien], draw[Board], draw[Fish],
                draw[Coin], draw[Food], draw[Alien], spriteCount,
                invalidSpriteCount, celChanges, currentWarnings,
                skippedSpriteCount);
        lastReportedTick = ticks;
        ++frame;
        for (int i=0; i<Kinds; ++i) { update[i] = 0; draw[i] = 0; }
        spriteCount = invalidSpriteCount = skippedSpriteCount = celChanges = 0;
        perFrameObjects = perFrameSprites = 0;
        lastSecondWarnings += currentWarnings;
        currentWarnings = 0;
        if ((frame % 300) == 0) {
            if (frames) std::fflush(frames);
            if (objects) std::fflush(objects);
            if (sprites) std::fflush(sprites);
            if (interp) std::fflush(interp);
            if (invalidSprites) std::fflush(invalidSprites);
            if (skippedSprites) std::fflush(skippedSprites);
            if (events) std::fflush(events);
            for (auto it = observations.begin(); it != observations.end();) {
                if (frame > it->second.frame + 1200) it = observations.erase(it);
                else ++it;
            }
        }
    }
    void WindowTitle(double simHz, double presentHz) {
        if (!active) return;
        lastSimRate = simHz;
        lastPresentRate = presentHz;
        std::snprintf(title, sizeof(title),
            "Insaniquarium Enhanced [M2 DEBUG] sim %.1f Hz | render %.1f FPS | warnings %u",
            simHz, presentHz, lastSecondWarnings);
        lastSecondWarnings = 0;
        if (simHz > 0 && (simHz < 32.0 || simHz > 39.0))
            LogEvent("WARN", "simulation_rate_out_of_range", simHz);
        if (presentHz > 0 && presentHz < 52.0)
            LogEvent("WARN", "presentation_rate_low", presentHz);
    }
    const char* Title() const { return title; }
};

inline Recorder& Get() {
    static Recorder recorder;
    return recorder;
}

// Scoped state snapshot catches render-time mutation, including early returns.
// It never modifies object state and remains inert outside debug mode.
struct DrawGuard {
    Kind kind;
    const void* object;
    const double &x, &y;
    const int &cel;
    double oldX, oldY;
    int oldCel;
    bool enabled;
    DrawGuard(Kind k, const void* obj, const double& px,
              const double& py, const int& pc) :
        kind(k), object(obj), x(px), y(py), cel(pc),
        oldX(px), oldY(py), oldCel(pc), enabled(Get().Active()) {
        if (enabled) Get().Drawn(kind, object, oldX, oldY, oldCel);
    }
    ~DrawGuard() {
        if (enabled) Get().DrawMutation(kind, object,
            oldX, oldY, oldCel, x, y, cel);
    }
    DrawGuard(const DrawGuard&) = delete;
    DrawGuard& operator=(const DrawGuard&) = delete;
};
} // namespace M2Debug
