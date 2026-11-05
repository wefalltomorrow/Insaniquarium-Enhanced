"""Regression tests for opt-in bounded missile interpolation."""
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from apply_missile_interpolation import (
    patch, HEADER_ANCHOR, INCLUDE_ANCHOR, UPDATE_ANCHOR, DRAW_ANCHOR
)

HEADER = '#include "GameObject.h"\n' + HEADER_ANCHOR + '\n\tint m0x178;\n\t};\n'
SOURCE = (INCLUDE_ANCHOR + "\n"
          + "void PopLib::Missle::Update()\n{\n" + UPDATE_ANCHOR + "\n    mXD += mVX;\n}\n"
          + "void PopLib::Missle::Draw(Graphics* g)\n{\n" + DRAW_ANCHOR
          + " (mMissleType == 1);\n    DrawHelper(g, doMirror);\n}\n")

class MissileInterpolationTests(unittest.TestCase):
    def test_guarded_shift_without_simulation_changes(self):
        head, source = patch(HEADER, SOURCE)
        self.assertIn("double mM2PrevXD = 0.0", head)
        self.assertIn("mM2HavePrev = false", head)
        self.assertIn("mM2PrevXD = mXD", source)
        self.assertIn("mM2PrevYD = mYD", source)
        self.assertIn("ScopedObjectTranslation<Graphics>", source)
        self.assertIn("gEnhancedM2Blend, 8.0", source)
        self.assertIn("m2VisualShift.ShiftX(), m2VisualShift.ShiftY()", source)
        self.assertIn("mXD += mVX", source)
        self.assertIn("DrawHelper(g, doMirror)", source)

    def test_sound_and_non_m2_path(self):
        _, src = patch(HEADER, SOURCE)
        self.assertIn("if (gEnhancedM2Enabled) {\n        mM2PrevXD", src)
        self.assertIn("if (!gEnhancedM2Enabled)\n        UpdateFishSongMgr();", src)
        self.assertEqual(src.count("UpdateFishSongMgr();"), 2)
        self.assertIn("mApp->mBoard && mApp->mBoard->mPause", src)

    def test_fail_closed_against_bad_or_duplicate_anchors(self):
        h, s = patch(HEADER, SOURCE)
        with self.assertRaises(RuntimeError):
            patch(h, s)
        with self.assertRaises(RuntimeError):
            patch(HEADER, SOURCE.replace("M2Debug::Missile", "M2Debug::Food"))
        with self.assertRaises(RuntimeError):
            patch(HEADER + HEADER, SOURCE)
        with self.assertRaises(RuntimeError):
            patch(HEADER, SOURCE.replace("UpdateCounters();", "BadCall();"))

if __name__ == "__main__":
    unittest.main()
