# Insaniquarium Enhanced

A Windows x64 rebuild of **Insaniquarium! Deluxe** using the [WinFish decompilation](https://github.com/Vindirect/WinFish) and the [SaMeiers native SDL3/PopLib port](https://github.com/SaMeiers/insaniquarium-port).

## Current milestone: M0

M0 is the **native x64 baseline**. It builds the decompiled game with SDL3 and fixes already present in the upstream native port. It is **not yet a native 4K or independent 60 FPS renderer**, and no such feature is claimed for this build.

The source is fetched in the GitHub Actions workflow with submodules, preserving the upstream port's *known-compatible* WinFish revision. Updating to the latest game decompilation is planned after the baseline compiles and launches.

### Get the game

See [Releases](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases) for Windows builds. The ZIP contains the game executable and any required runtime libraries, **not the copyrighted game artwork, sound or music**. To play, copy the `data`, `images`, `music`, `properties`, `sounds`, and `fishsongs` directories from your purchased Insaniquarium Deluxe installation next to `InsaniquariumEnhanced.exe`. The game has not been runtime-tested until someone launches it with those files.

### Build

The workflow at [`.github/workflows/windows.yml`](.github/workflows/windows.yml) builds on **Windows Server 2022 / Visual Studio 2022** and generates `InsaniquariumEnhanced-M0-Win64.zip` from the upstream source. Manual build requirements are Visual Studio 2022, CMake 3.26+, Git Bash and Python 3.

A successful workflow can publish a GitHub **pre-release** only after compiling and inspecting the x64 executable. It also uploads the packaged executable as a workflow artifact.

### Source, credits and licence

- [Vindirect/WinFish](https://github.com/Vindirect/WinFish): reverse-engineered game source
- [SaMeiers/insaniquarium-port](https://github.com/SaMeiers/insaniquarium-port): portable SDL3/PopLib integration, builds and gameplay fixes
- [SaMeiers/PopLib](https://github.com/SaMeiers/PopLib): enhanced framework
- [Team PopWork](https://github.com/teampopwork/PopLib): upstream PopLib project

The port and modified framework are AGPL-3.0 licensed; the original PopCap framework license and third-party notices still apply. See [the port license](https://github.com/SaMeiers/insaniquarium-port/blob/main/LICENSE) and its dependency notices. **Original commercial game assets are not distributed.**

This project is independent, unaffiliated with PopCap or EA.
