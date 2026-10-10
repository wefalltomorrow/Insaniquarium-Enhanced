#pragma once
// Guard experimental sprite-only interpolation against unrepresentable
// coordinates. Simulation, collision and save state are never modified.
#include <cmath>
#include <limits>

namespace EnhancedM2 {
inline bool RenderableCoordinate(double value) {
    return std::isfinite(value) &&
           value >= static_cast<double>(std::numeric_limits<int>::min()) &&
           value <= static_cast<double>(std::numeric_limits<int>::max());
}
inline bool RenderablePosition(double x, double y) {
    return RenderableCoordinate(x) && RenderableCoordinate(y);
}

inline bool SafeFishRenderOffset(double previousX, double previousY,
                                 double currentX, double currentY,
                                 int gameX, int gameY, double blend,
                                 int& offsetX, int& offsetY) {
    offsetX = offsetY = 0;
    if (!RenderablePosition(previousX, previousY) ||
        !RenderablePosition(currentX, currentY) ||
        !std::isfinite(blend) || blend < 0.0 || blend > 1.0)
        return false;

    // Preserve the previous teleport/spawn rejection semantics.
    if (std::abs(currentX - previousX) >= 48.0 ||
        std::abs(currentY - previousY) >= 48.0)
        return false;

    const double renderX = previousX + (currentX - previousX) * blend;
    const double renderY = previousY + (currentY - previousY) * blend;
    if (!RenderablePosition(renderX, renderY))
        return false;

    // Round while safely inside the integer range, then subtract using a
    // wider type so an extreme game coordinate cannot overflow an int.
    const long long dx = std::llround(renderX) - static_cast<long long>(gameX);
    const long long dy = std::llround(renderY) - static_cast<long long>(gameY);
    if (dx < std::numeric_limits<int>::min() ||
        dx > std::numeric_limits<int>::max() ||
        dy < std::numeric_limits<int>::min() ||
        dy > std::numeric_limits<int>::max())
        return false;

    offsetX = static_cast<int>(dx);
    offsetY = static_cast<int>(dy);
    return true;
}
}  // namespace EnhancedM2
