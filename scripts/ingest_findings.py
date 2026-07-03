#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

CATEGORY_DEFAULTS = {
    'proof_gate':(8,4,4,3,3),'cost_control':(9,5,5,4,3),
    'memory_persistence':(9,5,5,4,3),'background_collection':(5,2,2,2,5),
    'integration':(7,4,3,5,2),'config_loading':(7,3,3,3,2),'rewrite_behavior':(8,4,4,2,4)
}

def action_from_claim(claim):
    base=CATEGORY_DEFAULTS.get(claim.get('category'),(5,2,2,2,3))
    priority,leverage,unblock,proof,risk=base
    title=f"Fix contradicted claim: {claim['text']}" if claim.get('evidence_class')=='contradicted' else f"Prove or downgrade claim: {claim['text']}"
    return {'action_id':claim['claim_id'].replace('CLAIM','ACT'),'title':title,'source':claim['claim_id'],
            'category':claim.get('category','unknown'),'priority':priority,'leverage_score':leverage,
            'unblock_power':unblock,'proof_value':proof,'reuse_value':3,'risk_level':risk,
            'dependencies':[],'executable_now':True,'execution_type':'manual',
            'command_or_patch':f"Resolve evidence gap for {claim['claim_id']}",
            'proof_of_done':'Updated claim to runtime_proven or downgraded production label',
            'rollback':'Revert claim/status files','status':'pending','notes':claim.get('notes','')}

def main(claim_map_path, out_path):
    claim_map=load_json(claim_map_path)
    actions=[action_from_claim(c) for c in claim_map.get('claims',[]) if c.get('required_for_production')]
    save_json(out_path,{'artifact_name':claim_map.get('artifact_name','unknown'),'actions':actions})

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2])
