import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1] / "enable_compiler_cache.py"
spec = importlib.util.spec_from_file_location("enable_compiler_cache", file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CachePatchTests(unittest.TestCase):
    def test_preserves_linker_debugging(self):
        result = mod.patch_source("start\n" + mod.OLD + "\nfinish\n")
        self.assertIn("PRIVATE /Z7)", result)
        self.assertIn("PRIVATE /DEBUG /OPT:REF /OPT:ICF)", result)
        self.assertNotIn("PRIVATE /Zi)", result)
    def test_unknown_upstream_version_fails(self):
        with self.assertRaises(RuntimeError):
            mod.patch_source("changed upstream")
    def test_duplicate_anchor_fails(self):
        with self.assertRaises(RuntimeError):
            mod.patch_source(mod.OLD + mod.OLD)

if __name__ == "__main__":
    unittest.main()
