#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
EXAMPLES = ROOT / 'examples'

def test_verify_proof_checks_pass():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        (case/'alpha.txt').write_text('hello world')
        (case/'data.json').write_text(json.dumps({'ok':True,'nested':{'value':7}}))
        checks={'checks':[
            {'check_id':'C1','kind':'file_exists','path':'alpha.txt'},
            {'check_id':'C2','kind':'text_contains','path':'alpha.txt','needle':'world'},
            {'check_id':'C3','kind':'json_field_equals','path':'data.json','json_path':['nested','value'],'expected':7},
            {'check_id':'C4','kind':'command_exit_zero','command':'python3 -c "print(1)"'}
        ]}
        (case/'proof_checks.json').write_text(json.dumps(checks))
        out=case/'proof_report.json'
        subprocess.run(['python3',str(SCRIPTS/'verify_proof.py'),str(case/'proof_checks.json'),str(case),str(out)],check=True)
        assert json.loads(out.read_text())['all_passed'] is True

def test_run_system_cycle_bundle_forensics():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        for name in ['claim_map.json','runtime_evidence.json','drift_report.json']:
            (case/name).write_text((EXAMPLES/'bundle_forensics_case'/name).read_text())
        (case/'proof_checks.json').write_text(json.dumps({'checks':[{'check_id':'P1','kind':'file_exists','path':'proof_runtime.json'}]}))
        subprocess.run(['python3',str(SCRIPTS/'run_system_cycle.py'),str(case),'bundle_forensics'],check=True)
        report=json.loads((case/'system_cycle_report.json').read_text())
        assert report['summary']['completed']>=1
        assert report['proof_report']['all_passed'] is True

def test_auto_patch_write_and_replace():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        s1=case/'p1.json'; s2=case/'p2.json'
        s1.write_text(json.dumps({'operation':'write','path':'notes.txt','content':'alpha beta'}))
        s2.write_text(json.dumps({'operation':'replace','path':'notes.txt','old':'beta','new':'gamma'}))
        subprocess.run(['python3',str(SCRIPTS/'auto_patch.py'),str(s1),str(case)],check=True)
        subprocess.run(['python3',str(SCRIPTS/'auto_patch.py'),str(s2),str(case)],check=True)
        assert (case/'notes.txt').read_text()=='alpha gamma'

if __name__=='__main__':
    test_verify_proof_checks_pass(); print('verify_proof PASSED')
    test_run_system_cycle_bundle_forensics(); print('run_system_cycle PASSED')
    test_auto_patch_write_and_replace(); print('auto_patch PASSED')
