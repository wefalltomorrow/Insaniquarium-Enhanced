#!/usr/bin/env python3
"""Observe image lifetime and explicit mutations without changing pixel operations."""
from pathlib import Path
import sys
from apply_shot_interpolation import replace_once

ROOT = Path(__file__).resolve().parent.parent
GRAPHICS = ROOT / 'upstream/poplib/PopLib/graphics'


def patch(header, source):
    if 'mM2ImageIdentity' in header or 'mM2ImageIdentity' in source:
        raise RuntimeError('Image identity patch is already applied')
    header = replace_once(header, '#include "common.hpp"',
                         '#include "common.hpp"\n#include "M2ImageIdentity.hpp"', 'image identity include')
    header = replace_once(header, '\tbool mDrawn;',
                         '\t// Presentation diagnostics only; not serialized.\n'
                         '\tEnhancedM2::ImageIdentity mM2ImageIdentity;\n\tbool mDrawn;', 'image identity field')
    anchor = 'void MemoryImage::BitsChanged()\n{'
    source = replace_once(source, anchor, anchor + '\n\tmM2ImageIdentity.BitsChanged();',
                          'reported image mutation')
    return header, source


def main():
    header, source = patch((GRAPHICS / 'image.hpp').read_text(encoding='utf-8-sig'),
                           (GRAPHICS / 'memoryimage.cpp').read_text(encoding='utf-8-sig'))
    helper = (ROOT / 'm2/ImageIdentity.hpp').read_text(encoding='utf-8')
    for path, content in ((GRAPHICS / 'image.hpp', header),
                          (GRAPHICS / 'memoryimage.cpp', source),
                          (GRAPHICS / 'M2ImageIdentity.hpp', helper)):
        path.write_text(content, encoding='utf-8', newline='\n')
    print('[ok] Image lifetime and reported mutation stamps; pixel operations unchanged')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(f'[FAILED] {exc}', file=sys.stderr)
        sys.exit(1)
