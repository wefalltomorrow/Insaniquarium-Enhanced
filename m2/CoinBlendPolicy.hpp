#pragma once
#include <cstdlib>
namespace EnhancedM2 {
inline bool CoinBlendEnabled() {
    static const bool enabled = [] {
        const char* m2 = std::getenv("INSANIQUARIUM_M2_60FPS");
        const char* coin = std::getenv("INSANIQUARIUM_M2_COIN_BLEND");
        return m2 && m2[0] == '1' && m2[1] == '\0' &&
               coin && coin[0] == '1' && coin[1] == '\0';
    }();
    return enabled;
}
} // namespace EnhancedM2
