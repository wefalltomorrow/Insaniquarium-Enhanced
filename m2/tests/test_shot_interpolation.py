"""Regression checks for M2 guarded shot-smoke interpolation."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from apply_shot_interpolation import (
    patch, HEADER_ANCHOR, INCLUDE_ANCHOR, UPDATE_ANCHOR, DRAW_ANCHOR,
)

HEADER = '#include "GameObject.h"\n' + HEADER_ANCHOR + '\n\tint m0x158;\n\t};\n'
SOURCE = (
    INCLUDE_ANCHOR + '\n'
    + 'void PopLib::Shot::Update()\n{\n' + UPDATE_ANCHOR
    + '\n\tif (mShotType == 6 || mShotType == 7) {\n\t\tmY -= 2;\n\t}\n}\n'
    + 'void PopLib::Shot::Draw(Graphics* g)\n{\n'
    + '\tM2Debug::IntDrawGuard m2Probe(M2Debug::ShotEffect, this, mX, mY, m0x158);\n'
    + DRAW_ANCHOR
    + '\n\tg->DrawImageCel(IMAGE_SMOKETINY, 0, 0, m0x15c);\n}\n'
)

class ShotInterpolationTests(unittest.TestCase):
    def test_moving_smoke_only_and_original_coordinates(self):
        header, source = patch(HEADER, SOURCE)
        self.assertIn("double mM2PrevShotX = 0.0", header)
        self.assertIn("bool mM2HavePrevShot = false", header)
        self.assertIn("mM2PrevShotY = mY", source)
        self.assertIn("mShotType == 6 || mShotType == 7", source)
        self.assertIn("gEnhancedM2Enabled && m2MovingSmoke", source)
        self.assertIn("gEnhancedM2Blend, 4.0", source)
        self.assertIn("ScopedObjectTranslation<Graphics>", source)
        self.assertIn("m2ShotShift.ShiftX(), m2ShotShift.ShiftY()", source)
        self.assertIn("mY -= 2", source)
        self.assertEqual(source.count("GameObject::UpdateFishSongMgr();"), 2)

    def test_non_m2_and_pause_guards(self):
        _, source = patch(HEADER, SOURCE)
        self.assertIn("if (!gEnhancedM2Enabled)\n\t\tGameObject::UpdateFishSongMgr();", source)
        self.assertIn("mApp->mBoard && mApp->mBoard->mPause", source)
        self.assertIn("mM2HavePrevShot = false;", source)
        self.assertIn("if (m0x164 != 0)\n\t\treturn;", source)
        self.assertNotIn(DRAW_ANCHOR, source)

    def test_fails_closed_on_second_patch_and_source_changes(self):
        header, source = patch(HEADER, SOURCE)
        with self.assertRaises(RuntimeError):
            patch(header, source)
        with self.assertRaises(RuntimeError):
            patch(HEADER, SOURCE.replace("ShotEffect", "Missile"))
        with self.assertRaises(RuntimeError):
            patch(HEADER + HEADER, SOURCE)
        with self.assertRaises(RuntimeError):
            patch(HEADER, SOURCE.replace("gEnhancedM2Enabled", "gEnhancedM2"))

if __name__ == "__main__":
    unittest.main()
