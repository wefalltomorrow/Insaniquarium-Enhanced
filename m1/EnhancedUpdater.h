#pragma once

namespace Sexy { class WinFishApp; }

namespace EnhancedUpdater {
    void Start(Sexy::WinFishApp* app);
    void Pump(Sexy::WinFishApp* app);
    void Download(Sexy::WinFishApp* app);
}
