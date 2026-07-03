#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

RULES=[('needs_permission',['permission','approval','risk above auto threshold']),
       ('needs_external_resource',['missing dependency','network','credential','resource']),
       ('needs_safe_patch',['contradicted','rewrite','cost','persistence','config']),
       ('downgrade_claim_now',['reference-only','reference only','downgrade production label'])]

def classify(text):
    lower=(text or '').lower()
    for label,needles in RULES:
        if any(n in lower for n in needles): return label
    return 'needs_design_decision'

def main(blocked_path, out_path):
    blocked=json.loads(Path(blocked_path).read_text())
    out=[{'action_id':a.get('action_id'),'classification':classify(f"{a.get('title','')} :: {a.get('notes','')}"),
          'detail':f"{a.get('title','')} :: {a.get('notes','')}"} for a in blocked]
    Path(out_path).write_text(json.dumps({'blocked':out},indent=2))

if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2])
