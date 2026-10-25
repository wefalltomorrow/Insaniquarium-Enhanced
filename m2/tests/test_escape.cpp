#include "../EscapePolicy.hpp"
#include <cstdio>
#include <cstdlib>
using EnhancedM2::DecideEscape;
using EnhancedM2::EscapeAction;

static void Check(bool condition, const char* what) {
    if (!condition) { std::fprintf(stderr, "FAIL: %s\n", what); std::exit(1); }
}
int main() {
    Check(DecideEscape(true,true,false,false,false,false) ==
        EscapeAction::OpenOptions,"Esc opens pause menu during game");
    Check(DecideEscape(true,true,true,false,true,true) ==
        EscapeAction::CloseOptions,"Esc closes pause menu while paused");
    Check(DecideEscape(true,true,true,false,true,false) ==
        EscapeAction::Ignore,"other modal dialogs remain untouched");
    Check(DecideEscape(true,true,false,false,true,false) ==
        EscapeAction::Ignore,"non-pause modal remains untouched");
    Check(DecideEscape(false,false,false,false,false,false) ==
        EscapeAction::Ignore,"no board on title screen");
    Check(DecideEscape(true,false,false,false,false,false) ==
        EscapeAction::Ignore,"hidden board cannot receive pause shortcut");
    Check(DecideEscape(true,true,true,false,false,false) ==
        EscapeAction::Ignore,"other pause causes not overridden");
    Check(DecideEscape(true,true,false,true,false,false) ==
        EscapeAction::Ignore,"shop/pet/other screens keep focus");
    Check(DecideEscape(true,true,true,true,true,true) ==
        EscapeAction::CloseOptions,"active options is always closable");
    std::puts("PASS Esc opens/closes existing in-game pause menu only");
}
