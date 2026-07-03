#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

def main(handoff_path, out_path):
    data=load_json(handoff_path)
    save_json(out_path,{'artifact_name':data.get('task','router_task'),'actions':data.get('actions',[])})

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2])
