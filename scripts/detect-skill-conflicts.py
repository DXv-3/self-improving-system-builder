#!/usr/bin/env python3
import json, sys, os
from pathlib import Path
from collections import defaultdict
registry_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.getenv("GROK_PLUGIN_DATA", str(Path.home() / ".grok" / "operator-router"))) / "registry.json"
if not registry_path.exists():
    print(json.dumps({"conflicts": [], "message": "registry not found"}))
    raise SystemExit(0)
registry = json.loads(registry_path.read_text())
trigger_map = defaultdict(list)
for skill in registry.get("skills", []):
    for trig in skill.get("triggers", []):
        trigger_map[trig.lower()].append(skill.get("name", "unknown"))
conflicts = []
for trig, skills in sorted(trigger_map.items()):
    if len(skills) > 1:
        conflicts.append({"trigger": trig, "skills": sorted(set(skills))})
print(json.dumps({"total_triggers": len(trigger_map), "conflicts": conflicts, "conflict_count": len(conflicts)}, indent=2))
