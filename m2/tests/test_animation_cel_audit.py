"""Counter evidence must not silently become inferred sprite-state evidence."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trace_integrity import inspect_animation_cels, audit_animation_cels
from analyze_logs import analyze


class AnimationCelAuditTests(unittest.TestCase):
    header = ["frame", "gameTick", "kind", "objectId", "animationCel"]

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.path = self.folder / "M2DebugObjects.csv"

    def scan(self, rows, **options):
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(self.header)
            writer.writerows(rows)
        return inspect_animation_cels(self.path, **options)

    def test_adjacent_tick_categories_include_reverse_and_unverified_wrap(self):
        stats, issues = self.scan([
            [0, 8, "coin", 1, 8], [1, 9, "coin", 1, 8],
            [2, 10, "coin", 1, 9], [3, 11, "coin", 1, 0],
            [4, 12, "coin", 1, 3], [5, 13, "coin", 1, 2]])
        coin = stats["coin"]
        self.assertEqual([coin[k] for k in ("adjacent_ticks", "unchanged",
                         "plus_one", "minus_one", "other_change")], [5, 1, 1, 1, 2])
        self.assertEqual(dict(issues), {"rows_read": 6})

    def test_same_tick_change_drops_history_and_duplicates_do_not_count(self):
        stats, _ = self.scan([
            [0, 1, "fish", 1, 0], [0, 1, "fish", 1, 0],
            [1, 1, "fish", 1, 0], [2, 1, "fish", 1, 1],
            [3, 2, "fish", 1, 2], [4, 3, "fish", 1, 3]])
        self.assertEqual([stats["fish"][k] for k in ("duplicate_samples",
            "same_tick_unchanged", "same_tick_changed", "baselines", "adjacent_ticks")], [1, 1, 1, 2, 1])

    def test_conflicting_draw_in_one_frame_is_not_a_transition(self):
        stats, _ = self.scan([[0, 1, "coin", 1, 0], [0, 2, "coin", 1, 1],
                             [1, 3, "coin", 1, 2]])
        self.assertEqual(stats["coin"]["same_frame_conflicts"], 1)
        self.assertEqual(stats["coin"]["adjacent_ticks"], 0)

    def test_missing_ticks_never_form_wrap_or_adjacent_pairs(self):
        stats, _ = self.scan([[0, 1, "coin", 1, 9], [7, 5, "coin", 1, 0],
                             [9, 6, "coin", 1, 1]])
        coin = stats["coin"]
        self.assertEqual([coin[k] for k in ("tick_gaps", "unobserved_ticks",
                         "adjacent_ticks", "plus_one", "nonconsecutive_frame_pairs")], [1, 3, 1, 1, 2])

    def test_regressions_clear_other_object_history_too(self):
        for reset in ([5, 5, "food", 7, 0], [11, 5, "food", 7, 0],
                      [5, 11, "food", 7, 0]):
            with self.subTest(reset=reset):
                stats, issues = self.scan([[10, 10, "fish", 1, 0], reset,
                                          [12, 11, "fish", 1, 1]])
                self.assertEqual(issues["order_resets"], 1)
                self.assertEqual(stats["fish"]["adjacent_ticks"], 0)

    def test_malformed_records_cannot_be_bridged(self):
        for bad in ([], [1, 1], [1, 1, "fish", 1, 1, "extra"],
                    [1, "NaN", "fish", 1, 0], [1, 1, "fish", "", 0],
                    [1, 1, "fish", 1, -1], [-1, 1, "fish", 1, 0]):
            with self.subTest(bad=bad):
                stats, issues = self.scan([[0, 1, "fish", 1, 0], bad,
                                          [2, 2, "fish", 1, 1]])
                self.assertEqual(issues["malformed_rows"], 1)
                self.assertEqual(stats["fish"]["adjacent_ticks"], 0)

    def test_kind_is_part_of_key_and_other_counters_are_excluded(self):
        stats, _ = self.scan([[0, 1, "fish", 1, 3], [1, 2, "fish_pet", 1, 4],
                             [2, 3, "shot_effect", 1, "not a cel"]])
        self.assertEqual(sum(s["adjacent_ticks"] for s in stats.values()), 0)
        self.assertEqual(sum(s["samples"] for s in stats.values()), 2)

    def test_lru_capacity_loss_starts_new_baseline(self):
        stats, issues = self.scan([[0, 1, "coin", 1, 0], [0, 1, "coin", 2, 0],
                                  [0, 1, "coin", 3, 0], [1, 2, "coin", 1, 1]],
                                 history_limit=2)
        self.assertEqual(issues["history_evictions"], 2)
        self.assertEqual(stats["coin"]["baselines"], 4)
        self.assertEqual(stats["coin"]["adjacent_ticks"], 0)
        with self.assertRaises(ValueError):
            inspect_animation_cels(self.path, history_limit=0)

    def test_pointer_reuse_without_a_gap_cannot_be_certified(self):
        # Two lifetimes could produce these same records; schema cannot tell.
        self.scan([[0, 1, "fish", 1, 2], [1, 2, "fish", 1, 3]])
        lines, notes = audit_animation_cels(self.folder)
        self.assertIn("1 +1", lines[0])
        self.assertTrue(any("Pointer IDs may be reused even on adjacent ticks" in n for n in notes))
        self.assertTrue(any("not verified wraps, state transitions or safe-to-blend pairs" in n for n in notes))

    def test_invalid_header_read_errors_and_empty_capture_are_explicit(self):
        for content in ("", "frame,gameTick,kind,objectId,animationCel,frame\n",
                        "frame,kind\n"):
            self.path.write_text(content, encoding="utf-8")
            self.assertEqual(inspect_animation_cels(self.path)[1]["incompatible_header"], 1)
        self.path.write_text(",".join(self.header) + '\n"unterminated', encoding="utf-8")
        self.assertEqual(inspect_animation_cels(self.path)[1]["read_errors"], 1)
        self.path.write_bytes(b"\xff")
        self.assertEqual(inspect_animation_cels(self.path)[1]["read_errors"], 1)
        self.scan([])
        lines, notes = audit_animation_cels(self.folder)
        self.assertFalse(lines)
        self.assertEqual(sum("No usable" in n for n in notes), 3)

    def test_missing_file_reports_no_capture(self):
        lines, notes = audit_animation_cels(self.folder)
        self.assertFalse(lines)
        self.assertIn("missing", notes[0])

    def test_report_integration_preserves_input(self):
        self.scan([[0, 1, "coin", 1, 8], [1, 2, "coin", 1, 9]])
        before = self.path.read_bytes()
        (self.folder / "M2DebugFrames.csv").write_text(
            "frame,totalSimTicks,presented\n0,1,1\n1,2,1\n", encoding="utf-8")
        report, failed = analyze(self.folder)
        self.assertFalse(failed)
        self.assertIn("Fish/coin animation counters (numeric observations; sprite state unknown)", report)
        self.assertIn("1 +1", report)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
