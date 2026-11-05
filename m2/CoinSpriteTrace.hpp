#pragma once
#include "DebugTrace.hpp"

namespace M2Debug {
// Resolved draw request; transform and clip are verbatim, before rasterization.
template<class Graphics, class Image>
void RecordCoinSprite(Recorder& recorder, Graphics* g, Image* image,
                      const void* owner, unsigned long long lifetime,
                      int type, bool shell, int cel, int row, int x, int y,
                      bool paused, bool collected, int disappear) {
    if (!recorder.Active() || !image) return;
    CoinSpriteState s;
    s.object = owner; s.lifetime = lifetime; s.type = type;
    s.shell = shell; s.image = image; s.cel = cel; s.row = row;
    s.imageLifetime = image->mM2ImageIdentity.Lifetime();
    s.reportedPixelRevision = image->mM2ImageIdentity.ReportedRevision();
    s.width = image->mWidth; s.height = image->mHeight;
    s.cols = image->mNumCols; s.rows = image->mNumRows;
    s.x = x; s.y = y;
    s.transX = g->mTransX; s.transY = g->mTransY;
    s.scaleX = g->mScaleX; s.scaleY = g->mScaleY;
    s.originX = g->mScaleOrigX; s.originY = g->mScaleOrigY;
    s.clipX = g->mClipRect.mX; s.clipY = g->mClipRect.mY;
    s.clipW = g->mClipRect.mWidth; s.clipH = g->mClipRect.mHeight;
    s.colorized = g->GetColorizeImages();
    if (s.colorized) {
        const auto& c = g->GetColor();
        s.red = c.mRed; s.green = c.mGreen; s.blue = c.mBlue; s.alpha = c.mAlpha;
    }
    s.drawMode = g->GetDrawMode();
    s.paused = paused; s.collected = collected; s.disappear = disappear;
    recorder.CoinSprite(s);
}
}
