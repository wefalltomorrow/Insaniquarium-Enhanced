"""Regression checks for M2 trace integrity and pet movement reporting."""
import csv
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from trace_integrity import inspect_trace, audit_traces, audit_object_movement, audit_fish_interpolation, audit_missile_motion, audit_shot_effect_motion
from analyze_logs import analyze


class TraceIntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = pathlib.Path(temp.name)

    def write_csv(self, name, head, rows):
        with (self.folder / name).open("w", newline="", encoding="utf-8") as file:
            w = csv.writer(file)
            w.writerow(head)
            w.writerows(rows)

    def test_valid_trace_has_no_findings(self):
        self.write_csv("M2DebugFrames.csv", ["frame", "presented"], [[0, 1], [1, 1]])
        self.write_csv("M2DebugObjects.csv", ["frame", "kind"], [[0, "fish"], [1, "fish"]])
        details, findings = audit_traces(self.folder, 1)
        self.assertEqual(findings, [])
        self.assertIn("M2DebugObjects.csv: 2 rows; last frame 1", details)

    def test_truncated_row_and_missing_newline(self):
        path = self.folder / "M2DebugObjects.csv"
        path.write_bytes(b"frame,gameTick,kind\n0,1,fish\n1,2")
        rows, last, issues = inspect_trace(path)
        self.assertEqual(rows, 2)
        self.assertEqual(last, 0)
        self.assertTrue(any("fields; expected" in x for x in issues))
        self.assertTrue(any("no newline" in x for x in issues))

    def test_trace_extends_beyond_master(self):
        self.write_csv("M2DebugInterpolation.csv", ["frame", "offsetX"], [[3, 0], [200, 1]])
        _details, findings = audit_traces(self.folder, 100)
        self.assertTrue(any("extends to frame 200" in x for x in findings))

    def test_object_csv_row_cap_reported(self):
        self.write_csv("M2DebugObjects.csv", ["frame", "kind"],
                       [[1, "fish"], [2, "fish"], [3, "fish"], [4, "fish"]])
        with patch("trace_integrity.ROW_CAP", 4):
            _details, findings = audit_traces(self.folder, 4)
        self.assertTrue(any("reached 4-row trace limit" in x for x in findings))

    def test_moving_and_stationary_pet_distinction(self):
        cols = ["frame", "gameTick", "kind", "objectId",
                "simulationX", "simulationY", "simMoved", "changedCel"]
        self.write_csv("M2DebugObjects.csv", cols, [
            [0, 1, "other_pet", "10", 50, 60, 0, 0],
            [1, 2, "other_pet", "10", 50, 60, 0, 1],
            [0, 1, "fish_pet", "20", 10, 20, 0, 0],
            [1, 2, "fish_pet", "20", 13, 19, 1, 0],
            [0, 1, "alien", "30", 21, 30, 0, 0],
            [1, 2, "alien", "30", 23, 30, 1, 1],
        ])
        info, findings = audit_object_movement(self.folder)
        self.assertTrue(any("fish_pet: 2 draw samples; 1 object IDs; 1 simulated moves" in x for x in info))
        self.assertTrue(any("largest observed step X/Y 3.00/1.00px" in x for x in info))
        self.assertTrue(any("other_pet was drawn, but no simulated movement" in x for x in findings))
        self.assertFalse(any("fish_pet was drawn, but no simulated movement" in x for x in findings))

    def test_detects_fish_pet_missing_visual_history(self):
        cols = ["frame", "gameTick", "kind", "objectId", "simulationX",
                "simulationY", "simMoved", "changedCel"]
        self.write_csv("M2DebugObjects.csv", cols, [
            [1, 1, "fish", 101, 10, 10, 0, 0],
            [1, 1, "fish_pet", 202, 20, 20, 0, 0],
            [2, 2, "fish_pet", 202, 22, 20, 1, 1]])
        self.write_csv("M2DebugInterpolation.csv",
                       ["frame", "objectId", "offsetX", "offsetY"],
                       [[1, 101, 1, 0], [1, 202, 0, 0], [2, 202, 0, 0]])
        lines, findings = audit_fish_interpolation(self.folder)
        self.assertTrue(any("fish_pet: 2 traced draws, 0 nonzero offsets" in x for x in lines))
        self.assertTrue(any("Fish-type pets were drawn but none" in x for x in findings))
        self.write_csv("M2DebugInterpolation.csv",
                       ["frame", "objectId", "offsetX", "offsetY"],
                       [[1, 101, 1, 0], [1, 202, -1, 0], [2, 202, 0, 0]])
        lines, findings = audit_fish_interpolation(self.folder)
        self.assertTrue(any("fish_pet: 2 traced draws, 1 nonzero offsets (50.0%)" in x for x in lines))
        self.assertFalse(any("Fish-type pets were drawn but none" in x for x in findings))

    def test_missile_movement_and_guard_analysis(self):
        self.write_csv(
            "M2DebugObjectMotion.csv",
            ["frame", "gameTick", "kind", "objectId", "simulationX",
             "simulationY", "renderX", "renderY", "offsetX", "offsetY"],
            [[0, 1, "missile", 8, 100, 100, 100, 100, 0, 0],
             [1, 1, "missile", 8, 100, 100, 100, 100, 0, 0],
             [2, 2, "missile", 8, 102, 103, 102, 103, 0, 0],
             [3, 3, "missile", 8, 155, 103, 155, 103, 0, 0],
             [4, 3, "food", 10, 3, 4, 3, 4, 0, 0]])
        detail, warnings = audit_missile_motion(self.folder)
        self.assertIn("missile: 4 draws, 1 object IDs, 2 adjacent-tick movements", detail[0])
        self.assertIn("largest consecutive step X/Y 53.00/3.00px", detail[0])
        self.assertIn("1 guard-sized jumps", detail[0])
        self.assertTrue(any("teleports/rapid movement" in x for x in warnings))

    def test_no_missile_samples_not_a_false_pass(self):
        self.write_csv(
            "M2DebugObjectMotion.csv",
            ["frame", "gameTick", "kind", "objectId", "simulationX",
             "simulationY", "offsetX", "offsetY"],
            [[0, 1, "food", 8, 100, 100, 0, 0]])
        details, notes = audit_missile_motion(self.folder)
        self.assertEqual(details, [])
        self.assertTrue(any("not captured" in x for x in notes))


    def test_shot_effect_motion_and_sampling_gaps(self):
        self.write_csv(
            "M2DebugObjectMotion.csv",
            ["frame", "gameTick", "kind", "objectId", "simulationX",
             "simulationY", "renderX", "renderY", "offsetX", "offsetY"],
            [[0, 1, "shot_effect", 8, 10, 20, 10, 20, 0, 0],
             [1, 1, "shot_effect", 8, 10, 20, 10, 20, 0, 0],
             [2, 2, "shot_effect", 8, 12, 20, 12, 20, 0, 0],
             [3, 4, "shot_effect", 8, 40, 20, 40, 20, 0, 0],
             [4, 4, "shot_effect", 8, 41, 20, 41, 20, 0, 0],
             [5, 5, "shot_effect", 8, 100, 20, 100, 20, 0, 0],
             [6, 5, "coin", 19, 4, 5, 4, 5, 0, 0]])
        detail, notes = audit_shot_effect_motion(self.folder)
        self.assertIn("shot_effect: 6 sampled draws, 1 object IDs, "
                      "2 adjacent-tick pairs (2 moving)", detail[0])
        self.assertIn("1 guard-sized jumps", detail[0])
        self.assertIn("2 same-tick redraws", detail[0])
        self.assertIn("1 unsampled tick gaps", detail[0])
        self.assertTrue(any("simulation coordinates changed" in n for n in notes))
        self.assertTrue(any("trace skips 1 tick" in n for n in notes))
        self.assertFalse(any("nonzero visual offset" in n for n in notes))
        report_folder = self.folder
        self.write_csv("M2DebugFrames.csv", ["frame", "totalSimTicks", "presented"],
                       [[i, i+1, 1] for i in range(6)])
        report, errors = analyze(report_folder)
        self.assertIn("Shot-effect simulation motion", report)
        self.assertFalse(errors)  # Data quality is a warning, not a fatal error.

    def test_smoke_smoothing_offsets_and_reset_history_jumps(self):
        self.write_csv(
            "M2DebugObjectMotion.csv",
            ["frame", "gameTick", "kind", "objectId", "simulationX",
             "simulationY", "renderX", "renderY", "offsetX", "offsetY",
             "blend", "paused", "hasHistory"],
            [[0, 20, "shot_effect", 801, 15, 200, 15, 200, 0, 0, 0.1, 0, 1],
             [1, 21, "shot_effect", 801, 15, 198, 15, 199, 0, 1, 0.5, 0, 1],
             [2, 21, "shot_effect", 801, 15, 198, 15, 199, 0, 1, 0.5, 0, 1],
             # Previous object died; freshly constructed effect reuses the address.
             [3, 22, "shot_effect", 801, 450, 300, 450, 300, 0, 0, 0.1, 0, 0]])
        details, notes = audit_shot_effect_motion(self.folder)
        self.assertIn("4 sampled draws", details[0])
        self.assertIn("2 visual shifts", details[0])
        self.assertIn("1 guard-sized jumps", details[0])
        self.assertTrue(any("reset visual history" in n for n in notes))
        self.assertFalse(any("though interpolation is disabled" in n for n in notes))
        self.assertFalse(any(n.startswith("WARN:") for n in notes))

    def test_interpolated_missile_is_not_reported_as_an_error(self):
        self.write_csv(
            "M2DebugObjectMotion.csv",
            ["frame", "gameTick", "kind", "objectId", "simulationX",
             "simulationY", "renderX", "renderY", "offsetX", "offsetY",
             "blend", "paused", "hasHistory"],
            [[0, 1, "missile", 901, 100, 200, 100, 200, 0, 0, .1, 0, 1],
             [1, 2, "missile", 901, 102.5, 201.25, 101.5, 201.25, -1, 0, .5, 0, 1],
             [2, 2, "missile", 901, 102.5, 201.25, 101.5, 201.25, -1, 0, .5, 0, 1]])
        details, notes = audit_missile_motion(self.folder)
        self.assertIn("3 draws", details[0])
        self.assertIn("2 interpolated draws", details[0])
        self.assertIn("largest consecutive step X/Y 2.50/1.25px", details[0])
        self.assertFalse(any(n.startswith("WARN:") for n in notes))

    def test_paused_or_uninitialised_missile_history_rejected(self):
        self.write_csv(
            "M2DebugObjectMotion.csv",
            ["frame", "gameTick", "kind", "objectId", "simulationX",
             "simulationY", "offsetX", "offsetY", "paused", "hasHistory"],
            [[0, 1, "missile", 900, 100, 200, 1, 0, 1, 0]])
        _details, notes = audit_missile_motion(self.folder)
        self.assertTrue(any("exceeded guard limits or occurred paused/without history"
                            in n for n in notes))

    def test_older_shot_trace_not_claimed_as_verified(self):
        self.write_csv("M2DebugObjectMotion.csv",
                       ["frame", "gameTick", "kind", "objectId", "simulationX",
                        "simulationY", "offsetX", "offsetY"],
                       [[0, 1, "missile", 3, 50, 60, 0, 0]])
        details, notes = audit_shot_effect_motion(self.folder)
        self.assertFalse(details)
        self.assertTrue(any("older M2 builds" in n for n in notes))

    def test_report_integration(self):
        self.write_csv("M2DebugFrames.csv",
                       ["frame", "totalSimTicks", "presented", "warnings", "renderMs"],
                       [[0, 1, 1, 0, 10], [1, 2, 1, 0, 8]])
        self.write_csv("M2DebugObjects.csv",
                       ["frame", "gameTick", "kind", "objectId", "simulationX",
                        "simulationY", "simMoved", "changedCel"],
                       [[0, 1, "other_pet", 1, 10, 10, 0, 0],
                        [1, 2, "other_pet", 1, 10, 10, 0, 0]])
        report, failed = analyze(self.folder)
        self.assertFalse(failed)
        self.assertIn("Trace integrity", report)
        self.assertIn("Other-object simulation motion", report)
        self.assertIn("no simulated movement", report)


if __name__ == "__main__":
    unittest.main()
