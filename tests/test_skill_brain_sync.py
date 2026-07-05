"""
tests/test_skill_brain_sync.py
-------------------------------
Tests for skill_brain_sync.py — the closed-loop brain bridge.
All brain_client and harmony calls are mocked; no real services needed.
"""

import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# ---------------------------------------------------------------------------
# Stub brain_client before importing skill_brain_sync
# ---------------------------------------------------------------------------

brain_client_stub = types.ModuleType("brain_client")
brain_client_stub.upsert_node = MagicMock(return_value=True)
brain_client_stub.upsert_edge = MagicMock(return_value=True)
brain_client_stub.query_nodes = MagicMock(return_value=[])
sys.modules["brain_client"] = brain_client_stub

from skill_brain_sync import (  # noqa: E402
    SkillEvent,
    BrainWriter,
    record_skill_promoted,
    record_skill_demoted,
    record_gate_result,
    record_skill_mutated,
    get_skill_history,
    get_all_skill_scores,
)


class TestSkillEvent(unittest.TestCase):
    def test_defaults(self):
        e = SkillEvent(event_type="promoted", skill_name="code")
        self.assertEqual(e.source_repo, "self-improving-system-builder")
        self.assertIsNotNone(e.event_id)
        self.assertIsNotNone(e.timestamp)

    def test_fields(self):
        e = SkillEvent(event_type="gate_fail", skill_name="review", outcome_score=0.2)
        self.assertEqual(e.event_type, "gate_fail")
        self.assertAlmostEqual(e.outcome_score, 0.2)


class TestBrainWriter(unittest.TestCase):
    def setUp(self):
        self.writer = BrainWriter()
        # Ensure it thinks brain_client is available
        self.writer._available = True
        self.writer._client = brain_client_stub
        # Use a tmp file for local mirror
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.writer._local_mirror = Path(self.tmp.name)

    def tearDown(self):
        self.writer._local_mirror.unlink(missing_ok=True)

    def test_write_skill_event_calls_upsert_node(self):
        brain_client_stub.upsert_node.reset_mock()
        e = SkillEvent(event_type="promoted", skill_name="code", outcome_score=0.9)
        self.writer.write_skill_event(e)
        self.assertTrue(brain_client_stub.upsert_node.called)

    def test_write_skill_event_appends_local(self):
        e = SkillEvent(event_type="mutated", skill_name="review", outcome_score=0.5)
        self.writer.write_skill_event(e)
        lines = self.writer._local_mirror.read_text().strip().split("\n")
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["skill_name"], "review")

    def test_read_local_history_filters_by_skill(self):
        events = [
            SkillEvent(event_type="promoted", skill_name="code"),
            SkillEvent(event_type="promoted", skill_name="review"),
            SkillEvent(event_type="demoted", skill_name="code"),
        ]
        for ev in events:
            self.writer._append_local(__import__('dataclasses').asdict(ev))

        self.writer._available = False  # force local fallback
        history = self.writer.read_skill_history("code", limit=10)
        self.assertEqual(len(history), 2)
        for h in history:
            self.assertEqual(h["skill_name"], "code")

    def test_brain_write_failure_falls_back_to_local(self):
        brain_client_stub.upsert_node.side_effect = Exception("brain down")
        e = SkillEvent(event_type="gate_pass", skill_name="deploy")
        # Should not raise
        self.writer.write_skill_event(e)
        brain_client_stub.upsert_node.side_effect = None
        # Local file should still have the record
        content = self.writer._local_mirror.read_text()
        self.assertIn("gate_pass", content)

    def test_read_all_skill_scores_local_fallback(self):
        self.writer._available = False
        records = [
            {"skill_name": "code", "outcome_score": 0.8},
            {"skill_name": "code", "outcome_score": 0.6},
            {"skill_name": "review", "outcome_score": 0.9},
        ]
        with self.writer._local_mirror.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        scores = self.writer.read_all_skill_scores()
        self.assertAlmostEqual(scores["code"], 0.7)
        self.assertAlmostEqual(scores["review"], 0.9)


class TestConvenienceFunctions(unittest.TestCase):
    def test_record_skill_promoted_returns_event(self):
        ev = record_skill_promoted("code", version=3, outcome_score=0.95, delta_summary="added retry logic")
        self.assertEqual(ev.event_type, "promoted")
        self.assertEqual(ev.skill_name, "code")

    def test_record_skill_demoted(self):
        ev = record_skill_demoted("deploy", version=1, outcome_score=0.1, reason="broke prod")
        self.assertEqual(ev.event_type, "demoted")

    def test_record_gate_result_pass(self):
        ev = record_gate_result("code", "gate_syntax", passed=True, score=1.0)
        self.assertEqual(ev.event_type, "gate_pass")

    def test_record_gate_result_fail(self):
        ev = record_gate_result("code", "gate_test", passed=False, score=0.0, detail="tests failed")
        self.assertEqual(ev.event_type, "gate_fail")

    def test_record_skill_mutated(self):
        ev = record_skill_mutated("review", version=2, mutation_summary="restructured prompt",
                                  model_used="claude/claude-sonnet-4-5", score=0.75)
        self.assertEqual(ev.event_type, "mutated")
        self.assertEqual(ev.metadata["model_used"], "claude/claude-sonnet-4-5")


if __name__ == "__main__":
    unittest.main()
