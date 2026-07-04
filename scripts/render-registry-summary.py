#!/usr/bin/env python3
import json, sys
from pathlib import Path
registry_path = Path(sys.argv[1])
if not registry_path.exists():
    print("Registry not found.")
    raise SystemExit(1)
registry = json.loads(registry_path.read_text())
skills = registry.get("skills", [])
print(f"\nREGISTRY SUMMARY")
print(f"  Total skills: {len(skills)}")
if not skills:
    print("  (no skills registered)")
    raise SystemExit(0)
reliable = sum(1 for s in skills if s.get("reliability") == "reliable")
bypass = sum(1 for s in skills if s.get("reliability") == "bypass")
unknown = sum(1 for s in skills if s.get("reliability") == "unknown")
print(f"\n  Reliability: reliable={reliable}, unknown={unknown}, bypass={bypass}")
with_scripts = sum(1 for s in skills if s.get("scripts"))
print(f"  Skills with scripts: {with_scripts}/{len(skills)}")
