#!/usr/bin/env python3
from __future__ import annotations
import sys, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json, now_iso

THRESHOLD = 4

def choose(actions):
    for a in actions:
        if a.get('status')!='pending': continue
        if not a.get('executable_now',True): continue
        if a.get('blocked_by_dependencies'): continue
        return a
    return None

def run_action(action, workdir):
    r={'action_id':action['action_id'],'timestamp':now_iso(),'status':'blocked',
       'verified':False,'stdout':'','stderr':'','returncode':0,'proof_observed':False,'blocker_reason':''}
    if float(action.get('risk_level',10))>THRESHOLD:
        r['blocker_reason']='risk above auto threshold'; return r
    et=action.get('execution_type')
    if et=='command':
        p=subprocess.run(action.get('command_or_patch',''),shell=True,cwd=str(workdir),capture_output=True,text=True)
        r.update({'status':'completed' if p.returncode==0 else 'failed','stdout':p.stdout,'stderr':p.stderr,'returncode':p.returncode})
    elif et=='python':
        p=subprocess.run(['python3','-c',action.get('command_or_patch','')],cwd=str(workdir),capture_output=True,text=True)
        r.update({'status':'completed' if p.returncode==0 else 'failed','stdout':p.stdout,'stderr':p.stderr,'returncode':p.returncode})
    elif et=='file_write':
        rel,_,content=action.get('command_or_patch','').partition('::')
        t=Path(workdir)/rel; t.parent.mkdir(parents=True,exist_ok=True); t.write_text(content)
        r.update({'status':'completed','stdout':str(t),'returncode':0})
    else:
        r['blocker_reason']='manual action requires operator'
    return r

def apply(queue, result):
    for a in queue['actions']:
        if a['action_id']==result['action_id']:
            a['status']=result['status']
            if result['status']=='blocked':
                a['notes']=(a.get('notes','')+' | '+result.get('blocker_reason','')).strip(' |')
            break
    return queue

def main(queue_path, result_path, workdir):
    queue=load_json(queue_path)
    action=choose(queue['actions'])
    if not action:
        save_json(result_path,{'status':'idle','reason':'no executable pending action','timestamp':now_iso()}); return
    result=run_action(action,Path(workdir))
    save_json(queue_path,apply(queue,result))
    save_json(result_path,result)

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else '.')
