#include "../ObjectInterpolation.hpp"
#include <cstdio>
#include <cstdlib>
#include <limits>

struct GraphicsProbe {
    int x = 0, y = 0, calls = 0;
    void Translate(int dx, int dy) { x += dx; y += dy; ++calls; }
};
static void Verify(bool ok, const char* message) {
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", message); std::exit(1); }
}
int main() {
    using EnhancedM2::ScopedObjectTranslation;
    GraphicsProbe g;
    bool prev = true;
    {
        // Simulated coin/food moves from 100,20 to 102,22 in one 28ms tick;
        // halfway between ticks the sprite is one pixel behind its hitbox.
        ScopedObjectTranslation<GraphicsProbe> shift(
            &g, true, false, prev, 100, 20, 102, 22, 102, 22, .5);
        Verify(shift.ShiftX() == -1 && shift.ShiftY() == -1, "fractional render shift");
        Verify(g.x == -1 && g.y == -1, "sprite translated, object not mutated");
    }
    Verify(g.x == 0 && g.y == 0 && g.calls == 2,
           "RAII translation undone even on Draw early return");

    {
        ScopedObjectTranslation<GraphicsProbe> shift(
            &g, true, true, prev, 100, 20, 102, 22, 102, 22, .5);
        Verify(shift.ShiftX() == 0 && shift.ShiftY() == 0, "pause has no shift");
        Verify(!prev, "pause discards stale motion history");
    }
    prev = true;
    {
        ScopedObjectTranslation<GraphicsProbe> shift(
            &g, false, false, prev, 100, 20, 102, 22, 102, 22, .5);
        Verify(shift.ShiftX() == 0 && shift.ShiftY() == 0, "normal launcher unchanged");
    }
    {
        ScopedObjectTranslation<GraphicsProbe> shift(
            &g, true, false, prev, 100, 20, 200, 22, 200, 22, .5);
        Verify(shift.ShiftX() == 0 && shift.ShiftY() == 0, "teleports rejected");
    }
    {
        ScopedObjectTranslation<GraphicsProbe> shift(
            &g, true, false, prev, std::numeric_limits<double>::quiet_NaN(),
            20, 102, 22, 102, 22, .5);
        Verify(shift.ShiftX() == 0 && shift.ShiftY() == 0, "nonfinite rejected");
    }
    prev = true;
    {
        ScopedObjectTranslation<GraphicsProbe> regularCoin(
            &g, true, false, prev, 14, 183.5, 90.5714, 164.1429,
            90, 164, .38701);
        Verify(regularCoin.ShiftX() == 0 && regularCoin.ShiftY() == 0,
               "normal coin must reject a 77px teleport");
    }
    {
        ScopedObjectTranslation<GraphicsProbe> collectedCoin(
            &g, true, false, prev, 14, 183.5, 90.5714, 164.1429,
            90, 164, .38701, 96.0);
        Verify(collectedCoin.ShiftX() < -30 && collectedCoin.ShiftY() > 0,
               "collected coin homing should interpolate 77px movement");
    }
    Verify(g.x == 0 && g.y == 0, "coin homing graphics shift balanced");
    {
        ScopedObjectTranslation<GraphicsProbe> unrelatedTeleport(
            &g, true, false, prev, 14, 183.5, 120, 164.1429,
            120, 164, .38701, 96.0);
        Verify(unrelatedTeleport.ShiftX() == 0, "even collected coin guards large teleports");
    }
    Verify(g.x == 0 && g.y == 0, "all visual translation operations balanced");
    std::puts("PASS M2 coin/food visual interpolation scope and pause guards");
}
