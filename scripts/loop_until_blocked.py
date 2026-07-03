#!/usr/bin/env python3
from __future__ import annotations
import sys, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

def rerank(queue_path, score_script):
    subprocess.run(['python3',score_script,queue_path,queue_path],check=True)

def main(case_dir, max_steps=25):
    case=Path(case_dir)
    queue_path=str(case/'action_queue.json')
    result_path=str(case/'last_result.json')
    verified_path=str(case/'verified_result.json')
    scripts=str(Path(__file__).resolve().parent)
    rerank(queue_path,f'{scripts}/score_actions.py')
    failures=steps=0
    while steps<max_steps:
        subprocess.run(['python3',f'{scripts}/execute_next.py',queue_path,result_path,str(case)],check=True)
        result=load_json(result_path)
        if result.get('status')=='idle': break
        subprocess.run(['python3',f'{scripts}/verify_result.py',result_path,queue_path,verified_path],check=True)
        subprocess.run(['python3',f'{scripts}/persist_result.py',queue_path,verified_path,str(case)],check=True)
        verified=load_json(verified_path)
        failures=failures+1 if verified.get('status') in {'failed','blocked'} else 0
        rerank(queue_path,f'{scripts}/score_actions.py')
        steps+=1
        if failures>=2: break
    queue=load_json(queue_path)
    save_json(case/'loop_summary.json',{'steps_executed':steps,
        'completed':len([a for a in queue['actions'] if a.get('status')=='completed']),
        'blocked_or_failed':len([a for a in queue['actions'] if a.get('status') in {'blocked','failed'}]),
        'pending':len([a for a in queue['actions'] if a.get('status')=='pending'])})

if __name__ == '__main__':
    main(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 25)
