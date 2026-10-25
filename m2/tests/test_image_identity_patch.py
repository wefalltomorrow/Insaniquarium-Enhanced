from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_image_identity import patch

HEADER = '#include "common.hpp"\nclass Image {\npublic:\n\tbool mDrawn;\n};\n'
SOURCE = 'void MemoryImage::BitsChanged()\n{\n\tmBitsChanged = true;\n\tmBitsChangedCount++;\n}\n'


class ImagePatchTests(unittest.TestCase):
    def test_original_pixel_operations_preserved(self):
        header, source = patch(HEADER, SOURCE)
        self.assertIn('EnhancedM2::ImageIdentity mM2ImageIdentity;', header)
        self.assertEqual(source.replace('\n\tmM2ImageIdentity.BitsChanged();', ''), SOURCE)
        with self.assertRaises(RuntimeError):
            patch(header, source)

    def test_anchor_drift_and_duplicate_fail_closed(self):
        for header, source in ((HEADER.replace('mDrawn', 'changed'), SOURCE),
                               (HEADER, SOURCE + SOURCE), (HEADER, SOURCE.replace('BitsChanged()', 'Other()'))):
            with self.subTest(header=header, source=source):
                with self.assertRaises(RuntimeError):
                    patch(header, source)


if __name__ == '__main__':
    unittest.main()
