#pragma once
// M2 keyboard policy; pure C++ for regression tests. No game-state writes.
namespace EnhancedM2 {
enum class EscapeAction { Ignore, OpenOptions, CloseOptions };

inline EscapeAction DecideEscape(
    bool boardExists,
    bool boardVisible,
    bool gameplayPaused,
    bool otherScreenActive,
    bool anyDialog,
    bool optionsIsTopDialog)
{
    // The in-game Options dialog is the pause menu. Closing it returns
    // focus to the board through the game's existing KillDialog behaviour.
    if (optionsIsTopDialog)
        return EscapeAction::CloseOptions;

    // Don't dismiss warnings, update prompts, user naming dialogs, etc.
    // Or open a second pause dialog on top of another game screen.
    if (!boardExists || !boardVisible || gameplayPaused ||
        otherScreenActive || anyDialog)
        return EscapeAction::Ignore;

    return EscapeAction::OpenOptions;
}
} // namespace EnhancedM2
