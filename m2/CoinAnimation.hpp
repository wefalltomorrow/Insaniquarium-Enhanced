#pragma once
#include "SmokePixels.hpp"
#include <algorithm>
#include <vector>

namespace EnhancedM2 {
struct CoinAnimationState {
    int type = 0, timer = 0, cel = 0, divisor = 2, mode = 0;
    bool shell = false, collected = false;
    int fade = 0;
    bool Eligible() const {
        return (type == 1 || type == 2) && !shell && !collected && fade == 0 &&
               (divisor == 2 || divisor == 4) && timer >= 0 && timer < 80 &&
               cel == (timer / divisor) % 10;
    }
};

struct CoinBlendResult {
    int from, to;
    double mix = 1.0;
    const char* reason = "state";
};

// Owner-local, observation-only history. Never retain a source image pointer.
// A full ten-cel row is compared, including raw writes without BitsChanged.
// Per owner maximum: 202.5 KiB row + 20.25 KiB output, allocated lazily.
// CPU pixel equality between observations is not a GPU synchronization proof.
template<class MemoryImage> class CoinAnimation {
    CoinAnimationState previous;
    std::vector<std::uint32_t> rowPixels;
    std::unique_ptr<MemoryImage> composed;
    std::uint64_t lifetime = 0, revision = 0;
    int sheetWidth = 0, sheetHeight = 0;
    bool valid = false;
    const char* captureReason = "history";

    static bool Layout(const MemoryImage* source) {
        return source && source->mNumCols == 10 && source->mNumRows == 5 &&
               source->mWidth > 0 && source->mWidth <= 720 && source->mWidth % 10 == 0 &&
               source->mHeight > 0 && source->mHeight <= 360 && source->mHeight % 5 == 0;
    }
public:
    void Reset(const char* reason = "history") { valid = false; captureReason = reason; }

    void Capture(bool enabled, const CoinAnimationState& state, MemoryImage* source) {
        Reset();
        if (!enabled) { captureReason = "disabled"; return; }
        if (!state.Eligible()) { captureReason = "state"; return; }
        if (!Layout(source)) { captureReason = "layout"; return; }
        if (!source->mBits) { captureReason = "nonresident"; return; }
        const auto id = source->mM2ImageIdentity.Lifetime();
        const auto rev = source->mM2ImageIdentity.ReportedRevision();
        if (!id || !rev) { captureReason = "identity"; return; }
        const int count = source->mWidth * (source->mHeight / 5);
        const auto* start = source->mBits + (state.type - 1) * count;
        try { rowPixels.assign(start, start + count); }
        catch (const std::bad_alloc&) { captureReason = "allocation"; return; }
        previous = state;
        sheetWidth = source->mWidth; sheetHeight = source->mHeight;
        lifetime = id; revision = rev;
        valid = true;
    }

    MemoryImage* Prepare(bool enabled, bool paused, bool normalGraphics,
                         const CoinAnimationState& state, MemoryImage* source,
                         double mix, CoinBlendResult& result) {
        result = {state.cel, state.cel, 1.0, "state"};
        const auto reject = [&](const char* reason) -> MemoryImage* {
            Reset(reason); result.reason = reason; return nullptr;
        };
        if (!enabled) return reject("disabled");
        if (paused || !state.Eligible()) return reject("state");
        if (!normalGraphics) return reject("graphics");
        if (!valid) { result.reason = captureReason; return nullptr; }
        if (state.type != previous.type || state.divisor != previous.divisor ||
            state.mode != previous.mode || state.timer != previous.timer + 1 ||
            !std::isfinite(mix) || mix < 0.0 || mix > 1.0) return reject("sequence");
        // Unchanged cels use the original drawing. Never blend a loop boundary.
        if (state.cel == previous.cel) { result.reason = "held"; return nullptr; }
        if (state.cel != previous.cel + 1) return reject("sequence");
        if (!Layout(source) || source->mWidth != sheetWidth || source->mHeight != sheetHeight)
            return reject("layout");
        if (!source->mBits) return reject("nonresident");
        if (source->mM2ImageIdentity.Lifetime() != lifetime ||
            source->mM2ImageIdentity.ReportedRevision() != revision) return reject("identity");
        const int width = sheetWidth / 10, height = sheetHeight / 5;
        const auto* currentRow = source->mBits + (state.type - 1) * sheetWidth * height;
        if (!std::equal(rowPixels.begin(), rowPixels.end(), currentRow)) return reject("pixels");
        if (mix == 0.0 || mix == 1.0) {
            result = {previous.cel, state.cel, mix, "endpoint"};
            return nullptr;
        }
        try {
            if (!composed) composed = std::make_unique<MemoryImage>();
            if (composed->mWidth != width || composed->mHeight != height)
                composed->Create(width, height);
            composed->mImageFlags = source->mImageFlags;
            auto* dst = composed->GetBits();
            if (!dst) return reject("allocation");
            const unsigned weight = static_cast<unsigned>(mix * 256 + 0.5);
            for (int y = 0; y < height; ++y)
                for (int x = 0; x < width; ++x)
                    dst[y * width + x] = BlendSmokePixel(
                        currentRow[y * sheetWidth + previous.cel * width + x],
                        currentRow[y * sheetWidth + state.cel * width + x], weight);
            composed->BitsChanged();
            result = {previous.cel, state.cel, mix, "composed"};
            return composed.get();
        } catch (const std::bad_alloc&) { return reject("allocation"); }
    }
};

template<class Graphics, class Image>
void DrawCoinFrame(Graphics* g, Image* source, Image* composed,
                   int x, int y, int row, const CoinBlendResult& result) {
    if (composed) g->DrawImage(composed, x, y);
    else g->DrawImageCel(source, x, y, result.mix == 0.0 ? result.from : result.to, row);
}
} // namespace EnhancedM2
