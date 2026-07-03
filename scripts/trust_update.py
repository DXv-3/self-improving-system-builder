#!/usr/bin/env python3
"""
trust_update.py

Convert accumulated success/failure patterns from learning_memory.jsonl
into updated risk weights and scoring adjustments.

STATUS: SCAFFOLD
  - compute_risk_adjustments() is a stub with the intended algorithm
  - apply_adjustments_to_queue() wires adjustments into a live action queue
  - Until wired into score_actions.py, this has no effect on execution

See ROADMAP_UNBUILT_BUT_DISCUSSED.md for full implementation spec.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from learning_memory import load_lessons

ADJUSTMENT_FILE = Path("trust_adjustments.json")

# Thresholds for adjusting risk
HIGH_SUCCESS_RATE = 0.80   # lower risk by 2 if success rate above this
LOW_SUCCESS_RATE  = 0.30   # raise risk by 1 if success rate below this
MIN_SAMPLES       = 5      # minimum samples before adjusting


def compute_risk_adjustments() -> dict[str, float]:
    """
    For each action category seen in history, compute a risk delta.
    Negative delta = safer than default.
    Positive delta = riskier than default.
    """
    lessons = load_lessons()
    if len(lessons) < MIN_SAMPLES:
        return {}

    category_outcomes: dict[str, list[bool]] = {}
    for lesson in lessons:
        strategy = lesson.get("retry_strategy", "")
        success = strategy in ("reaudit_now", "apply_downgrades_and_reaudit")
        for cr in lesson.get("claim_resolutions", []):
            cat = cr.get("category", "unknown")
            category_outcomes.setdefault(cat, []).append(success)

    adjustments = {}
    for cat, outcomes in category_outcomes.items():
        if len(outcomes) < MIN_SAMPLES:
            continue
        rate = sum(outcomes) / len(outcomes)
        if rate > HIGH_SUCCESS_RATE:
            adjustments[cat] = -2.0
        elif rate < LOW_SUCCESS_RATE:
            adjustments[cat] = +1.0
        else:
            adjustments[cat] = 0.0

    return adjustments


def save_adjustments(adjustments: dict[str, float]) -> None:
    ADJUSTMENT_FILE.write_text(json.dumps({
        "adjustments": adjustments,
        "sample_count": len(load_lessons()),
        "note": "Apply these deltas to risk_level in score_actions.py",
    }, indent=2))


def apply_adjustments_to_queue(queue_path: str) -> None:
    """Read action_queue.json and apply risk adjustments in place."""
    queue = json.loads(Path(queue_path).read_text())
    adjustments = compute_risk_adjustments()
    if not adjustments:
        print("[trust_update] Insufficient history for adjustments")
        return

    adjusted = 0
    for action in queue.get("actions", []):
        cat = action.get("category", "")
        if cat in adjustments:
            original = action["risk_level"]
            action["risk_level"] = max(0, min(10, original + adjustments[cat]))
            action["notes"] = (
                action.get("notes", "") +
                f" [trust_update: risk {original} -> {action['risk_level']} for category {cat}]"
            )
            adjusted += 1

    Path(queue_path).write_text(json.dumps(queue, indent=2))
    print(f"[trust_update] Adjusted risk for {adjusted} actions")
    save_adjustments(adjustments)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--apply":
        apply_adjustments_to_queue(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "--preview":
        adj = compute_risk_adjustments()
        print(json.dumps(adj, indent=2))
    else:
        print("Usage:")
        print("  python3 trust_update.py --apply action_queue.json")
        print("  python3 trust_update.py --preview")
