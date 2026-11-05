import csv
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from coin_blend_audit import HEADER, audit_coin_blend

class CoinBlendAuditTests(unittest.TestCase):
    def audit(self, rows, header=HEADER):
        with tempfile.TemporaryDirectory() as tmp:
            folder=pathlib.Path(tmp)
            with (folder/'M2DebugCoinBlend.csv').open('w',newline='') as f:
                writer=csv.writer(f); writer.writerow(header); writer.writerows(rows)
            return audit_coin_blend(folder)
    def row(self, **changes):
        row=dict(zip(HEADER, [0,1,'0x123',1,4,2,1,2,0.5,'composed']))
        row.update(changes)
        return [row[k] for k in HEADER]
    def test_counts_and_evidence_limit(self):
        detail,notes=self.audit([self.row(), self.row(frame=1,fromCel=2,mix=1,result='pixels')])
        self.assertIn('composed=1', '\n'.join(detail))
        self.assertIn('pixels=1', '\n'.join(detail))
        self.assertIn('unverified', '\n'.join(detail))
        self.assertFalse(notes)
    def test_invalid_results(self):
        for changed in ({'mix':'nan'},{'mix':0},{'fromCel':9},{'toCel':3},{'result':'unknown'},
                        {'lifetimeId':0},{'timer':80},{'frame':-1},{'objectId':''},
                        {'result':'pixels'},{'result':'endpoint'}):
            with self.subTest(changed=changed):
                _,notes=self.audit([self.row(**changed)])
                self.assertTrue(any(n.startswith('ERROR:') for n in notes))
    def test_order_and_frame_budget(self):
        for rows in ([self.row(frame=2),self.row(frame=1)],
                     [self.row(),self.row(gameTick=2)], [self.row()]*65):
            _,notes=self.audit(rows)
            self.assertTrue(any(n.startswith('ERROR:') for n in notes))
    def test_missing_empty_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,notes=audit_coin_blend(pathlib.Path(tmp))
            self.assertIn('absent',notes[0])
        _,notes=self.audit([])
        self.assertIn('No composed',notes[0])
        _,notes=self.audit([],['bad'])
        self.assertTrue(notes[0].startswith('ERROR:'))
    def test_fallback_and_endpoints(self):
        for reason in ('disabled','state','graphics','history','sequence','held','layout',
                       'nonresident','identity','pixels','allocation'):
            _,notes=self.audit([self.row(fromCel=2,mix=1,result=reason)])
            self.assertFalse(any(n.startswith('ERROR:') for n in notes))
        for mix in (0,1):
            _,notes=self.audit([self.row(result='endpoint',mix=mix)])
            self.assertFalse(any(n.startswith('ERROR:') for n in notes))

if __name__=='__main__': unittest.main()
