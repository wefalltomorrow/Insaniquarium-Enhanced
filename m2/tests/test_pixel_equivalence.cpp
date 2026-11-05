#include "../SmokePixels.hpp"
#include <cstdlib>
#include <iostream>
using namespace EnhancedM2;
// Independent 64-bit rational reference for straight ARGB output.
// Does not use the equal-opacity optimization or packed-channel arithmetic.
std::uint32_t Reference(std::uint32_t a,std::uint32_t b,unsigned w) {
    if(w==0) return a;
    if(w>=256) return b;
    const std::uint64_t left=(a>>24)*(256-w), right=(b>>24)*w;
    const auto coverage=left+right;
    if(!coverage) return 0;
    std::uint32_t out=static_cast<std::uint32_t>((coverage+128)/256)<<24;
    for(unsigned shift : {0u,8u,16u}) {
        const auto numerator=((a>>shift)&255)*left+((b>>shift)&255)*right;
        out |= static_cast<std::uint32_t>((2*numerator+coverage)/(2*coverage))<<shift;
    }
    return out;
}
int main() {
    std::uint64_t checks=0;
    const auto check=[&](std::uint32_t a,std::uint32_t b,unsigned w) {
        ++checks;
        if(BlendSmokePixel(a,b,w)!=Reference(a,b,w)) {
            std::cerr << "Pixel mismatch: " << a << "," << b << "," << w << "\n";
            std::exit(1);
        }
    };
    std::uint32_t random=0x91e10da5;
    const auto next=[&]() { random^=random<<13; random^=random>>17; random^=random<<5; return random&0xffffffu; };
    // Every alpha pair and weight, varying all RGB channels deterministically.
    for(unsigned aa=0;aa<256;++aa) for(unsigned ab=0;ab<256;++ab) for(unsigned w=0;w<=256;++w) {
        const auto a=(aa<<24)|next(), b=(ab<<24)|next();
        check(a,b,w);
    }
    // Exhaustive channel pairs/weights at three nonzero equal opacities.
    for(unsigned alpha : {1u,127u,255u})
        for(unsigned a=0;a<256;++a) for(unsigned b=0;b<256;++b) for(unsigned w=0;w<=256;++w)
            check((alpha<<24)|(a*0x010101u),(alpha<<24)|(b*0x010101u),w);
    check(0x00123456,0x00654321,128);
    check(0x01020304,0xfefdfcfb,257);
    check(0x01020304,0xfefdfcfb,~0u);
    std::cout << "PASS " << checks << " exact pixel comparisons\n";
}
