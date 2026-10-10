"""Regression fixtures for the local M2 CSV diagnostic report."""
import csv
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_logs import analyze

class DiagnosticAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def csv(self, name, header, records):
        with (self.folder / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header.split(","))
            writer.writerows(records)

    def normal(self):
        self.csv("M2DebugFrames.csv",
                 "frame,totalSimTicks,presented,invalidCels,warnings,renderMs,drawsFish,drawsCoin,drawsFood,drawsAlien,drawsOtherPet,drawsMissile,drawsShotEffect,drawsFishPet",
                 [[0, 1, 1, 0, 0, 10.4, 1, 1, 1, 1, 1, 1, 1, 1],
                  [1, 1, 1, 0, 0, 13.1, 1, 1, 1, 1, 1, 1, 1, 1]])
        self.csv("M2DebugEvents.csv", "frame,gameTick,severity,event",
                 [[0, 0, "INFO", "debug_enabled"],
                  [0, 1, "INFO", "tank_paused"],
                  [1, 1, "INFO", "tank_resumed"]])
        self.csv("M2DebugInvalidSprites.csv", "frame,assetPath", [])
        self.csv("M2DebugObjectMotion.csv",
                 "frame,gameTick,kind,objectId,offsetX,offsetY,paused",
                 [[0, 1, "coin", 100, -1, 0, 0],
                  [0, 1, "food", 200, 0, -1, 0],
                  [1, 1, "coin", 100, 0, 0, 1]])
        self.csv("M2DebugInterpolation.csv",
                 "frame,gameTick,objectId,offsetX,offsetY",
                 [[0, 1, 300, 1, 0]])
        (self.folder / "M2Timing.log").write_text(
            "sim=35.71 Hz, present=59.98 Hz, mode=M2 experimental\n", encoding="utf-8")

    def test_normal_report(self):
        self.normal()
        message, bad = analyze(self.folder)
        self.assertFalse(bad)
        self.assertIn("Recorded frame rows: 2", message)
        self.assertIn("59.980FPS", message)
        self.assertIn("coin: 2 samples, 1 shifted", message)
        self.assertIn("No automated issues detected", message)

    def test_invalid_sprite_detected(self):
        self.normal()
        self.csv("M2DebugInvalidSprites.csv", "frame,assetPath",
                 [[1, "images/bad"]])
        message, bad = analyze(self.folder)
        self.assertTrue(bad)
        self.assertIn("ERROR: unexpected sprite rows", message)

    def test_paused_object_movement_detected(self):
        self.normal()
        self.csv("M2DebugObjectMotion.csv",
                 "frame,gameTick,kind,objectId,offsetX,offsetY,paused",
                 [[1, 1, "coin", 100, 3, 0, 1]])
        message, bad = analyze(self.folder)
        self.assertTrue(bad)
        self.assertIn("moving sprites while paused", message)

    def test_nonpresented_frame_details(self):
        self.normal()
        self.csv("M2DebugFrames.csv",
                 "frame,totalSimTicks,presented,invalidCels,warnings,renderMs,elapsedMs,drawsOtherPet,drawsMissile,drawsShotEffect",
                 [[42, 24, 0, 0, 0, 9.505, 16.670, 1, 1, 1]])
        message, bad = analyze(self.folder)
        self.assertFalse(bad)
        self.assertIn("frame 42 (tick 24, render 9.505ms", message)
        self.assertIn("not proof of a monitor drop", message)

    def test_missing_extra_coverage_is_not_claimed(self):
        self.normal()
        self.csv("M2DebugFrames.csv",
                 "frame,totalSimTicks,presented,invalidCels,warnings,renderMs,drawsFish,drawsCoin,drawsFood,drawsAlien",
                 [[0, 1, 1, 0, 0, 1.0, 1, 1, 1, 0]])
        message, bad = analyze(self.folder)
        self.assertFalse(bad)
        self.assertIn("extra pet/missile/shot probes not present", message)

    def test_missing_frame_file_detected(self):
        message, bad = analyze(self.folder)
        self.assertTrue(bad)
        self.assertIn("M2DebugFrames.csv missing", message)

if __name__ == "__main__":
    unittest.main()
