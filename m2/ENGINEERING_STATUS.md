# M2 engineering handover â€” 24 October 2026

This is the current engineering status. Older appended README sections describe
historical stages and may contradict later implementations. Keep evidence levels
separate: source, unit tests, Windows compilation, recorded runtime and visual
user acceptance are different claims.

## Baseline and protected branch

- Stable M1.2 `main`: `39a581e009767dea9e6829912c201f18b125f16d`.
  Do not merge M2 without explicit user permission.
- Recovered M2 baseline: `1e39752c4a13d84dd55e997f89ce40e00d9a05d3`,
  `feature/m2-fixed-timestep`. Open PR #5 targets main; it is not approval to merge.
- Latest published baseline at recovery: `m2-updater-fix-20261013`, asset
  `InsaniquariumEnhanced-M2UpdaterFix-Win64.zip`, successful CI `38393586383`.
- Published October 23 smoke baseline: m2-smoke-animation-20261023,
  commit 59bdb74cde9f455f3e360b72938c43c0983bf742, successful CI 39937822570.
  ZIP SHA256: 9026c074ea3a9c7722cc6eb1b9d03bcdbde13e0d7e88166d2e37f02ddbc22e2f.
- October 24 verified release: `m2-smoke-pixels-guard-20261024`, commit
  `9cd1dff14895f030528cf95d97fb84e699ad623c`, successful CI `40091120645`.
  This supersedes the intermediate `m2-smoke-pixels-20261024` release.
  BUILD_INFO.json records source/run/tag and premultiplied pixel composition.
- Pinned native port: `95d4aafe408b36e8a195982ad7acbae5fb6a0b33`;
  WinFish: `f919b3c241cfd611c547f1653fb3514f500f761b`;
  PopLib gitlink: `45776cefdeb8cd5bd43ce7f345aa7be1807c7380`.
  These pins were verified and are unchanged.

## Recovery and chronology

The supplied outer ZIP and nested October 13 7z were extracted. All 48 nested
ZIPs passed CRC checks. Historical conversations and audit documents were indexed
and compared with branch history, source patches and user reports. Recovery
includes nine historical Markdown documents plus the final outer conversation.
The raw CSV audit covered 129 files and 8,600,926 data rows. The only width errors
were truncated final rows of historical `093-M2DebugSprites(9).csv` (line 107913)
and `094-M2DebugInterpolation(9).csv` (line 268395). These are incomplete evidence,
not engine faults. The latest capture has no malformed rows.

Archived screenshots include the actual failed updater popup. Videos and images
remain available locally; this recovery does not claim a new full playback or
independent frame-pacing/audio analysis of every historic recording. Personal
exports, raw captures and original game assets are not part of this repository.

| Stage | Outcome and interpretation |
| --- | --- |
| Early October DLL experiments | D3D11 scaling and repeated presentation exposed cursor mapping, custom cursor, mode-toggle and DirectDraw rebuild failures. Increasing tick rate changed gameplay speed. This route is superseded by the native port; do not port old hooks into M2. |
| October 9 M0/M1 | Native x64 SDL3/PopLib baseline; newer WinFish pin with overlapping applause fixes reconciled. M1 menu changes and M1.2 in-game updater followed. User reported the stable build worked. |
| October 9â€“10 M2 clock | Separate 28 ms simulation and 60 Hz presentation; position history and guards. User saw ~60 FPS. Legacy hardware acceleration could break the renderer, so M2 disables that path. |
| Pause/input fixes | Freeze/invalidate interpolation during Options; Esc toggles the existing dialog, ignoring key repeats and unrelated dialogs. |
| Fish/coin/food/alien | Initialize missing positive fish velocity; reject invalid render coordinates; preserve legitimate collected-coin homing with a larger bound; move M2 draw callbacks to simulation. |
| Pets | FishTypePet bypassed Fish::Update and needed its own history capture. OtherTypePet received its own guarded translation/callback patch. |
| October 12 long session | About 32.5 minutes, 117,178 frames and 24 pause cycles reported; actual moving other-pet offsets are independently recovered below. Sparse details and file caps limit later coverage. |
| Shot first use/sentinels | Typed Shot constructor read its kind before assignment; assign it before branching without adding RNG calls. Preserve intentional hidden sprite frames, including missile-smoke cel -1. |
| October 13 effect traces | Sparse sampling prevented adjacent-tick effect analysis; shots/missiles now have continuous motion sampling with a separate frame budget. |
| October 13 smoke/missile | Types 6/7 rise 2 px/tick and gain guarded sprite translation. Missile capture before its smoothing patch showed 957 draws and <=2.5 px/axis adjacent movement; implement an 8 px guard, awaiting runtime verification. |
| October 13 updater | Semantic-only selection skipped M2 tags; release-array order was unreliable. M2 now selects compatible project assets by publication time, embeds its public tag and avoids offering an older installed release. |
| October 23 continuation | Optional adjacent-cell smoke crossfade, independent diagnostics, A/B launchers and this handover. This is a small presentation experiment, not completion of all sprite animation work. |

## Recomputed runtime evidence

Latest supplied capture: frames `20261013-125335`, motion `(9)`, report `(10)`.
This identifies a capture, not cryptographic proof of its executable commit.
Re-running the current baseline analyzer on the original raw files yields:

| Metric | Recomputed result |
| --- | ---: |
| Frame rows / simulation ticks | 35,399 / 21,088 |
| Mean timing-window render/simulation rates | 59.951 FPS / 35.716 Hz |
| Slow renders >25 ms / warnings | 12 / 14 |
| Worst logged render | 83.326 ms |
| Unexpected invalid sprite rows | 0 |
| Pause/resume | 2 / 2 |
| Shot motion samples / shifted samples | 29,016 / 4,131 |
| Maximum shot offset | 2 px Y, 0 px X |
| Missile draws | 0 |

Shot Draw totals are 29,235, different from the 29,016 post-delay motion rows;
do not equate probes with visible effect draws. Two guard-sized shot jumps had
history reset and zero visual offset. Address reuse is plausible, not proven
identity. Detail streams end before the frame stream, potentially because objects
were absent or sampling stopped; internal telemetry cannot settle display pacing.

**Correction to the supplied handover:** older raw
`124-M2DebugObjectMotion(5).csv` contains **80,040 other_pet samples, 42,818
nonzero offsets (53.5%), maximum 4 px on each axis**. Moving other-type pet
interpolation has recorded evidence. The final capture has a stationary other
pet (12,101 samples, zero shifts); it does not erase that earlier coverage or
establish coverage of all pet types.

User feedback on the smoke-stage testing was approximately "Feels okay but I
can't confirm 100%." Treat this as provisional, not visual certification. The
fixed updater's final Up to Date UI and missile interpolation remain unconfirmed.

## Architecture and animation audit

`FrameClock.hpp` schedules original 28 ms updates and ~60 Hz presentation.
`gEnhancedM2Blend` provides render phase; `INSANIQUARIUM_M2_60FPS=1` enables M2.
Simulation coordinates, collision/targeting, lifetime and serialized fields remain
authoritative. Object translations use guarded history and restore graphics state.
Pause invalidates stale history; teleports and unsafe coordinates fall back.
`DebugTrace.hpp` is deployed identically to game and framework; keep both copies
identical to avoid inconsistent recorder definitions.

| Animation family | Pinned source observations | Safe scope / remaining risk |
| --- | --- | --- |
| Fish and fish-type pets | Swim/turn/eat/death counters select directional rows; feeding and state transitions share update logic. Fields are saved. | Position interpolation exists. Separate phase/state audit needed before altering appearance; no render-driven counters. |
| Other-type pets | Different divisors and state-specific indices, special abilities and transformation. | Recorded position interpolation; each pet animation requires its own transition policy. |
| Aliens | Swim/attack states and indices share AI callbacks. | Keep combat events on ticks; no broad crossfade. |
| Coins | Animation timer wraps at 80; type-dependent divisors, rows, sparkle/additive passes and pet-dependent cadence. | Visually promising future candidate, but wrap/row/blend-mode policy first. Saved timer/frame unchanged. |
| Food | Frame uses `m0x178 / m0x17c`; fade and exotic food branches use additional state. | Preserve disappearance/edibility and opacity logic. |
| Missiles | UpdateAnimations, directional/body/trail drawing, energy balls and ball cels; saved fields and collision logic. | Position smoothing implemented; runtime missile capture still needed before more changes. |
| Rising smoke 6/7 | Age increments once/tick; cel = age/2 - 1; random initial delay; removal after age 39; normal alpha drawing. | New opt-in crossfade only on a valid adjacent cel transition. Lifetime stays on simulation. |
| Other shots | Lasers/additive explosions, chomp and missile smoke have distinct cadence, sentinels and passes; some ages increment twice. | Excluded from new blend. |
| Board/background/UI | Crosshair uses game counter/4; wave uses GetAnimCel(game counter); other menus/transitions have separate update code. | No changes in this increment. Full menu/hover/dialog and background audit remains. |

New `SmokeAnimation.hpp` captures render-only history before Update. Draw uses
current/previous cels with the existing fractional blend, only for types 6/7 and
normal drawing. No extrapolated future cel, extra timer increment or new save
field is introduced. Startup, delay, pause, serialization, unexpected sheet
layout, age discontinuity and invalid phase fall back to the original draw.
The single draw does not modify the caller color, including on exceptions.

The October 23 version used two alpha-over passes, which reduced coverage of
overlapping pixels. The October 24 version composes one cel with interpolated
coverage and premultiplied RGB, then uses the original single normal draw and
tint. Transparent RGB is excluded from the color mix. Output remains 8-bit,
in asset color space, with 1/256 phase precision; it is not linear-light blending.
Endpoints draw the original sheet. Double edges from differing shapes can remain.
Unchanged-cell ticks still draw one cel; transitions cover one tick. Keep this
off by default until visual comparison. See [test instructions](SMOKE_ANIMATION_TEST.md).

SmokePixelBuffer owns one lazy temporary MemoryImage per Shot, capped at 128x128.
No global resource pointers survive reloads; source pixels are read afresh. The
buffer is destroyed with its Shot. Invalid sheet dimensions, unavailable pixels
and allocation failure revert to the current cel before telemetry is recorded.
Composition requires resident source mBits before calling GetBits. The pinned
RecoverBits can return success after a failed static-texture lock, leaving newly
allocated pixels uninitialized. Purged sources therefore use the original cel
without recovery or mutation; regression coverage checks no source read occurs
and blending resumes after pixels become resident. No renderer-wide fix is made.
Temporary draws bypass SpriteCel instrumentation; use the separate smoke CSV.
The pinned SDL renderer recreates textures on BitsChanged, so CPU pixel work and
texture upload cost require runtime comparison. No renderer-wide changes made.

## Build and verification

The existing 17 post-generation patch stages applied cleanly to the pinned tree;
the port generator reported no failed transformations/warnings. The new smoke
stage runs after missile interpolation and before Esc. Source anchors fail closed
on missing/duplicate anchors and on a second patch application. Upstream pins and
stable M1 source files are unchanged. Published test tags are no longer overwritten
by a workflow rerun; use a fresh tag for a new binary.

Local verification: 44 baseline Python tests and seven native C++ programs passed.
After this increment: **51 Python tests and eight C++ programs passed** on Windows
using portable Zig C++ for local native checks. Coverage includes complete smoke
age bounds, invalid phases, changed types, sheet bounds, delay/reset/pause, draw
state restoration, serialization/source guards, diagnostic budgeting and malformed
CSV detection. Existing clock tests cover 60/120/144/165/240 Hz render schedules.
GitHub CI separately uses MSVC for tests and the complete Windows executable.
Check its exact commit/run and release contents; local helper tests alone do not
establish a full game build or gameplay success.

## October 24 validation

All 51 Python tests and eight native C++ programs pass locally. The pixel test
checks identical coverage for all 256 alpha values at all 257 weights, and
compares unequal red/blue coverage against an independent floating-point
reference. It also checks transparent RGB, row stride, source immutability,
buffer reuse/resize, missing data, allocation failure and fallbacks. Existing
lifetime, pause/reset, sheet, draw-state and source guards remain covered.
The revised patch applied to real pinned generated Shot files; entire Update
and Sync functions are byte-identical to the previous patched source after
newline normalization. Full Windows build verification follows in CI.
No new user recording was supplied; smoke visual acceptance remains pending.

## October 24 fish/coin diagnostic continuation

The guarded smoke release is verified: `m2-smoke-pixels-guard-20261024`,
commit `9cd1dff14895f030528cf95d97fb84e699ad623c`, successful CI `40091120645`.
ZIP SHA256: `1f4d401726982c3b3e6144df61e1943f106d43d8396de80d79f355c8b9260192`.
It supersedes the intermediate unguarded pixel build.

The next increment changes only Python diagnostics, tests and documentation.
See [fish/coin phase audit](ANIMATION_PHASE_AUDIT.md) for pinned source anchors,
counter formulas, draw-state exclusions and the proposed future history policy.
The analyzer now separates adjacent-tick numeric differences from gaps,
duplicates and same-tick inconsistencies. Existing logs cannot identify actual
sprite state or lifetime; numeric transitions are not blend approval.

All 63 Python tests pass locally. Reprocessed the archived October 13 capture:
31,495 fish, 10,082 fish-pet and 1,443 coin adjacent-tick counter pairs, with
substantial sampling gaps. No new gameplay recording or visual acceptance.
A standalone analyzer is delivered; the verified game binary is unchanged.
Use `[skip ci]` for this diagnostics-only commit to avoid rerunning the binary
release workflow against its already published immutable tag. No workflow or
stable-branch changes; future runtime work still requires full Windows CI.

## Next work

1. Compare optional smoke animation visually; retain or revise based on opacity
   and edge quality, backed by new same-tick blend telemetry.
2. Record a missile-producing encounter on the current build; verify movement,
   target/collision timing, effects and sound. Do not confuse pre-patch missile
   motion samples with proof of interpolated drawing.
3. Confirm Check Updates UI on the released tag.
4. Implement resolved draw-state telemetry for a narrow coin candidate using
   ANIMATION_PHASE_AUDIT.md; capture lifetime, sheet/row, mode, mirror and opacity
   before expanding interpolation. Source audit and counter analysis are done;
   family-specific blend policies and runtime evidence remain outstanding.
5. Exercise Adventure, Time Trial, Challenge, Virtual Tank, save/load, focus,
   purchases, feeding, transitions, audio and long sessions. Internal logs do not
   certify every mode or physical display frame pacing.
6. Native 4K, widescreen layout and antialiasing remain separate later objectives.
