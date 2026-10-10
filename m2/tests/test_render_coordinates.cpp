#include "../RenderCoordinates.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

int main() {
    using EnhancedM2::SafeFishRenderOffset;
    int x = 999, y = 999;
    assert(SafeFishRenderOffset(10.0, 20.0, 14.0, 28.0, 14, 28, 0.5, x, y));
    assert(x == -2 && y == -4);
    assert(SafeFishRenderOffset(0.0, 0.0, 1.0, 1.0, 1, 1, 0.5, x, y));
    assert(x == 0 && y == 0);
    assert(!SafeFishRenderOffset(14, 20, -5.653851e214, 30, 14, 30, .2, x, y));
    assert(x == 0 && y == 0);
    assert(!SafeFishRenderOffset(-5.653851e214, 20, -5.653851e214, 30, 14, 30, .2, x, y));
    assert(x == 0 && y == 0);
    assert(!SafeFishRenderOffset(NAN, 20, 14, 30, 14, 30, .2, x, y));
    assert(!SafeFishRenderOffset(INFINITY, 20, 14, 30, 14, 30, .2, x, y));
    assert(!SafeFishRenderOffset(10, 20, 70, 30, 10, 30, .2, x, y));
    assert(!SafeFishRenderOffset(10, 20, 15, 30, 10, 30, INFINITY, x, y));
    assert(!SafeFishRenderOffset(10, 20, 15, 30, 10, 30, -0.1, x, y));
    assert(!SafeFishRenderOffset(-2147483648.0, 20, -2147483648.0, 30,
                                 2147483647, 30, .5, x, y));
    assert(EnhancedM2::RenderablePosition(149, 30));
    assert(!EnhancedM2::RenderablePosition(-5.653851e214, 30));
    std::cout << "PASS safe fish render-only coordinates\n";
}
