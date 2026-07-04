#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
data_root = Path(os.getenv("GROK_PLUGIN_DATA", str(Path.home() / ".grok" / "operator-router")))
task = sys.argv[1]
workspace = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
registry_path = data_root / "registry.json"
if registry_path.exists():
    registry = json.loads(registry_path.read_text())
else:
    registry = {"skills": [], "commands": [], "instruction_files": []}
task_lower = task.lower()
task_class = "unknown"
if any(w in task_lower for w in ["scaffold", "create app", "demo app", "init project"]):
    task_class = "scaffold_app"
elif any(w in task_lower for w in ["init repo", "git init", "git setup"]):
    task_class = "init_repo"
elif any(w in task_lower for w in ["inspect", "analyze", "what is", "show me"]):
    task_class = "inspect_environment"
elif any(w in task_lower for w in ["reverse engineer", "understand skill"]):
    task_class = "reverse_engineer_skill"
candidates = []
for skill in registry.get("skills", []):
    triggers = [t.lower() for t in skill.get("triggers", [])]
    score = 0
    matched = []
    for trig in triggers:
        if trig in task_lower:
            score += 1.5
            matched.append(trig)
    score = min(score, 4.0)
    if not triggers:
        score -= 2.0
    has_scripts = bool(skill.get("scripts"))
    if not has_scripts and score > 0:
        score -= 2.0
    reliability = skill.get("reliability", "unknown")
    if reliability == "reliable":
        score += 2.0
    elif reliability == "bypass":
        score -= 3.0
    risk_flags = []
    effects = skill.get("side_effects", [])
    if "possible_overwrite" in effects:
        score -= 0.5
        risk_flags.append("possible_overwrite")
    if "possible_install" in effects:
        score -= 0.5
        risk_flags.append("possible_install")
    if score > 0 or matched:
        candidates.append({"name": skill.get("name", "unknown"), "score": round(score, 2),
            "matched_triggers": matched, "has_scripts": has_scripts,
            "reliability": reliability, "risk_flags": risk_flags, "path": skill.get("path", "")})
candidates.sort(key=lambda x: -x["score"])
if candidates and candidates[0]["score"] >= 6.0:
    mode = "skill_direct"
    winner = candidates[0]["name"]
    commands = ["# Execute via skill: " + winner]
elif candidates and candidates[0]["score"] >= 3.0:
    mode = "skill_chain"
    winner = "chain:" + ",".join(c["name"] for c in candidates[:3])
    commands = ["# Chain: " + winner]
else:
    mode = "shell_direct"
    winner = "shell"
    if task_class == "inspect_environment":
        commands = ["pwd", "ls -la", "git status 2>/dev/null || true"]
    elif task_class == "init_repo":
        commands = ["git init", "git add -A", "git commit -m initial"]
    elif task_class == "scaffold_app":
        commands = ["npm create vite@latest . -- --template react", "npm install"]
    else:
        commands = ["echo No skill match. Shell fallback.", "pwd", "ls -la"]
all_risks = set()
for c in candidates:
    all_risks.update(c.get("risk_flags", []))
if mode == "shell_direct" and task_class == "unknown":
    all_risks.add("unknown_script_side_effects")
plan = {"task": task, "task_class": task_class,
    "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    "candidates": candidates[:5], "execution_mode": mode, "winner": winner,
    "planned_commands": commands, "risk_flags": sorted(all_risks),
    "recordable_recipe": {"task_class": task_class, "winner": winner, "commands": commands, "mode": mode}}
plan_path = data_root / "last-plan.json"
plan_path.parent.mkdir(parents=True, exist_ok=True)
plan_path.write_text(json.dumps(plan, indent=2))
print(json.dumps(plan, indent=2))
