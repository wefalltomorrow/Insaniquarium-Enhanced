#pragma once

// M2 fixed-simulation/independent-presentation timing, no SDL dependency.
// This clock never advances game logic to meet a render deadline.
#include <algorithm>
#include <cmath>

namespace EnhancedM2 {

struct FramePlan {
    int simulationTicks = 0;
    bool present = false;
    double blend = 1.0;
};

class FrameClock {
    static constexpr double kSimulationMs = 28.0;
    static constexpr double kPresentationMs = 1000.0 / 60.0;

    double mSimulationMs = 0.0;
    double mPresentationMs = 0.0;

public:
    void Reset() {
        mSimulationMs = 0.0;
        mPresentationMs = 0.0;
    }

    FramePlan Advance(double elapsedMs) {
        FramePlan result;
        if (!std::isfinite(elapsedMs) || elapsedMs <= 0.0)
            return result;

        // A debugger pause, focus switch, or stall cannot trigger a huge
        // burst of game logic. The original engine also caps its backlog.
        elapsedMs = std::min(elapsedMs, 200.0);
        mSimulationMs += elapsedMs;
        mPresentationMs += elapsedMs;

        result.simulationTicks =
            std::min(static_cast<int>(mSimulationMs / kSimulationMs), 3);
        mSimulationMs -= result.simulationTicks * kSimulationMs;
        if (mSimulationMs >= kSimulationMs)
            mSimulationMs = std::fmod(mSimulationMs, kSimulationMs);

        result.present = (mPresentationMs + 1e-9 >= kPresentationMs);
        if (result.present)
            mPresentationMs = std::fmod(mPresentationMs, kPresentationMs);

        result.blend = std::clamp(mSimulationMs / kSimulationMs, 0.0, 1.0);
        return result;
    }
};

} // namespace EnhancedM2
