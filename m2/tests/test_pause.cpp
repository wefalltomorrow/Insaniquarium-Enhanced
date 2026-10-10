#include "../PauseInterpolation.hpp"
#include <cstdio>
#include <cstdlib>

static void check(bool pass, const char* label) {
    if (!pass) { std::fprintf(stderr, "FAIL %s\n", label); std::exit(1); }
}

int main() {
    // A fish has a previous simulation position when Options is opened.
    bool history = true;
    check(EnhancedM2::CanInterpolate(true, false, history),
          "active gameplay may interpolate");

    // UI stays live at 60 FPS, but the tank itself must be frozen.
    for (int displayFrame=0; displayFrame<600; ++displayFrame) {
        const double fractionalBlend = (displayFrame % 10) / 10.0;
        EnhancedM2::InvalidateHistoryOnPause(true, true, history);
        check(!EnhancedM2::CanInterpolate(true, true, history),
              "paused fish never interpolates even as render blend advances");
        (void)fractionalBlend;
    }
    check(!history, "pause discards stale movement history");
    check(!EnhancedM2::CanInterpolate(true, false, history),
          "first frame after resume remains at fixed simulation position");

    // The next actual fish simulation update samples a new history pair.
    history = true;
    check(EnhancedM2::CanInterpolate(true, false, history),
          "interpolation resumes following an actual simulation update");

    // Normal / legacy rendering doesn't manipulate the visual cache.
    history = true;
    EnhancedM2::InvalidateHistoryOnPause(false, true, history);
    check(history, "vanilla renderer unaffected");
    check(!EnhancedM2::CanInterpolate(false, false, history),
          "opt-in M2 path only");

    std::puts("PASS pause freeze, no stale lerp on resume, normal rendering unchanged");
}
