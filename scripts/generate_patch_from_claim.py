#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def patch_for_claim(claim):
    cat=claim.get('category','unknown'); cid=claim.get('claim_id','CLAIM-UNK')
    if cat=='cost_control':
        return {'claim_id':cid,'operation':'write','path':f'generated_patches/{cid.lower()}_cost_control.py',
                'content':'def accrue_cost(cur,delta,cap):\n    cur+=delta\n    return {"current_cost":round(cur,4),"cap_reached":cur>=cap}\n'}
    if cat=='memory_persistence':
        return {'claim_id':cid,'operation':'write','path':f'generated_patches/{cid.lower()}_memory_persistence.py',
                'content':'import json\nfrom pathlib import Path\ndef persist_trace(root,sid,trace):\n    p=Path(root)/f"{sid}.json"\n    p.parent.mkdir(parents=True,exist_ok=True)\n    p.write_text(json.dumps(trace,indent=2))\n    return str(p)\n'}
    if cat=='proof_gate':
        return {'claim_id':cid,'operation':'write','path':'proof_runtime.json',
                'content':json.dumps({'claim_id':cid,'status':'runtime proof placeholder'},indent=2)}
    if cat=='background_collection':
        return {'claim_id':cid,'operation':'write','path':f'generated_patches/{cid.lower()}_downgrade_note.md',
                'content':f'Claim {cid} not runtime-proven; downgrade production label until evidence exists.\n'}
    return {'claim_id':cid,'operation':'write','path':f'generated_patches/{cid.lower()}_manual_note.md',
            'content':f'Claim {cid} requires manual design resolution.\n'}

def main(claim_map_path, out_dir):
    claim_map=json.loads(Path(claim_map_path).read_text())
    out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    patches=[]
    for claim in claim_map.get('claims',[]):
        if claim.get('required_for_production') and claim.get('evidence_class')!='runtime_proven':
            spec=patch_for_claim(claim)
            target=out_dir/f"{claim['claim_id'].lower()}.patch.json"
            target.write_text(json.dumps(spec,indent=2))
            patches.append({'claim_id':claim['claim_id'],'patch_spec':str(target)})
    (out_dir/'patch_index.json').write_text(json.dumps({'patches':patches},indent=2))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2])
