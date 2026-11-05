"""Fail-closed source-shape tests for the M2-only updater channel override."""
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from apply_updater_channel import patch, START, END

HEADER = '#pragma once\n#define ENHANCED_VERSION_TAG "v0.3.0-m2-timing-test"\n'
SOURCE = ('#include "EnhancedUpdaterVersion.h"\n'
          'struct CheckResult { bool success; };\n'
          + START + '    Version best{};\n}\n'
          + END + '\n')

class M2UpdaterTests(unittest.TestCase):
    def test_switch_to_actual_published_m2_tag(self):
        src, version = patch(SOURCE, HEADER, "m2-updater-fix-20261013")
        self.assertIn('#define ENHANCED_VERSION_TAG "m2-updater-fix-20261013"', version)
        self.assertIn('#include "M2ReleaseSelector.hpp"', src)
        self.assertIn('M2ReleaseSelector::Latest(releases, kAssetPrefix, kCurrentVersion)', src)
        self.assertNotIn('Version best{};', src)
        self.assertIn('result.newer = latest.newer;', src)

    def test_invalid_tags_or_changed_updater_fail_closed(self):
        for tag in ("v0.3.0", "m2-invalid", "m2-evil/thing-20261013",
                    "m2-any-2026-10-13"):
            with self.assertRaises(RuntimeError):
                patch(SOURCE, HEADER, tag)
        with self.assertRaises(RuntimeError):
            patch(SOURCE.replace('Version best{};', 'Unsupported new parser;'),
                  HEADER, "m2-updater-fix-20261013")
        with self.assertRaises(RuntimeError):
            patch(SOURCE + SOURCE, HEADER, "m2-updater-fix-20261013")
        with self.assertRaises(RuntimeError):
            patch(SOURCE, HEADER.replace("v0.3.0-m2-timing-test", "bad"),
                  "m2-updater-fix-20261013")
        src, version = patch(SOURCE, HEADER, "m2-updater-fix-20261013")
        with self.assertRaises(RuntimeError):
            patch(src, version, "m2-updater-fix-20261013")

if __name__ == "__main__":
    unittest.main()
