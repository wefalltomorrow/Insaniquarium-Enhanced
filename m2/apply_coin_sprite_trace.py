#!/usr/bin/env python3
"""Record resolved silver/gold body requests without modifying their draws."""
from pathlib import Path
import sys
from apply_shot_interpolation import replace_once

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / 'upstream/port/winfish'

def patch(header, source):
    if 'mM2CoinLifetime' in header or 'RecordCoinSprite' in source:
        raise RuntimeError('Coin sprite trace is already applied')
    header = replace_once(header, '\t\tCoin();',
        '\t\t// Debug identity only; never serialized.\n'
        '\t\tunsigned long long mM2CoinLifetime = 0;\n\n\t\tCoin();', 'coin lifetime field')
    source = replace_once(source, '#include "Coin.h"',
        '#include "Coin.h"\n#include "DataSync.h"\n#include "M2CoinSpriteTrace.hpp"', 'trace include')
    for signature in ('PopLib::Coin::Coin()',
                      'PopLib::Coin::Coin(int theX, int theY, int theType, OtherTypePet* unk, double theVel)'):
        anchor = signature + '\n{'
        source = replace_once(source, anchor, anchor +
            '\n\tmM2CoinLifetime = M2Debug::Get().NewCoinLifetime();', 'constructor identity')
    anchor = 'void PopLib::Coin::Sync(DataSync* theSync)\n{'
    source = replace_once(source, anchor, anchor +
        '\n\tif (theSync->mReader)\n\t\tmM2CoinLifetime = M2Debug::Get().NewCoinLifetime();', 'load identity')
    for row in (0, 1):
        anchor = f'\t\tg->DrawImageCel(aCoinImg, aX, aY, mAnimationFrame, {row});'
        probe = ('\t\tM2Debug::RecordCoinSprite(M2Debug::Get(), g, aCoinImg, this, mM2CoinLifetime,\n'
                 f'\t\t\tmCoinType, isShell, mAnimationFrame, {row}, aX, aY,\n'
                 '\t\t\tmApp->mBoard && mApp->mBoard->mPause, m0x198, mDisappearTimer);\n')
        source = replace_once(source, anchor, probe + anchor, f'coin row {row} resolved request')
    return header, source

def main():
    h, s = patch((GAME/'Coin.h').read_text(encoding='utf-8-sig'),
                 (GAME/'Coin.cpp').read_text(encoding='utf-8-sig'))
    helper = (ROOT/'m2/CoinSpriteTrace.hpp').read_text(encoding='utf-8').replace(
        '"DebugTrace.hpp"', '"M2DebugTrace.hpp"')
    for path, value in ((GAME/'Coin.h', h), (GAME/'Coin.cpp', s),
                        (GAME/'M2CoinSpriteTrace.hpp', helper)):
        path.write_text(value, encoding='utf-8', newline='\n')
    print('[ok] Resolved silver/gold coin requests; simulation and save fields unchanged')

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f'[FAILED] {exc}', file=sys.stderr)
        sys.exit(1)
