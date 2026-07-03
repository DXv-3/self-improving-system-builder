#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def make_action(aid,title,path,content):
    return {'action_id':aid,'title':title,'source':'adaptive_retry','category':'integration',
            'priority':6,'leverage_score':3,'unblock_power':4,'proof_value':2,'reuse_value':3,
            'risk_level':1,'dependencies':[],'executable_now':True,'execution_type':'file_write',
            'command_or_patch':f'{path}::{content}','proof_of_done':f'{path} exists',
            'rollback':f'delete {path}','status':'pending','notes':'Generated adaptive follow-up action.'}

def main(blocked_path, blocker_report_path, out_path):
    blocked=json.loads(Path(blocked_path).read_text())
    report=json.loads(Path(blocker_report_path).read_text())
    classes={b['action_id']:b['classification'] for b in report.get('blocked',[])}
    followups=[]
    for action in blocked:
        aid=action.get('action_id','UNKNOWN')
        cls=classes.get(aid,'needs_design_decision')
        detail=f"{action.get('title','')} :: {action.get('notes','')}"
        followups.append(make_action(f'{aid}-REQ',f'Create request record for {aid}',f'approval_requests/{aid}.md',f'# Request for {aid}\n\n{detail}\n\nclassification: {cls}\n'))
        if cls in {'downgrade_claim_now','needs_permission'} and ('reference-only' in detail.lower() or 'downgrade' in detail.lower()):
            followups.append(make_action(f'{aid}-DOWNGRADE',f'Downgrade claim for {aid}',f'claim_downgrades/{aid}.md',f'Claim for {aid} downgraded pending runtime proof.\n'))
        elif cls=='needs_permission':
            followups.append(make_action(f'{aid}-PLAN',f'Implementation plan for {aid}',f'implementation_plans/{aid}.md',f'Implementation plan required before approval for {aid}.\n'))
        elif cls=='needs_external_resource':
            followups.append(make_action(f'{aid}-RESOURCE',f'Resource request for {aid}',f'resource_requests/{aid}.md',f'Resource needed to proceed with {aid}.\n'))
        elif cls=='needs_design_decision':
            followups.append(make_action(f'{aid}-DESIGN',f'Design decision for {aid}',f'design_decisions/{aid}.md',f'Design decision needed for {aid}.\n'))
    Path(out_path).write_text(json.dumps({'artifact_name':'adaptive_followups','actions':followups},indent=2))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3])
