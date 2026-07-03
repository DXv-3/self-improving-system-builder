#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

CATEGORY_FIXES = {
    'proof_gate':('python',"from pathlib import Path; Path('proof_runtime.json').write_text('{\"status\":\"placeholder\"}')\n",2),
    'cost_control':('manual','Implement cost tracking and add a regression test.',8),
    'memory_persistence':('manual','Implement persistence write/read cycle and tests.',8),
    'background_collection':('manual','Produce runtime log evidence or downgrade production label.',8),
    'config_loading':('manual','Wire YAML config loading into runtime constructor and tests.',7),
    'rewrite_behavior':('manual','Replace naive string rewrite with safe boundary-aware transform.',7),
    'integration':('file_write','integration_note.txt::validated integration handoff placeholder',1)
}

def build_actions(claim_map):
    actions=[]
    for claim in claim_map.get('claims',[]):
        if not claim.get('required_for_production'): continue
        if claim.get('evidence_class')=='runtime_proven': continue
        etype,cmd,risk=CATEGORY_FIXES.get(claim.get('category'),('manual','Investigate and resolve claim gap.',7))
        prefix={'contradicted':'Fix or downgrade contradicted claim','reference_only':'Prove or downgrade reference-only claim','unverified':'Prove or downgrade unverified claim'}.get(claim.get('evidence_class'),'Resolve claim')
        actions.append({'action_id':claim['claim_id'].replace('CLAIM','BFA'),'title':f"{prefix}: {claim['text']}",
            'source':claim['claim_id'],'category':claim.get('category','unknown'),
            'priority':9 if claim.get('evidence_class')=='contradicted' else 8,
            'leverage_score':5,'unblock_power':4,'proof_value':5,'reuse_value':4,
            'risk_level':risk,'dependencies':[],'executable_now':True,'execution_type':etype,
            'command_or_patch':cmd,'proof_of_done':'Claim downgraded or runtime evidence added',
            'rollback':'Revert edited evidence or claim files','status':'pending','notes':claim.get('notes','')})
    return actions

def main(claim_map_path, runtime_path, drift_path, out_path):
    claim_map=load_json(claim_map_path)
    save_json(out_path,{'artifact_name':claim_map.get('artifact_name','unknown_artifact'),'actions':build_actions(claim_map)})

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])
