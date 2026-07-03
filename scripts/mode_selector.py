#!/usr/bin/env python3
"""
mode_selector.py

Auto-select the correct execution mode from project state.
Eliminates the need for the user to know which sub-script to call.

Modes (in priority order):
  bundle_forensics      -- claim_map exists, many unverified claims
  router_handoff        -- router_handoff.json present
  full_meta_cycle       -- claim_map + drift_report, needs patching
  adaptive_meta_cycle   -- blockers present from previous run
  reaudit               -- all claims runtime_proven, check for drift

Usage:
  python3 scripts/mode_selector.py <case_dir>
  python3 scripts/mode_selector.py <case_dir> --execute
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

# Fix: ensure scripts dir is on sys.path so common.py is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))


def select_mode(case_dir: Path) -> str:
    files = {p.name for p in case_dir.iterdir() if p.is_file()}

    # Mode 1: Active blockers from a previous run
    blocked_path = case_dir / "blocked_actions.json"
    if blocked_path.exists():
        try:
            blocked = json.loads(blocked_path.read_text())
            # blocked_actions.json may be a list or {"actions": [...]}
            items = blocked if isinstance(blocked, list) else blocked.get("actions", blocked)
            if items:
                return "adaptive_meta_cycle"
        except Exception:
            pass

    # Mode 2: Router handoff artifact
    if "router_handoff.json" in files:
        return "router_handoff"

    # Mode 3: Claim map with unverified claims
    claim_map_path = case_dir / "claim_map.json"
    if claim_map_path.exists():
        try:
            data = json.loads(claim_map_path.read_text())
            claims = data.get("claims", [])
            if claims:
                unverified = sum(
                    1 for c in claims
                    if c.get("evidence_class") in ("unverified", "reference_only", "contradicted")
                )
                drift_ratio = unverified / len(claims)
                if drift_ratio > 0.5:
                    return "bundle_forensics"
                elif drift_ratio > 0.0:
                    return "full_meta_cycle"
                else:
                    return "reaudit"
        except Exception:
            pass

    # Default: full adaptive cycle on whatever is present
    return "adaptive_meta_cycle"


def execute_mode(mode: str, case_dir: Path, scripts_dir: Path) -> None:
    mode_scripts = {
        "bundle_forensics":    ("run_system_cycle.py",    ["bundle_forensics"]),
        "router_handoff":      ("run_system_cycle.py",    ["router_handoff"]),
        "full_meta_cycle":     ("run_full_meta_cycle.py", []),
        "adaptive_meta_cycle": ("run_adaptive_meta_cycle.py", []),
        "reaudit":             ("run_adaptive_meta_cycle.py", []),
    }
    script_name, extra_args = mode_scripts[mode]
    cmd = ["python3", str(scripts_dir / script_name), str(case_dir)] + extra_args
    print(f"[mode_selector] Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/mode_selector.py <case_dir> [--execute]")
        sys.exit(1)

    case_dir = Path(sys.argv[1])
    do_execute = "--execute" in sys.argv

    if not case_dir.exists():
        print(f"Error: {case_dir} does not exist")
        sys.exit(1)

    mode = select_mode(case_dir)
    print(f"[mode_selector] Selected mode: {mode}")

    if do_execute:
        scripts_dir = Path(__file__).resolve().parent
        execute_mode(mode, case_dir, scripts_dir)
    else:
        print("[mode_selector] Dry run. Pass --execute to run.")
        print(f"[mode_selector] Would run: {mode}")
