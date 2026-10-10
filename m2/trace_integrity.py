"""Read-only integrity and movement checks for optional M2 debug CSV streams.

Never infer GPU presentation or smoothness from these per-game draw records.
Limits and long gaps are reported as caveats, not automatic gameplay errors.
"""
import collections
import csv
from pathlib import Path

ROW_CAP = 350000
TRACE_NAMES = (
    "M2DebugFrames.csv",
    "M2DebugObjects.csv",
    "M2DebugSprites.csv",
    "M2DebugInterpolation.csv",
    "M2DebugObjectMotion.csv",
    "M2DebugEvents.csv",
    "M2DebugInvalidSprites.csv",
    "M2DebugSkippedSprites.csv",
)

def inspect_trace(path: Path):
    """Return (row_count, last_frame, problems) without storing CSV rows."""
    problems = []
    count = 0
    last_frame = -1
    if not path.is_file():
        return 0, -1, problems
    with path.open("rb") as raw:
        raw.seek(0, 2)
        size = raw.tell()
        if size:
            raw.seek(-1, 2)
            if raw.read(1) != b"\n":
                problems.append("final CSV line has no newline (possibly copied mid-write)")
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as file:
            reader = csv.reader(file, strict=True)
            header = next(reader, [])
            if not header or "frame" not in header:
                problems.append("missing 'frame' column or empty CSV")
                return 0, -1, problems
            idx = header.index("frame")
            for line_number, row in enumerate(reader, 2):
                if not row:
                    continue
                count += 1
                if len(row) != len(header):
                    if len(problems) < 5:
                        problems.append("CSV row {} has {} fields; expected {}".format(
                            line_number, len(row), len(header)))
                    continue
                try:
                    current = int(row[idx])
                except ValueError:
                    if len(problems) < 5:
                        problems.append("CSV row {} has nonnumeric frame".format(line_number))
                    continue
                if current < last_frame and len(problems) < 5:
                    problems.append("frame number decreases at row {}".format(line_number))
                last_frame = max(last_frame, current)
    except (OSError, csv.Error) as exc:
        problems.append("unable to parse CSV: {}".format(exc))
    return count, last_frame, problems

def audit_traces(folder: Path, reference_last_frame: int):
    details = []
    findings = []
    for filename in TRACE_NAMES:
        path = folder / filename
        if not path.is_file():
            continue
        count, last, issues = inspect_trace(path)
        details.append("{}: {:,} rows; last frame {}".format(filename, count, last))
        for issue in issues:
            findings.append("WARN: {}: {}.".format(filename, issue))
        if filename != "M2DebugFrames.csv":
            if count >= ROW_CAP and filename in (
                "M2DebugObjects.csv", "M2DebugSprites.csv",
                "M2DebugInterpolation.csv", "M2DebugObjectMotion.csv"):
                findings.append("WARN: {} reached {}-row trace limit; later samples are unavailable.".format(
                    filename, ROW_CAP))
            if reference_last_frame >= 0 and last > reference_last_frame + 3:
                findings.append("WARN: {} extends to frame {} but Frames.csv ends at {}; "
                                "files may belong to different captures or were copied while running.".format(
                                    filename, last, reference_last_frame))
            if reference_last_frame >= 0 and 0 <= last < reference_last_frame - 120 and count < ROW_CAP:
                findings.append("INFO: {} ends {} frames early; this may reflect absent objects, "
                                "sampling or a partial capture.".format(
                                    filename, reference_last_frame - last))
    return details, findings

def audit_object_movement(folder: Path):
    """Count observed object kinds, distinct IDs, and actual sim-tick motion."""
    path = folder / "M2DebugObjects.csv"
    if not path.is_file():
        return [], []
    summary = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0.0])
    ids = collections.defaultdict(set)
    previous = {}
    findings = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                if not row.get("kind") or not row.get("objectId"):
                    continue
                kind = row["kind"]
                key = (kind, row["objectId"])
                try:
                    tick = int(row["gameTick"])
                    x = float(row["simulationX"])
                    y = float(row["simulationY"])
                    moved = int(row.get("simMoved", "0")) != 0
                    changed_cel = int(row.get("changedCel", "0")) != 0
                except (KeyError, TypeError, ValueError):
                    continue
                stats = summary[kind]
                stats[0] += 1
                stats[2] += int(changed_cel)
                if len(ids[kind]) < 20000:
                    ids[kind].add(row["objectId"])
                if moved:
                    stats[1] += 1
                    old = previous.get(key)
                    if old and tick != old[0] and 0 < tick-old[0] <= 30:
                        stats[3] = max(stats[3], abs(x - old[1]))
                        stats[4] = max(stats[4], abs(y - old[2]))
                if len(previous) < 20000 or key in previous:
                    previous[key] = (tick, x, y)
    except (OSError, csv.Error) as exc:
        return [], ["WARN: Object movement summary could not read CSV: {}.".format(exc)]
    lines = []
    for kind in ("alien", "other_pet", "fish_pet", "missile", "shot_effect"):
        if kind not in summary:
            continue
        count, moved, changed, dx, dy = summary[kind]
        lines.append("{}: {:,} draw samples; {} object IDs; {:,} simulated moves; "
                     "{:,} cel changes; largest observed step X/Y {:.2f}/{:.2f}px".format(
                         kind, count, len(ids[kind]), moved, changed, dx, dy))
        if kind in ("other_pet", "fish_pet") and moved == 0:
            findings.append("INFO: {} was drawn, but no simulated movement was "
                            "observed; moving-pet interpolation is not yet verified.".format(kind))
    return lines, findings
