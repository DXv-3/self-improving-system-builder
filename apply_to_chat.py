#!/usr/bin/env python3
"""
apply_to_chat.py

Takes any context (conversation, audit, README, description) and:
  1. Runs context_spinner to detect blind spots and generate actions
  2. Scores the action queue
  3. Activates the enforcement prompt in the case dir
  4. Runs the full adaptive meta-cycle
  5. Emits a human-readable enforcement report

Usage:
  python3 apply_to_chat.py --context my_project_context.md --case-dir ./my_case
  python3 apply_to_chat.py --inline "I am building X" --case-dir ./my_case
  python3 apply_to_chat.py --self   # applies to this repo's own context
"""

from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, check=check, capture_output=True, text=True, cwd=cwd)


def write_enforcement_marker(case_dir: Path):
    (case_dir / "enforcement_active.json").write_text(json.dumps({
        "version": "1.0.0", "active": True,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "rules": {
            "evidence_classification": "required_on_all_claims",
            "idkwidk_gates": "required_before_completion",
            "auto_execute_threshold": 4,
            "no_recommendations_without_implementation": True,
            "roadmap_required": True,
            "github_push_required": True,
            "loop_termination": "only_when_no_honest_next_move_exists",
        },
        "blind_spot_checks": [
            "IGNITION_GAP", "MEMORY_GAP", "PROOF_GAP",
            "OPTIONALITY_TRAP", "INTERFACE_GAP",
            "CALIBRATION_GAP", "SKILL_GENERALIZATION_GAP",
        ],
    }, indent=2))


def self_context() -> str:
    parts = []
    for p in [ROOT / "README.md", ROOT / "ROADMAP_UNBUILT_BUT_DISCUSSED.md"]:
        if p.exists(): parts.append(p.read_text()[:1500])
    if SCRIPTS.exists():
        parts.append("\n\n--- SCRIPTS ---\n" + "\n".join(p.name for p in SCRIPTS.glob("*.py")))
    skills_dir = ROOT / "skills"
    if skills_dir.exists():
        parts.append("\n\n--- SKILLS ---\n" + "\n".join(p.name for p in skills_dir.glob("*.md")))
    return "\n".join(parts)


def generate_stubs(case_dir: Path, queue: dict):
    stubs = {
        "claim_map.json": json.dumps({
            "artifact_name": queue.get("artifact_name", "spinner_context"),
            "claims": [
                {"claim_id": f"SPIN-{i:03d}", "text": a["title"],
                 "category": a.get("category", "integration"),
                 "required_for_production": True, "evidence_class": "unverified",
                 "notes": a.get("notes", "")}
                for i, a in enumerate(queue["actions"], 1)
            ]
        }, indent=2),
        "runtime_evidence.json": json.dumps(
            {"artifact_name": "spinner_context", "evidence_items": []}, indent=2),
        "drift_report.json": json.dumps({
            "artifact_name": "spinner_context",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "drift_count": len(queue["actions"]),
            "items": [f"{a['action_id']} unverified" for a in queue["actions"]],
            "verdict": "HOLD"
        }, indent=2),
        "proof_checks.json": json.dumps({"checks": [
            {"check_id": "ENFORCE-01", "kind": "file_exists", "path": "enforcement_active.json"},
            {"check_id": "ENFORCE-02", "kind": "file_exists", "path": "ENFORCEMENT_PROMPT.md"},
        ]}, indent=2),
    }
    for name, content in stubs.items():
        p = case_dir / name
        if not p.exists():
            p.write_text(content)
            print(f"[stub] Created {name}")


def generate_report(case_dir: Path) -> str:
    lines = ["# Enforcement Apply Report", f"Generated: {datetime.now().isoformat()}", ""]

    for path, label in [
        (case_dir / "loop_summary.json", "## Execution Summary"),
    ]:
        if path.exists():
            s = json.loads(path.read_text())
            lines += [label,
                      f"- Steps: {s.get('steps_executed','?')}",
                      f"- Completed: {s.get('completed','?')}",
                      f"- Blocked/Failed: {s.get('blocked_or_failed','?')}",
                      f"- Pending: {s.get('pending','?')}", ""]

    if (case_dir / "retry_strategy.json").exists():
        r = json.loads((case_dir / "retry_strategy.json").read_text())
        lines += ["## Retry Strategy", f"- **{r.get('strategy','?')}**", ""]

    if (case_dir / "next_blockers.md").exists():
        lines += ["## Active Blockers", (case_dir / "next_blockers.md").read_text(), ""]

    proof = case_dir / "adaptive_proof_report.json"
    if proof.exists():
        p = json.loads(proof.read_text())
        status = "ALL PASSED" if p.get("all_passed") else "SOME FAILED"
        lines += [f"## Proof Status: {status}"]
        for r in p.get("results", []):
            lines.append(f"- {'PASS' if r['passed'] else 'FAIL'} {r['check_id']}")
        lines.append("")

    lines += [
        "## IDKWIDK Gates (complete before marking done)",
        "- [ ] WHAT WE BUILT: exact artifacts + commit SHA",
        "- [ ] WHAT WE DID NOT BUILD: by name",
        "- [ ] WHAT WILL BREAK: top 3 failure modes",
        "- [ ] WHAT WE DO NOT KNOW: deferred decisions",
        "- [ ] DEPENDENCY RISKS: external requirements",
        "- [ ] WHAT TO TEST NEXT: specific test names",
        "- [ ] PRE-MORTEM: 5 causes x (kill criterion + early warning)",
        "",
        "---",
        "_Generated by apply_to_chat.py under Enforcement Prompt v1.0_",
    ]

    report = "\n".join(lines)
    (case_dir / "ENFORCEMENT_APPLY_REPORT.md").write_text(report)
    return report


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--context", type=str)
    group.add_argument("--inline", type=str)
    group.add_argument("--self", action="store_true")
    parser.add_argument("--case-dir", type=str, default="./spinner_case")
    parser.add_argument("--skip-cycle", action="store_true")
    args = parser.parse_args()

    case_dir = Path(args.case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    if args.self:
        context = self_context()
        print(f"[context] Using self-context ({len(context)} chars)")
    elif args.inline:
        context = args.inline
    else:
        context = Path(args.context).read_text()

    (case_dir / "context.md").write_text(context)
    write_enforcement_marker(case_dir)
    print("[enforcement] Marker written -> enforcement_active.json")

    spinner = ROOT / "context_spinner.py"
    run(["python3", str(spinner), "--context", str(case_dir / "context.md"),
         "--out", str(case_dir / "action_queue.json")])
    queue = json.loads((case_dir / "action_queue.json").read_text())
    blind_spots = queue.get("blind_spots_detected", [])
    print(f"[spinner] {len(blind_spots)} blind spots: {', '.join(blind_spots)}")
    print(f"[spinner] {len(queue['actions'])} actions -> action_queue.json")

    if args.skip_cycle:
        print("[skip] Queue written. Run loop_until_blocked.py manually.")
        return

    run(["python3", str(SCRIPTS / "score_actions.py"),
         str(case_dir / "action_queue.json"), str(case_dir / "action_queue.json")])
    print("[score] Actions scored")

    generate_stubs(case_dir, queue)
    shutil.copy2(case_dir / "action_queue.json", case_dir / "action_queue.spinner.json")

    try:
        run(["python3", str(SCRIPTS / "run_adaptive_meta_cycle.py"), str(case_dir)])
        print("[cycle] Adaptive meta-cycle complete")
    except subprocess.CalledProcessError:
        shutil.copy2(case_dir / "action_queue.spinner.json", case_dir / "action_queue.json")
        run(["python3", str(SCRIPTS / "loop_until_blocked.py"), str(case_dir), "20"])
        print("[cycle] Fallback loop complete")

    report = generate_report(case_dir)
    print("\n" + "=" * 70)
    print(report)
    print("=" * 70)
    print(f"\n[done] Report -> {case_dir}/ENFORCEMENT_APPLY_REPORT.md")


if __name__ == "__main__":
    main()
