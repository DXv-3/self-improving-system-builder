#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

def verify(result,queue):
    v=result.get('status')=='completed' and result.get('returncode',0)==0
    result['verified']=v; result['proof_observed']=v; return result

def main(result_path,queue_path,out_path):
    save_json(out_path,verify(load_json(result_path),load_json(queue_path)))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3])
