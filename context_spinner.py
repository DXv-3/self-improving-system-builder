#!/usr/bin/env python3
"""
context_spinner.py

Reads a project context (from stdin, file, or inline) and generates:
  1. The unasked questions specific to that context
  2. Custom spin-up actions derived from those questions
  3. Applies the enforcement prompt to each action
  4. Produces an action_queue.json ready for loop_until_blocked.py

Usage:
  python3 context_spinner.py --context context.md
  python3 context_spinner.py --inline "I am building X that does Y"
  cat context.md | python3 context_spinner.py
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from datetime import datetime, timezone

BLIND_SPOT_PATTERNS = [
    {
        "id": "IGNITION_GAP",
        "trigger_keywords": ["loop", "cycle", "run", "execute", "schedule"],
        "question": "Who re-runs this system? Is there a scheduler, trigger, or event?",
        "spin_up_title": "Add ignition layer — define what fires the next cycle",
        "spin_up_type": "file_write",
        "spin_up_path": "ignition/trigger_spec.md",
        "spin_up_content": lambda ctx: f"""# Ignition Layer Spec\n\n## Context\n{ctx[:200]}...\n\n## Unresolved Question\nWho or what causes the next execution cycle to fire?\n\n## Options to Evaluate\n- [ ] Cron job / system scheduler\n- [ ] File watcher (watchdog on case_dir)\n- [ ] HTTP endpoint trigger\n- [ ] Post-commit git hook\n- [ ] Manual only (document this explicitly as a limitation)\n\n## Decision Required\nChoose one option above and implement it.\nRisk if unresolved: System is self-improving only when manually triggered.\n""",
        "risk_level": 2,
        "priority": 9,
    },
    {
        "id": "MEMORY_GAP",
        "trigger_keywords": ["improve", "learn", "better", "iterate", "cycle", "run"],
        "question": "What is being learned and where is it stored across runs?",
        "spin_up_title": "Scaffold learning_memory.py — cross-run knowledge persistence",
        "spin_up_type": "file_write",
        "spin_up_path": "scripts/learning_memory.py",
        "spin_up_content": lambda ctx: '#!/usr/bin/env python3\n"""\nlearning_memory.py SCAFFOLD\nPersist cross-run lessons so cycle N+1 starts smarter than cycle N.\n"""\nfrom __future__ import annotations\nimport json\nfrom pathlib import Path\nfrom datetime import datetime, timezone\n\nMEMORY_FILE = Path("learning_memory.jsonl")\n\ndef record_cycle_outcome(cycle_id, blocker_patterns, successful_followup_types,\n                         approval_outcomes, retry_strategy, claim_resolutions):\n    record = {"cycle_id": cycle_id, "timestamp": datetime.now(timezone.utc).isoformat(),\n              "blocker_patterns": blocker_patterns,\n              "successful_followup_types": successful_followup_types,\n              "approval_outcomes": approval_outcomes,\n              "retry_strategy": retry_strategy,\n              "claim_resolutions": claim_resolutions}\n    with MEMORY_FILE.open("a") as f: f.write(json.dumps(record) + "\\n")\n\ndef load_lessons():\n    if not MEMORY_FILE.exists(): return []\n    return [json.loads(l) for l in MEMORY_FILE.read_text().splitlines() if l.strip()]\n\ndef get_risk_adjustment(action_category):\n    """TODO: implement trust_update logic. Returns 0 until trust_update.py built."""\n    return 0.0\n',
        "risk_level": 2,
        "priority": 9,
    },
    {
        "id": "PROOF_GAP",
        "trigger_keywords": ["test", "verify", "proof", "check", "validate", "assert"],
        "question": "Does a proof_checks.json exist and can it actually produce False?",
        "spin_up_title": "Audit proof gates — verify each gate can fail",
        "spin_up_type": "file_write",
        "spin_up_path": "proof_gate_audit.md",
        "spin_up_content": lambda ctx: f"""# Proof Gate Audit\n\n## Context\n{ctx[:200]}...\n\n## Audit Checklist\nFor each proof check, verify:\n  [ ] check_id is unique and descriptive\n  [ ] kind is one of: file_exists | text_contains | json_field_equals | command_exit_zero\n  [ ] The check CAN FAIL\n  [ ] The check verifies the claim it is named after\n\n## Common Fake Gates\n  - file_exists on a file always created by setup\n  - text_contains on a hardcoded string\n  - command_exit_zero on python3 -c print(1)\n  - json_field_equals where the field is set by the same script\n\n## Action\nReview proof_checks.json. Delete or replace any gate that cannot fail.\n""",
        "risk_level": 1,
        "priority": 8,
    },
    {
        "id": "OPTIONALITY_TRAP",
        "trigger_keywords": ["feature", "add", "extend", "also", "could", "might", "plan"],
        "question": "Is more infrastructure being built instead of shipping to a user?",
        "spin_up_title": "Define smallest shippable unit — what can a non-engineer use today?",
        "spin_up_type": "file_write",
        "spin_up_path": "minimum_shippable_unit.md",
        "spin_up_content": lambda ctx: f"""# Minimum Shippable Unit\n\n## Context\n{ctx[:200]}...\n\n## The Question\nWhat is the smallest version a non-engineer can:\n  - Run without reading code\n  - Understand the output of\n  - Trust the results of\n  - Pay for or use repeatedly\n\n## Ship Criteria\n  [ ] One command starts it\n  [ ] Output is human-readable without knowing the schema\n  [ ] Failure is in plain language, not stack traces\n  [ ] README followable in under 5 minutes\n\n## Next Action\nStrip everything not required for the above. Ship what remains.\n""",
        "risk_level": 1,
        "priority": 10,
    },
    {
        "id": "INTERFACE_GAP",
        "trigger_keywords": ["user", "run", "output", "report", "result", "show"],
        "question": "What does a non-engineer touch, see, and trust in this system?",
        "spin_up_title": "Design human interface layer — the non-engineer entry point",
        "spin_up_type": "file_write",
        "spin_up_path": "interface_layer/spec.md",
        "spin_up_content": lambda ctx: f"""# Interface Layer Spec\n\n## Context\n{ctx[:200]}...\n\n## Current State\nEverything is a developer tool: CLI scripts, raw JSON, GitHub repos.\n\n## Minimal Implementation Options\n  Option A: generate_human_report.py\n    Read loop_summary.json + next_blockers.md -> REPORT.md\n  Option B: serve.py\n    Flask endpoint serving progress_snapshot.md as HTML\n  Option C: Slack/email digest\n    Post loop_summary to webhook after each cycle\n\n## Decision Required\nChoose one and implement before calling this system usable.\n""",
        "risk_level": 2,
        "priority": 8,
    },
    {
        "id": "CALIBRATION_GAP",
        "trigger_keywords": ["risk", "score", "threshold", "weight", "priority"],
        "question": "Are risk thresholds and scoring weights calibrated against outcomes or guessed?",
        "spin_up_title": "Document and calibrate all magic numbers",
        "spin_up_type": "file_write",
        "spin_up_path": "calibration/magic_numbers.md",
        "spin_up_content": lambda ctx: """# Magic Number Registry\n\n| Number | Location | Purpose | Chosen How | Status |\n|--------|----------|---------|------------|--------|\n| 4 | execute_next.py THRESHOLD | Auto-execute threshold | Arbitrary | UNCALIBRATED |\n| 2 | loop_until_blocked.py | Consecutive failure limit | Arbitrary | UNCALIBRATED |\n| 25 | loop_until_blocked.py | Max loop iterations | Arbitrary | UNCALIBRATED |\n| 3 | score_actions.py | Dependency penalty multiplier | Arbitrary | UNCALIBRATED |\n\n## Calibration Method\nAfter 10+ cycles, adjust thresholds based on empirical outcomes.\nImplement in trust_update.py.\n""",
        "risk_level": 1,
        "priority": 7,
    },
    {
        "id": "SKILL_GENERALIZATION_GAP",
        "trigger_keywords": ["skill", "extract", "reuse", "pattern", "generalize"],
        "question": "Has the skill been tested on a different conversation to verify it generalizes?",
        "spin_up_title": "Create skill generalization test scaffold",
        "spin_up_type": "file_write",
        "spin_up_path": "tests/test_skill_generalization.py",
        "spin_up_content": lambda ctx: '#!/usr/bin/env python3\n"""\ntest_skill_generalization.py SCAFFOLD\nTests that conversation-to-system-extractor produces consistent quality\nwhen applied to a conversation other than the one it was extracted from.\n"""\nDIFFERENT_CONVERSATION = """\n[INSERT: A completely different conversation transcript here.\nNot the self-improving-system conversation.]\n"""\n\ndef test_extractor_produces_skill_from_different_conversation():\n    required_sections = ["name:", "version:", "description:", "core_thesis:",\n                         "when_to_use:", "inputs:", "outputs:",\n                         "mistakes_to_avoid:", "hard_stop_conditions:"]\n    assert DIFFERENT_CONVERSATION.strip() != "", "Insert real conversation first"\n    assert True, "SCAFFOLD: implement extractor CLI then wire here"\n\nif __name__ == "__main__":\n    test_extractor_produces_skill_from_different_conversation()\n    print("SCAFFOLD registered")\n',
        "risk_level": 1,
        "priority": 7,
    },
]


def detect_blind_spots(context: str) -> list[dict]:
    context_lower = context.lower()
    triggered = []
    for pattern in BLIND_SPOT_PATTERNS:
        if any(kw in context_lower for kw in pattern["trigger_keywords"]):
            triggered.append(pattern)
    ids = {p["id"] for p in triggered}
    for must_include in ["OPTIONALITY_TRAP", "MEMORY_GAP"]:
        if must_include not in ids:
            triggered.append(next(p for p in BLIND_SPOT_PATTERNS if p["id"] == must_include))
    return triggered


def build_enforcement_action() -> dict:
    return {
        "action_id": "SPINNER-000-ENFORCEMENT",
        "title": "Write enforcement prompt marker to case dir",
        "source": "context_spinner:enforcement",
        "category": "integration",
        "priority": 10, "leverage_score": 5, "unblock_power": 5,
        "proof_value": 4, "reuse_value": 5, "risk_level": 1,
        "dependencies": [], "executable_now": True, "execution_type": "file_write",
        "command_or_patch": "ENFORCEMENT_PROMPT.md::# Enforcement Prompt Active\n\nSELF-IMPROVING SYSTEM BUILDER ENFORCEMENT PROMPT v1.0 is active.\nSee ENFORCEMENT_PROMPT.md in repo root for full rules.\n",
        "proof_of_done": "ENFORCEMENT_PROMPT.md exists",
        "rollback": "delete ENFORCEMENT_PROMPT.md",
        "status": "pending",
        "notes": "Enforcement prompt marker. Confirms rules are active for this session.",
    }


def build_action(pattern: dict, context: str, idx: int) -> dict:
    content = pattern["spin_up_content"](context)
    return {
        "action_id": f"SPINNER-{idx:03d}-{pattern['id']}",
        "title": pattern["spin_up_title"],
        "source": f"context_spinner:{pattern['id']}",
        "category": "integration",
        "priority": pattern["priority"],
        "leverage_score": 4, "unblock_power": 5, "proof_value": 3, "reuse_value": 5,
        "risk_level": pattern["risk_level"],
        "dependencies": [], "executable_now": True,
        "execution_type": pattern["spin_up_type"],
        "command_or_patch": f"{pattern['spin_up_path']}::{content}",
        "proof_of_done": f"{pattern['spin_up_path']} exists",
        "rollback": f"delete {pattern['spin_up_path']}",
        "status": "pending",
        "notes": f"Blind spot: {pattern['id']}. Unasked question: {pattern['question']}",
    }


def spin(context: str, out_path: str | None = None) -> dict:
    patterns = detect_blind_spots(context)
    actions = [build_enforcement_action()]
    for idx, pattern in enumerate(patterns, start=1):
        actions.append(build_action(pattern, context, idx))
    queue = {
        "artifact_name": "context_spinner_output",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "context_summary": context[:300] + "..." if len(context) > 300 else context,
        "blind_spots_detected": [p["id"] for p in patterns],
        "enforcement_active": True,
        "actions": actions,
    }
    output = json.dumps(queue, indent=2)
    if out_path:
        Path(out_path).write_text(output)
        print(f"Written to {out_path}")
    else:
        print(output)
    return queue


def main():
    parser = argparse.ArgumentParser(
        description="Spin up custom unasked actions from project context."
    )
    parser.add_argument("--context", type=str)
    parser.add_argument("--inline", type=str)
    parser.add_argument("--out", type=str, default="action_queue.json")
    args = parser.parse_args()
    if args.inline:
        context = args.inline
    elif args.context:
        context = Path(args.context).read_text()
    elif not sys.stdin.isatty():
        context = sys.stdin.read()
    else:
        parser.print_help(); sys.exit(1)
    spin(context, args.out)


if __name__ == "__main__":
    main()
