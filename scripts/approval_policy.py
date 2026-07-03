#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def decide(item):
    cls=item.get('classification','needs_design_decision')
    detail=item.get('detail','').lower()
    if cls=='downgrade_claim_now' or 'reference-only' in detail or 'downgrade production label' in detail:
        d,r='auto_downgrade_claim','Claim lacks runtime proof; safer to downgrade pending evidence.'
    elif cls=='needs_permission': d,r='request_human_approval','Action remains high risk under auto-approval threshold.'
    elif cls=='needs_external_resource': d,r='request_resource','Blocked by missing external dependency or input.'
    elif cls=='needs_safe_patch': d,r='auto_generate_safe_patch','Generate lower-risk patch or staging artifact first.'
    else: d,r='request_design_decision','Design choice needed before safe execution can continue.'
    return {'action_id':item.get('action_id'),'classification':cls,'decision':d,'rationale':r,'detail':item.get('detail','')}

def main(blocker_report_path, out_path):
    report=json.loads(Path(blocker_report_path).read_text())
    Path(out_path).write_text(json.dumps({'decisions':[decide(i) for i in report.get('blocked',[])]},indent=2))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2])
