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
    {
        // Two real alien encounters moved less than 7px per 28ms tick.
        // Use the ordinary guarded offset, never simulation coordinates.
        ScopedObjectTranslation<GraphicsProbe> alienSprite(
            &g, true, false, prev, 197.0, 290.0, 201.4062, 289.8594,
            201, 290, .5);
        Verify(alienSprite.ShiftX() < 0, "alien moves between simulation samples");
        Verify(g.x == alienSprite.ShiftX(), "alien render-only shift active");
    }
    Verify(g.x == 0 && g.y == 0, "alien transform is restored");
    {
        ScopedObjectTranslation<GraphicsProbe> alienPaused(
            &g, true, true, prev, 197, 290, 201.4062, 289.8594,
            201, 290, .5);
        Verify(alienPaused.ShiftX() == 0 && !prev,
               "pausing clears alien visual history without moving the sprite");
    }
    prev = true;
    {
        // Other-type pets from the prior gameplay trace took sub-2px steps.
        // An uninterrupted graphics shift must not change any hitbox coords.
        ScopedObjectTranslation<GraphicsProbe> otherPet(
            &g, true, false, prev, 140.0, 300.0,
            141.0, 302.0, 141, 302, .25);
        Verify(otherPet.ShiftY() == -2,
               "other-pet render-only interpolation of small movements");
        Verify(g.y == -2, "other-pet translation applied only to Graphics");
    }
    Verify(g.x == 0 && g.y == 0, "other-pet translation restored");
    {
        ScopedObjectTranslation<GraphicsProbe> petPaused(
            &g, true, true, prev, 140.0, 300.0,
            141.0, 302.0, 141, 302, .25);
        Verify(petPaused.ShiftX() == 0 && petPaused.ShiftY() == 0 && !prev,
               "other-pet pause invalidates visual history");
    }
    prev = true;
    {
        ScopedObjectTranslation<GraphicsProbe> petTeleport(
            &g, true, false, prev, 140.0, 300.0,
            240.0, 302.0, 240, 302, .5);
        Verify(petTeleport.ShiftX() == 0 && petTeleport.ShiftY() == 0,
               "other-pet teleport guard remains active");
    }
    Verify(g.x == 0 && g.y == 0, "all visual translation operations balanced");
    std::puts("PASS M2 coin/food visual interpolation scope and pause guards");
}
