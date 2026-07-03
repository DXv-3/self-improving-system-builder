#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

COMPLETED={'completed','skipped'}

def score_action(action, completed_ids):
    dep_penalty=sum(1 for d in action.get('dependencies',[]) if d not in completed_ids)*3
    score=(float(action.get('priority',0))+float(action.get('leverage_score',0))
           +float(action.get('unblock_power',0))+float(action.get('proof_value',0))
           +float(action.get('reuse_value',0))-float(action.get('risk_level',0))-dep_penalty)
    action['score']=round(score,2); action['dependency_penalty']=dep_penalty
    action['blocked_by_dependencies']=dep_penalty>0; return action

def main(queue_path, out_path):
    queue=load_json(queue_path)
    completed_ids={a['action_id'] for a in queue['actions'] if a.get('status') in COMPLETED}
    queue['actions']=sorted([score_action(a,completed_ids) for a in queue['actions']],
                             key=lambda x:(-x.get('score',0),x['action_id']))
    save_json(out_path,queue)

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else sys.argv[1])
