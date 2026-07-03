#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def apply_patch(spec, workdir):
    workdir=Path(workdir)
    target=workdir/spec['path']
    target.parent.mkdir(parents=True,exist_ok=True)
    op=spec['operation']
    if op=='write': target.write_text(spec.get('content',''))
    elif op=='append': target.write_text((target.read_text() if target.exists() else '')+spec.get('content',''))
    elif op=='replace': target.write_text(target.read_text().replace(spec['old'],spec.get('new','')))
    else: raise ValueError(f'Unknown operation: {op}')
    return {"status":"completed","target":str(target),"operation":op}

if __name__ == '__main__':
    spec=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(apply_patch(spec,sys.argv[2])))
