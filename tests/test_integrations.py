#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
EXAMPLES = ROOT / 'examples'

def test_bundle_forensics_reconcile_builds_queue():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        for name in ['claim_map.json','runtime_evidence.json','drift_report.json']:
            (case/name).write_text((EXAMPLES/'bundle_forensics_case'/name).read_text())
        out=case/'action_queue.json'
        subprocess.run(['python3',str(SCRIPTS/'reconcile_with_bundle_forensics.py'),str(case/'claim_map.json'),str(case/'runtime_evidence.json'),str(case/'drift_report.json'),str(out)],check=True)
        data=json.loads(out.read_text())
        assert len(data['actions'])==3
        assert 'BFA-001' in {a['action_id'] for a in data['actions']}

def test_router_handoff_import_and_loop():
    with tempfile.TemporaryDirectory() as td:
        case=Path(td)
        queue=case/'action_queue.json'
        subprocess.run(['python3',str(SCRIPTS/'import_router_handoff.py'),str(EXAMPLES/'router_handoff.json'),str(queue)],check=True)
        subprocess.run(['python3',str(SCRIPTS/'score_actions.py'),str(queue),str(queue)],check=True)
        subprocess.run(['python3',str(SCRIPTS/'loop_until_blocked.py'),str(case),'3'],check=True)
        summary=json.loads((case/'loop_summary.json').read_text())
        assert summary['completed']==1
        assert (case/'router_note.txt').exists()

if __name__=='__main__':
    test_bundle_forensics_reconcile_builds_queue(); print('test_bundle_forensics PASSED')
    test_router_handoff_import_and_loop(); print('test_router_handoff PASSED')
