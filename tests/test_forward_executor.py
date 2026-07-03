#!/usr/bin/env python3
import json, subprocess, tempfile, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'

def test_end_to_end_loop_runs():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        claim_map={'artifact_name':'demo.md','claims':[
            {'claim_id':'CLAIM-001','text':'safe file create','category':'integration','required_for_production':True,'evidence_class':'unverified','notes':'demo'},
            {'claim_id':'CLAIM-002','text':'manual risky step','category':'cost_control','required_for_production':True,'evidence_class':'contradicted','notes':'demo'}
        ]}
        (case/'claim_map.json').write_text(json.dumps(claim_map))
        subprocess.run(['python3',str(SCRIPTS/'ingest_findings.py'),str(case/'claim_map.json'),str(case/'action_queue.json')],check=True)
        q=json.loads((case/'action_queue.json').read_text())
        q['actions'][0].update({'execution_type':'file_write','command_or_patch':'made.txt::ok','risk_level':1})
        q['actions'][1].update({'execution_type':'manual','risk_level':8})
        (case/'action_queue.json').write_text(json.dumps(q))
        subprocess.run(['python3',str(SCRIPTS/'loop_until_blocked.py'),str(case),'5'],check=True)
        summary=json.loads((case/'loop_summary.json').read_text())
        assert summary['completed']>=1
        assert (case/'made.txt').exists()

if __name__=='__main__':
    test_end_to_end_loop_runs()
    print('test_end_to_end_loop_runs PASSED')
