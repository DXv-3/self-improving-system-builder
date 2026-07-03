#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json, append_jsonl

def main(queue_path, verified_result_path, case_dir):
    case=Path(case_dir); case.mkdir(parents=True,exist_ok=True)
    queue=load_json(queue_path); result=load_json(verified_result_path)
    append_jsonl(case/'execution_log.jsonl',result)
    completed=[a for a in queue['actions'] if a.get('status')=='completed']
    blocked=[a for a in queue['actions'] if a.get('status') in {'blocked','failed'}]
    pending=[a for a in queue['actions'] if a.get('status')=='pending']
    save_json(case/'completed_actions.json',completed)
    save_json(case/'blocked_actions.json',blocked)
    save_json(case/'pending_actions.json',pending)
    (case/'progress_snapshot.md').write_text(
        f'# Progress Snapshot\n\n- Completed: {len(completed)}\n- Blocked/Failed: {len(blocked)}\n- Pending: {len(pending)}\n'
        f'- Last action: {result.get("action_id","none")}\n- Verified: {result.get("verified",False)}\n')
    lines=['# Next Blockers\n']
    lines+=[f"- {b['action_id']}: {b.get('title','')} :: {b.get('notes','')}" for b in blocked] or ['- None currently blocked.']
    (case/'next_blockers.md').write_text('\n'.join(lines)+'\n')

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3])
