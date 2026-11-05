import pathlib
import re
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from apply_coin_animation import patch, HEADER, UPDATE, DRAW, SYNC

H = '#include "GameObject.h"\n' + HEADER
GUARD = '\tif (!mApp->mBoard || mApp->mBoard->mPause)\n\t\treturn;'
S = ('void PopLib::Coin::Update()\n{\n' + GUARD + '\n' + UPDATE +
     '\n\tmAnimationTimer++;\n\tUpdateCounters();\n\tRemove();\n}\n' + DRAW + '\n' +
     ''.join(f'\t\tg->DrawImageCel(aCoinImg, aX, aY, mAnimationFrame, {r});\n' for r in (0,1)) +
     SYNC + '\n\ttheSync->SyncLong(mAnimationFrame);\n}')
R = '#include "resourcemanager.hpp"\n\tif (aSDLImage->mPurgeBits)\n\t\taSDLImage->PurgeBits();'


def strip_blocks(source):
    def original(match):
        row = re.search(r'aX, aY, ([01]), result\);', match[0])
        return (f'\t\tg->DrawImageCel(aCoinImg, aX, aY, mAnimationFrame, {row[1]});\n'
                if row else '')
    return re.sub(r'\t// M2 coin animation begin\n.*?\t// M2 coin animation end\n', original, source, flags=re.S)


class CoinAnimationPatchTests(unittest.TestCase):
    def test_only_presentation_added(self):
        h, s, r = patch(H, S, R)
        normalize = lambda x: [line for line in x.splitlines() if line.strip()]
        self.assertEqual(normalize(strip_blocks(s)), normalize(S))
        self.assertEqual(normalize(strip_blocks(r).replace('#include "graphics/M2CoinBlendPolicy.hpp"\n','')), normalize(R))
        self.assertEqual(s.count('SyncLong('), 1)
        self.assertIn('CoinAnimation<PopLib::MemoryImage>', h)
        self.assertLess(s.index('mM2CoinAnimation.Capture'), s.index('mAnimationTimer++'))
        self.assertIn('state.Eligible() ?', s)
        self.assertIn('theRes->mId == "IMAGE_MONEY"', r)
        self.assertIn('EnhancedM2::CoinBlendEnabled()', r)
        self.assertLess(r.index('mPurgeBits = false'), r.index('aSDLImage->PurgeBits()'))

    def test_fail_closed(self):
        for index, anchors in enumerate(((HEADER, '#include "GameObject.h"'),
                                         (UPDATE, DRAW, SYNC, GUARD, 'mAnimationFrame, 0);'),
                                         ('#include "resourcemanager.hpp"', '\tif (aSDLImage->mPurgeBits)'))):
            for anchor in anchors:
                args = [H,S,R]
                args[index] = args[index].replace(anchor, 'changed')
                with self.assertRaises(RuntimeError): patch(*args)
        with self.assertRaises(RuntimeError): patch(*patch(H,S,R))
        with self.assertRaises(RuntimeError): patch(H,S+SYNC,R)


if __name__ == '__main__': unittest.main()
