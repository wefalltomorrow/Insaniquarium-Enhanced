#pragma once
// Coin/Food sprite interpolation only: no game-state, hitbox or save changes.
// The scoped translation balances even when Draw() returns early.
#include "RenderCoordinates.hpp"
#include "PauseInterpolation.hpp"

extern "C" bool gEnhancedM2Enabled;
extern "C" double gEnhancedM2Blend;

namespace EnhancedM2 {
template<class GraphicsT>
class ScopedObjectTranslation {
    GraphicsT* graphics_;
    int dx_ = 0, dy_ = 0;
public:
    ScopedObjectTranslation(GraphicsT* graphics, bool enabled,
                            bool paused, bool& haveHistory,
                            double previousX, double previousY,
                            double currentX, double currentY,
                            int gameX, int gameY, double blend,
                            double maxMovePerTick = 48.0)
        : graphics_(graphics) {
        InvalidateHistoryOnPause(enabled, paused, haveHistory);
        if (!graphics_ || !CanInterpolate(enabled, paused, haveHistory))
            return;
        if (SafeFishRenderOffset(previousX, previousY, currentX, currentY,
                                 gameX, gameY, blend, dx_, dy_,
                                 maxMovePerTick) &&
            (dx_ != 0 || dy_ != 0))
            graphics_->Translate(dx_, dy_);
    }
    ScopedObjectTranslation(const ScopedObjectTranslation&) = delete;
    ScopedObjectTranslation& operator=(const ScopedObjectTranslation&) = delete;
    ~ScopedObjectTranslation() {
        if (graphics_ && (dx_ != 0 || dy_ != 0))
            graphics_->Translate(-dx_, -dy_);
    }
    int ShiftX() const { return dx_; }
    int ShiftY() const { return dy_; }
};
} // namespace EnhancedM2
