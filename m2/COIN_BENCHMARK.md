# Coin blend CPU benchmark

Run `M2CoinBenchmark.exe > coin-benchmark.csv` in a terminal in the extracted
release folder. No original assets or Python are required. `--quick` reduces
samples from 31 to 5 for a correctness smoke check; use the default for timings.
The tool checks that transitions actually compose, held/disabled cases fall
back for the expected reason, and source pixels remain unchanged.

The CSV covers 1, 32 and 128 independent coin histories on a 720x432 synthetic
sheet, both silver/gold rows, and four pixel profiles: opaque, equal partial
opacity, random mixed opacity, and circular opaque masks with transparent
surroundings. Each case has three warmups. Timings are for the complete batch
of owners, in microseconds, using a monotonic clock. p95 is nearest rank.
Checksums consume every output pixel outside the measured region.

- `capture`: copying the complete selected ten-cel row before an update.
- `transition`: equality checking the row and composing a cel, with changing
  blend phase. All coins transition together to stress the helper.
- `endpoint`: the same complete-row validation with an exact blend endpoint,
  so no destination pixels are composed. This isolates validation cost.
- `held`: eligible adjacent ticks with the same cel; ordinary drawing is used.
- `disabled`: the disabled helper path.

The cases are separate measurements, not a modeled game frame. Captures occur
on simulation ticks; draws occur on presentation frames. Sub-microsecond
results can be dominated by clock and loop overhead. Memory payload is a
maximum retained row plus output per owner: 228,096 bytes (222.75 KiB),
27.84375 MiB for 128 owners. It excludes allocator/framework overhead and the
shared sheet. All cases report that bound, not live process memory.

## Reproducing before/after comparisons

Build the same benchmark source in Release/O2 against the headers from the
layout-fix runtime commit `90454ecdc2e462cc124edbeaa6dcf7c0d3e8e87e`, then
against this release. The source uses include search paths so separate header
snapshots can be selected. Use the same compiler/options for both. Run:

`python m2/compare_coin_benchmarks.py before.exe after.exe comparison.json`

The script runs three pairs in alternating order and records each run plus
the median of medians, machine identification, binary hashes and output
checksum agreement. Keep background load low. Performance results vary by
CPU, compiler and pixel profile; no timing threshold is used as a CI gate.
The package includes COIN_BENCHMARK_CI.json from the Windows Release/MSVC
build. Hosted-runner results characterize that machine, not your PC.

## What this establishes

The equal-opacity optimization cancels a common coverage factor before RGB
division. It preserves integer rounding, transparent hidden-color behavior
and exact endpoints. `M2PixelEquivalenceTest` checks 67,371,011 pixel pairs
against independent 64-bit rational arithmetic. Coin row checks and all
game simulation behavior are unchanged. Smoke uses the same pixel helper.
The original full-row comparison remains exact equality, not a hash or a
revision-only shortcut.
Regression checks mutate every byte lane at row/cel boundaries and the middle.

This is a warmed CPU helper benchmark with a minimal image stand-in. It omits
first allocation, GPU texture upload, renderer submission, game logic, audio,
OS/display pacing and actual artwork. It cannot establish FPS, busy-tank
performance or visual acceptance. Use the normal/debug game launchers and
COIN_ANIMATION_TEST.md for gameplay comparison. Blending stays opt-in.
