import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from smoke_animation_audit import audit_smoke_animation

HEADER="frame,gameTick,objectId,shotType,simulationAge,simulationCel,fromCel,toCel,mix,transition,paused\n"
class SmokeAuditTests(unittest.TestCase):
    def audit(self,text):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)
            (path/"M2DebugSmokeAnimation.csv").write_text(text)
            return audit_smoke_animation(path)
    def test_fractional_same_tick_coverage(self):
        lines,notes=self.audit(HEADER+"10,6,A,6,4,1,0,1,0.25,1,0\n11,6,A,6,4,1,0,1,0.75,1,0\n")
        self.assertIn("2 fractional blends; 1 same-tick",lines[0])
        self.assertFalse(any(n.startswith("ERROR:") for n in notes))
    def test_invalid_paused_transition_and_truncated_row(self):
        _,notes=self.audit(HEADER+"10,6,A,6,4,1,0,1,0.5,1,1\n11,6,A,6,4\n")
        self.assertTrue(any("1 invalid transitions and 1 malformed" in n for n in notes))
    def test_baseline_and_absent_trace_are_not_success_claims(self):
        _,notes=self.audit(HEADER+"10,6,A,6,4,1,1,1,1,0,0\n")
        self.assertTrue(any("No fractional" in n for n in notes))
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(audit_smoke_animation(pathlib.Path(d)),([],[]))
    def test_nonfinite_and_wrong_header(self):
        _,notes=self.audit(HEADER+"10,6,A,6,4,1,0,1,nan,1,0\n")
        self.assertTrue(any("1 malformed" in n for n in notes))
        self.assertTrue(self.audit("unexpected\n")[1][0].startswith("ERROR:"))
