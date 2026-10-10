# Insaniquarium Enhanced

A modern Windows x64 build of **Insaniquarium! Deluxe**, based on the community [WinFish decompilation](https://github.com/Vindirect/WinFish) and [SaMeiers' SDL3/PopLib native port](https://github.com/SaMeiers/insaniquarium-port). No executable hooking or proxy DLL patches.

## Downloads

| Release | Game source | Status |
| --- | --- | --- |
| [M1.2 in-game updater (Windows x64)](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/v0.2.2-m1-update) | WinFish [f919b3c](https://github.com/Vindirect/WinFish/commit/f919b3c241cfd611c547f1653fb3514f500f761b), October 8, 2026 | Native compilation verified; in-game update popup tested by user |
| [M1.1 menu update (Windows x64)](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/v0.2.1-m1-menu) | WinFish [f919b3c](https://github.com/Vindirect/WinFish/commit/f919b3c241cfd611c547f1653fb3514f500f761b), October 8, 2026 | Compiled and packaged; menu changes tested by user |
| [M1 preview (Windows x64)](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/v0.2.0-m1-preview) | WinFish [f919b3c](https://github.com/Vindirect/WinFish/commit/f919b3c241cfd611c547f1653fb3514f500f761b), October 8, 2026 | Native compilation verified; gameplay testing required |
| [M0 (Windows x64)](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/v0.1.0-m0) | WinFish [61ddba1](https://github.com/Vindirect/WinFish/commit/61ddba10056621c7857ea6f822139c39c76a4019), March 13, 2026 | Original known-compatible port baseline |

These builds are **pre-releases**: Windows x64 compilation, binary architecture and ZIP packaging passed automated checks, but this does not establish that every game mode works at runtime.

### What's different in M1?

M1 updates the game code to the latest WinFish revision used in the build, **32 commits newer than M0**, including upstream bug fixes for Virtual Tank, fish behaviour, bonuses and coins. It retains SaMeiers' Windows/SDL3 integration, game fixes and the PopLib framework. Two already-fixed fish-song applause patches are safely omitted after checking the current source; all other upstream port fixes remain enforced.

M1.1 restores the full **Hardware Acceleration** text in the Options menu and removes the **Register** button. **M1.2** replaces the old Check Updates browser link with an asynchronous in-game GitHub API check: it compares the embedded build version with published Windows x64 releases (including prereleases), displays an up-to-date message when appropriate, and offers a **Download / Later** prompt if a newer ZIP exists. Downloads launch only after confirmation; the game isn't silently updated. **Hardware Acceleration** is a legacy setting in the SDL3 build: the GPU renderer is selected automatically, and that checkbox is not a true GPU enable/disable switch.\n\nThe game uses its original 28 ms simulation interval (about 35.7 updates/second). A user confirmed M1 launches and runs around 36 FPS. **Neither M1 nor M0 currently includes independent 60 FPS rendering, native 4K framebuffer rendering or MSAA.** SDL3 scales the original 640x480 presentation into modern resizable/fullscreen windows. Scaling alone does not create native-resolution detail.

## Install

1. Download and extract a Windows x64 release ZIP.
2. Copy `data`, `images`, `music`, `properties`, `sounds`, and `fishsongs` from your own copy of Insaniquarium Deluxe (Steam/GOG) into the folder next to `InsaniquariumEnhanced.exe`.
3. Launch `InsaniquariumEnhanced.exe`.

**No original PopCap game assets are distributed by this project.** Existing save data should be backed up before testing pre-releases.

## M2 boundary diagnostics (experimental)

The October 10 Sprite Audit logs showed 18 nonrendered warp frames
(`images/warphole` / `images/warpglow`), and two nonrendered
`images/eggcrack2` terminal frames. The pinned WinFish source requests
frame 17 on 17-frame warp strips and frame 10 on a 10-frame egg strip;
the original renderer ignores those requests.

The [boundary-audit source patch](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/commit/5213766a9bbb08f52837d97b8fe6cd910a6b9309)
classifies **only** those exact frame/asset combinations as expected skips
and keeps malformed or different out-of-range requests as warnings. It does
not clamp animation frames or change how sprites render.

This patch also gives the objects, sprites and interpolation CSV logs separate
350,000-row budgets, improving coverage during longer M2 test sessions.
GitHub Actions validates the changes before publishing an experimental
Windows x64 release.

## Experimental M2 — independent 60 FPS presentation

[M2 is being tested in draft PR #5](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/pull/5), **not merged into `main`**. M1.2 remains the baseline build. The most recently **completed and published** M2 test is [Sprite Sentinels](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/releases/tag/m2-sprite-sentinels-20261010). Newer M2 Fish Initialization and Render Guard changes are undergoing Windows compilation; do not treat a queued or running Actions job as a downloadable release.

The experimental M2 scheduler preserves **one gameplay update every 28 ms (~35.7 Hz)** while targeting **60 rendered frames per second**. Fish movement receives render-only positional interpolation. Other animations and moving object classes have *not* been fully interpolated, and the game still presents a **640×480 logical framebuffer** rather than native 4K. Native-resolution rendering and antialiasing remain future work.

### Running the M2 test

1. Extract the published M2 ZIP into a **separate folder** so the working M1.2 installation stays intact.
2. Copy the original game folders `data`, `images`, `music`, `properties`, `sounds`, and `fishsongs` alongside the new executable.
3. Run **`Start M2.cmd`** for 60 FPS presentation with normal diagnostic overhead.
4. Run **`Start M2 Debug.cmd`** instead when collecting troubleshooting logs. Esc toggles the gameplay Options pause menu; it does not dismiss unrelated modal dialogs.
5. To use the nonexperimental timing path, start `InsaniquariumEnhanced.exe` directly.

The opt-in debug launcher writes `M2Timing.log`, `M2DebugFrames.csv`, `M2DebugEvents.csv`, `M2DebugObjects.csv`, `M2DebugSprites.csv`, `M2DebugInterpolation.csv`, `M2DebugInvalidSprites.csv` and `M2DebugSkippedSprites.csv`. The skipped-sprite file tracks known no-draw sentinel calls; it does not indicate corrupt animations. Report genuinely unexpected calls using the invalid-sprite file.

The October 10 recording showed ~35.7 gameplay Hz and ~60 presentation FPS, along with a fish acquiring an extreme simulation X coordinate on its first update. The experimental branch has two additional **unreleased until Windows CI succeeds** source changes: a render-only guard against unsafe coordinate conversion and a fix that initialises newly spawned fish's positive horizontal velocity. Neither has been validated in user gameplay yet.

## Faster Windows M2 builds

The experimental M2 GitHub Actions workflow uses **MSVC + Ninja + sccache**
to reuse unchanged compiled C/C++ files. The October 10 Boundary Audit build
reported 693 compiler cache hits and 9 misses (98.72% hit rate), reducing
the complete workflow from around 16 minutes to under 5 minutes.

A second, separate **immutable source cache** stores the exact pinned
native port, WinFish, PopLib and required Git submodules before any generated
or modified sources are written. On hits, it skips network clones and verifies
the pinned revision SHAs. The [verified warm-cache run](https://github.com/wefalltomorrow/Insaniquarium-Enhanced/actions/runs/38025453987)
completed in **4m 11s**, with 700 compiler cache hits, 2 misses (99.72%),
and a successful experimental Windows x64 release. This is a repeatable
measurement, not a promise of identical timing on every GitHub runner.

The next experimental build investigates turning off unnecessary C++20 module
dependency scanning in CMake. Until its CI run passes, the warm-cache build
above remains the known-good release.

Neither cache includes original PopCap game assets. Normal source and
gameplay behaviour is unchanged, and existing PE x64/release checks remain.

### Longer M2 diagnostics

Detailed object and fish interpolation traces now record every presentation
frame through frame 9,999, then one out of every three frames thereafter.
Each stream retains its own 350,000-row cap. This reduces premature
truncation during extended tests while keeping per-frame timing, all warning
checks, skipped/invalid sprite classification and game behaviour unchanged.
On the 27,259-frame CacheWarm log, the new scheme would require
approximately 311,000 object rows rather than exhausting 350,000
rows before the session ends. The ratio is a budget estimate, not a claim
that the new recorder has been tested in-game.

### Coin and food interpolation (experimental)

M2 now applies scoped, render-only positional interpolation to coin and food
sprites, in addition to fish. Object movement/collision coordinates and save
data stay on the original 28 ms simulation ticks; visual transforms are restored
even on early Draw returns. During M2 mode, coin/food fish-song updates run on
simulation ticks, not repeated presentation calls. The patch is opt-in and
does not change the M1.2 stable release. Windows CI has source-anchor checks
and tests for pause, teleport and invalid-position safety.

The M2 debug launcher also writes `M2DebugObjectMotion.csv` with coin/food simulation positions, render shifts, frame blend, pause status and visual-history state. It is independent of the fish-only `M2DebugInterpolation.csv` and uses the same long-session sampling policy.

### Collected-coin animation smoothing (M2 experimental)

On the October 10 Motion Diagnostics recording, collected coins moved
more than 48 pixels in 21 consecutive simulation steps, up to 76.57px.
The original coin-collection homing behavior was visible in the generated
native port, but the 48px teleport guard prevented rendering interpolation
on these early collection steps. M2 now uses a bounded 96px per-tick
interpolation limit **only when the coin is in collected/homing state**.
Fish, food and uncollected coins retain the previous 48px limit.
Coin positions, collision/click handling, collection rate, audio and
saved game state are unchanged. CI includes a 77px homing regression test,
pause checks, and a >96px teleport rejection test.

### Automatic M2 diagnostic report

Experimental ZIPs now include **Analyze M2 Logs.cmd** and
`AnalyzeM2Logs.py`. After a debug session, close the game and run
the batch file from the extracted game folder (requires Windows Python 3).
It writes `M2DiagnosticReport.txt` summarising recorded simulation/display
rates, frame stalls, pause events, invalid sprite calls, fish/coin/food
interpolation coverage and paused-frame motion errors. This is a read-only
analysis of the CSVs; it cannot directly measure monitor/GPU presentation
or certify every audio/visual effect. The analyzer has synthetic CI fixtures
for clean runs, missing logs, invalid sprite calls and moving paused objects.

### M2 pets and effects diagnostic coverage

The experimental **M2 Effects Audit** adds read-only simulation-update,
sprite-draw and draw-state mutation probes for `OtherTypePet`, `Missle`
(the original source spelling) and `Shot` effects. Aliens already have
a probe; fish-type pets inherit the fish drawing path. Additional counters
appear at the end of `M2DebugFrames.csv`, preserving the older column order.

The one-click report identifies the exact frame, tick and render duration
for any `presented=0` entry. It also distinguishes object types that were
**not observed** during a recording from object types that were verified.
These are game-side metrics and do not establish independent GPU/monitor
presentation or complete smoothness of all remaining visual effects.

### M2 alien interpolation (experimental)

Following the Effects Audit raw logs (8,409 presented frames, 5,006
original simulation ticks), two alien encounters were traced over 564
draw records. The largest adjacent single-tick alien position changes
were 6.28px horizontally and 3.28px vertically. No alien position or
animation-cell changes were observed between ticks. The M2 experiment
adds **render-only** alien sprite translation using the same pause-safe,
48px teleport-protected interpolation helper as other game objects.
AI, target selection, hitboxes, collisions and save data stay on the
original 28ms tick. Alien offsets are logged to M2DebugObjectMotion.csv.
Other pets, missiles and shot effects are not interpolated by this change.

### M2 trace integrity and pet motion audit

The optional `Analyze M2 Logs.cmd` now checks each CSV for malformed or
unfinished rows, inconsistent end-frame numbers and the 350,000-row
detail limit. Differences in the final recorded frame are flagged as
**possible** partial/mixed captures—not automatically a gameplay failure,
because some objects can legitimately stop producing trace rows.

`M2DebugObjects.csv` is also summarised by object kind, including
individual moving versus stationary pets, aliens, missiles and shot effects.
Fish-type pets (which inherit `Fish::Draw`) now have distinct
`fish_pet` drawing and simulation counters, while preserving original
gameplay, AI and collision handling. A missing or stationary pet is not
proof that every pet animation is smooth at 60 FPS.

The trace analyzer still measures game-side diagnostics only; successful
CSV checks do not establish physical monitor frame delivery.

### Fish-type pet smoothing (M2 experimental)

Raw **M2 Trace Audit** recordings separated 37,457 ordinary fish draws
(26,363 with nonzero render interpolation) from 15,775 fish-type pet
draws (**zero** with nonzero interpolation), despite 7,239 simulated
pet movements. This is because `FishTypePet::Update` overrides
`Fish::Update` but inherits `Fish::Draw`; prior M2 history sampling
and its 28ms sound callback only ran in `Fish::Update`.

The experimental `m2/apply_fish_pet.py` restores per-simulation-tick
previous-position sampling and the sound callback in
`FishTypePet::Update` for M2 only. Pause and teleport safety
remain in the inherited draw path. It makes **no changes** to AI,
collisions, save data, pet simulation movement, ordinary fish or M1.2.

`Analyze M2 Logs.cmd` now compares actual nonzero visual offsets
for ordinary fish and fish-type pets by their respective object IDs,
so an in-game recording can confirm or refute the effect.

### Other-type pet interpolation (M2 experimental)

The earlier **M2 Trace Audit** included four `other_pet` object IDs,
295 simulation movements and observed maximum adjacent-tick changes
around 0.67 px horizontally and 1.62 px vertically. The latest FishPet
recording contained just one stationary other-type pet, so that
recording alone was not sufficient to verify smoothing.

The experimental `m2/apply_other_pet.py` now samples other-pet visual
history in `OtherTypePet::Update` and uses scoped Graphics-only
translation during `OtherTypePet::Draw`. The normal 48px per-tick
teleport limit and pause-history invalidation apply. The
`UpdateFishSongMgr` callback runs on the 28ms simulation update
rather than repeated draw calls in M2 mode.

Other-pet movement offsets are included in
`M2DebugObjectMotion.csv`. **No other-pet smoothness claim** is made
until gameplay logs show nonzero `other_pet` offsets while moving.
The normal/non-M2 path, AI, hitboxes, collisions, clicks and saves
are not changed. Missiles and shot-effect animation remain unmodified.

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
