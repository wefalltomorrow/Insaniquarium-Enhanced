"""Fail-closed regression checks for M2 Shot callback timing."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fix_shot_sound_tick import patch, UPDATE, DRAW, UPDATE_FIXED, DRAW_FIXED

SOURCE = (
    '#include "Shot.h"\n'
    + UPDATE
    + '\n\tm0x158++;\n}\n'
    + DRAW
    + '\n\tif (m0x164) return;\n}\n'
)


class ShotSoundTickTests(unittest.TestCase):
    def test_m2_callbacks_move_to_simulation_only(self):
        fixed = patch(SOURCE)
        self.assertIn(UPDATE_FIXED, fixed)
        self.assertIn(DRAW_FIXED, fixed)
        self.assertEqual(fixed.count("GameObject::UpdateFishSongMgr();"), 2)
        self.assertIn(
            "if (gEnhancedM2Enabled)\n\t\tGameObject::UpdateFishSongMgr();",
            fixed)
        self.assertIn(
            "if (!gEnhancedM2Enabled)\n\t\tGameObject::UpdateFishSongMgr();",
            fixed)
        self.assertIn("\tm0x158++;", fixed)
        self.assertIn("\tif (m0x164) return;", fixed)

    def test_original_mode_uses_only_draw_callback(self):
        fixed = patch(SOURCE)
        update_body = fixed.split("void PopLib::Shot::Update()", 1)[1].split(
            "\n}", 1)[0]
        draw_body = fixed.split("void PopLib::Shot::Draw(Graphics* g)", 1)[1].split(
            "\n}", 1)[0]
        self.assertEqual(update_body.count("GameObject::UpdateFishSongMgr();"), 1)
        self.assertEqual(draw_body.count("GameObject::UpdateFishSongMgr();"), 1)
        self.assertTrue("if (gEnhancedM2Enabled)" in update_body)
        self.assertTrue("if (!gEnhancedM2Enabled)" in draw_body)

    def test_fail_closed_on_source_changes_and_second_application(self):
        with self.assertRaises(RuntimeError):
            patch(patch(SOURCE))
        with self.assertRaises(RuntimeError):
            patch(SOURCE.replace("M2Debug::ShotEffect", "M2Debug::OtherPet"))
        with self.assertRaises(RuntimeError):
            patch(SOURCE + SOURCE)
        with self.assertRaises(RuntimeError):
            patch(SOURCE.replace("\tGameObject::UpdateFishSongMgr();", "",
                                 1))


if __name__ == "__main__":
    unittest.main()
