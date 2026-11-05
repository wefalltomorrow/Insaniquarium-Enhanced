"""Compare CPU-only helper binaries with alternating run order; never report FPS."""
import argparse
import csv
import hashlib
import io
import json
import platform
import statistics
import subprocess
from pathlib import Path


def read_rows(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    expected = {(p, str(n), op) for p in ("opaque", "equal_partial", "mixed_alpha", "masked")
                for n in (1, 32, 128) for op in ("capture", "transition", "endpoint", "held", "disabled")}
    result = {}
    for row in rows:
        key = (row["profile"], row["owners"], row["operation"])
        if key in result:
            raise ValueError("Duplicate benchmark row")
        median, p95 = float(row["median_us"]), float(row["p95_us"])
        if not 0 <= median <= p95 < float("inf") or int(row["samples"]) != 31:
            raise ValueError("Invalid timing/sample count")
        if int(row["payload_bytes"]) != int(row["owners"]) * 228096:
            raise ValueError("Unexpected CPU payload size")
        int(row["checksum"])
        result[key] = row
    if set(result) != expected:
        raise ValueError("Missing or unexpected benchmark cases")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    paths = {name: getattr(args, name).resolve() for name in ("before", "after")}
    runs = {"before": [], "after": []}
    for repeat in range(3):
        for name in (("before", "after") if repeat % 2 == 0 else ("after", "before")):
            print(f"Running {name}, pair {repeat+1}/3", flush=True)
            run = subprocess.run([str(paths[name])], capture_output=True, text=True, check=True, timeout=180)
            runs[name].append(read_rows(run.stdout))
    rows = []
    for key in sorted(runs["before"][0]):
        measurements = [r[key] for values in runs.values() for r in values]
        if len({r["checksum"] for r in measurements}) != 1:
            raise ValueError(f"Output mismatch: {key}")
        before = statistics.median(float(r[key]["median_us"]) for r in runs["before"])
        after = statistics.median(float(r[key]["median_us"]) for r in runs["after"])
        rows.append(dict(profile=key[0], owners=int(key[1]), operation=key[2],
                         before_median_us=before, after_median_us=after,
                         speedup=before / after if after else None,
                         measurements=measurements))
    report = dict(schema=1, platform=platform.platform(), processor=platform.processor(),
                  binaries={name: dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                            for name, path in paths.items()},
                  methodology="Three paired runs, alternating order; each case has 3 warmups and 31 samples. "
                  "Median of run medians. Exact output checksums agree. Synchronized transition stress, "
                  "synthetic pixels at 720x432. Payload excludes allocator/framework overhead.",
                  limitations="CPU helper only: no GPU upload, game, audio, OS pacing or FPS measurement. "
                  "Steady-state timings exclude initial allocation. No timing pass/fail threshold.",
                  rows=rows)
    args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    for row in rows:
        if row["owners"] == 128 and row["operation"] == "transition":
            print(row["profile"], before_label(row))


def before_label(row):
    return f"{row['before_median_us']:.3f} -> {row['after_median_us']:.3f} us ({row['speedup']:.2f}x)"


if __name__ == "__main__":
    main()
