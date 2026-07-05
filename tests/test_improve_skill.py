"""
tests/test_improve_skill.py — Integration tests for improve_skill + IDKWIDK auditor.

Runs without any live API keys by monkeypatching ModelCaller.call().
Tests cover: mutation acceptance, each of the 7 gate rejections, empty patch,
JSON parse failure, model error, dry-run, and learning_memory logging.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from improve_skill import (
    IDKWIDKRejection,
    SkillMutationAuditor,
    improve_skill,
    _build_mutation_prompt,
    _emit_build_watch_event,
)
from model_caller import ProviderResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def tmp_dirs(tmp_path, monkeypatch):
    """Redirect all file I/O to a temp dir so tests never touch real disk."""
    import improve_skill as ism
    monkeypatch.setattr(ism, "LEARNING_MEMORY", tmp_path / "learning_memory.jsonl")
    monkeypatch.setattr(ism, "SKILLS_DIR", tmp_path / "skills")
    monkeypatch.setattr(ism, "BUILD_WATCH_DIR", tmp_path / ".build-watch")
    (tmp_path / "skills").mkdir()
    return tmp_path


def _make_result(text: str, provider: str = "zai") -> ProviderResult:
    return ProviderResult(provider=provider, model="test-model", text=text, latency_ms=42.0)


def _valid_mutation(patch_override=None):
    return json.dumps({
        "patch": patch_override or {"steps": ["step A", "step B improved"]},
        "rationale": "The previous steps caused ambiguous routing in context_spinner.",
        "expected_improvement": "More accurate context selection with fewer retries.",
    })


BASE_SKILL = {
    "name": "context_spinner",
    "steps": ["step A", "step B"],
    "notes": "routes context",
}


# ---------------------------------------------------------------------------
# Test 1: Happy path — mutation applied
# ---------------------------------------------------------------------------

def test_improve_skill_applied(tmp_dirs):
    with patch("improve_skill.ModelCaller.call", return_value=_make_result(_valid_mutation())), \
         patch("improve_skill._load_skill", return_value=BASE_SKILL), \
         patch("improve_skill._push_patch_to_brain", return_value=True):
        result = improve_skill("context_spinner")
    assert result["outcome"] == "applied"
    assert result["gate_failed"] is None
    assert "steps" in result["patch"]
    # skill file written to disk
    skill_file = tmp_dirs / "skills" / "context_spinner.json"
    assert skill_file.exists()


# ---------------------------------------------------------------------------
# Test 2: Dry run — no disk write
# ---------------------------------------------------------------------------

def test_improve_skill_dry_run(tmp_dirs):
    with patch("improve_skill.ModelCaller.call", return_value=_make_result(_valid_mutation())), \
         patch("improve_skill._load_skill", return_value=BASE_SKILL), \
         patch("improve_skill._push_patch_to_brain", return_value=True):
        result = improve_skill("context_spinner", dry_run=True)
    assert result["outcome"] == "dry_run_ok"
    skill_file = tmp_dirs / "skills" / "context_spinner.json"
    assert not skill_file.exists(), "Dry run must not write to disk"


# ---------------------------------------------------------------------------
# Test 3: Empty patch → no_change
# ---------------------------------------------------------------------------

def test_improve_skill_no_change(tmp_dirs):
    empty = json.dumps({
        "patch": {},
        "rationale": "No improvement identified.",
        "expected_improvement": "No change expected.",
    })
    with patch("improve_skill.ModelCaller.call", return_value=_make_result(empty)), \
         patch("improve_skill._load_skill", return_value=BASE_SKILL):
        result = improve_skill("context_spinner")
    assert result["outcome"] == "no_change"


# ---------------------------------------------------------------------------
# Test 4: Non-JSON model output → error
# ---------------------------------------------------------------------------

def test_improve_skill_bad_json(tmp_dirs):
    with patch("improve_skill.ModelCaller.call", return_value=_make_result("not json at all")), \
         patch("improve_skill._load_skill", return_value=BASE_SKILL):
        result = improve_skill("context_spinner")
    assert result["outcome"] == "error"
    assert result["gate_failed"] == "parse"


# ---------------------------------------------------------------------------
# Test 5: Model caller fails → error
# ---------------------------------------------------------------------------

def test_improve_skill_model_error(tmp_dirs):
    from model_caller import ModelCallerError
    with patch("improve_skill.ModelCaller.call", side_effect=ModelCallerError("all providers down")), \
         patch("improve_skill._load_skill", return_value=BASE_SKILL):
        result = improve_skill("context_spinner")
    assert result["outcome"] == "error"
    assert result["provider"] == "none"


# ---------------------------------------------------------------------------
# Test 6: learning_memory.jsonl is written
# ---------------------------------------------------------------------------

def test_outcome_logged_to_learning_memory(tmp_dirs):
    import improve_skill as ism
    with patch("improve_skill.ModelCaller.call", return_value=_make_result(_valid_mutation())), \
         patch("improve_skill._load_skill", return_value=BASE_SKILL), \
         patch("improve_skill._push_patch_to_brain", return_value=True):
        improve_skill("context_spinner")
    lines = ism.LEARNING_MEMORY.read_text().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["skill"] == "context_spinner"
    assert entry["outcome"] == "applied"


# ---------------------------------------------------------------------------
# Test 7-12: IDKWIDK gate rejections (one per gate)
# ---------------------------------------------------------------------------

class TestIDKWIDKGates:
    AUDITOR = SkillMutationAuditor()
    ORIGINAL = BASE_SKILL

    def test_g1_empty_patch(self):
        with pytest.raises(IDKWIDKRejection, match="G1"):
            self.AUDITOR.audit(self.ORIGINAL, {"patch": None, "rationale": "x" * 30, "expected_improvement": "y"})

    def test_g2_missing_keys(self):
        with pytest.raises(IDKWIDKRejection, match="G2"):
            self.AUDITOR.audit(self.ORIGINAL, {"patch": {"steps": ["a"]}})

    def test_g3_short_rationale(self):
        with pytest.raises(IDKWIDKRejection, match="G3"):
            self.AUDITOR.audit(self.ORIGINAL, {
                "patch": {"steps": ["a"]},
                "rationale": "too short",
                "expected_improvement": "better",
            })

    def test_g4_regression_signal(self):
        with pytest.raises(IDKWIDKRejection, match="G4"):
            self.AUDITOR.audit(self.ORIGINAL, {
                "patch": {"steps": ["a"]},
                "rationale": "This will reduce accuracy because of the new approach.",
                "expected_improvement": "this will degrade performance slightly",
            })

    def test_g5_rogue_key(self):
        with pytest.raises(IDKWIDKRejection, match="G5"):
            self.AUDITOR.audit(self.ORIGINAL, {
                "patch": {"__builtins__": {}},
                "rationale": "injecting something dangerous here for test",
                "expected_improvement": "might do something unexpected",
            })

    def test_g6_forbidden_op(self):
        with pytest.raises(IDKWIDKRejection, match="G6"):
            self.AUDITOR.audit(self.ORIGINAL, {
                "patch": {"steps": ["eval(input())"]},
                "rationale": "eval added for dynamic dispatch which is faster",
                "expected_improvement": "faster dispatch",
            })

    def test_g7_oversized_patch(self):
        huge_patch = {"notes": "x" * 100_000}
        with pytest.raises(IDKWIDKRejection, match="G7"):
            self.AUDITOR.audit(self.ORIGINAL, {
                "patch": huge_patch,
                "rationale": "Expanding notes with comprehensive documentation",
                "expected_improvement": "better docs",
            })


# ---------------------------------------------------------------------------
# Test 13: build-watch event file created
# ---------------------------------------------------------------------------

def test_build_watch_event_created(tmp_dirs):
    import improve_skill as ism
    _emit_build_watch_event("test event", kind="test")
    events_file = ism.BUILD_WATCH_DIR / "events.jsonl"
    assert events_file.exists()
    entry = json.loads(events_file.read_text().splitlines()[0])
    assert entry["msg"] == "test event"
    assert entry["kind"] == "test"
