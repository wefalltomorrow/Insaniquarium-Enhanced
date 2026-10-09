# Insaniquarium Enhanced

A modern Windows x64 build of **Insaniquarium! Deluxe**, based on the community [WinFish decompilation](https://github.com/Vindirect/WinFish) and [SaMeiers' SDL3/PopLib native port](https://github.com/SaMeiers/insaniquarium-port). No executable hooking or proxy DLL patches.

## Downloads

| Release | Game source | Status |
| --- | --- | --- |
| [M1.1 menu update (Windows x64)](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/v0.2.1-m1-menu) | WinFish [f919b3c](https://github.com/Vindirect/WinFish/commit/f919b3c241cfd611c547f1653fb3514f500f761b), October 8, 2026 | Compiled and packaged; menu changes need gameplay validation |\n| [M1 preview (Windows x64)](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/v0.2.0-m1-preview) | WinFish [f919b3c](https://github.com/Vindirect/WinFish/commit/f919b3c241cfd611c547f1653fb3514f500f761b), October 8, 2026 | Native compilation verified; gameplay testing required |
| [M0 (Windows x64)](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/v0.1.0-m0) | WinFish [61ddba1](https://github.com/Vindirect/WinFish/commit/61ddba10056621c7857ea6f822139c39c76a4019), March 13, 2026 | Original known-compatible port baseline |

Both are **pre-releases**: Windows x64 compilation, binary architecture and ZIP packaging passed automated checks, but this does not establish that every game mode works at runtime.

### What's different in M1?

M1 updates the game code to the latest WinFish revision used in the build, **32 commits newer than M0**, including upstream bug fixes for Virtual Tank, fish behaviour, bonuses and coins. It retains SaMeiers' Windows/SDL3 integration, game fixes and the PopLib framework. Two already-fixed fish-song applause patches are safely omitted after checking the current source; all other upstream port fixes remain enforced.

M1.1 restores the full **Hardware Acceleration** text in the Options menu, removes the **Register** button, and routes **Check Updates** to this project's GitHub Releases page. **Hardware Acceleration** is a legacy setting in the SDL3 build: the GPU renderer is selected automatically, and that checkbox is not a true GPU enable/disable switch.\n\nThe game uses its original 28 ms simulation interval (about 35.7 updates/second). A user confirmed M1 launches and runs around 36 FPS. **Neither M1 nor M0 currently includes independent 60 FPS rendering, native 4K framebuffer rendering or MSAA.** SDL3 scales the original 640x480 presentation into modern resizable/fullscreen windows. Scaling alone does not create native-resolution detail.

## Install

1. Download and extract a Windows x64 release ZIP.
2. Copy `data`, `images`, `music`, `properties`, `sounds`, and `fishsongs` from your own copy of Insaniquarium Deluxe (Steam/GOG) into the folder next to `InsaniquariumEnhanced.exe`.
3. Launch `InsaniquariumEnhanced.exe`.

**No original PopCap game assets are distributed by this project.** Existing save data should be backed up before testing pre-releases.

## Development

- [M1 Windows build workflow](.github/workflows/windows-m1.yml): Windows Server 2022, Visual Studio 2022, CMake x64, SDL3, libopenmpt
- [Source reconciliation script](m1/prepare_source.py): verifies the newer WinFish applause fix and retains all remaining upstream port patches
- [M0 build workflow](.github/workflows/windows.yml): original pinned baseline

Every release pins the game and port revisions for reproducibility. Builds download source and dependencies through GitHub Actions rather than copying proprietary files or including old executable patches.

### Next

- Verify the new source in Adventure, Time Trial and Virtual Tank, including music and save/load
- Test mouse and cursor coordinates with window resize, maximize, DPI scaling and multiple monitors
- Decouple rendering from the 28 ms game simulation and add render-only motion interpolation
- Add a true high-resolution rendering target and test AA/texture filtering without stretching, cropping or changing input coordinates

Window/DPI improvements are being developed and compiled separately, so experimental changes do not replace the baseline unless they pass testing.

## Credits and licence

- [Vindirect/WinFish](https://github.com/Vindirect/WinFish): original reverse-engineered game code
- [SaMeiers/insaniquarium-port](https://github.com/SaMeiers/insaniquarium-port): SDL3/PopLib port and compatibility/gameplay fixes
- [SaMeiers/PopLib](https://github.com/SaMeiers/PopLib) and [Team PopWork/PopLib](https://github.com/teampopwork/PopLib): framework and improvements

Our port-related work is distributed under [AGPL-3.0](LICENSE), reflecting the upstream port and framework. Original PopCap framework and third-party licences continue to apply. Insaniquarium Deluxe and its assets belong to their respective owners. This project is unaffiliated with PopCap or EA.
