#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
def parse_skill_md(skill_md_path):
    skill = {"name": "", "description": "", "triggers": [], "scripts": [], "side_effects": [], "reliability": "unknown", "path": str(skill_md_path.parent)}
    if not skill_md_path.exists():
        return skill
    content = skill_md_path.read_text()
    in_fm = False
    in_trig = False
    for line in content.splitlines():
        s = line.strip()
        if s == "---":
            in_fm = not in_fm
            continue
        if not in_fm:
            continue
        if s.startswith("name:"):
            skill["name"] = s.split(":", 1)[1].strip().strip('"').strip("'")
            in_trig = False
        elif s.startswith("description:"):
            skill["description"] = s.split(":", 1)[1].strip()
            in_trig = False
        elif s.startswith("triggers:"):
            in_trig = True
        elif in_trig and s.startswith("-"):
            skill["triggers"].append(s[1:].strip().strip('"').strip("'"))
        elif in_trig and not s.startswith("-"):
            in_trig = False
    return skill
def scan_scripts(skill_dir):
    scripts = []
    sd = skill_dir / "scripts"
    if sd.exists():
        for p in sorted(sd.iterdir()):
            if p.is_file() and p.suffix in (".sh", ".py"):
                scripts.append(p.name)
    return scripts
def detect_side_effects(scripts, skill_dir):
    effects = set()
    sd = skill_dir / "scripts"
    for name in scripts:
        p = sd / name
        if not p.exists():
            continue
        try:
            c = p.read_text().lower()
            if any(w in c for w in ["rm -rf", "rm -f"]): effects.add("delete")
            if any(w in c for w in ["npm install", "pip install", "apt install", "brew install"]): effects.add("possible_install")
            if any(w in c for w in ["git add", "git commit", "git push", "git reset"]): effects.add("git_mutation")
            if any(w in c for w in ["curl", "wget"]): effects.add("network")
            if any(w in c for w in ["> ", ">>", "touch ", "mkdir ", "cp "]): effects.add("writes")
        except Exception:
            pass
    return sorted(effects)
skill_dir = Path(sys.argv[1]).resolve()
registry_path = Path(sys.argv[2])
if not skill_dir.is_dir():
    print(json.dumps({"error": f"not a directory: {skill_dir}"}))
    raise SystemExit(1)
skill_md = skill_dir / "SKILL.md"
if not skill_md.exists():
    for c in ["skill.md", "CLAUDE.md", "AGENTS.md"]:
        if (skill_dir / c).exists():
            skill_md = skill_dir / c
            break
skill = parse_skill_md(skill_md)
if not skill["name"]:
    skill["name"] = skill_dir.name
skill["scripts"] = scan_scripts(skill_dir)
skill["side_effects"] = detect_side_effects(skill["scripts"], skill_dir)
if registry_path.exists():
    registry = json.loads(registry_path.read_text())
else:
    registry = {"skills": [], "commands": [], "instruction_files": []}
existing = [s for s in registry.get("skills", []) if s.get("name") == skill["name"]]
if existing:
    existing[0].update(skill)
else:
    registry.setdefault("skills", []).append(skill)
registry_path.write_text(json.dumps(registry, indent=2))
print(json.dumps({"imported": skill["name"], "triggers": len(skill["triggers"]), "scripts": len(skill["scripts"]), "side_effects": skill["side_effects"]}))
