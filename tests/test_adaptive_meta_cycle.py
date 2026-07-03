#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
EXAMPLES = ROOT / 'examples'

def test_approval_policy_and_retry_strategy():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        blocker={'blocked':[
            {'action_id':'B1','classification':'needs_permission','detail':'contradicted cost tracking'},
            {'action_id':'B2','classification':'downgrade_claim_now','detail':'reference-only claim'}
        ]}
        (case/'blocker_report.json').write_text(json.dumps(blocker))
        subprocess.run(['python3',str(SCRIPTS/'approval_policy.py'),str(case/'blocker_report.json'),str(case/'approval_decisions.json')],check=True)
        decisions=json.loads((case/'approval_decisions.json').read_text())
        (case/'loop_summary.json').write_text(json.dumps({'completed':2,'blocked_or_failed':0,'pending':0}))
        subprocess.run(['python3',str(SCRIPTS/'retry_strategy.py'),str(case/'approval_decisions.json'),str(case/'loop_summary.json'),str(case/'retry_strategy.json')],check=True)
        assert len(decisions['decisions'])==2
        assert json.loads((case/'retry_strategy.json').read_text())['strategy']=='reaudit_now'

def test_split_risky_actions():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        blocked=[
            {'action_id':'BFA-001','title':'Blocked reference-only claim','notes':'downgrade production label'},
            {'action_id':'BFA-002','title':'Blocked contradicted cost claim','notes':'risk above auto threshold'}
        ]
        blocker={'blocked':[
            {'action_id':'BFA-001','classification':'downgrade_claim_now','detail':'reference-only claim'},
            {'action_id':'BFA-002','classification':'needs_permission','detail':'contradicted cost claim'}
        ]}
        (case/'blocked_actions.json').write_text(json.dumps(blocked))
        (case/'blocker_report.json').write_text(json.dumps(blocker))
        subprocess.run(['python3',str(SCRIPTS/'split_risky_actions.py'),str(case/'blocked_actions.json'),str(case/'blocker_report.json'),str(case/'followup_queue.json')],check=True)
        assert len(json.loads((case/'followup_queue.json').read_text())['actions'])>=3

def test_run_adaptive_meta_cycle():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        for name in ['claim_map.json','runtime_evidence.json','drift_report.json','proof_checks.json']:
            (case/name).write_text((EXAMPLES/'bundle_forensics_case'/name).read_text())
        subprocess.run(['python3',str(SCRIPTS/'run_adaptive_meta_cycle.py'),str(case)],check=True)
        report=json.loads((case/'adaptive_meta_cycle_report.json').read_text())
        assert report['final_summary']['completed']>=2
        assert (case/'approval_requests'/'BFA-002.md').exists()
        assert (case/'adaptive_proof_report.json').exists()

if __name__=='__main__':
    test_approval_policy_and_retry_strategy(); print('approval_policy + retry PASSED')
    test_split_risky_actions(); print('split_risky_actions PASSED')
    test_run_adaptive_meta_cycle(); print('run_adaptive_meta_cycle PASSED')
