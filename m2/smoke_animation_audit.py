"""Read-only coverage audit for optional smoke sprite transitions."""
import csv
import math

def audit_smoke_animation(folder):
    path = folder / "M2DebugSmokeAnimation.csv"
    if not path.is_file(): return [], []
    count = transitions = fractional = same_tick_changes = invalid = malformed = 0
    previous = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"frame","gameTick","objectId","shotType","simulationAge","simulationCel",
                    "fromCel","toCel","mix","transition","paused"}
        if not required.issubset(reader.fieldnames or []):
            return [], ["ERROR: Smoke animation trace has an incompatible header."]
        for row in reader:
            count += 1
            try:
                if None in row or any(v is None for v in row.values()): raise ValueError()
                values = {k:int(row[k]) for k in required - {"objectId","mix"}}
                mix = float(row["mix"])
                if not math.isfinite(mix): raise ValueError()
            except (ValueError, TypeError):
                malformed += 1
                continue
            active = values["transition"] == 1
            if active:
                transitions += 1
                fractional += 0.0 < mix < 1.0
                if (values["shotType"] not in (6,7) or values["paused"] or
                    not 0.0 <= mix <= 1.0 or not 4 <= values["simulationAge"] <= 38 or
                    values["simulationAge"] % 2 or values["fromCel"] < 0 or
                    values["toCel"] != values["fromCel"] + 1 or
                    values["toCel"] != values["simulationCel"] or
                    values["simulationCel"] != values["simulationAge"] // 2 - 1):
                    invalid += 1
            key = (row["objectId"], values["shotType"])
            identity = (values["gameTick"], values["simulationAge"], values["simulationCel"],
                        values["fromCel"], values["toCel"])
            old = previous.get(key)
            if active and old and old[0] == identity and old[1] != mix and old[2] < values["frame"]:
                same_tick_changes += 1
            previous[key] = (identity, mix, values["frame"]) if active else None
            if len(previous) > 10000: previous.clear()
    lines = [f"Smoke animation: {count:,} samples; {transitions:,} guarded transitions; "
             f"{fractional:,} fractional blends; {same_tick_changes:,} same-tick changing blends with stable simulation fields."]
    notes = []
    if invalid or malformed:
        notes.append(f"ERROR: Smoke animation has {invalid} invalid transitions and {malformed} malformed rows.")
    if count >= 350000:
        notes.append("INFO: Smoke animation reached its 350,000-row cap; later coverage is unavailable.")
    if not fractional:
        notes.append("INFO: No fractional smoke transitions recorded; use the Smoke Blend Debug launcher and trigger rising smoke.")
    notes.append("INFO: Smoke crossfade telemetry does not establish visual quality; compare opacity and doubled edges in game.")
    return lines, notes
