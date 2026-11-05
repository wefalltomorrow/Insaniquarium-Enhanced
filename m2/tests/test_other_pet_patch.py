"""M2 OtherTypePet patch must only add tick history and scoped sprite shifts."""
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from apply_other_pet import patch_header, patch_source

BASE_H = "\tclass OtherTypePet : public GameObject\n\t{\n\tpublic:\n\t\tdouble mXD;\n"
BASE_CPP = (
    '#include "OtherTypePet.h"\n'
    'void PopLib::OtherTypePet::Update()\n'
    '{\n\tM2Debug::Get().Updated(M2Debug::OtherPet);\n'
    '\tif (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n'
    '\t\treturn;\n\n\tUpdateCounters();\n'
    '}\n'
    'void PopLib::OtherTypePet::Draw(Graphics* g)\n'
    '{\n'
    '\tM2Debug::DrawGuard m2Probe(M2Debug::OtherPet, this, mXD, mYD, mAnimationIndex);\n'
    '\tUpdateFishSongMgr();\n'
    '\tDrawHelper(g, false);\n'
    '}\n'
)

class OtherPetPatchTests(unittest.TestCase):
    def test_visual_only_patch(self):
        h=patch_header(BASE_H)
        self.assertIn("mM2PrevXD = 0.0", h)
        self.assertIn("mM2HavePrev = false", h)
        s=patch_source(BASE_CPP)
        self.assertIn("mM2PrevXD = mXD;", s)
        self.assertIn("mM2PrevYD = mYD;", s)
        self.assertIn("mM2HavePrev = true;", s)
        self.assertIn("mM2HavePrev = false;", s)
        self.assertIn("ScopedObjectTranslation<Graphics> m2VisualShift", s)
        self.assertIn("ObjectMotion(M2Debug::OtherPet", s)
        self.assertEqual(s.count("UpdateFishSongMgr();"), 2)
        self.assertIn("if (!gEnhancedM2Enabled)\n\t\tUpdateFishSongMgr();", s)
        self.assertIn("if (mApp->mBoard == nullptr || mApp->mBoard->mPause)\n\t\treturn;", s)
        self.assertIn("\tUpdateCounters();", s)
        self.assertIn("\tDrawHelper(g, false);", s)
        self.assertNotIn("mXD =", s[s.index("void PopLib::OtherTypePet::Draw"):])
        self.assertNotIn("mX =", s[s.index("void PopLib::OtherTypePet::Draw"):])
        self.assertNotIn("->Sync", s)

    def test_bad_source_rejected(self):
        with self.assertRaises(RuntimeError):
            patch_header("no class")
        with self.assertRaises(RuntimeError):
            patch_source("void OtherTypePet::Draw() {}")
        with self.assertRaises(RuntimeError):
            patch_source(BASE_CPP + BASE_CPP)

    def test_double_patching_rejected(self):
        with self.assertRaises(RuntimeError):
            patch_source(patch_source(BASE_CPP))
        with self.assertRaises(RuntimeError):
            patch_header(patch_header(BASE_H))

if __name__ == "__main__":
    unittest.main()
