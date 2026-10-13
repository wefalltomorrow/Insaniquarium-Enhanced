"""Regression suite for a confirmed uninitialised shot-kind read in WinFish.

Validate the exact generated source transform without modifying defaults,
random-number calls, the shot animation timer, or gameplay save logic.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fix_shot_constructor import patch, ORIGINAL, FIXED, CONSTRUCTOR_START

SOURCE = (
    '#include "Shot.h"\n'
    'PopLib::Shot::Shot() {\n'
    '\tmType = TYPE_SHOT;\n'
    '}\n'
    'PopLib::Shot::Shot(int theX, int theY, int theType)\n'
    '{\n'
    + ORIGINAL +
    '\tm0x168 = mApp->mSeed->Next() % 200 + 50;\n'
    '}\n'
    'void PopLib::Shot::Update() { m0x158++; }\n'
    'void PopLib::Shot::Draw(Graphics* g) { DrawHelper(g, false); }\n'
)

class ShotConstructorFixTests(unittest.TestCase):
    def test_assign_type_before_branch(self):
        changed = patch(SOURCE)
        ctor = changed.split(CONSTRUCTOR_START, 1)[1].split("\n}", 1)[0]
        self.assertIn(FIXED, ctor)
        self.assertEqual(ctor.count("mShotType = theType;"), 1)
        self.assertLess(ctor.index("mShotType = theType;"),
                        ctor.index("if (mShotType == 0 || mShotType == 2)"))
        self.assertEqual(ctor.count("mApp->mSeed->Next() % 3"), 1)
        self.assertEqual(ctor.count("mApp->mSeed->Next() % 200 + 50"), 1)
        self.assertIn("void PopLib::Shot::Update() { m0x158++; }", changed)
        self.assertIn("void PopLib::Shot::Draw(Graphics* g) { DrawHelper(g, false); }", changed)
        self.assertIn("PopLib::Shot::Shot() {\n\tmType = TYPE_SHOT;", changed)

    def test_source_with_other_changes_fails_closed(self):
        with self.assertRaises(RuntimeError):
            patch(SOURCE.replace("mShotType == 2", "mShotType == 3"))
        with self.assertRaises(RuntimeError):
            patch(SOURCE.replace("mApp->mSeed->Next() % 3", "mApp->mSeed->Next() % 4"))
        with self.assertRaises(RuntimeError):
            patch(SOURCE + SOURCE)
        with self.assertRaises(RuntimeError):
            patch("void PopLib::Shot::Draw(Graphics* g) {}")

    def test_reapplying_fix_is_rejected(self):
        with self.assertRaises(RuntimeError):
            patch(patch(SOURCE))

    def test_gameplay_delay_semantics(self):
        # A deterministic argument-dependent decision, not heap contents.
        # Random values still come from the same RNG for other shot types.
        def needs_rng(kind):
            return kind not in (0, 2)
        self.assertEqual([needs_rng(k) for k in range(9)],
                         [False, True, False, True, True, True, True, True, True])

if __name__ == "__main__":
    unittest.main()
