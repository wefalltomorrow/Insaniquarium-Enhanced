#pragma once
// M2 render-only pause state. The gameplay scheduler and object world
// co-ordinates must not be changed when the user opens a modal dialog.
namespace EnhancedM2 {
inline void InvalidateHistoryOnPause(bool enabled, bool gameplayPaused,
                                     bool& hasVisualHistory) {
    // Clear stale previous positions as soon as the board is paused so
    // repeated 60 Hz drawings cannot oscillate between old simulation ticks.
    if (enabled && gameplayPaused) hasVisualHistory = false;
}
inline bool CanInterpolate(bool enabled, bool gameplayPaused,
                           bool hasVisualHistory) {
    return enabled && !gameplayPaused && hasVisualHistory;
}
}
