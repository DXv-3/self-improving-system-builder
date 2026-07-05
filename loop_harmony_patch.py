"""
loop_harmony_patch.py
---------------------
Patch module that wires skill_brain_sync into loop.py's trigger
handler without modifying loop.py directly.

Apply at startup:
    from loop_harmony_patch import patch_loop
    patch_loop()  # monkeypatches LoopRunner._handle_trigger

Or apply from the CLI:
    python loop_harmony_patch.py --test

This is exactly the same patch pattern loop.py already uses for its
IDKWIDK gate injections — same philosophy, same file.

What the patch adds:
  After every trigger execution that produces an outcome_score, the patch
  calls skill_brain_sync.record_skill_event() so:
    1. The SQLite sidecar is updated immediately
    2. The harmony bus receives a skill_event
    3. the-brain KG receives a kg_write (if reachable)
    4. conductor's BrainSkillRouter gets fresh scores on next call
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_PATCHED = False


def _extract_skill_name(trigger_result: Dict[str, Any]) -> str:
    """
    Extract a canonical skill_name from a loop trigger result.
    Tries, in order:
      1. result["skill_name"]
      2. result["skill"]["name"]
      3. result["task_type"] + "_" + result.get("operator_id", "")
      4. "unknown"
    """
    if "skill_name" in trigger_result:
        return str(trigger_result["skill_name"])
    skill = trigger_result.get("skill", {})
    if isinstance(skill, dict) and "name" in skill:
        return str(skill["name"])
    task_type = trigger_result.get("task_type", "")
    op_id = trigger_result.get("operator_id", "")
    if task_type:
        return f"{task_type}_{op_id}" if op_id else task_type
    return "unknown"


def _extract_skill_version(trigger_result: Dict[str, Any]) -> int:
    return int(
        trigger_result.get("skill_version")
        or trigger_result.get("version")
        or trigger_result.get("skill", {}).get("version", 1)
        or 1
    )


def _extract_outcome_score(trigger_result: Dict[str, Any]) -> float:
    raw = (
        trigger_result.get("outcome_score")
        or trigger_result.get("score")
        or trigger_result.get("result", {}).get("outcome_score")
        or 0.0
    )
    return float(raw)


def _extract_event_type(trigger_result: Dict[str, Any]) -> str:
    """
    Map loop.py's internal action labels to skill_brain_sync event types.
    """
    action = (
        trigger_result.get("event_type")
        or trigger_result.get("action")
        or trigger_result.get("gate_outcome")
        or "evaluated"
    )
    mapping = {
        "PROMOTE":   "promoted",
        "DEMOTE":    "demoted",
        "AUDIT":     "audited",
        "PATCH":     "patched",
        "EVAL":      "evaluated",
        "promote":   "promoted",
        "demote":    "demoted",
        "audit":     "audited",
        "patch":     "patched",
        "evaluated": "evaluated",
    }
    return mapping.get(str(action), "evaluated")


def patch_loop():
    """
    Monkeypatch LoopRunner._handle_trigger to record every skill event
    into skill_brain_sync after the original handler runs.
    """
    global _PATCHED
    if _PATCHED:
        return

    try:
        import skill_brain_sync as sbs
    except ImportError:
        logger.warning("loop_harmony_patch: skill_brain_sync not found — patch skipped")
        return

    try:
        import loop  # loop.py in this repo
    except ImportError:
        logger.warning("loop_harmony_patch: loop.py not found — patch skipped")
        return

    runner_class = getattr(loop, "LoopRunner", None)
    if runner_class is None:
        logger.warning("loop_harmony_patch: LoopRunner class not found in loop.py — patch skipped")
        return

    original_handle = runner_class._handle_trigger

    def patched_handle_trigger(self, trigger_result: Dict[str, Any], *args, **kwargs):
        # Run the original handler first
        outcome = original_handle(self, trigger_result, *args, **kwargs)

        # Extract fields and record to skill_brain_sync
        try:
            result_dict = trigger_result if isinstance(trigger_result, dict) else {}
            if isinstance(outcome, dict):
                result_dict = {**result_dict, **outcome}

            skill_name = _extract_skill_name(result_dict)
            skill_version = _extract_skill_version(result_dict)
            event_type = _extract_event_type(result_dict)
            outcome_score = _extract_outcome_score(result_dict)
            delta_summary = str(
                result_dict.get("delta_summary")
                or result_dict.get("summary")
                or result_dict.get("message")
                or ""
            )[:200]  # truncate for DB

            sbs.record_skill_event(
                skill_name=skill_name,
                skill_version=skill_version,
                event_type=event_type,
                outcome_score=outcome_score,
                delta_summary=delta_summary,
            )
        except Exception as exc:
            logger.warning("loop_harmony_patch: record_skill_event failed (non-fatal): %s", exc)

        return outcome

    runner_class._handle_trigger = patched_handle_trigger
    _PATCHED = True
    logger.info("loop_harmony_patch: LoopRunner._handle_trigger patched successfully")


# ---------------------------------------------------------------------------
# CLI test mode
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Test loop_harmony_patch and skill_brain_sync")
    parser.add_argument("--test", action="store_true", help="Run a quick smoke test")
    args = parser.parse_args()

    if args.test:
        import skill_brain_sync as sbs

        print("--- skill_brain_sync smoke test ---")

        eid1 = sbs.promote_skill("test_skill", 1, 0.9, "added retry logic")
        print(f"promote_skill event_id: {eid1}")

        eid2 = sbs.demote_skill("test_skill", 1, 0.4, "regression in edge case")
        print(f"demote_skill event_id: {eid2}")

        eid3 = sbs.audit_skill("deploy_agent", 2, 0.75, "IDKWIDK gate passed")
        print(f"audit_skill event_id: {eid3}")

        scores = sbs.get_all_skill_scores()
        print(f"All scores: {scores}")

        history = sbs.get_skill_history("test_skill")
        print(f"test_skill history ({len(history)} events):")
        for h in history:
            print(f"  [{h['event_type']}] v{h['skill_version']} score={h['outcome_score']:.2f}: {h['delta_summary']}")

        top = sbs.get_top_skills(3)
        print(f"Top 3 skills: {top}")

        summary = sbs.get_skill_summary("test_skill")
        print(f"test_skill summary: avg={summary['avg_score']:.3f} peak={summary['peak_score']:.3f} events={summary['event_count']}")

        print("\n✅ smoke test passed")
        sys.exit(0)
