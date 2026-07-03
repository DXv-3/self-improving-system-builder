#!/usr/bin/env python3
"""
learning_memory.py

Persist cross-run lessons so cycle N+1 starts smarter than cycle N.

STATUS: SCAFFOLD
  - record_cycle_outcome() and load_lessons() are stubs
  - Wire record_cycle_outcome() into persist_result.py after each cycle
  - Wire load_lessons() into score_actions.py before scoring
  - get_risk_adjustment() returns 0 until trust_update.py is built

See ROADMAP_UNBUILT_BUT_DISCUSSED.md for full implementation spec.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY_FILE = Path("learning_memory.jsonl")


def record_cycle_outcome(
    cycle_id: str,
    blocker_patterns: list[dict],
    successful_followup_types: list[str],
    approval_outcomes: list[dict],
    retry_strategy: str,
    claim_resolutions: list[dict],
) -> None:
    """Append one cycle's lessons to the persistent memory file."""
    record = {
        "cycle_id": cycle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "blocker_patterns": blocker_patterns,
        "successful_followup_types": successful_followup_types,
        "approval_outcomes": approval_outcomes,
        "retry_strategy": retry_strategy,
        "claim_resolutions": claim_resolutions,
    }
    with MEMORY_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")


def load_lessons() -> list[dict]:
    """Load all past cycle lessons for use in scoring adjustments."""
    if not MEMORY_FILE.exists():
        return []
    return [
        json.loads(line)
        for line in MEMORY_FILE.read_text().splitlines()
        if line.strip()
    ]


def get_risk_adjustment(action_category: str) -> float:
    """
    Return a risk adjustment based on historical outcomes.
    Negative = safer than default. Positive = riskier.
    Returns 0.0 until trust_update.py is implemented.
    """
    # TODO: implement via trust_update.py
    # lessons = load_lessons()
    # outcomes = [l for l in lessons if action_category in str(l.get('claim_resolutions', []))]
    # success_rate = sum(1 for o in outcomes if o.get('retry_strategy') == 'reaudit_now') / max(len(outcomes), 1)
    # return -2.0 if success_rate > 0.8 else (1.0 if success_rate < 0.3 else 0.0)
    return 0.0


def get_common_blocker_types() -> dict[str, int]:
    """Return frequency count of blocker types seen across all runs."""
    lessons = load_lessons()
    counts: dict[str, int] = {}
    for lesson in lessons:
        for bp in lesson.get("blocker_patterns", []):
            label = bp.get("label", "unknown")
            counts[label] = counts.get(label, 0) + 1
    return counts


def get_best_followup_for_blocker(blocker_label: str) -> str | None:
    """Return the follow-up type that most often resolved this blocker label."""
    lessons = load_lessons()
    resolution_counts: dict[str, int] = {}
    for lesson in lessons:
        patterns = lesson.get("blocker_patterns", [])
        followups = lesson.get("successful_followup_types", [])
        matched = any(bp.get("label") == blocker_label for bp in patterns)
        if matched:
            for ft in followups:
                resolution_counts[ft] = resolution_counts.get(ft, 0) + 1
    if not resolution_counts:
        return None
    return max(resolution_counts, key=resolution_counts.get)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--stats":
        lessons = load_lessons()
        print(f"Total cycles recorded: {len(lessons)}")
        print(f"Blocker type frequencies: {get_common_blocker_types()}")
    else:
        print("Usage: python3 learning_memory.py --stats")
        print("SCAFFOLD: wire into persist_result.py and score_actions.py")
