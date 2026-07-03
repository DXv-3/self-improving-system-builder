#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, subprocess, sys
from pathlib import Path

def run(cmd):
    return subprocess.run(cmd,check=True,capture_output=True,text=True)

def main(case_dir):
    case=Path(case_dir)
    scripts=str(Path(__file__).resolve().parent)
    report={'case_dir':str(case),'steps':[]}
    run(['python3',f'{scripts}/run_full_meta_cycle.py',str(case)])
    report['steps'].append('run_full_meta_cycle')
    report['initial_report']=json.loads((case/'full_meta_cycle_report.json').read_text())
    blocker_report=case/'blocker_report.json'
    if blocker_report.exists():
        run(['python3',f'{scripts}/approval_policy.py',str(blocker_report),str(case/'approval_decisions.json')])
        report['steps'].append('approval_policy')
        run(['python3',f'{scripts}/split_risky_actions.py',str(case/'blocked_actions.json'),str(blocker_report),str(case/'followup_queue.json')])
        report['steps'].append('split_risky_actions')
        queue=case/'action_queue.json'
        if queue.exists() and not (case/'action_queue.initial.json').exists():
            shutil.copy2(queue,case/'action_queue.initial.json')
        shutil.copy2(case/'followup_queue.json',queue)
        run(['python3',f'{scripts}/score_actions.py',str(queue),str(queue)]); report['steps'].append('score_actions_followups')
        run(['python3',f'{scripts}/loop_until_blocked.py',str(case),'10']); report['steps'].append('loop_until_blocked_followups')
        run(['python3',f'{scripts}/retry_strategy.py',str(case/'approval_decisions.json'),str(case/'loop_summary.json'),str(case/'retry_strategy.json')])
        report['steps'].append('retry_strategy')
        report['approval_decisions']=json.loads((case/'approval_decisions.json').read_text())
        report['retry_strategy']=json.loads((case/'retry_strategy.json').read_text())
    if (case/'proof_checks.json').exists():
        run(['python3',f'{scripts}/verify_proof.py',str(case/'proof_checks.json'),str(case),str(case/'adaptive_proof_report.json')])
        report['steps'].append('verify_proof')
        report['adaptive_proof_report']=json.loads((case/'adaptive_proof_report.json').read_text())
    report['final_summary']=json.loads((case/'loop_summary.json').read_text())
    (case/'adaptive_meta_cycle_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main(sys.argv[1])
