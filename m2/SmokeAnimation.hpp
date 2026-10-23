#pragma once
// Opt-in presentation experiment. Never advances or writes game animation state.
#include <cmath>
#include <cstdlib>

namespace EnhancedM2 {
inline bool SmokeAnimationEnabled() {
    static const bool enabled = [] {
        const char* value = std::getenv("INSANIQUARIUM_M2_SMOKE_BLEND");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return enabled;
}

struct SmokeFramePlan {
    int from = 0, to = 0;
    double mix = 1.0;
    bool transition = false;
};

struct SmokeAnimationHistory {
    int age = 0, cel = 0, type = 0;
    bool valid = false;

    void Capture(bool enabled, int shotType, int tickAge, int frame, int delay) {
        valid = enabled && (shotType == 6 || shotType == 7) && delay == 0 &&
                tickAge >= 2 && tickAge <= 39 && frame == tickAge / 2 - 1;
        age = tickAge;
        cel = frame;
        type = shotType;
    }

    SmokeFramePlan Plan(bool enabled, bool paused, int shotType, int tickAge,
                        int frame, int delay, int columns, int rows, double blend) const {
        SmokeFramePlan result{frame, frame, 1.0, false};
        // Original smoke has a hidden startup cel and a 39-tick lifetime.
        // Never blend across startup, delay, reset/load, type changes or removal.
        if (!enabled || paused || !valid || type != shotType ||
            (shotType != 6 && shotType != 7) || delay != 0 ||
            age < 2 || age > 38 || tickAge != age + 1 ||
            frame != tickAge / 2 - 1 || cel != age / 2 - 1 ||
            rows != 1 || cel < 0 || frame >= columns || frame != cel + 1 ||
            !std::isfinite(blend) || blend < 0.0 || blend > 1.0) return result;
        return {cel, frame, blend, true};
    }
};

// Normal alpha-over crossfade, deliberately restricted to soft smoke. This is
// not per-pixel linear image interpolation: overlap can change apparent opacity.
// Keep it optional until visual comparison justifies broader use.
template<class Graphics, class Image>
void DrawSmokeFrames(Graphics* g, Image* image, const SmokeFramePlan& plan) {
    if (!plan.transition) {
        g->DrawImageCel(image, 0, 0, plan.to);
        return;
    }
    const auto original = g->GetColor();
    struct RestoreColor {
        Graphics* g;
        decltype(original) color;
        ~RestoreColor() { g->SetColor(color); }
    } restore{g, original};
    auto color = original;
    const int nextAlpha = static_cast<int>(original.mAlpha * plan.mix + 0.5);
    color.mAlpha = original.mAlpha - nextAlpha;
    if (color.mAlpha > 0) {
        g->SetColor(color);
        g->DrawImageCel(image, 0, 0, plan.from);
    }
    color.mAlpha = nextAlpha;
    if (color.mAlpha > 0) {
        g->SetColor(color);
        g->DrawImageCel(image, 0, 0, plan.to);
    }
}
} // namespace EnhancedM2
