"""Regression checks for M2 trace integrity and pet movement reporting."""
import csv
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from trace_integrity import inspect_trace, audit_traces, audit_object_movement
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
