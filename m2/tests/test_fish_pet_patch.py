"""Ensure the optional M2 fish-type pet patch cannot touch unrelated logic."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from apply_fish_pet import ANCHOR, patch

class FishPetPatchTests(unittest.TestCase):
    def test_only_simulation_tick_path_changes(self):
        source = '#include "FishTypePet.h"\n' + ANCHOR + '\n\tBoard* aBoard = mApp->mBoard;\n'
        changed = patch(source)
        self.assertEqual(changed.count("UpdateFishSongMgr();"), 1)
        self.assertIn("mM2PrevXD = mXD;", changed)
        self.assertIn("mM2PrevYD = mYD;", changed)
        self.assertIn("mM2HavePrev = true;", changed)
        self.assertIn('extern "C" bool gEnhancedM2Enabled;', changed)
        self.assertIn("if (gEnhancedM2Enabled)", changed)
        self.assertIn("mM2HavePrev = false;", changed)
        self.assertIn("GameObject::UpdateCounters();\n\tBoard* aBoard", changed)
        self.assertNotIn("Translate(", changed)
        self.assertEqual(changed.count("UpdateCounters();"), 1)

    def test_patch_rejects_missing_or_duplicate_anchor(self):
        with self.assertRaises(RuntimeError):
            patch("void FishTypePet::Draw() {}")
        with self.assertRaises(RuntimeError):
            patch(ANCHOR + "\n" + ANCHOR)

    def test_patch_rejects_second_application(self):
        with self.assertRaises(RuntimeError):
            patch(patch(ANCHOR))

if __name__ == "__main__":
    unittest.main()
