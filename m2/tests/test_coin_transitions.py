"""Synthetic observations only; these tests do not establish visual behavior."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coin_sprite_audit import CoinTransitions, FIELDS, audit_coin_sprites


def row(frame=0, tick=0, lifetime=1, **changes):
    result = dict.fromkeys(FIELDS, 0)
    result.update(frame=frame, gameTick=tick, lifetimeId=lifetime,
                  objectId=f'0x{lifetime:x}', imageId='0x100', coinType=1,
                  resource='IMAGE_MONEY', imageWidth=720, imageHeight=360,
                  sheetCols=10, sheetRows=5, scaleX=1, scaleY=1,
                  red=255, green=255, blue=255, alpha=255)
    result.update(changes)
    return result


def audit(rows):
    result = CoinTransitions()
    for request in rows:
        result.observe(request)
    report, notes = result.finish()
    return result.counts, report, notes


class TransitionTests(unittest.TestCase):
    def test_interleaved_lifetimes_and_last_frame(self):
        counts, _, notes = audit([row(), row(lifetime=2),
                                  row(1, 1, 2, celColumn=1), row(1, 1)])
        self.assertFalse(notes)
        self.assertEqual(counts['pairs'], 2)
        self.assertEqual(counts['cel_1_same'], 1)
        self.assertEqual(counts['cel_1_plus_one'], 1)

    def test_same_tick_and_numeric_wrap_not_inferred(self):
        counts, report, _ = audit([row(celColumn=9), row(1, celColumn=0),
                                   row(2, 1, celColumn=1)])
        self.assertEqual(counts['cel_0_other'], 1)
        self.assertEqual(counts['cel_1_plus_one'], 1)
        self.assertIn('not verified animation advances or wraps', '\n'.join(report))

    def test_pointer_reuse_with_fresh_lifetime_is_unpaired(self):
        counts, _, notes = audit([row(), row(1, 1, 2, objectId='0x1')])
        self.assertFalse(notes)
        self.assertEqual(counts['pairs'], 0)
        self.assertEqual(counts['unpaired_requests'], 2)

    def test_same_lifetime_changed_owner_rejected(self):
        counts, _, notes = audit([row(), row(1, 1, objectId='0x2')])
        self.assertEqual(counts['owner_mismatches'], 1)
        self.assertEqual(counts['pairs'], 0)
        self.assertTrue(notes[0].startswith('ERROR:'))

    def test_absent_owner_and_frame_gap_do_not_bridge(self):
        counts, _, _ = audit([row(), row(1, lifetime=2), row(2), row(4)])
        self.assertEqual(counts['pairs'], 0)
        self.assertEqual(counts['frame_gaps'], 1)

    def test_scheduler_tick_gap_does_not_infer_advance(self):
        counts, _, _ = audit([row(), row(1, 2, celColumn=1)])
        self.assertEqual(counts['pairs'], 0)
        self.assertEqual(counts['tick_gaps'], 1)

    def test_duplicate_at_end_excludes_entire_owner_frame(self):
        counts, _, notes = audit([row(), row(1), row(1), row(2)])
        self.assertEqual(counts['pairs'], 0)
        self.assertEqual(counts['ambiguous_requests'], 2)
        self.assertTrue(notes[0].startswith('WARN:'))
        self.assertFalse(any(note.startswith('ERROR:') for note in notes))

    def test_owner_alias_excludes_both_lifetimes_but_keeps_other_owners(self):
        counts, _, _ = audit([row(), row(lifetime=3), row(1),
                              row(1, lifetime=2, objectId='0x1'), row(1, lifetime=3)])
        self.assertEqual(counts['ambiguous_requests'], 2)
        self.assertEqual(counts['pairs'], 1)

    def test_each_sheet_change_excludes_cel_comparison(self):
        for field, value in {'coinType': 2, 'shellMode': 1, 'imageId': '0x200',
                             'resource': 'IMAGE_SHELLS', 'resourceGeneration': 1,
                             'celRow': 1, 'imageWidth': 800, 'imageHeight': 400,
                             'sheetCols': 20, 'sheetRows': 6}.items():
            with self.subTest(field=field):
                counts, _, _ = audit([row(), row(1, 1, celColumn=1, **{field: value})])
                self.assertEqual(counts['pairs'], 1)
                self.assertEqual(counts['sheet_changes'], 1)
                self.assertEqual(counts['cel_1_plus_one'], 0)

    def test_overlapping_state_changes_are_observations(self):
        counts, _, _ = audit([row(), row(1, 1, celColumn=1, translationX=1.5,
                              scaleX=2, clipWidth=500, alpha=100, paused=1,
                              collected=1, disappearTimer=2)])
        for group in ('position', 'transform', 'clip', 'appearance', 'owner_state'):
            self.assertEqual(counts[group + '_changes'], 1)
        self.assertEqual(counts['cel_1_plus_one'], 1)

    def test_generation_values_never_certify_continuity(self):
        for generation in (0, 1):
            counts, report, _ = audit([row(resourceGeneration=generation),
                                       row(1, resourceGeneration=generation)])
            self.assertEqual(counts['unknown_generation_pairs'], int(generation == 0))
            self.assertIn('Resource continuity is unverified for every pair', '\n'.join(report))

    def test_oversized_frame_discards_all_pairs_and_bounds_memory(self):
        tracker = CoinTransitions()
        tracker.observe(row())
        for lifetime in range(1, 10001):
            tracker.observe(row(1, lifetime=lifetime))
            self.assertLessEqual(len(tracker.rows) + len(tracker.previous), 128)
        tracker.observe(row(2))
        _, notes = tracker.finish()
        self.assertEqual(tracker.counts['pairs'], 0)
        self.assertEqual(tracker.counts['oversized_frames'], 1)
        self.assertTrue(notes)

    def test_inconsistent_tick_in_frame_excluded(self):
        counts, _, notes = audit([row(), row(1), row(1, 1, 2), row(2, 1)])
        self.assertEqual(counts['pairs'], 0)
        self.assertEqual(counts['inconsistent_frames'], 1)
        self.assertTrue(notes)

    def test_finish_is_idempotent(self):
        tracker = CoinTransitions()
        tracker.observe(row())
        tracker.observe(row(1))
        self.assertEqual(tracker.finish(), tracker.finish())
        self.assertEqual(tracker.counts['pairs'], 1)

    def test_image_address_reuse_is_detected_by_new_lifetime(self):
        counts, _, notes = audit([row(imageLifetimeId=10, reportedPixelRevision=1),
                                  row(1, 1, imageLifetimeId=11, reportedPixelRevision=1, celColumn=1)])
        self.assertFalse(notes)
        self.assertEqual(counts['image_identity_changes'], 1)
        self.assertEqual(counts['cel_1_plus_one'], 0)
        self.assertEqual(counts['unknown_image_lifetime_pairs'], 0)

    def test_reported_pixel_mutation_excludes_cel_pairing(self):
        counts, _, notes = audit([row(imageLifetimeId=10, reportedPixelRevision=1),
                                  row(1, 1, imageLifetimeId=10, reportedPixelRevision=2, celColumn=1)])
        self.assertFalse(notes)
        self.assertEqual(counts['reported_pixels_changes'], 1)
        self.assertEqual(counts['cel_1_plus_one'], 0)

    def test_conflicting_image_stamps_fail_closed(self):
        for changes in ({'imageId': '0x200'}, {'reportedPixelRevision': 1}):
            counts, _, notes = audit([row(imageLifetimeId=10, reportedPixelRevision=2),
                row(1, 1, imageLifetimeId=10, reportedPixelRevision=2) | changes])
            self.assertEqual(counts['pairs'], 0)
            self.assertEqual(counts['inconsistent_image_pairs'], 1)
            self.assertTrue(notes[0].startswith('ERROR:'))

    def test_invalid_and_regressed_csv_rows_break_history(self):
        for bad, expected_pairs in ((dict(row(), alpha='nan'), 1), (row(-1), 1),
                                    (row(0), 2)):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                with (folder / 'M2DebugCoinSprites.csv').open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, FIELDS)
                    writer.writeheader()
                    writer.writerows([row(1), bad, row(2), row(3), row(4)])
                report, notes = audit_coin_sprites(folder)
                text = '\n'.join(report)
                # Malformed rows quarantine the next observed frame; a parsed
                # regressed frame is itself quarantined, then tracking restarts.
                self.assertIn(f'{expected_pairs} pairs:', text)
                self.assertIn('invalid/order barriers 1', text)
                self.assertTrue(any(note.startswith('ERROR:') for note in notes))


if __name__ == '__main__':
    unittest.main()
