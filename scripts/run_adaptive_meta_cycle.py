#!/usr/bin/env python3
"""
run_adaptive_meta_cycle.py

Full adaptive cycle:
  reconcile -> patch -> score -> loop -> classify blockers
  -> approval policy -> split follow-ups -> loop follow-ups
  -> retry strategy -> verify proof -> generate human report

Usage:
  python3 scripts/run_adaptive_meta_cycle.py <case_dir>
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPTS = Path(__file__).resolve().parent


def run(cmd: list, cwd: str | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check, cwd=cwd)


def step(label: str, cmd: list, case_dir: str) -> bool:
    print(f"[adaptive] {label}")
    r = run(cmd, cwd=case_dir)
    if r.returncode != 0:
        print(f"  WARNING ({label}): {r.stderr.strip()[:200]}")
        return False
    return True


def script(name: str) -> str:
    return str(SCRIPTS / name)


def main(case_dir_str: str) -> None:
    case_dir = Path(case_dir_str)
    case_dir.mkdir(parents=True, exist_ok=True)
    cd = str(case_dir)
    q  = str(case_dir / 'action_queue.json')
    ts = datetime.now(timezone.utc).isoformat()

    steps_run = []

    def s(label, cmd):
        ok = step(label, cmd, cd)
        steps_run.append({'label': label, 'ok': ok})
        return ok

    # Core pipeline
    s('reconcile',         ['python3', script('reconcile_with_bundle_forensics.py'),
                             str(case_dir/'claim_map.json'),
                             str(case_dir/'runtime_evidence.json'),
                             str(case_dir/'drift_report.json'), q])
    s('generate_patches',  ['python3', script('generate_patch_from_claim.py'),
                             str(case_dir/'claim_map.json'),
                             str(case_dir/'patch_specs')])
    s('apply_patches',     ['python3', script('auto_patch.py'),
                             str(case_dir/'patch_specs'), cd])
    s('score',             ['python3', script('score_actions.py'), q, q])
    s('loop',              ['python3', script('loop_until_blocked.py'), cd, '25'])
    s('classify_blockers', ['python3', script('blocker_classifier.py'),
                             str(case_dir/'blocked_actions.json'),
                             str(case_dir/'blocker_report.json')])
    s('approval_policy',   ['python3', script('approval_policy.py'),
                             str(case_dir/'blocker_report.json'),
                             str(case_dir/'approval_decisions.json')])
    s('split_risky',       ['python3', script('split_risky_actions.py'),
                             str(case_dir/'blocked_actions.json'),
                             str(case_dir/'blocker_report.json'),
                             str(case_dir/'followup_queue.json')])

    # Merge follow-up queue into main queue if it exists
    followup_path = case_dir / 'followup_queue.json'
    if followup_path.exists():
        try:
            main_q  = json.loads((case_dir / 'action_queue.json').read_text())
            followup = json.loads(followup_path.read_text())
            fu_actions = followup.get('actions', followup if isinstance(followup, list) else [])
            existing_ids = {a['action_id'] for a in main_q.get('actions', [])}
            new_actions = [a for a in fu_actions if a['action_id'] not in existing_ids]
            main_q.setdefault('actions', []).extend(new_actions)
            (case_dir / 'action_queue.json').write_text(json.dumps(main_q, indent=2))
            print(f"[adaptive] Merged {len(new_actions)} follow-up actions into queue")
        except Exception as e:
            print(f"[adaptive] WARNING: could not merge followup queue: {e}")

    s('score_followups',   ['python3', script('score_actions.py'), q, q])
    s('loop_followups',    ['python3', script('loop_until_blocked.py'), cd, '15'])
    s('retry_strategy',    ['python3', script('retry_strategy.py'),
                             str(case_dir/'approval_decisions.json'),
                             str(case_dir/'loop_summary.json'),
                             str(case_dir/'retry_strategy.json')])

    # Proof verification
    proof_checks = case_dir / 'proof_checks.json'
    if proof_checks.exists():
        s('verify_proof',  ['python3', script('verify_proof.py'),
                             str(proof_checks), cd,
                             str(case_dir/'adaptive_proof_report.json')])

    # Generate human-readable report (closes INTERFACE_GAP)
    s('human_report',      ['python3', script('generate_human_report.py'), cd])

    # Write cycle report
    report = {
        'artifact_name': 'adaptive_meta_cycle_report',
        'timestamp': ts,
        'case_dir': cd,
        'steps': steps_run,
        'succeeded': sum(1 for s in steps_run if s['ok']),
        'failed':    sum(1 for s in steps_run if not s['ok']),
    }
    (case_dir / 'adaptive_meta_cycle_report.json').write_text(json.dumps(report, indent=2))
    print(f"[adaptive] Done. {report['succeeded']}/{len(steps_run)} steps succeeded.")
    print(f"[adaptive] Human report -> {case_dir}/REPORT.md")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 run_adaptive_meta_cycle.py <case_dir>')
        sys.exit(1)
    main(sys.argv[1])
