# Optional smoke animation comparison

Current package: m2-smoke-pixels-20261024. This replaces the October 23
two-draw crossfade with one pixel-composed image, fixing its overlap opacity dip.

This experiment crossfades adjacent sprite cells for rising smoke types 6 and 7.
It retains the original 28 ms simulation, effect lifetime, random delay, sound
callbacks and save fields. It does not add intermediate artwork to fish, pets,
missiles, explosions, lasers or menus. Position interpolation remains enabled.

## Install and compare

1. Extract the experimental ZIP into a separate folder. Copy your original
   `data`, `images`, `music`, `properties`, `sounds` and `fishsongs` folders next
   to `InsaniquariumEnhanced.exe`, as with the previous native builds.
2. Run **Start M2.cmd** for the baseline. During an alien encounter, watch the
   small rising smoke puffs around weapon impacts. Close the game.
3. Run **Start M2 Smoke Blend.cmd** and compare the same kind of effect. Look for
   smoother transitions, but also softer/doubled edges or changing opacity.
   Smoke is brief; other animation types should look as before.
4. Open Options with Esc while smoke is visible, wait briefly, then resume.
   Check for frozen smoke while paused and no stale transition on resume.
5. In Options, try Check Updates. Record the exact message; the earlier updater
   fix has automated coverage but its final UI response remains unconfirmed.

The experiment is off in the normal launchers. Direct EXE launch reads the
environment as before; the crossfade additionally requires
`INSANIQUARIUM_M2_60FPS=1` and `INSANIQUARIUM_M2_SMOKE_BLEND=1`.
Launchers use local settings and explicitly choose the comparison mode.

## Capture only if needed

Use **Start M2 Smoke Blend Debug.cmd** for 1–2 minutes including a smoke-producing
fight and one pause/resume. Close the game, then run **Analyze M2 Logs.cmd**
(Python 3 required). Preserve that run before starting another debug session: logs
are overwritten. A normal comparison capture uses **Start M2 Debug.cmd**.

Return `M2DiagnosticReport.txt`, `M2DebugSmokeAnimation.csv`,
`M2DebugObjectMotion.csv`, `M2DebugFrames.csv`, `M2DebugEvents.csv`,
`M2DebugInvalidSprites.csv`, `M2Timing.log` and `BUILD_INFO.json`. Include the
other M2 CSVs if convenient. A short recording is useful specifically for
judging edge/opacity artifacts that telemetry cannot measure.

The smoke CSV records simulation age/cel independently from drawn cels and
blend. A positive same-tick-changing-blends count shows presentation changing
between simulation updates. It does **not** establish that the result looks
better. Zero transitions may mean no suitable smoke appeared, only unchanged
cells were sampled, or the optional launcher was not used.

Smoke rows have an independent limit of 64 per frame and 350,000 per run.
Verbose logs add overhead; compare perceived performance with the non-debug
launchers as well. Preserve a working M1.2 installation as the fallback.

## Known limits

Only valid adjacent cell changes are blended over one 28 ms interval; intervening
ticks whose cells do not change still display one cell. This deliberately modest
test does not claim a continuous all-animation 60 FPS conversion. It shares the
existing one-tick presentation delay used for interpolated positions.

The new draw interpolates coverage and premultiplied RGB before drawing once.
Identical pixels keep their opacity; hidden RGB in transparent pixels cannot
create colored fringes. Color remains in the original asset's encoded space,
with 8-bit output and 1/256 phase precision. This is not motion synthesis:
differing shapes can still produce double edges. It remains optional.

Each smoke object lazily owns one temporary cel (at most 128 by 128 pixels).
The pinned renderer recreates its texture when pixel data changes; the extra
CPU work and texture uploads need performance comparison during busy fights.
Unsupported sheets, missing pixels or allocation failure revert to the original
cel and the smoke CSV records a non-transition. The CSV is the authoritative
animation trace; composed draws use DrawImage and do not emit sprite-sheet rows.
Startup sentinels, delay, resets and removal retain their original rendering.
No extra simulation tick, animation event or terminal lifetime is added.

Missile smoothing remains a separate runtime verification task: a recording
without missile draws cannot verify it. Native 4K, widescreen and antialiasing
remain future work.
