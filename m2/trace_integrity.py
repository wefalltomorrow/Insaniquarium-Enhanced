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

ANIMATION_KINDS = ("fish", "fish_pet", "coin")


def inspect_animation_cels(path: Path, history_limit=20000):
    """Stream numeric cel observations, never infer sprite state or lifetime.

    History is an LRU bounded by history_limit. Malformed records and global
    frame/tick regressions clear it. Gaps start a new baseline; duplicate draws
    do not count as tick transitions. Pointer reuse without a gap is inherently
    undetectable in this schema. No image/cel-row joins are attempted.
    """
    if history_limit < 1:
        raise ValueError("history_limit must be positive")
    stats = {kind: collections.Counter() for kind in ANIMATION_KINDS}
    issues = collections.Counter()
    previous = collections.OrderedDict()
    last = None
    required = ("frame", "gameTick", "kind", "objectId", "animationCel")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, strict=True)
            header = next(reader, [])
            if len(header) != len(set(header)) or not set(required).issubset(header):
                issues["incompatible_header"] += 1
                return stats, issues
            columns = {name: header.index(name) for name in required}
            for row in reader:
                issues["rows_read"] += 1
                try:
                    if len(row) != len(header):
                        raise ValueError()
                    frame, tick = int(row[columns["frame"]]), int(row[columns["gameTick"]])
                    kind, object_id = row[columns["kind"]], row[columns["objectId"]]
                    if frame < 0 or tick < 0 or not kind.strip() or not object_id.strip():
                        raise ValueError()
                    cel = int(row[columns["animationCel"]]) if kind in stats else 0
                    if cel < 0:
                        raise ValueError()
                except (ValueError, TypeError):
                    issues["malformed_rows"] += 1
                    previous.clear()
                    last = None
                    continue
                if last and (frame < last[0] or tick < last[1]):
                    issues["order_resets"] += 1
                    previous.clear()
                last = (frame, tick)
                if kind not in stats:
                    continue
                count = stats[kind]
                count["samples"] += 1
                key = (kind, object_id)
                old = previous.pop(key, None)
                if old is None:
                    count["baselines"] += 1
                else:
                    df, dt, dc = frame - old[0], tick - old[1], cel - old[2]
                    if df == 0:
                        if dt == 0 and dc == 0:
                            count["duplicate_samples"] += 1
                            previous[key] = old
                        else:
                            count["same_frame_conflicts"] += 1
                        continue
                    if df > 1:
                        count["nonconsecutive_frame_pairs"] += 1
                    if dt == 0:
                        count["same_tick_changed" if dc else "same_tick_unchanged"] += 1
                        if dc:
                            # No trustworthy state/lifetime boundary: start fresh next time.
                            continue
                    elif dt == 1:
                        count["adjacent_ticks"] += 1
                        category = {0: "unchanged", 1: "plus_one", -1: "minus_one"}.get(dc, "other_change")
                        count[category] += 1
                    else:
                        count["tick_gaps"] += 1
                        count["unobserved_ticks"] += dt - 1
                if len(previous) >= history_limit:
                    previous.popitem(last=False)
                    issues["history_evictions"] += 1
                previous[key] = (frame, tick, cel)
    except (OSError, UnicodeError, csv.Error):
        # Partial observations remain reportable, but are never a clean pass.
        issues["read_errors"] += 1
    return stats, issues


def audit_animation_cels(folder: Path):
    """Summarize recorded counters, without certifying animation or smoothing.

    The source counter need not be the cel actually drawn (e.g. static coins).
    Even adjacent ticks with a +1 difference do not establish blend eligibility.
    """
    path = folder / "M2DebugObjects.csv"
    if not path.is_file():
        return [], ["INFO: Animation counters not captured; M2DebugObjects.csv is missing."]
    stats, issues = inspect_animation_cels(path)
    lines, notes = [], []
    for kind, count in stats.items():
        if not count["samples"]:
            notes.append(f"INFO: No usable {kind} animation-counter samples.")
            continue
        lines.append(
            f"{kind}: {count['samples']:,} samples; {count['baselines']:,} baselines; "
            f"{count['adjacent_ticks']:,} adjacent-tick pairs: "
            f"{count['unchanged']:,} unchanged, {count['plus_one']:,} +1, "
            f"{count['minus_one']:,} -1, {count['other_change']:,} other numeric changes.")
        lines.append(
            f"{kind}: same-tick redraws {count['same_tick_unchanged']:,} unchanged / "
            f"{count['same_tick_changed']:,} changed; {count['duplicate_samples']:,} duplicates; "
            f"{count['same_frame_conflicts']:,} same-frame conflicts; "
            f"{count['tick_gaps']:,} tick gaps ({count['unobserved_ticks']:,} unobserved ticks "
            f"summed per ID); {count['nonconsecutive_frame_pairs']:,} pairs skip render frames.")
        if count["same_tick_changed"] or count["same_frame_conflicts"]:
            notes.append(f"WARN: {kind} counters differ within a tick/frame; history was reset. "
                         "Possible identity reuse, mixed capture or state mutation; not automatically a gameplay bug.")
        if count["tick_gaps"]:
            notes.append(f"INFO: {kind} tick gaps were excluded from adjacent-tick counts; "
                         "sampling, missing objects or reused addresses can cause gaps.")
    for name, description in (
        ("incompatible_header", "incompatible/duplicate CSV headers"),
        ("malformed_rows", "malformed rows (all history cleared)"),
        ("order_resets", "frame/tick regressions (all history cleared)"),
        ("read_errors", "CSV read/encoding errors (results may be partial)"),
        ("history_evictions", "bounded-history evictions (later observations start new baselines)"),
    ):
        if issues[name]:
            notes.append(f"WARN: Animation counter audit: {issues[name]:,} {description}.")
    notes.append(
        "INFO: Animation counter observations cannot identify sprite state, sheet, row, mirror, "
        "draw mode, pause or object lifetime. Pointer IDs may be reused even on adjacent ticks. "
        "Numeric changes are not verified wraps, state transitions or safe-to-blend pairs; "
        "unchanged counters do not prove unchanged appearance. Sprite CSV rows cannot be reliably "
        "joined to these objects. Visual quality and display frame pacing remain unverified.")
    return lines, notes

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


def audit_fish_interpolation(folder: Path):
    """Match fish / fish-type-pet object IDs to their visual render offsets.

    Fish::Draw records both categories in M2DebugInterpolation.csv, so raw
    interpolation rows lack an explicit kind column. Object IDs are used only
    within one captured session; this is diagnostic, not gameplay logic.
    """
    objects = folder / "M2DebugObjects.csv"
    interpolation = folder / "M2DebugInterpolation.csv"
    if not objects.is_file() or not interpolation.is_file():
        return [], []
    ids = {"fish": set(), "fish_pet": set()}
    try:
        with objects.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                kind = row.get("kind")
                if kind in ids and row.get("objectId") and len(ids[kind]) < 20000:
                    ids[kind].add(row["objectId"])
        overlap = ids["fish"].intersection(ids["fish_pet"])
        totals = collections.Counter()
        shifted = collections.Counter()
        with interpolation.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                object_id = row.get("objectId")
                if not object_id or object_id in overlap:
                    continue
                for kind in ids:
                    if object_id in ids[kind]:
                        totals[kind] += 1
                        try:
                            if float(row["offsetX"]) or float(row["offsetY"]):
                                shifted[kind] += 1
                        except (KeyError, TypeError, ValueError):
                            pass
                        break
    except (OSError, csv.Error) as exc:
        return [], ["WARN: Cannot audit fish-type pet interpolation: {}.".format(exc)]
    lines = []
    notes = []
    for kind in ("fish", "fish_pet"):
        if totals[kind]:
            lines.append("{}: {:,} traced draws, {:,} nonzero offsets ({:.1f}%)".format(
                kind, totals[kind], shifted[kind],
                100.0 * shifted[kind] / totals[kind]))
            if kind == "fish_pet" and shifted[kind] == 0:
                notes.append("WARN: Fish-type pets were drawn but none received an interpolation "
                             "offset; verify FishTypePet::Update visual history.")
    if overlap:
        notes.append("INFO: {} fish/fish-pet object IDs overlap; excluded from interpolation "
                     "coverage to avoid misclassification.".format(len(overlap)))
    return lines, notes


def audit_missile_motion(folder: Path):
    """Audit original-tick missile movement and optional M2 visual offsets.

    An active, guarded graphical shift is expected in newer builds. It does
    not change the underlying simulation coordinates or prove display FPS.
    """
    path = folder / "M2DebugObjectMotion.csv"
    if not path.is_file():
        return [], []
    previous = {}
    ids = set()
    samples = moved = repeats = jumps = shifted = bad_shifts = same_tick_moves = 0
    max_x = max_y = max_dx = max_dy = 0.0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                if row.get("kind") != "missile":
                    continue
                samples += 1
                key = row.get("objectId")
                if not key:
                    continue
                ids.add(key)
                try:
                    tick = int(row["gameTick"])
                    x, y = float(row["simulationX"]), float(row["simulationY"])
                    dx, dy = float(row["offsetX"]), float(row["offsetY"])
                except (ValueError, TypeError, KeyError):
                    continue
                max_dx, max_dy = max(max_dx, abs(dx)), max(max_dy, abs(dy))
                if dx or dy:
                    shifted += 1
                    # The interpolation guard rejects >=8px per tick. The
                    # rendered integer offset must not exceed that bound.
                    if abs(dx) > 8 or abs(dy) > 8 or (
                        row.get("paused") == "1" or row.get("hasHistory") == "0"
                    ):
                        bad_shifts += 1
                if key in previous:
                    old_tick, old_x, old_y = previous[key]
                    if tick == old_tick:
                        repeats += 1
                        if abs(x-old_x) > .005 or abs(y-old_y) > .005:
                            same_tick_moves += 1
                    elif tick == old_tick + 1:
                        step_x, step_y = abs(x-old_x), abs(y-old_y)
                        if step_x > .005 or step_y > .005:
                            moved += 1
                        max_x, max_y = max(max_x, step_x), max(max_y, step_y)
                        if step_x >= 48 or step_y >= 48:
                            jumps += 1
                previous[key] = tick, x, y
    except (OSError, csv.Error) as exc:
        return [], ["WARN: Missile motion audit could not read CSV: {}.".format(exc)]
    if not samples:
        return [], ["INFO: Missile movement not captured in the sampled motion stream."]
    result = ["missile: {:,} draws, {} object IDs, {:,} adjacent-tick movements; "
              "largest consecutive step X/Y {:.2f}/{:.2f}px; {} guard-sized jumps; "
              "{:,} same-tick repeat draws; {:,} interpolated draws; "
              "maximum render offsets X/Y {:.2f}/{:.2f}px".format(
                  samples, len(ids), moved, max_x, max_y, jumps, repeats,
                  shifted, max_dx, max_dy)]
    notes = []
    if jumps:
        notes.append("INFO: Missile teleports/rapid movement need investigation before adding interpolation.")
    if same_tick_moves:
        notes.append("WARN: Missile simulation coordinates changed on {} same-tick redraw(s).".format(same_tick_moves))
    if bad_shifts:
        notes.append("WARN: {} missile render offset(s) exceeded guard limits or occurred paused/without history.".format(bad_shifts))
    if moved and not shifted:
        notes.append("INFO: No nonzero missile render offsets were captured; graphical smoothing not verified in this recording.")
    return result, notes


def audit_shot_effect_motion(folder: Path):
    """Inspect motion of shot effects with or without M2 smoke smoothing.

    Only smoke types 6 and 7 receive guarded render-only translations in
    current M2; legacy builds legitimately log zero visual offsets. Reused
    object pointers can yield apparent adjacent-tick jumps: keep reset/no-
    history jumps distinct from valid-history unexplained jumps.
    """
    path = folder / "M2DebugObjectMotion.csv"
    if not path.is_file():
        return [], ["INFO: Shot-effect motion CSV absent; animation movement unverified."]
    previous = {}
    ids = set()
    samples = repeats = same_tick_moves = adjacent = moves = jumps = gaps = 0
    visual_shifts = bad_shifts = new_history_jumps = uncertain_jumps = 0
    tick_rewinds = 0
    max_x = max_y = max_dx = max_dy = 0.0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                if row.get("kind") != "shot_effect":
                    continue
                samples += 1
                key = row.get("objectId")
                if not key:
                    continue
                ids.add(key)
                try:
                    tick = int(row["gameTick"])
                    x, y = float(row["simulationX"]), float(row["simulationY"])
                    dx, dy = float(row.get("offsetX", 0)), float(row.get("offsetY", 0))
                except (ValueError, TypeError, KeyError):
                    continue
                max_dx, max_dy = max(max_dx, abs(dx)), max(max_dy, abs(dy))
                if dx or dy:
                    visual_shifts += 1
                    if abs(dx) > 4 or abs(dy) > 4 or (
                        row.get("paused") == "1" or row.get("hasHistory") == "0"
                    ):
                        bad_shifts += 1
                if key in previous:
                    old_tick, old_x, old_y = previous[key]
                    delta = tick - old_tick
                    step_x, step_y = abs(x - old_x), abs(y - old_y)
                    if delta == 0:
                        repeats += 1
                        if step_x > .005 or step_y > .005:
                            same_tick_moves += 1
                    elif delta == 1:
                        adjacent += 1
                        max_x, max_y = max(max_x, step_x), max(max_y, step_y)
                        if step_x > .005 or step_y > .005:
                            moves += 1
                        if step_x >= 48.0 or step_y >= 48.0:
                            jumps += 1
                            if row.get("hasHistory") == "0" and not dx and not dy:
                                new_history_jumps += 1
                            else:
                                uncertain_jumps += 1
                    elif delta > 1:
                        gaps += 1
                    else:
                        tick_rewinds += 1
                previous[key] = tick, x, y
    except (OSError, csv.Error) as exc:
        return [], ["WARN: Shot-effect movement audit could not read CSV: {}.".format(exc)]
    if not samples:
        return [], ["INFO: No shot-effect motion samples; older M2 builds do not emit this trace. "
                    "No shot animation smoothness conclusion is possible."]
    lines = [
        "shot_effect: {:,} sampled draws, {} object IDs, {:,} adjacent-tick pairs "
        "({:,} moving); largest consecutive step X/Y {:.2f}/{:.2f}px; "
        "{} guard-sized jumps; {:,} same-tick redraws; {:,} unsampled tick gaps; "
        "{:,} visual shifts; maximum render offsets X/Y {:.2f}/{:.2f}px".format(
            samples, len(ids), adjacent, moves, max_x, max_y, jumps,
            repeats, gaps, visual_shifts, max_dx, max_dy)
    ]
    notes = []
    if not adjacent:
        notes.append("INFO: No consecutive-tick shot-effect positions recorded; "
                     "motion safety and interpolation cannot be assessed.")
    if gaps:
        notes.append("INFO: Shot-effect trace skips {} tick interval(s); "
                     "do not interpret gaps as individual movement steps.".format(gaps))
    if same_tick_moves:
        notes.append("WARN: Shot-effect simulation coordinates changed on {} "
                     "same-tick redraw(s); investigate before interpolating.".format(same_tick_moves))
    if bad_shifts:
        notes.append("WARN: {} shot-effect visual shift(s) exceeded guards or occurred "
                     "during pause/without history.".format(bad_shifts))
    if new_history_jumps:
        notes.append("INFO: {} >=48px shot-effect jump(s) had reset visual history "
                     "and zero offset; likely newly spawned objects reusing addresses, "
                     "but object identity cannot be proven from this trace.".format(new_history_jumps))
    if uncertain_jumps:
        notes.append("INFO: {} >=48px shot-effect jump(s) lacked confirmed reset/no-shift "
                     "evidence; investigate before broad interpolation.".format(uncertain_jumps))
    if tick_rewinds:
        notes.append("INFO: {} shot-effect tick rewind(s); check whether object IDs "
                     "were reused or captures mixed.".format(tick_rewinds))
    return lines, notes
