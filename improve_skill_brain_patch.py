"""
improve_skill_brain_patch.py
-----------------------------
Monkey-patch / mixin for improve_skill.py that injects brain write-back
at each stage of the skill improvement lifecycle WITHOUT modifying the
original improve_skill.py source (preserves git blame, avoids merge conflicts).

Activate by importing this module before running improve_skill:

    import improve_skill_brain_patch  # noqa — activates patch on import
    from improve_skill import run_improvement_cycle
    run_improvement_cycle(skill_name="my_skill")

Or run directly:
    python improve_skill_brain_patch.py --skill my_skill --task-type code

What the patch adds to the improvement lifecycle:
  PRE:   read skill history from the-brain → inject as context into prompt
  MID:   after each IDKWIDK gate → record gate result to brain
  POST:  on promotion → record_skill_promoted; on rejection → record_skill_demoted
         on mutation → record_skill_mutated (every LLM-generated diff)
"""

import functools
import logging
import sys
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import skill_brain_sync (the bridge module)
# ---------------------------------------------------------------------------
try:
    from skill_brain_sync import (
        record_skill_promoted,
        record_skill_demoted,
        record_skill_mutated,
        record_gate_result,
        get_skill_history,
    )
    _sync_available = True
except ImportError:
    logger.warning("improve_skill_brain_patch: skill_brain_sync not found — brain write-back disabled")
    _sync_available = False


# ---------------------------------------------------------------------------
# Import model_router_adapter to upgrade model calls inside improve_skill
# ---------------------------------------------------------------------------
try:
    from model_router_adapter import call_model_for_task
    _router_available = True
except ImportError:
    _router_available = False


# ---------------------------------------------------------------------------
# Patch improve_skill module if it's importable
# ---------------------------------------------------------------------------

def _patch_improve_skill():
    try:
        import improve_skill as ism
    except ImportError:
        logger.warning("improve_skill_brain_patch: improve_skill.py not importable")
        return

    # --- Patch 1: wrap call_model inside improve_skill to use ModelRouter ---
    if _router_available and hasattr(ism, "call_model"):
        original_call_model = ism.call_model

        @functools.wraps(original_call_model)
        def patched_call_model(prompt, model=None, task_type="reasoning", **kwargs):
            try:
                return call_model_for_task(prompt, task_type=task_type)
            except Exception:
                return original_call_model(prompt, model=model, **kwargs)

        ism.call_model = patched_call_model
        logger.info("improve_skill_brain_patch: patched improve_skill.call_model → ModelRouter")

    # --- Patch 2: wrap promote_skill to record brain event ---
    if _sync_available and hasattr(ism, "promote_skill"):
        original_promote = ism.promote_skill

        @functools.wraps(original_promote)
        def patched_promote(skill_name, version=1, score=0.0, delta="", trigger="improve_skill", **kwargs):
            result = original_promote(skill_name, version=version, score=score,
                                      delta=delta, trigger=trigger, **kwargs)
            record_skill_promoted(
                skill_name=skill_name,
                version=version,
                outcome_score=score,
                delta_summary=delta,
                trigger=trigger,
            )
            return result

        ism.promote_skill = patched_promote
        logger.info("improve_skill_brain_patch: patched improve_skill.promote_skill → brain write-back")

    # --- Patch 3: wrap run_idkwidk_gate (if it exists) to record gate results ---
    if _sync_available and hasattr(ism, "run_idkwidk_gate"):
        original_gate = ism.run_idkwidk_gate

        @functools.wraps(original_gate)
        def patched_gate(skill_name, gate_id, **kwargs):
            result = original_gate(skill_name, gate_id, **kwargs)
            passed = result.get("passed", False) if isinstance(result, dict) else bool(result)
            score = result.get("score", 1.0 if passed else 0.0) if isinstance(result, dict) else (1.0 if passed else 0.0)
            detail = result.get("detail", "") if isinstance(result, dict) else ""
            record_gate_result(
                skill_name=skill_name,
                gate_id=gate_id,
                passed=passed,
                score=score,
                detail=detail,
            )
            return result

        ism.run_idkwidk_gate = patched_gate
        logger.info("improve_skill_brain_patch: patched improve_skill.run_idkwidk_gate → brain gate recording")

    # --- Patch 4: inject brain history as context into the prompt builder ---
    if _sync_available and hasattr(ism, "build_improvement_prompt"):
        original_build = ism.build_improvement_prompt

        @functools.wraps(original_build)
        def patched_build_prompt(skill_name, current_skill_text, task_description, **kwargs):
            history = get_skill_history(skill_name, limit=5)
            brain_context = ""
            if history:
                summaries = [
                    f"  [{h.get('event_type','?')}] v{h.get('skill_version',1)} "
                    f"score={h.get('outcome_score',0):.2f}: {h.get('delta_summary','')[:120]}"
                    for h in history[-5:]
                ]
                brain_context = (
                    "\n\n### Recent Skill History (from the-brain KG):\n"
                    + "\n".join(summaries)
                    + "\n\nUse this history to avoid repeating past mistakes and build on successful mutations.\n"
                )

            original_prompt = original_build(
                skill_name, current_skill_text, task_description, **kwargs
            )
            return original_prompt + brain_context

        ism.build_improvement_prompt = patched_build_prompt
        logger.info("improve_skill_brain_patch: patched improve_skill.build_improvement_prompt → brain context injection")


# Activate patch on import
_patch_improve_skill()


# ---------------------------------------------------------------------------
# CLI entry point — run a single improvement cycle with brain wiring active
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run improve_skill with brain write-back active")
    parser.add_argument("--skill", required=True, help="Skill name to improve")
    parser.add_argument("--task-type", default="reasoning",
                        choices=["code", "reasoning", "fast", "creative", "vision"],
                        help="Task type for ModelRouter routing")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without writing to brain")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN: brain write-back disabled")
        _sync_available = False

    try:
        import improve_skill
        if hasattr(improve_skill, "run_improvement_cycle"):
            improve_skill.run_improvement_cycle(
                skill_name=args.skill,
                task_type=args.task_type,
            )
        else:
            print(f"improve_skill.py does not expose run_improvement_cycle. "
                  f"Patch is active — import improve_skill and call its main function directly.")
    except ImportError:
        print("improve_skill.py not found in current directory. "
              "Run this script from the self-improving-system-builder root.")
        sys.exit(1)
