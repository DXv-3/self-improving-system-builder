#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def main(approval_path, followup_summary_path, out_path):
    approvals=json.loads(Path(approval_path).read_text()).get('decisions',[])
    summary=json.loads(Path(followup_summary_path).read_text())
    decisions={d['decision'] for d in approvals}
    if summary.get('blocked_or_failed',0)==0 and summary.get('completed',0)>0: strategy='reaudit_now'
    elif 'auto_downgrade_claim' in decisions: strategy='apply_downgrades_and_reaudit'
    elif 'request_human_approval' in decisions: strategy='await_approval_then_rerun'
    elif 'request_resource' in decisions: strategy='acquire_resources_then_rerun'
    else: strategy='perform_design_review'
    Path(out_path).write_text(json.dumps({'strategy':strategy,'completed':summary.get('completed',0),
        'blocked_or_failed':summary.get('blocked_or_failed',0),'pending':summary.get('pending',0)},indent=2))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3])
