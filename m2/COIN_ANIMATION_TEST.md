# Optional silver/gold coin animation experiment

This build can crossfade adjacent, observed animation cels for ordinary silver
and gold coins during the existing 60 Hz presentation. The original 28 ms game
simulation, animation counters, movement, callbacks, RNG and save fields remain
unchanged. This is a visual experiment, not completed 60 FPS animation for the
whole game. Crossfading can look soft or ghosted; it does not create new poses.

## Compare

1. Extract this release into its own folder. Copy the original game's data,
   images, music, properties, sounds and fishsongs directories beside
   the executable. Original assets are not included.
2. Run **Start M2.cmd** for the baseline. Observe falling silver and gold coins.
   Close the game before switching launchers.
3. Run **Start M2 Coin Blend.cmd** for the experiment. Compare coin rotation
   during ordinary play, with and without the pet that slows falling coins.
   Check whether the transitions look smoother or produce unwanted ghosting.
4. Collect coins, let some fade, pause/resume, and save/load. These cases use
   the original drawing and reset animation history. Try a shell/bonus mode:
   shells and explicit shell coin types retain the original animation.
5. For evidence, run **Start M2 Coin Blend Debug.cmd**, play for 30–60 seconds,
   then close the game. Preserve all M2Debug*.csv files and BUILD_INFO.json
   before another debug run overwrites them. Run **Analyze M2 Logs.cmd**
   (Python 3 required). A baseline capture uses **Start M2 Debug.cmd**.

The report lists composed draws, exact endpoint draws, unchanged held
cels, and fallback reasons. No composed draws means the capture has not
demonstrated active smoothing. "pixels" means the selected row changed;
"identity" means the image lifetime or reported revision changed;
"nonresident" means CPU pixels were unavailable. Each stream has a separate
64-row/frame and 350,000-row cap; counts are samples, not complete totals.
M2DebugCoinSprites.csv describes the original resolved request, while
M2DebugCoinBlend.csv describes the chosen composition/fallback. General
sprite-cel counts omit composed draws because those use one DrawImage call.

## Boundaries

- Off by default. The new launchers enable only the coin experiment; smoke
  blending remains off. All baseline/smoke launchers explicitly disable coins.
- Only types 1/2, non-shell mode, unfaded/uncollected, normal unscaled untinted
  drawing, a 10×5 sheet with cells at most 72×72, and adjacent observed cels.
  Timer wraps, cel 9→0, mode/speed changes, invalid state and missing history
  fall back. Reset/load/pause never reuses a previous interval's blend.
- A CPU copy of the entire selected ten-cel row is captured before each original
  update and compared before composition. Lifetime/revision checks supplement
  that comparison. Unreported writes between observations are detected if the
  bytes differ; writes restored between observations are not observable.
- In this mode only, the resource loader retains IMAGE_MONEY's existing CPU
  pixels before purging. Other resources and default memory policy are untouched.
  Source pixels are never recovered from GPU textures or modified by this code.
- Each active owner lazily retains at most 202.5 KiB of row pixels and 20.25 KiB
  of output pixels (plus framework overhead). Work and memory scale with the
  number of coins. Gameplay performance still needs a busy-scene capture.
- Composition uses the smoke experiment's tested premultiplied coverage/RGB
  math, in the source color space, then draws once. It is not optical flow.
  Equal CPU observations do not prove GPU synchronization or full resource
  continuity. CI and synthetic traces do not establish appearance, audio,
  gameplay fidelity or physical display pacing. Visual acceptance is pending.

Release tag: m2-coin-blend-20261025.
