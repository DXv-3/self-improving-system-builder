#!/usr/bin/env python3
"""
run_operator_layer.py

Single top-level launcher. The user runs one command.
The system inspects project state, selects the correct mode,
and runs the full cycle. Eliminates mode selection burden.

Usage:
  python3 run_operator_layer.py <case_dir>
  python3 run_operator_layer.py <case_dir> --dry-run
  python3 run_operator_layer.py <case_dir> --force-mode <mode>

This is the intended primary entry point for all cycle execution.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent

VALID_MODES = [
    "bundle_forensics",
    "router_handoff",
    "full_meta_cycle",
    "adaptive_meta_cycle",
    "reaudit",
]


def check_enforcement(case_dir: Path) -> dict:
    enforcement_path = case_dir / "enforcement_active.json"
    if enforcement_path.exists():
        return json.loads(enforcement_path.read_text())
    return {"active": False}


def run_mode_selector(case_dir: Path) -> str:
    result = subprocess.run(
        ["python3", str(SCRIPTS / "mode_selector.py"), str(case_dir)],
        capture_output=True, text=True, check=True
    )
    for line in result.stdout.splitlines():
        if "Selected mode:" in line:
            return line.split(":")[-1].strip()
    return "adaptive_meta_cycle"


def run_trust_update(case_dir: Path) -> None:
    queue_path = case_dir / "action_queue.json"
    if queue_path.exists():
        try:
            subprocess.run(
                ["python3", str(SCRIPTS / "trust_update.py"), "--apply", str(queue_path)],
                capture_output=True, text=True, check=False, cwd=str(SCRIPTS)
            )
        except Exception:
            pass  # trust_update is optional enhancement, never block on it


def write_operator_log(case_dir: Path, mode: str, result: str) -> None:
    log_path = case_dir / "operator_log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "result": result,
    }
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Single entry point for all self-improving system execution."
    )
    parser.add_argument("case_dir", type=str)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-mode", choices=VALID_MODES, default=None)
    args = parser.parse_args()

    case_dir = Path(args.case_dir)
    if not case_dir.exists():
        print(f"Error: {case_dir} does not exist")
        sys.exit(1)

    # 1. Check enforcement state
    enforcement = check_enforcement(case_dir)
    if enforcement.get("active"):
        print(f"[operator] Enforcement prompt active (v{enforcement.get('version', '?')})")
    else:
        print("[operator] WARNING: enforcement_active.json not found. "
              "Run apply_to_chat.py first to activate enforcement.")

    # 2. Apply trust updates to queue if available
    run_trust_update(case_dir)

    # 3. Select mode
    if args.force_mode:
        mode = args.force_mode
        print(f"[operator] Force mode: {mode}")
    else:
        mode = run_mode_selector(case_dir)
        print(f"[operator] Auto-selected mode: {mode}")

    if args.dry_run:
        print(f"[operator] Dry run. Would execute mode: {mode}")
        write_operator_log(case_dir, mode, "dry_run")
        return

    # 4. Execute
    mode_scripts = {
        "bundle_forensics":    ["run_system_cycle.py", "bundle_forensics"],
        "router_handoff":      ["run_system_cycle.py", "router_handoff"],
        "full_meta_cycle":     ["run_full_meta_cycle.py"],
        "adaptive_meta_cycle": ["run_adaptive_meta_cycle.py"],
        "reaudit":             ["run_adaptive_meta_cycle.py"],
    }
    script_args = mode_scripts[mode]
    cmd = ["python3", str(SCRIPTS / script_args[0]), str(case_dir)] + script_args[1:]

    print(f"[operator] Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        write_operator_log(case_dir, mode, "completed")
        print(f"[operator] Cycle complete. Mode: {mode}")
    except subprocess.CalledProcessError as e:
        write_operator_log(case_dir, mode, f"failed: {e}")
        print(f"[operator] Cycle failed. Check {case_dir}/execution_log.jsonl")
        sys.exit(1)


if __name__ == "__main__":
    main()
