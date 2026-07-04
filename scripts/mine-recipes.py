#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
from collections import Counter, defaultdict
data_root = Path(os.getenv("GROK_PLUGIN_DATA", str(Path.home() / ".grok" / "operator-router")))
history = data_root / "execution-history.ndjson"
if not history.exists():
    print(json.dumps({"recipes": [], "promotions": []}))
    raise SystemExit(0)
rows = []
for line in history.read_text().splitlines():
    if not line.strip():
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        continue
shell_wins = defaultdict(list)
for row in rows:
    er = row.get("execution_result", {})
    if er.get("status") == "success" and er.get("chosen_mode") == "shell_direct":
        task_class = row.get("task_class", "unknown")
        commands = er.get("commands_run", [])
        shell_wins[task_class].append(commands)
promotions = []
for task_class, wins in shell_wins.items():
    if len(wins) >= 3:
        flat = [cmd for cmds in wins for cmd in cmds if not cmd.startswith("#") and not cmd.startswith("echo")]
        common = Counter(flat).most_common(5)
        promotions.append({"task_class": task_class, "win_count": len(wins),
            "common_commands": [c[0] for c in common],
            "recommended_skill_name": "auto-" + task_class.replace("_", "-")})
print(json.dumps({"total_shell_wins": sum(len(w) for w in shell_wins.values()),
    "promotion_candidates": len(promotions), "promotions": promotions}, indent=2))
