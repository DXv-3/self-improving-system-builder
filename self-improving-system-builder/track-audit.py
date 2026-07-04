#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
from datetime import datetime
store = Path(os.getenv("IDKWIDK_STORE", str(Path.home() / ".idkwidk")))
store.mkdir(parents=True, exist_ok=True)
history = store / "audit-history.ndjson"
def record_audit(project, gates):
    entry = {"timestamp": datetime.utcnow().isoformat() + "Z", "project": project, "gates": gates, "total_findings": sum(len(v) if isinstance(v, list) else (0 if v == "PASS" else 1) for v in gates.values())}
    with open(history, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
def show_history(project=None, limit=20):
    if not history.exists():
        print("No audit history yet.")
        return
    rows = []
    for line in history.read_text().splitlines():
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except: continue
    if project:
        rows = [r for r in rows if r.get("project") == project]
    rows = rows[-limit:]
    if not rows:
        print("No matching audit history.")
        return
    print("\nRecent audits:")
    for r in reversed(rows):
        ts = r["timestamp"][:19]
        proj = r.get("project", "unknown")[:30]
        findings = r.get("total_findings", 0)
        print(f"  {ts} | {proj:<30} | {findings} findings")
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        proj = sys.argv[2] if len(sys.argv) > 2 else None
        show_history(proj)
    elif len(sys.argv) > 1 and sys.argv[1] == "record":
        audit = json.loads(sys.stdin.read())
        project = audit.get("project", os.getcwd())
        gates = audit.get("gates", {})
        result = record_audit(project, gates)
        print(json.dumps(result, indent=2))
    else:
        show_history()
