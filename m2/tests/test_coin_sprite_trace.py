import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_coin_sprite_trace import patch
from coin_sprite_audit import FIELDS, FIELDS_V2, audit_coin_sprites

HEADER = '\t\tCoin();'
SOURCE = ('#include "Coin.h"\nPopLib::Coin::Coin()\n{}\n'
          'PopLib::Coin::Coin(int theX, int theY, int theType, OtherTypePet* unk, double theVel)\n{}\n'
          'void PopLib::Coin::Sync(DataSync* theSync)\n{\n\ttheSync->SyncLong(mAnimationFrame);\n}\n'
          'void PopLib::Coin::Draw(Graphics* g)\n{\n'
          '\t\tg->DrawImageCel(aCoinImg, aX, aY, mAnimationFrame, 0);\n'
          '\t\tg->DrawImageCel(aCoinImg, aX, aY, mAnimationFrame, 1);\n}\n')

class PatchTests(unittest.TestCase):
    def test_preserves_draws_and_serialized_fields(self):
        h,s=patch(HEADER,SOURCE)
        self.assertEqual(s.count('NewCoinLifetime()'),3)
        self.assertEqual(s.count('RecordCoinSprite('),2)
        self.assertIn('if (theSync->mReader)',s)
        self.assertEqual([l for l in s.splitlines() if '->DrawImage' in l],
                         [l for l in SOURCE.splitlines() if '->DrawImage' in l])
        self.assertEqual([l for l in s.splitlines() if '->Sync' in l],
                         [l for l in SOURCE.splitlines() if '->Sync' in l])
        with self.assertRaises(RuntimeError): patch(h,s)

    def test_missing_and_duplicate_anchors_rejected(self):
        for broken in (SOURCE.replace('mAnimationFrame, 1','mAnimationFrame, 2'),
                       SOURCE+'\nPopLib::Coin::Coin()\n{}'):
            with self.assertRaises(RuntimeError): patch(HEADER,broken)

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.row=dict.fromkeys(FIELDS,'0')
        self.row.update(objectId='0x1',imageId='0x2',lifetimeId='1',coinType='1',
                        resource='IMAGE_MONEY',imageWidth='720',imageHeight='360',
                        sheetCols='10',sheetRows='5',scaleX='1',scaleY='1',
                        red='255',green='255',blue='255',alpha='255')

    def write(self,rows,fields=FIELDS):
        with (self.folder/'M2DebugCoinSprites.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

    def test_missing_and_empty_are_not_proof(self):
        self.assertIn('absent',audit_coin_sprites(self.folder)[1][0])
        self.write([])
        self.assertIn('empty',audit_coin_sprites(self.folder)[1][0])

    def test_resolved_money_shell_and_lifetime_reuse(self):
        shell=dict(self.row,frame='1',lifetimeId='2',coinType='9',shellMode='1',
                   resource='IMAGE_SHELLS',celRow='1',paused='1',collected='1',disappearTimer='2')
        self.write([self.row,shell])
        report,notes=audit_coin_sprites(self.folder)
        self.assertFalse(notes)
        self.assertIn('2 valid','\n'.join(report))
        self.assertIn('unknown image generation','\n'.join(report))

    def test_invalid_requests(self):
        for changes in ({'celColumn':'10'}, {'lifetimeId':'0'}, {'translationX':'nan'},
                        {'resource':'IMAGE_PEARL'}, {'coinType':'7'}, {'alpha':'256'},
                        {'paused':'2'}, {'celRow':'1'}, {'sheetCols':'0'}):
            with self.subTest(changes=changes):
                self.write([dict(self.row,**changes)])
                self.assertTrue(audit_coin_sprites(self.folder)[1][0].startswith('ERROR:'))

    def test_truncation_and_order_regression(self):
        self.write([dict(self.row,frame='2'),self.row])
        self.assertIn('1 ordering regressions','\n'.join(audit_coin_sprites(self.folder)[0]))
        self.write([self.row])
        with (self.folder/'M2DebugCoinSprites.csv').open('a') as f: f.write('3,2,0x1\n')
        self.assertIn('1 invalid','\n'.join(audit_coin_sprites(self.folder)[0]))

    def test_header_rejected(self):
        self.write([],['frame','gameTick'])
        self.assertIn('unsupported header',audit_coin_sprites(self.folder)[1][0])

    def test_v2_stamps_and_legacy_unknowns(self):
        self.write([self.row])
        self.assertIn('v1 (not recorded)', '\n'.join(audit_coin_sprites(self.folder)[0]))
        modern = dict(self.row, imageLifetimeId='10', reportedPixelRevision='1')
        self.write([modern], FIELDS_V2)
        report, notes = audit_coin_sprites(self.folder)
        self.assertFalse(notes)
        self.assertIn('v2; unknown image lifetimes 0, unknown reported pixel revisions 0', '\n'.join(report))

    def test_v2_invalid_stamps(self):
        for field in ('imageLifetimeId', 'reportedPixelRevision'):
            for value in ('-1', str(2**64), 'nan', ''):
                modern = dict(self.row, imageLifetimeId='10', reportedPixelRevision='1')
                modern[field] = value
                self.write([modern], FIELDS_V2)
                self.assertIn('1 invalid', '\n'.join(audit_coin_sprites(self.folder)[0]))

    def test_v2_exhausted_stamps_remain_unknown(self):
        self.write([dict(self.row, imageLifetimeId='0', reportedPixelRevision='0')], FIELDS_V2)
        report, notes = audit_coin_sprites(self.folder)
        self.assertFalse(notes)
        self.assertIn('unknown image lifetimes 1, unknown reported pixel revisions 1', '\n'.join(report))

    def test_partial_v2_header_rejected(self):
        self.write([], FIELDS + ['imageLifetimeId'])
        self.assertIn('unsupported header', audit_coin_sprites(self.folder)[1][0])

if __name__=='__main__': unittest.main()
