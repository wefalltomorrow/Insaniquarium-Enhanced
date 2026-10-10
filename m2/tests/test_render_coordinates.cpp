#include "../RenderCoordinates.hpp"
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <iostream>
#include <limits>

static void Check(bool ok, const char* label = "render coordinate invariant") {
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", label); std::exit(1); }
}

int main() {
    using EnhancedM2::SafeFishRenderOffset;
    int x = 999, y = 999;
    Check(SafeFishRenderOffset(10.0, 20.0, 14.0, 28.0, 14, 28, 0.5, x, y));
    Check(x == -2 && y == -4);
    Check(SafeFishRenderOffset(0.0, 0.0, 1.0, 1.0, 1, 1, 0.5, x, y));
    Check(x == 0 && y == 0);
    Check(!SafeFishRenderOffset(14, 20, -5.653851e214, 30, 14, 30, .2, x, y));
    Check(x == 0 && y == 0);
    Check(!SafeFishRenderOffset(-5.653851e214, 20, -5.653851e214, 30, 14, 30, .2, x, y));
    Check(x == 0 && y == 0);
    Check(!SafeFishRenderOffset(NAN, 20, 14, 30, 14, 30, .2, x, y));
    Check(!SafeFishRenderOffset(INFINITY, 20, 14, 30, 14, 30, .2, x, y));
    Check(!SafeFishRenderOffset(10, 20, 70, 30, 10, 30, .2, x, y));
    Check(!SafeFishRenderOffset(10, 20, 15, 30, 10, 30, INFINITY, x, y));
    Check(!SafeFishRenderOffset(10, 20, 15, 30, 10, 30, -0.1, x, y));
    Check(!SafeFishRenderOffset(-2147483648.0, 20, -2147483648.0, 30,
                                 2147483647, 30, .5, x, y));
    Check(EnhancedM2::RenderablePosition(149, 30));
    Check(!EnhancedM2::RenderablePosition(-5.653851e214, 30));
    std::cout << "PASS safe fish render-only coordinates\n";
}
