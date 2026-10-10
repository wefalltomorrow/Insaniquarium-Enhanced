#!/usr/bin/env python3
"""Audit Insaniquarium Enhanced M2 recordings; no external dependencies.

Verifies recorded game-side metrics, not GPU/display presentation or whether
every visual animation looks correct. CSV input is always read-only.
"""
from __future__ import annotations
import argparse
import collections
import csv
from pathlib import Path
import re
import statistics

def rows(folder: Path, filename: str):
    path = folder / filename
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        yield from csv.DictReader(file)

def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def analyze(folder: Path):
    report = []
    notes = []
    frame_total = 0
    first_frame = last_frame = -1
    last_tick = 0
    present_ok = 0
    non_presented = []
    traced_types = set()
    frame_invalid = frame_warn = 0
    slow_render = 0
    longest_render = 0.0
    frame_types = collections.Counter()
    detail_last = {}
    for row in rows(folder, "M2DebugFrames.csv") or ():
        frame_total += 1
        frame = int(number(row.get("frame"), -1))
        if frame_total == 1:
            first_frame = frame
        last_frame = frame
        last_tick = int(number(row.get("totalSimTicks")))
        presented = int(number(row.get("presented")))
        present_ok += presented
        if not presented and len(non_presented) < 12:
            non_presented.append("frame {} (tick {}, render {:.3f}ms, elapsed {:.3f}ms)".format(
                frame, int(number(row.get("totalSimTicks"))),
                number(row.get("renderMs")), number(row.get("elapsedMs"))))
        frame_invalid += int(number(row.get("invalidCels")))
        frame_warn += int(number(row.get("warnings")))
        duration = number(row.get("renderMs"))
        longest_render = max(longest_render, duration)
        slow_render += duration > 25.0
        for kind in ("Fish", "Coin", "Food", "Alien", "OtherPet", "Missile", "ShotEffect"):
            field = "draws" + kind
            if row.get(field) is not None:
                traced_types.add(kind)
                frame_types[kind] += int(number(row[field]))
    report.append("Insaniquarium Enhanced M2 - recorded diagnostics")
    report.append("Input folder: " + str(folder.resolve()))
    report.append("Recorded frame rows: {:,}; last frame: {}; total sim ticks: {:,}".format(
        frame_total, last_frame, last_tick))
    if not frame_total:
        notes.append("ERROR: M2DebugFrames.csv missing or contains no frame data.")
    if frame_total and present_ok != frame_total:
        notes.append("WARN: {:,} logged frames have presented=0.".format(frame_total - present_ok))
        report.append("Non-presented frame samples (up to 12): " + "; ".join(non_presented))
        notes.append("INFO: presented=0 is a game-side draw result, not proof of a monitor drop.")
    if frame_invalid:
        notes.append("ERROR: {:,} invalid sprite draws counted in frame summaries.".format(frame_invalid))
    report.append("Frame warnings: {:,}; render over 25ms: {:,}; worst render: {:.3f}ms".format(
        frame_warn, slow_render, longest_render))
    report.append("Object draw totals: " + ", ".join(
        "{} {:,}".format(k.lower(), frame_types[k])
        for k in ("Fish", "Coin", "Food", "Alien", "OtherPet", "Missile", "ShotEffect")
        if k in traced_types))

    for kind in ("Alien", "OtherPet", "Missile", "ShotEffect"):
        if kind in traced_types and not frame_types[kind]:
            notes.append("INFO: {} was not drawn during this recording; movement is untested.".format(kind))
    if "OtherPet" not in traced_types:
        notes.append("INFO: extra pet/missile/shot probes not present in this build's frame CSV.")
    values = {"simulation": [], "presentation": []}
    timing = folder / "M2Timing.log"
    if timing.is_file():
        pattern = re.compile(r"sim=([0-9.]+)\s*Hz,\s*present=([0-9.]+)\s*Hz")
        for match in pattern.finditer(timing.read_text(encoding="utf-8-sig", errors="replace")):
            values["simulation"].append(float(match.group(1)))
            values["presentation"].append(float(match.group(2)))
    if values["presentation"]:
        sim = statistics.mean(values["simulation"])
        present = statistics.mean(values["presentation"])
        report.append("Timing windows: {}; sim mean {:.3f}Hz; render mean {:.3f}FPS".format(
            len(values["presentation"]), sim, present))
        if not 34.0 <= sim <= 37.0:
            notes.append("WARN: average logged simulation rate outside 34-37Hz.")
        if not 58.0 <= present <= 61.0:
            notes.append("WARN: average logged presentation rate outside 58-61FPS.")
    else:
        notes.append("INFO: M2Timing.log not available; cannot establish average rates.")

    events = collections.Counter()
    severity = collections.Counter()
    for row in rows(folder, "M2DebugEvents.csv") or ():
        events[row.get("event", "")] += 1
        severity[row.get("severity", "")] += 1
    report.append("Event log: " + (", ".join("{}={}".format(k,v) for k,v in sorted(severity.items())) or "missing/empty"))
    report.append("Pause events: {}, resume events: {}".format(
        events["tank_paused"], events["tank_resumed"]))
    if abs(events["tank_paused"] - events["tank_resumed"]) > 1:
        notes.append("WARN: pause/resume event counts differ by more than one.")
    for issue in ("nonfinite_fish_render_offset", "draw_mutated_game_state",
                  "simulation_position_changed_without_game_tick",
                  "animation_cel_changed_without_game_tick", "invalid_interpolation_factor"):
        if events[issue]:
            notes.append("ERROR: {} occurs {} time(s).".format(issue, events[issue]))
    if severity["ERROR"]:
        notes.append("ERROR: {} ERROR-level events logged.".format(severity["ERROR"]))
    if severity["WARN"]:
        notes.append("WARN: {} WARN-level events logged; check M2DebugEvents.csv.".format(severity["WARN"]))

    invalid_count = sum(1 for _ in rows(folder, "M2DebugInvalidSprites.csv") or ())
    skipped = collections.Counter()
    for row in rows(folder, "M2DebugSkippedSprites.csv") or ():
        skipped[row.get("assetPath", "unknown")] += 1
    report.append("Invalid sprite detail rows: {}; expected skipped sprite rows: {}".format(
        invalid_count, sum(skipped.values())))
    if invalid_count:
        notes.append("ERROR: unexpected sprite rows found (inspect M2DebugInvalidSprites.csv).")
    if skipped:
        report.append("Expected skips by asset: " + ", ".join(
            "{}={}".format(k, v) for k, v in skipped.most_common(8)))

    for filename, label in (("M2DebugInterpolation.csv", "fish"),
                            ("M2DebugObjectMotion.csv", "coin/food")):
        counts = collections.Counter()
        moving = collections.Counter()
        max_offsets = collections.defaultdict(lambda: [0.0, 0.0])
        paused_nonzero = collections.Counter()
        last_sample = -1
        for row in rows(folder, filename) or ():
            kind = row.get("kind", label)
            counts[kind] += 1
            last_sample = max(last_sample, int(number(row.get("frame"), -1)))
            dx = number(row.get("offsetX"))
            dy = number(row.get("offsetY"))
            max_offsets[kind][0] = max(max_offsets[kind][0], abs(dx))
            max_offsets[kind][1] = max(max_offsets[kind][1], abs(dy))
            if dx or dy:
                moving[kind] += 1
                if int(number(row.get("paused"))) == 1:
                    paused_nonzero[kind] += 1
        if counts:
            for kind, count in sorted(counts.items()):
                report.append("{}: {:,} samples, {:,} shifted ({:.1f}%), max offsets X/Y {:.1f}/{:.1f}px".format(
                    kind, count, moving[kind], 100 * moving[kind] / count,
                    *max_offsets[kind]))
                if paused_nonzero[kind]:
                    notes.append("ERROR: {} has {} moving sprites while paused.".format(
                        kind, paused_nonzero[kind]))
            if last_frame >= 0 and last_sample < last_frame - 300 and max(counts.values()) >= 350000:
                notes.append("INFO: {} hit per-file 350k sample cap; later frames not included.".format(filename))
            detail_last[filename] = last_sample
        else:
            notes.append("INFO: {} missing or contains no samples.".format(filename))
    report.append("Detailed trace latest frames: " + ", ".join(
        "{}={}".format(k, v) for k, v in detail_last.items()))
    report.append("Interpretation: measures logged game-side behaviour only; external frame")
    report.append("presentation, visual smoothness, audio fidelity and all gameplay modes")
    report.append("require separate observation/testing.")
    if not notes:
        notes.append("No automated issues detected in the supplied recordings.")
    report.append("")
    report.append("Findings:")
    report.extend("- " + n for n in notes)
    return "\n".join(report) + "\n", any(n.startswith("ERROR:") for n in notes)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("."),
                        help="Directory containing M2Debug*.csv and M2Timing.log")
    parser.add_argument("--output", type=Path, default=Path("M2DiagnosticReport.txt"),
                        help="Text report location")
    args = parser.parse_args()
    report, has_errors = analyze(args.directory)
    args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    print("Saved report to: " + str(args.output.resolve()))
    return 1 if has_errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
