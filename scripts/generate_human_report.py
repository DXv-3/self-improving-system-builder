#!/usr/bin/env python3
"""
generate_human_report.py

Closes the INTERFACE_GAP.
Reads loop artifacts and produces REPORT.md in plain English.
A non-engineer can read this output without knowing any JSON schema.

Usage:
  python3 scripts/generate_human_report.py <case_dir>
  python3 scripts/generate_human_report.py <case_dir> --out custom_report.md
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from datetime import datetime


def safe_load(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def format_action_list(actions: list[dict], verb: str) -> list[str]:
    if not actions:
        return [f"  (nothing {verb})"]
    return [f"  - {a.get('title', a.get('action_id', '?'))}" for a in actions]


def plain_retry(strategy: str) -> str:
    mapping = {
        "reaudit_now":                "Everything completed successfully. Re-check all claims against current state.",
        "apply_downgrades_and_reaudit": "Some unverified claims were safely downgraded. Re-run to resolve the rest.",
        "await_approval_then_rerun":  "Waiting for human approval on one or more blocked actions. Review and approve, then re-run.",
        "acquire_resources_then_rerun": "Missing external resources (credentials, dependencies). Acquire them, then re-run.",
        "perform_design_review":      "Some decisions need human input. Review the design_decisions/ folder, then re-run.",
    }
    return mapping.get(strategy, f"Strategy: {strategy}")


def plain_blocker(label: str) -> str:
    mapping = {
        "needs_permission":         "Needs human approval before it can run.",
        "needs_external_resource":  "Needs an external resource (credential, dependency, or network access).",
        "needs_safe_patch":         "Needs a code patch to fix a contradicted or reference-only claim.",
        "downgrade_claim_now":      "This claim's production label needs to be downgraded to match the evidence.",
        "needs_design_decision":    "Needs a design decision before it can proceed.",
    }
    return mapping.get(label, f"Blocked: {label}")


def generate(case_dir: Path, out_path: Path) -> str:
    loop   = safe_load(case_dir / 'loop_summary.json') or {}
    retry  = safe_load(case_dir / 'retry_strategy.json') or {}
    proof  = safe_load(case_dir / 'adaptive_proof_report.json') or \
             safe_load(case_dir / 'proof_report.json') or {}
    blocker_report = safe_load(case_dir / 'blocker_report.json') or {}
    completed_raw  = safe_load(case_dir / 'completed_actions.json') or []
    blocked_raw    = safe_load(case_dir / 'blocked_actions.json') or []
    roadmap        = (case_dir / 'ROADMAP_UNBUILT_BUT_DISCUSSED.md')
    enforcement    = safe_load(case_dir / 'enforcement_active.json') or {}

    completed = completed_raw if isinstance(completed_raw, list) else completed_raw.get('actions', [])
    blocked   = blocked_raw   if isinstance(blocked_raw,   list) else blocked_raw.get('actions',   [])

    lines = [
        "# System Run Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Case: {case_dir.resolve()}",
        "",
    ]

    # Enforcement status
    if enforcement.get('active'):
        lines += ["**Enforcement Prompt:** Active (v" + enforcement.get('version', '?') + ")", ""]
    else:
        lines += ["**Enforcement Prompt:** NOT ACTIVE — run apply_to_chat.py first", ""]

    # What happened
    lines += [
        "## What Happened",
        f"{loop.get('steps_executed', '?')} steps executed. "
        f"{loop.get('completed', len(completed))} actions completed. "
        f"{loop.get('blocked_or_failed', len(blocked))} blocked or failed.",
        "",
    ]

    # What was built
    lines += ["## What Was Built"]
    lines += format_action_list(completed, 'completed')
    lines += [""]

    # What is blocked
    if blocked:
        lines += ["## What Is Blocked"]
        classified = blocker_report.get('blockers', [])
        classified_map = {b.get('action_id'): b for b in classified}
        for b in blocked:
            aid   = b.get('action_id', '?')
            title = b.get('title', aid)
            label = classified_map.get(aid, {}).get('label', b.get('blocker_label', 'unknown'))
            reason = plain_blocker(label)
            lines.append(f"  - **{title}**")
            lines.append(f"    Reason: {reason}")
        lines += [""]

    # Proof status
    if proof:
        results = proof.get('results', [])
        passed  = sum(1 for r in results if r.get('passed'))
        total   = len(results)
        status  = "ALL PASSED" if proof.get('all_passed') else f"{passed}/{total} passed"
        lines += [f"## Proof Status: {status}"]
        for r in results:
            icon = "PASS" if r.get('passed') else "FAIL"
            lines.append(f"  - [{icon}] {r.get('check_id', '?')}")
        lines += [""]

    # What to do next
    strategy = retry.get('strategy', '')
    if strategy:
        lines += [
            "## What To Do Next",
            plain_retry(strategy),
            "",
        ]

    # IDKWIDK checklist
    lines += [
        "## Before Marking This Done",
        "Check each item. Do not mark complete until all are answered specifically.",
        "- [ ] WHAT WE BUILT: list exact file names and commit SHA",
        "- [ ] WHAT WE DID NOT BUILD: list by name",
        "- [ ] WHAT WILL BREAK: top 3 failure modes with specifics",
        "- [ ] WHAT WE DO NOT KNOW: deferred decisions and magic numbers",
        "- [ ] DEPENDENCY RISKS: external requirements with versions",
        "- [ ] WHAT TO TEST NEXT: specific test names",
        "- [ ] PRE-MORTEM: 5 causes x (kill criterion + early warning)",
        "",
    ]

    # Roadmap
    if roadmap.exists():
        lines += [
            "## What Was Not Built (Roadmap)",
            roadmap.read_text().strip()[:2000],
            "",
        ]

    lines += ["---", "_Generated by generate_human_report.py_"]

    report = "\n".join(lines)
    out_path.write_text(report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case_dir')
    parser.add_argument('--out', default=None)
    args = parser.parse_args()

    case_dir = Path(args.case_dir)
    out_path = Path(args.out) if args.out else case_dir / 'REPORT.md'

    if not case_dir.exists():
        print(f'Error: {case_dir} does not exist'); sys.exit(1)

    report = generate(case_dir, out_path)
    print(report)
    print(f"\nReport written -> {out_path}")


if __name__ == '__main__':
    main()
