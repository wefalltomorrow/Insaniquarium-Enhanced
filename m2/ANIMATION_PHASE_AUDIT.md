# Fish and coin animation audit — October 24, 2026

This increment adds read-only counter analysis and documents source transitions.
It does not add fish/coin crossfades or change the game executable. The guarded
smoke build remains the current test binary, with smoke blending off by default.

## Source and evidence boundary

Inspected the generated, M2-patched source at baseline
`9cd1dff14895f030528cf95d97fb84e699ad623c`, using port
`95d4aafe408b36e8a195982ad7acbae5fb6a0b33`, WinFish
`f919b3c241cfd611c547f1653fb3514f500f761b` and PopLib
`45776cefdeb8cd5bd43ce7f345aa7be1807c7380`. Locations below refer to files
under generated `upstream/port/winfish/`, not upstream's unpatched line numbers.
Function names are the durable anchors.

`M2DebugObjects.csv` records a counter plus kind/pointer/frame/tick, not a resolved
sprite state. `fish` includes derived fish classes. `coin` includes objects whose
draw path ignores the animation counter. Pointer IDs can be reused within a
capture, even across adjacent ticks. There is no lifetime generation.

`M2DebugSprites.csv` lacks object identity, asset path, mirror and blend mode.
An image is shared by many objects. Draw order and coordinates do not provide a
reliable join. Instrumentation in `apply_debug.py` covers `DrawImageCel`; main
fish bodies use `DrawImageMirror` with rectangles. Their overlays may be recorded
even when their bodies are not. No cross-stream join is attempted here.

## Coins

`Coin::Update` (Coin.cpp:67) advances the timer once per unpaused simulation tick,
wrapping after 79. Shrapnel bombs use `(timer / 2) % 5`. Other types use divisor
2 or 4 according to pet slot 10, then modulo 10 or 20. The 20-cel path requires
shell mode AND one of: COIN_SILVER_C, COIN_GOLD_C, COIN_DIAMOND,
COIN_DIAMOND_PENTA, COIN_PEARL, COIN_TREASURE, SHELL_BLUE, SHELL_BLUE_PENTA,
SHELL_SPIRAL, SHELL_SACK. `IsShell` (line 722) means Virtual Tank or bonus round.
Explicit SHELL_SILVER/GOLD use the 10-cel path even in shell mode. Preserve that
asymmetry; shared imagery alone does not establish an upstream bug.

`Coin::Draw` (line 382) resolves the following main branches. Numbers are rows,
and assets below omit the `IMAGE_` prefix.

| Type family | Ordinary mode | Shell mode | Initial candidate policy |
| --- | --- | --- | --- |
| Silver / gold | MONEY row 0 / 1 | SHELLS row 0 / 1, offset 20,20 | Audit normal, unfaded body first |
| Diamond variants | MONEY row 3 | SHELLS row 2, offset 20,20 | Separate mode/state key |
| Pearl / spiral | Static PEARL | SHELLS row 3, offset 20,20 | Exclude ordinary static branch |
| Treasure / sack | MONEY row 4 | Static MONEYBAG cel 0 at 18,18 | Exclude shell static branch |
| Star / shell star | MONEY row 2 | MONEY row 2 | Do not infer shell sheet from type alone |
| Peanut | Static PEANUT | Static PEANUT | Exclude |
| Niko pearl | Static PEARL when collected; otherwise no body here | Same condition | Exclude |
| Note | Static misc cell or text, with conditional fade | Same branch | Exclude |
| Shrapnel bomb | Static misc body plus additive SPARKS | Same branch | Exclude additive pass initially |

Animation advances before collection/disappearance early exits. Fading uses
`mDisappearTimer * 255 / 5`; collection also changes movement and awards money.
Bomb collision and removal paths spawn effects, consume RNG and play sounds.
`Coin::Sync` (line 695) saves the existing timer/frame and collection state.
Never move these operations into rendering or serialize presentation history.

## Fish

`Fish::FishUpdateAnimation` (Fish.cpp:1396) has three different frame formulas:
swim increments a counter by 1 or 2, wraps at 20 and divides by 2; eating uses
`9 - eatingTimer/2`; turning uses signed timers and `9 +/- turnTimer/2`. C++
signed division truncates toward zero. Turns start at +/-20 and count toward
zero. Scream state can hold cel 4. Rainbow/invisibility and crosshair updates
also run here; this is not a render-only animation routine.

`GetImageToDraw` (line 1637) chooses turn before swim/eat, with hunger variants.
`DrawFish` (line 1025) selects a size-dependent row, mirror and destination
rectangle. Growth scales the destination; zombie mode uses fixed death-sheet
cells; colored/star fish add passes; hunger transitions mix sheets; invisibility
and crosshairs have separate paths. Identical counters can produce different
images, and adjacent counters can straddle unrelated sheets.

`OnFoodAte` (line 709) changes hunger, growth, transformation and sound state;
some food can remove/replace a fish or kill it and spawn effects. `Die`
(line 1518) removes the live fish and spawns a separate DeadFish. DeadFish has
its own Update/Draw, including different source rectangles. Never carry live
fish history into the new object. `Fish::Sync` saves existing animation fields.

Derived classes need explicit policies; generic fish observations cannot
identify which class produced a numeric transition:

| Source anchor | Difference relevant to presentation |
| --- | --- |
| BallFish.cpp:365, FishUpdateAnimation | Signed velocity advances or reverses a counter; divisor 6/12 depends on size |
| BiFish.cpp:376, FishUpdateAnimation | Turn changes a variant; swim can use a triangular sequence; scream can hold an endpoint |
| SylvesterFish.cpp:390, FishUpdateAnimation | Shorter turn sequence, speed-dependent holds; routine also changes actual X/Y positions |
| Ultra.cpp:432, FishUpdateAnimation | Turning clears eating; draw uses a separate body layout |
| Oscar.cpp:172, DrawFish | Own row and color/hunger/zombie composition |
| Gekko.cpp:157, DrawFish | Delegates to DrawGekko and can add a growth highlight pass |
| FishTypePet.cpp:1468, FishUpdateAnimation | Per-pet rules; some mutate velocity and RNG |

Fish-type pet examples: Vert/Walter use forward/reverse sequences; Walter has
an eating hold; Nimbus/Brinkley divide by 4; Shrapnel by 6; Seymour by 8.
Stanley/Gash can use eating or special counters directly. Zorf can reset the
swim counter after choosing the frame. Prego/Walter may zero velocity during
special states. Meryl's frame-zero logic consumes RNG for blinking. Pet effects
and draw states require a separate audit before blending each family.

## Read-only observation policy

The new `inspect_animation_cels` / `audit_animation_cels` in `trace_integrity.py`
are integrated into `analyze_logs.py`; no new runtime dependency is needed.
They stream the CSV with a 20,000-entry LRU history keyed by kind/pointer.

- Compare numeric values only on increasing render frames and adjacent ticks.
  Count unchanged, +1, -1 and other differences; never label a wrap as verified.
- Count unchanged/changed same-tick redraws separately. Drop history after a
  same-tick change or conflicting same-frame observation. Exact duplicate
  counter samples do not count as transitions.
- Gaps start a fresh baseline; do not bridge unobserved simulation ticks.
  Missing-tick totals are summed per ID, not elapsed session time.
- Malformed records and frame/tick regressions clear history. Invalid headers,
  partial parse failures, missing kinds/files and memory evictions are explicit.
- No anomaly is automatically a gameplay bug. No +1 pair is automatically
  eligible for blending. No unchanged counter proves unchanged appearance.

## Archived recording results

Reprocessed the previously recovered October 13 capture (frame filename
`20261013-125335`, motion `(9)`, report `(10)`), not a new runtime test. The
capture is not cryptographic proof of its executable commit. Object detail
contains 248,739 rows, ending at frame 34,720; frame totals end at 35,398.

| Kind | Counter samples | Adjacent ticks | Unchanged / +1 / -1 / other | Tick gaps |
| --- | ---: | ---: | --- | ---: |
| fish | 158,763 | 31,495 | 12,254 / 17,199 / 40 / 2,002 | 105,787 |
| fish_pet | 24,202 | 10,082 | 5,469 / 1,993 / 998 / 1,622 | 7,270 |
| coin | 8,735 | 1,443 | 709 / 664 / 0 / 70 | 6,243 |

No same-tick counter changes, duplicate samples, same-frame conflicts, malformed
rows, order resets or history evictions were observed by this audit. This does
not rule out hidden state/lifetime changes. Existing report warnings remain:
14 logged WARN events, incomplete late detail, stationary other-pet coverage
and no missile encounter. The capture has no current smoke-blend telemetry.

## Implementation boundary for the next visual experiment

Start with one normal, non-fading coin body family. Before expanding, record a
resolved draw descriptor at the drawing site: object lifetime/generation, tick,
type, mode/state, sheet resource identity and generation, cel/row, source size,
destination geometry, mirror, tint/opacity and blend mode. Preserve the actual
selected sprite; do not predict its future state from a counter.

Store presentation history with the owner, invalidate on construction, load,
pause/resume, resource replacement, state/layout change, missing history and
unexpected ticks. Keep the 28 ms simulation and all callbacks unchanged.
Initially reject wraps, reverse sequences, mode changes, static branches and
additive effects; later policies need family-specific evidence. Use the existing
single-cel premultiplied composition only when source pixels are resident and
the resolved states are compatible. Restore caller graphics state and retain
an original-draw fallback. Avoid introducing serialized fields.

This descriptor/history policy is a design boundary, not implemented telemetry.
New captures must cover turns, feeding/growth/death, shell-mode entry, collection,
fade, pause and save/load. Visual edge quality, audio and physical presentation
remain separate tests. Smoke acceptance and a missile encounter are still pending.

## Verification and delivery

63 local Python tests pass, including 12 new audit tests. New coverage checks
gaps, reverse/numeric wrap observations, same-tick changes, duplicate/conflicting
records, cross-object resets, bounded history, invalid CSV/encoding, missing
coverage, irreducible pointer ambiguity and report integration/input preservation.
The existing binary's 51 Python/eight native tests and successful Windows CI
remain historical evidence for that binary; native tests were not rerun for
this Python/docs-only change.

Deliver a standalone analyzer ZIP containing all three Python modules and a
Windows launcher. Python 3.10+ is required; no third-party packages. Preserve
input CSVs and ship only the report/manifest, not the raw personal capture.
The diagnostics commit deliberately uses `[skip ci]`: the existing release
workflow still names the immutable guarded-smoke tag. No new executable is
needed and no existing release should be republished. A future runtime change
must use a fresh release tag and run full Windows CI.
