#!/usr/bin/env python3
"""Optional ordinary silver/gold presentation, after identity and coin trace patches."""
from pathlib import Path
import sys
from apply_shot_interpolation import replace_once

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / 'upstream/port/winfish'
RESOURCES = ROOT / 'upstream/poplib/PopLib/resources'
HEADER = '\t\tbool mM2HavePrev = false;'
UPDATE = '\t// No sound/game callbacks from 60Hz presentation redraws.'
DRAW = '\tM2Debug::DrawGuard m2DrawGuard(M2Debug::Coin, this, mXD, mYD, mAnimationFrame);'
SYNC = 'void PopLib::Coin::Sync(DataSync* theSync)\n{'
STATE = ('{mCoinType, mAnimationTimer, mAnimationFrame,\n'
         '\t\t\t(mApp->mBoard && mApp->mBoard->mPetsInTank[10] != 0) ? 4 : 2,\n'
         '\t\t\tstatic_cast<int>(mApp->mGameMode),\n'
         '\t\t\t!mApp->mBoard || IsShell(), m0x198, mDisappearTimer}')


def marked(body):
    return '\t// M2 coin animation begin\n' + body + '\n\t// M2 coin animation end\n'


def patch(header, source, resources):
    if 'mM2CoinAnimation' in header or 'mM2CoinAnimation' in source or 'M2CoinBlendPolicy' in resources:
        raise RuntimeError('Coin animation already applied')
    header = replace_once(header, '#include "GameObject.h"',
        '#include "GameObject.h"\n#include "M2CoinAnimation.hpp"\n'
        '#include "M2CoinBlendPolicy.hpp"\n#include "PopLib/graphics/memoryimage.hpp"', 'Coin includes')
    header = replace_once(header, HEADER, HEADER +
        '\n\t\tEnhancedM2::CoinAnimation<PopLib::MemoryImage> mM2CoinAnimation;', 'Coin history')
    guard = '\tif (!mApp->mBoard || mApp->mBoard->mPause)\n\t\treturn;'
    source = replace_once(source, guard, marked(
        '\tif (!mApp->mBoard || mApp->mBoard->mPause) mM2CoinAnimation.Reset("state");') + guard, 'pause reset')
    source = replace_once(source, UPDATE, marked(
        '\tif (gEnhancedM2Enabled && EnhancedM2::CoinBlendEnabled()) {\n'
        f'\t\tconst EnhancedM2::CoinAnimationState state{STATE};\n'
        '\t\tmM2CoinAnimation.Capture(true, state, state.Eligible() ?\n'
        '\t\t\tdynamic_cast<MemoryImage*>(IMAGE_MONEY) : nullptr);\n'
        '\t} else mM2CoinAnimation.Reset("disabled");') + UPDATE, 'pre-update capture')
    source = replace_once(source, DRAW, DRAW + '\n' + marked(
        '\tif (!mApp->mBoard || mApp->mBoard->mPause || !gEnhancedM2Enabled)\n'
        '\t\tmM2CoinAnimation.Reset("state");'), 'draw pause reset')
    source = replace_once(source, SYNC, SYNC + '\n' + marked(
        '\tmM2CoinAnimation.Reset();'), 'save/load reset')
    for row in (0, 1):
        old = f'\t\tg->DrawImageCel(aCoinImg, aX, aY, mAnimationFrame, {row});'
        body = f'''\t\tconst EnhancedM2::CoinAnimationState state{STATE};
\t\tEnhancedM2::CoinBlendResult result{{mAnimationFrame, mAnimationFrame}};
\t\tauto* composed = mM2CoinAnimation.Prepare(
\t\t\tgEnhancedM2Enabled && EnhancedM2::CoinBlendEnabled(),
\t\t\t!mApp->mBoard || mApp->mBoard->mPause,
\t\t\tg->GetDrawMode() == Graphics::DRAWMODE_NORMAL && !g->GetColorizeImages() &&
\t\t\tg->mScaleX == 1.0 && g->mScaleY == 1.0,
\t\t\tstate, dynamic_cast<MemoryImage*>(aCoinImg), gEnhancedM2Blend, result);
\t\tM2Debug::Get().CoinBlend(this, mM2CoinLifetime, mAnimationTimer, mAnimationFrame,
\t\t\tresult.from, result.to, result.mix, result.reason);
\t\tEnhancedM2::DrawCoinFrame(g, aCoinImg, static_cast<Image*>(composed), aX, aY, {row}, result);'''
        source = replace_once(source, old, marked(body), f'coin row {row}')
    resources = replace_once(resources, '#include "resourcemanager.hpp"',
        '#include "resourcemanager.hpp"\n#include "graphics/M2CoinBlendPolicy.hpp"', 'resource include')
    # Keep only this opt-in asset's existing CPU pixels, before any purge.
    # Never reconstruct pixels from a static texture or mutate their contents.
    anchor = '\tif (aSDLImage->mPurgeBits)\n\t\taSDLImage->PurgeBits();'
    resources = replace_once(resources, anchor, marked(
        '\tif (EnhancedM2::CoinBlendEnabled() && theRes->mId == "IMAGE_MONEY")\n'
        '\t\taSDLImage->mPurgeBits = false;') + anchor, 'money pixel retention')
    return header, source, resources


def main():
    paths = [GAME / 'Coin.h', GAME / 'Coin.cpp', RESOURCES / 'resourcemanager.cpp']
    patched = patch(*(p.read_text(encoding='utf-8-sig') for p in paths))
    outputs = list(zip(paths, patched))
    helper = (ROOT / 'm2/CoinAnimation.hpp').read_text().replace('"SmokePixels.hpp"', '"M2SmokePixels.hpp"')
    policy = (ROOT / 'm2/CoinBlendPolicy.hpp').read_text()
    outputs += [(GAME / 'M2CoinAnimation.hpp', helper), (GAME / 'M2CoinBlendPolicy.hpp', policy),
                (RESOURCES.parent / 'graphics/M2CoinBlendPolicy.hpp', policy)]
    for path, text in outputs:
        path.write_text(text, encoding='utf-8', newline='\n')
    print('[ok] Opt-in ordinary coin composition; original simulation and saved fields preserved')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f'[FAILED] {exc}', file=sys.stderr)
        sys.exit(1)
