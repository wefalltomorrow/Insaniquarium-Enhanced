import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from apply_smoke_animation import patch, HEADER, UPDATE, DRAW, SYNC

H = '#include "GameObject.h"\n' + HEADER
UPDATE_BODY = UPDATE + "\n\tGameObject::UpdateCounters();\n\tm0x158++;\n\tmY -= 2;\n\tif (m0x158 > 39) Remove();\n\tm0x15c = m0x158 / 2 - 1;\n"
SYNC_BODY = "\n\tGameObject::Sync(theSync);\n" + "".join(
    f"\ttheSync->SyncLong({field});\n" for field in ["m0x158","m0x15c","mShotType","m0x164","m0x168"])
S = ("void PopLib::Shot::Update()\n{\n" + UPDATE_BODY + "}\n" +
     "void PopLib::Shot::Draw(Graphics* g)\n{\n" + DRAW + "\n" +
     "".join(f"\t\tg->DrawImageCel({im}, 0, 0, m0x15c);\n" for im in
         ["IMAGE_SMOKETINY","IMAGE_SMOKESMALL","IMAGE_SMOKEMISSILE","IMAGE_EXPLOSION"]) +
     "}\n" + SYNC + SYNC_BODY + "}\n")

class SmokePatchTests(unittest.TestCase):
    def test_simulation_and_serialized_calls_preserved(self):
        h,s=patch(H,S)
        self.assertIn(UPDATE_BODY,s)
        self.assertIn(SYNC_BODY,s)
        self.assertEqual(s.count("theSync->SyncLong("),5)
        self.assertIn("SmokeAnimationHistory mM2SmokeAnimation",h)
        self.assertIn("mM2SmokeAnimation.valid = false;",s[s.index(SYNC):])
        self.assertEqual(s.count("DrawSmokeFrames"),2)
        for im in ["IMAGE_SMOKEMISSILE","IMAGE_EXPLOSION"]:
            self.assertIn(f"g->DrawImageCel({im}, 0, 0, m0x15c);",s)
        self.assertIn("g->GetDrawMode() == Graphics::DRAWMODE_NORMAL",s)
        self.assertIn("gEnhancedM2Enabled && EnhancedM2::SmokeAnimationEnabled()",s)
    def test_pause_reset_before_drawing(self):
        _,s=patch(H,S)
        self.assertLess(s.index("if (m2SmokePaused"),s.index("DrawSmokeFrames"))
        self.assertIn("!mApp->mBoard || mApp->mBoard->mPause",s)
    def test_changed_missing_duplicate_anchors_fail_closed(self):
        for anchor in [UPDATE,DRAW,SYNC,"IMAGE_SMOKETINY","IMAGE_SMOKESMALL"]:
            with self.subTest(anchor=anchor):
                with self.assertRaises(RuntimeError): patch(H,S.replace(anchor,"changed"))
        with self.assertRaises(RuntimeError): patch(H,S+SYNC)
        with self.assertRaises(RuntimeError): patch(*patch(H,S))
        with self.assertRaises(RuntimeError): patch(H+HEADER,S)

if __name__ == "__main__": unittest.main()
