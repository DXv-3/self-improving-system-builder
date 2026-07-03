#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

def run(cmd):
    return subprocess.run(cmd,check=True,capture_output=True,text=True)

def main(case_dir, mode='bundle_forensics'):
    case=Path(case_dir)
    scripts=str(Path(__file__).resolve().parent)
    report={'mode':mode,'case_dir':str(case),'steps':[]}
    queue=str(case/'action_queue.json')
    if mode=='bundle_forensics':
        run(['python3',f'{scripts}/reconcile_with_bundle_forensics.py',str(case/'claim_map.json'),str(case/'runtime_evidence.json'),str(case/'drift_report.json'),queue])
        report['steps'].append('reconcile_with_bundle_forensics')
    elif mode=='router_handoff':
        run(['python3',f'{scripts}/import_router_handoff.py',str(case/'router_handoff.json'),queue])
        report['steps'].append('import_router_handoff')
    else: raise ValueError(f'Unknown mode: {mode}')
    run(['python3',f'{scripts}/score_actions.py',queue,queue]); report['steps'].append('score_actions')
    run(['python3',f'{scripts}/loop_until_blocked.py',str(case),'10']); report['steps'].append('loop_until_blocked')
    report['summary']=json.loads((case/'loop_summary.json').read_text())
    if (case/'proof_checks.json').exists():
        run(['python3',f'{scripts}/verify_proof.py',str(case/'proof_checks.json'),str(case),str(case/'proof_report.json')])
        report['steps'].append('verify_proof')
        report['proof_report']=json.loads((case/'proof_report.json').read_text())
    (case/'system_cycle_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'bundle_forensics')
