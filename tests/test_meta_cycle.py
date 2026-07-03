#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
EXAMPLES = ROOT / 'examples'

def test_blocker_classifier():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        blocked=[
            {'action_id':'A1','title':'Manual risky step','notes':'risk above auto threshold'},
            {'action_id':'A2','title':'Downgrade label','notes':'reference-only claim; downgrade production label'}
        ]
        src=case/'blocked_actions.json'; out=case/'blocker_report.json'
        src.write_text(json.dumps(blocked))
        subprocess.run(['python3',str(SCRIPTS/'blocker_classifier.py'),str(src),str(out)],check=True)
        labels={x['action_id']:x['classification'] for x in json.loads(out.read_text())['blocked']}
        assert labels['A1']=='needs_permission'
        assert labels['A2']=='downgrade_claim_now'

def test_generate_patch_from_claim():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        claim_map={'artifact_name':'demo.md','claims':[
            {'claim_id':'CLAIM-001','category':'proof_gate','required_for_production':True,'evidence_class':'unverified'},
            {'claim_id':'CLAIM-002','category':'cost_control','required_for_production':True,'evidence_class':'contradicted'}
        ]}
        src=case/'claim_map.json'; out=case/'patch_specs'
        src.write_text(json.dumps(claim_map))
        subprocess.run(['python3',str(SCRIPTS/'generate_patch_from_claim.py'),str(src),str(out)],check=True)
        assert len(json.loads((out/'patch_index.json').read_text())['patches'])==2

def test_run_full_meta_cycle():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        for name in ['claim_map.json','runtime_evidence.json','drift_report.json','proof_checks.json']:
            (case/name).write_text((EXAMPLES/'bundle_forensics_case'/name).read_text())
        subprocess.run(['python3',str(SCRIPTS/'run_full_meta_cycle.py'),str(case)],check=True)
        report=json.loads((case/'full_meta_cycle_report.json').read_text())
        assert report['summary']['completed']>=1
        assert report['proof_report']['all_passed'] is True
        assert (case/'proof_runtime.json').exists()

if __name__=='__main__':
    test_blocker_classifier(); print('blocker_classifier PASSED')
    test_generate_patch_from_claim(); print('generate_patch PASSED')
    test_run_full_meta_cycle(); print('run_full_meta_cycle PASSED')
