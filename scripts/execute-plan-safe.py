#!/usr/bin/env python3
import json, subprocess, sys, os, signal
from pathlib import Path
from datetime import datetime
def load_config():
    config_path = Path(os.getenv("GROK_PLUGIN_DATA", str(Path.home() / ".grok" / "operator-router"))) / "config.toml"
    defaults = {"command_timeout": 120, "max_output_bytes": 2000, "max_artifacts": 200}
    if config_path.exists():
        try:
            import tomllib
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
                return {**defaults, **data.get("execution", {})}
        except Exception:
            pass
    return defaults
class GracefulShutdown:
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)
    def _handler(self, signum, frame):
        self.shutdown_requested = True
    def should_stop(self):
        return self.shutdown_requested
def snapshot_workspace(workspace):
    return {str(p): p.stat().st_size for p in workspace.rglob("*") if p.is_file()}
def rollback(workspace, before):
    after = {str(p): p.stat().st_size for p in workspace.rglob("*") if p.is_file()}
    created = set(after.keys()) - set(before.keys())
    rolled = []
    for path in sorted(created, reverse=True):
        try:
            p = Path(path)
            if p.is_file():
                p.unlink()
                rolled.append(path)
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
                rolled.append(path)
        except Exception:
            pass
    return rolled
plan_path = Path(sys.argv[1])
allow_risky = "--allow-risky" in sys.argv
config = load_config()
plan = json.loads(plan_path.read_text())
mode = plan.get("execution_mode", "shell_direct")
commands = plan.get("planned_commands", [])
risks = set(plan.get("risk_flags", []))
dangerous = {"possible_overwrite", "possible_install", "git_mutation", "delete", "unknown_script_side_effects"}
if risks & dangerous and not allow_risky:
    print(json.dumps({"execution_result": {"status": "blocked", "reason": "risky plan requires --allow-risky"}}, indent=2))
    raise SystemExit(2)
workspace = Path.cwd()
before = snapshot_workspace(workspace)
shutdown = GracefulShutdown()
ran = []
failures = []
for cmd in commands:
    if not cmd.strip() or cmd.strip().startswith("#"):
        continue
    if shutdown.should_stop():
        failures.append({"command": cmd, "reason": "interrupted"})
        break
    try:
        proc = subprocess.run(cmd, shell=True, cwd=workspace, text=True, capture_output=True, timeout=config["command_timeout"])
        ran.append({"command": cmd, "returncode": proc.returncode, "stdout": proc.stdout[-config["max_output_bytes"]:], "stderr": proc.stderr[-config["max_output_bytes"]:]})
        if proc.returncode != 0:
            failures.append({"command": cmd, "returncode": proc.returncode})
            break
    except subprocess.TimeoutExpired:
        ran.append({"command": cmd, "returncode": -1, "stderr": "timeout"})
        failures.append({"command": cmd, "reason": "timeout"})
        break
    except Exception as e:
        failures.append({"command": cmd, "reason": str(e)})
        break
status = "success" if not failures else "failed"
after = snapshot_workspace(workspace)
created = sorted(set(after.keys()) - set(before.keys()))[:config["max_artifacts"]]
if failures and mode != "shell_direct":
    rolled = rollback(workspace, before)
    if rolled:
        created = [c for c in created if c not in rolled]
print(json.dumps({"timestamp": datetime.utcnow().isoformat() + "Z", "task": plan.get("task"),
    "execution_result": {"status": status, "chosen_mode": mode,
        "winner": plan.get("recordable_recipe", {}).get("winner", "none"),
        "commands_run": [r["command"] for r in ran],
        "artifacts_found": created,
        "should_save_recipe": status == "success",
        "should_draft_skill": status == "success" and mode == "shell_direct"},
    "command_details": ran}, indent=2))
