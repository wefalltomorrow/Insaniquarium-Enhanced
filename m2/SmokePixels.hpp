#pragma once
#include "SmokeAnimation.hpp"
#include <cstdint>
#include <memory>
#include <new>

namespace EnhancedM2 {
// Interpolate coverage and premultiplied RGB, then return straight ARGB8888
// for PopLib's normal image draw. Hidden RGB in transparent pixels contributes
// nothing. Integer weight has 1/256 resolution; endpoints remain original draws.
inline std::uint32_t BlendSmokePixel(std::uint32_t a, std::uint32_t b, unsigned w) {
    if (w == 0) return a;
    if (w >= 256) return b;
    const unsigned aa = (a >> 24) * (256 - w), ab = (b >> 24) * w;
    const unsigned coverage = aa + ab;
    if (!coverage) return 0;
    std::uint32_t result = ((coverage + 128) / 256) << 24;
    for (unsigned shift : {0u, 8u, 16u}) {
        const unsigned channel = (((a >> shift) & 255) * aa +
                                  ((b >> shift) & 255) * ab + coverage / 2) / coverage;
        result |= channel << shift;
    }
    return result;
}

// One lazily allocated cel per Shot, destroyed with its owner. No global cache
// retains resource pointers past reload/shutdown. Source pixels are never edited.
template<class MemoryImage> class SmokePixelBuffer {
    std::unique_ptr<MemoryImage> image;
public:
    MemoryImage* Prepare(MemoryImage* source, SmokeFramePlan& plan) {
        if (!plan.transition || plan.mix == 0.0 || plan.mix == 1.0) return nullptr;
        const auto fallback = [&]() -> MemoryImage* {
            plan = {plan.to, plan.to, 1.0, false};
            return nullptr;
        };
        if (!source || !std::isfinite(plan.mix) || plan.mix < 0 || plan.mix > 1 ||
            source->mNumRows != 1 || source->mNumCols <= 0 ||
            source->mNumCols > 64 || source->mWidth <= 0 ||
            source->mWidth % source->mNumCols != 0 ||
            source->mHeight <= 0 || source->mHeight > 128 ||
            plan.from < 0 || plan.from >= source->mNumCols ||
            plan.to != plan.from + 1 || plan.to >= source->mNumCols)
            return fallback();
        const int width = source->mWidth / source->mNumCols;
        if (width <= 0 || width > 128) return fallback();
        try {
            const auto* src = source->GetBits();
            if (!src) return fallback();
            if (!image) image = std::make_unique<MemoryImage>();
            if (image->mWidth != width || image->mHeight != source->mHeight)
                image->Create(width, source->mHeight);
            auto* dst = image->GetBits();
            if (!dst) return fallback();
            const unsigned weight = static_cast<unsigned>(plan.mix * 256 + 0.5);
            for (int y = 0; y < source->mHeight; ++y)
                for (int x = 0; x < width; ++x)
                    dst[y * width + x] = BlendSmokePixel(
                        src[y * source->mWidth + plan.from * width + x],
                        src[y * source->mWidth + plan.to * width + x], weight);
            image->BitsChanged();
            return image.get();
        } catch (const std::bad_alloc&) {
            return fallback();
        }
    }
};
} // namespace EnhancedM2
