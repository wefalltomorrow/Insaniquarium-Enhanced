#include "../FrameClock.hpp"
#include <cassert>
#include <cmath>
#include <cstdio>

static void verify(double refresh, double seconds) {
    EnhancedM2::FrameClock clock;
    const int iterations = static_cast<int>(refresh * seconds);
    int ticks = 0;
    int presents = 0;
    for (int i = 0; i < iterations; ++i) {
        auto frame = clock.Advance(1000.0 / refresh);
        ticks += frame.simulationTicks;
        presents += frame.present ? 1 : 0;
        assert(frame.simulationTicks <= 3);
        assert(frame.blend >= 0.0 && frame.blend <= 1.0);
    }
    int expectedTicks = static_cast<int>(1000.0 * seconds / 28.0);
    int expectedPresents = static_cast<int>(60.0 * seconds);
    assert(std::abs(ticks - expectedTicks) <= 1);
    assert(std::abs(presents - expectedPresents) <= 1);
    std::printf("PASS display %.0f Hz -> %d simulation ticks, %d presents / %.0f seconds\n",
                refresh, ticks, presents, seconds);
}
int main() {
    for (double hz : {60.0, 120.0, 144.0, 165.0, 240.0})
        verify(hz, 10.0);
    EnhancedM2::FrameClock clock;
    // After debugger pause, never fast-forward arbitrarily.
    assert(clock.Advance(2000).simulationTicks <= 3);
    clock.Reset();
    assert(clock.Advance(10.0).simulationTicks == 0);
    assert(clock.Advance(18.0).simulationTicks == 1);
    std::puts("PASS paused/stalled clock safeguards");
    return 0;
}
