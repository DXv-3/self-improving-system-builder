#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

def get_nested(data,path):
    cur=data
    for part in path: cur=cur[part]
    return cur

def run_check(check, workdir):
    kind=check['kind']
    if kind=='file_exists': return {'check_id':check['check_id'],'passed':(workdir/check['path']).exists()}
    if kind=='text_contains':
        p=workdir/check['path']
        return {'check_id':check['check_id'],'passed':check['needle'] in (p.read_text() if p.exists() else '')}
    if kind=='json_field_equals':
        actual=get_nested(json.loads((workdir/check['path']).read_text()),check['json_path'])
        return {'check_id':check['check_id'],'passed':actual==check['expected']}
    if kind=='command_exit_zero':
        p=subprocess.run(check['command'],shell=True,cwd=str(workdir),capture_output=True,text=True)
        return {'check_id':check['check_id'],'passed':p.returncode==0}
    raise ValueError(f'Unknown kind: {kind}')

def main(checks_path, workdir, out_path=None):
    checks=json.loads(Path(checks_path).read_text())
    results=[run_check(c,Path(workdir)) for c in checks.get('checks',[])]
    report={'all_passed':all(r['passed'] for r in results),'results':results}
    if out_path: Path(out_path).write_text(json.dumps(report,indent=2))
    else: print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
