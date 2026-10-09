#pragma once

namespace PopLib { class WinFishApp; }

namespace EnhancedUpdater {
    void Start(PopLib::WinFishApp* app);
    void Pump(PopLib::WinFishApp* app);
    void Download(PopLib::WinFishApp* app);
}
