#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

def run(cmd):
    return subprocess.run(cmd,check=True,capture_output=True,text=True)

def main(case_dir):
    case=Path(case_dir)
    scripts=str(Path(__file__).resolve().parent)
    report={'case_dir':str(case),'steps':[]}
    queue=str(case/'action_queue.json')
    run(['python3',f'{scripts}/reconcile_with_bundle_forensics.py',str(case/'claim_map.json'),str(case/'runtime_evidence.json'),str(case/'drift_report.json'),queue])
    report['steps'].append('reconcile_with_bundle_forensics')
    run(['python3',f'{scripts}/generate_patch_from_claim.py',str(case/'claim_map.json'),str(case/'patch_specs')])
    report['steps'].append('generate_patch_from_claim')
    patch_index=json.loads((case/'patch_specs'/'patch_index.json').read_text())
    applied=[]
    for item in patch_index.get('patches',[]):
        run(['python3',f'{scripts}/auto_patch.py',item['patch_spec'],str(case)]); applied.append(Path(item['patch_spec']).name)
    if applied: report['applied_patches']=applied; report['steps'].append('auto_patch')
    run(['python3',f'{scripts}/score_actions.py',queue,queue]); report['steps'].append('score_actions')
    run(['python3',f'{scripts}/loop_until_blocked.py',str(case),'10']); report['steps'].append('loop_until_blocked')
    if (case/'blocked_actions.json').exists():
        run(['python3',f'{scripts}/blocker_classifier.py',str(case/'blocked_actions.json'),str(case/'blocker_report.json')])
        report['steps'].append('blocker_classifier')
        report['blocker_report']=json.loads((case/'blocker_report.json').read_text())
    if (case/'proof_checks.json').exists():
        run(['python3',f'{scripts}/verify_proof.py',str(case/'proof_checks.json'),str(case),str(case/'proof_report.json')])
        report['steps'].append('verify_proof')
        report['proof_report']=json.loads((case/'proof_report.json').read_text())
    report['summary']=json.loads((case/'loop_summary.json').read_text())
    (case/'full_meta_cycle_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main(sys.argv[1])
