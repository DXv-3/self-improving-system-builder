#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
from collections import defaultdict
data_root = Path(os.getenv("GROK_PLUGIN_DATA", str(Path.home() / ".grok" / "operator-router")))
registry_path = data_root / "registry.json"
history_path = data_root / "execution-history.ndjson"
if not registry_path.exists():
    print(json.dumps({"error": "registry not found"}))
    raise SystemExit(1)
registry = json.loads(registry_path.read_text())
stats = defaultdict(lambda: {"success": 0, "failed": 0})
if history_path.exists():
    for line in history_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            er = row.get("execution_result", {})
            winner = er.get("winner", "none")
            if winner in ("none", "shell"):
                continue
            status = er.get("status", "unknown")
            if status in ("success", "failed"):
                stats[winner][status] += 1
        except Exception:
            continue
updated = 0
for skill in registry.get("skills", []):
    name = skill.get("name", "unknown")
    s = stats.get(name, {"success": 0, "failed": 0})
    success = s["success"]
    fail = s["failed"]
    total = success + fail
    old = skill.get("reliability", "unknown")
    if total == 0:
        new_state = "unknown"
    elif fail >= 2 and success == 0:
        new_state = "bypass"
    elif success >= 3 and fail == 0:
        new_state = "reliable"
    elif fail > success:
        new_state = "needs_wrapper"
    else:
        new_state = "unknown"
    if old != new_state:
        skill["reliability"] = new_state
        updated += 1
        print(f"  {name}: {old} -> {new_state} (s={success}, f={fail})")
    skill["reliability_stats"] = {"success": success, "failed": fail, "total": total}
registry_path.write_text(json.dumps(registry, indent=2))
print(f"\nReliability rebuild complete. {updated} skills updated.")
