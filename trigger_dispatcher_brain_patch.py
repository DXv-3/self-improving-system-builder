"""
trigger_dispatcher_brain_patch.py
----------------------------------
Patch for trigger_dispatcher.py that adds:
  1. Skill score-weighted routing: tasks are routed to the skill with
     the highest avg outcome_score from the-brain KG.
  2. Dispatch events written to the-brain as `dispatch_event` KG nodes.
  3. ModelRouter integration for the model call inside each dispatch.

Activate by importing before trigger_dispatcher:
    import trigger_dispatcher_brain_patch  # noqa
    from trigger_dispatcher import dispatch

Or used standalone:
    python trigger_dispatcher_brain_patch.py --event-type file_changed --payload '{"path": "skills/code.md"}'
"""

import functools
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from skill_brain_sync import get_all_skill_scores, get_brain_writer, SkillEvent
    _sync_available = True
except ImportError:
    _sync_available = False
    logger.warning("trigger_dispatcher_brain_patch: skill_brain_sync unavailable")

try:
    from model_router_adapter import call_model_for_task
    _router_available = True
except ImportError:
    _router_available = False


# ---------------------------------------------------------------------------
# Skill-score-weighted router
# ---------------------------------------------------------------------------

def score_weighted_skill_select(candidate_skills: list, task_type: str = "reasoning") -> Optional[str]:
    """
    Given a list of candidate skill names, return the one with the highest
    avg outcome_score from the-brain. Falls back to first candidate if unavailable.
    """
    if not _sync_available or not candidate_skills:
        return candidate_skills[0] if candidate_skills else None

    try:
        scores = get_all_skill_scores()
        ranked = sorted(candidate_skills, key=lambda s: scores.get(s, 0.0), reverse=True)
        selected = ranked[0]
        logger.debug(
            "score_weighted_skill_select: selected '%s' (score=%.3f) from %s",
            selected, scores.get(selected, 0.0), candidate_skills
        )
        return selected
    except Exception as exc:
        logger.warning("score_weighted_skill_select failed: %s", exc)
        return candidate_skills[0]


# ---------------------------------------------------------------------------
# Dispatch event write-back
# ---------------------------------------------------------------------------

def record_dispatch_event(
    event_type: str,
    skill_selected: str,
    payload: Dict,
    outcome: str = "dispatched",
    model_used: str = "",
):
    if not _sync_available:
        return
    try:
        writer = get_brain_writer()
        event = SkillEvent(
            event_type="dispatch",
            skill_name=skill_selected,
            trigger=event_type,
            outcome_score=1.0 if outcome == "dispatched" else 0.0,
            delta_summary=f"dispatch:{event_type} → {skill_selected} outcome={outcome}",
            metadata={"payload_keys": list(payload.keys()), "model_used": model_used},
        )
        writer.write_skill_event(event)
    except Exception as exc:
        logger.warning("record_dispatch_event failed: %s", exc)


# ---------------------------------------------------------------------------
# Patch trigger_dispatcher.py
# ---------------------------------------------------------------------------

def _patch_trigger_dispatcher():
    try:
        import trigger_dispatcher as td
    except ImportError:
        logger.warning("trigger_dispatcher_brain_patch: trigger_dispatcher.py not importable")
        return

    # Patch: wrap dispatch() to add score-weighted skill selection + brain write-back
    if hasattr(td, "dispatch"):
        original_dispatch = td.dispatch

        @functools.wraps(original_dispatch)
        def patched_dispatch(event_type: str, payload: Dict, **kwargs):
            # Score-weight skill selection if dispatcher passes candidate_skills
            candidate_skills = kwargs.pop("candidate_skills", [])
            if candidate_skills:
                kwargs["skill"] = score_weighted_skill_select(candidate_skills, task_type=event_type)

            result = original_dispatch(event_type, payload, **kwargs)

            # Write dispatch event to brain
            skill_used = kwargs.get("skill", event_type)
            model_used = result.get("model", "") if isinstance(result, dict) else ""
            record_dispatch_event(
                event_type=event_type,
                skill_selected=skill_used,
                payload=payload,
                outcome="dispatched",
                model_used=model_used,
            )
            return result

        td.dispatch = patched_dispatch
        logger.info("trigger_dispatcher_brain_patch: patched trigger_dispatcher.dispatch")

    # Patch: replace model calls inside trigger_dispatcher with ModelRouter
    if _router_available and hasattr(td, "call_model"):
        original_td_call = td.call_model

        @functools.wraps(original_td_call)
        def patched_td_call(prompt, task_type="reasoning", **kwargs):
            try:
                return call_model_for_task(prompt, task_type=task_type)
            except Exception:
                return original_td_call(prompt, **kwargs)

        td.call_model = patched_td_call
        logger.info("trigger_dispatcher_brain_patch: patched trigger_dispatcher.call_model → ModelRouter")


_patch_trigger_dispatcher()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dispatch a trigger event with brain wiring")
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--payload", default="{}", help="JSON payload string")
    parser.add_argument("--skill", default=None, help="Force a specific skill")
    args = parser.parse_args()

    payload = json.loads(args.payload)

    import trigger_dispatcher as td
    kwargs = {}
    if args.skill:
        kwargs["skill"] = args.skill
    result = td.dispatch(args.event_type, payload, **kwargs)
    print(json.dumps(result, indent=2, default=str))
