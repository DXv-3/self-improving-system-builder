"""
tests/test_skill_brain_sync.py
-------------------------------
Tests for skill_brain_sync (SYNC-01) and loop_harmony_patch.
All external dependencies mocked. SQLite uses a temp file path.
"""

import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- Point skill_brain_sync at a temp DB so tests don't pollute real data ---
_tmp_db = tempfile.mktemp(suffix="_sbs_test.db")
os.environ["SKILL_SYNC_DB"] = _tmp_db

# Stub harmony_publisher_base
_harmony_pub_mod = types.ModuleType("harmony_publisher_base")
_mock_pub = MagicMock()
_harmony_pub_mod.HarmonyPublisher = MagicMock(return_value=_mock_pub)
sys.modules["harmony_publisher_base"] = _harmony_pub_mod

import skill_brain_sync as sbs


class TestSkillBrainSyncWrite(unittest.TestCase):

    def test_record_skill_event_returns_uuid(self):
        eid = sbs.record_skill_event("code", 1, "promoted", 0.85, "added retry")
        self.assertIsInstance(eid, str)
        self.assertEqual(len(eid), 36)  # UUID format

    def test_record_creates_skill_score_row(self):
        sbs.record_skill_event("review", 1, "evaluated", 0.72, "eval")
        scores = sbs.get_all_skill_scores()
        self.assertIn("review", scores)
        self.assertAlmostEqual(scores["review"], 0.72, places=2)

    def test_rolling_avg_applied_on_second_event(self):
        sbs.record_skill_event("deploy", 1, "promoted", 0.8, "first")
        time.sleep(0.05)  # let threads settle
        sbs.record_skill_event("deploy", 2, "demoted", 0.2, "second")
        time.sleep(0.05)
        scores = sbs.get_all_skill_scores()
        # After 2 events: first=0.8, second=0.7*0.8+0.3*0.2=0.62
        self.assertAlmostEqual(scores["deploy"], 0.62, places=5)

    def test_promote_skill_sets_event_type(self):
        sbs.promote_skill("audit_agent", 1, 0.9, "passed all gates")
        time.sleep(0.05)
        history = sbs.get_skill_history("audit_agent")
        self.assertTrue(any(h["event_type"] == "promoted" for h in history))

    def test_demote_skill_records_demoted_type(self):
        sbs.demote_skill("flaky_skill", 1, 0.3, "flaky")
        time.sleep(0.05)
        history = sbs.get_skill_history("flaky_skill")
        self.assertTrue(any(h["event_type"] == "demoted" for h in history))

    def test_audit_skill_records_audited_type(self):
        sbs.audit_skill("gated_skill", 2, 0.75, "gate passed")
        time.sleep(0.05)
        history = sbs.get_skill_history("gated_skill")
        self.assertTrue(any(h["event_type"] == "audited" for h in history))

    def test_tags_stored_as_json(self):
        sbs.record_skill_event("tagged", 1, "evaluated", 0.5, "", tags=["tag1", "tag2"])
        time.sleep(0.05)
        history = sbs.get_skill_history("tagged")
        self.assertEqual(len(history), 1)
        tags = json.loads(history[0]["tags"])
        self.assertEqual(tags, ["tag1", "tag2"])


class TestSkillBrainSyncRead(unittest.TestCase):

    def setUp(self):
        sbs.record_skill_event("read_a", 1, "promoted", 0.95, "top")
        sbs.record_skill_event("read_b", 1, "evaluated", 0.50, "mid")
        sbs.record_skill_event("read_c", 1, "demoted", 0.10, "low")
        time.sleep(0.1)  # let threads settle

    def test_get_all_skill_scores_returns_dict(self):
        scores = sbs.get_all_skill_scores()
        self.assertIsInstance(scores, dict)
        self.assertIn("read_a", scores)

    def test_get_top_skills_sorted_descending(self):
        top = sbs.get_top_skills(3)
        scores_only = [s for _, s in top]
        self.assertEqual(scores_only, sorted(scores_only, reverse=True))

    def test_get_skill_score_returns_float(self):
        score = sbs.get_skill_score("read_a")
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0.0)

    def test_get_skill_score_unknown_returns_zero(self):
        score = sbs.get_skill_score("does_not_exist_xyz")
        self.assertEqual(score, 0.0)

    def test_get_skill_history_returns_list(self):
        history = sbs.get_skill_history("read_a")
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)

    def test_get_skill_history_limit_respected(self):
        for i in range(5):
            sbs.record_skill_event("limit_test", i+1, "evaluated", 0.5, str(i))
        time.sleep(0.1)
        history = sbs.get_skill_history("limit_test", limit=3)
        self.assertLessEqual(len(history), 3)

    def test_get_skill_summary_found(self):
        summary = sbs.get_skill_summary("read_a")
        self.assertTrue(summary["found"])
        self.assertIn("avg_score", summary)
        self.assertIn("peak_score", summary)
        self.assertIn("recent_history", summary)

    def test_get_skill_summary_not_found(self):
        summary = sbs.get_skill_summary("ghost_skill_xyz")
        self.assertFalse(summary["found"])

    def test_peak_score_never_decreases(self):
        sbs.record_skill_event("peak_test", 1, "promoted", 0.9, "high")
        sbs.record_skill_event("peak_test", 2, "demoted", 0.1, "low")
        time.sleep(0.1)
        summary = sbs.get_skill_summary("peak_test")
        self.assertGreaterEqual(summary["peak_score"], 0.9)


class TestLoopHarmonyPatch(unittest.TestCase):

    def test_extract_skill_name_direct(self):
        from loop_harmony_patch import _extract_skill_name
        self.assertEqual(_extract_skill_name({"skill_name": "code"}), "code")

    def test_extract_skill_name_nested(self):
        from loop_harmony_patch import _extract_skill_name
        self.assertEqual(_extract_skill_name({"skill": {"name": "deploy"}}), "deploy")

    def test_extract_skill_name_task_type(self):
        from loop_harmony_patch import _extract_skill_name
        self.assertEqual(_extract_skill_name({"task_type": "code", "operator_id": "op1"}), "code_op1")

    def test_extract_skill_name_fallback(self):
        from loop_harmony_patch import _extract_skill_name
        self.assertEqual(_extract_skill_name({}), "unknown")

    def test_extract_outcome_score(self):
        from loop_harmony_patch import _extract_outcome_score
        self.assertAlmostEqual(_extract_outcome_score({"outcome_score": 0.88}), 0.88)
        self.assertAlmostEqual(_extract_outcome_score({"score": 0.5}), 0.5)
        self.assertAlmostEqual(_extract_outcome_score({}), 0.0)

    def test_extract_event_type_mapping(self):
        from loop_harmony_patch import _extract_event_type
        self.assertEqual(_extract_event_type({"action": "PROMOTE"}), "promoted")
        self.assertEqual(_extract_event_type({"action": "DEMOTE"}), "demoted")
        self.assertEqual(_extract_event_type({"event_type": "audited"}), "audited")
        self.assertEqual(_extract_event_type({}), "evaluated")

    def test_extract_skill_version(self):
        from loop_harmony_patch import _extract_skill_version
        self.assertEqual(_extract_skill_version({"skill_version": 3}), 3)
        self.assertEqual(_extract_skill_version({"version": 2}), 2)
        self.assertEqual(_extract_skill_version({}), 1)


if __name__ == "__main__":
    unittest.main()
