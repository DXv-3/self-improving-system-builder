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
  python3 mode_selector.py <case_dir>
  python3 mode_selector.py <case_dir> --execute
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path


def select_mode(case_dir: Path) -> str:
    files = {p.name for p in case_dir.iterdir() if p.is_file()}

    # Mode 1: Active blockers from a previous run
    blocked_path = case_dir / "blocked_actions.json"
    if blocked_path.exists():
        blocked = json.loads(blocked_path.read_text())
        if blocked:
            return "adaptive_meta_cycle"

    # Mode 2: Router handoff artifact
    if "router_handoff.json" in files:
        return "router_handoff"

    # Mode 3: Claim map with unverified claims
    claim_map_path = case_dir / "claim_map.json"
    if claim_map_path.exists():
        claims = json.loads(claim_map_path.read_text()).get("claims", [])
        unverified = sum(
            1 for c in claims
            if c.get("evidence_class") in ("unverified", "reference_only", "contradicted")
        )
        total = len(claims)
        if total > 0:
            drift_ratio = unverified / total
            if drift_ratio > 0.5:
                return "bundle_forensics"
            elif drift_ratio > 0.0:
                return "full_meta_cycle"
            else:
                return "reaudit"

    # Default: full adaptive cycle on whatever is present
    return "adaptive_meta_cycle"


def execute_mode(mode: str, case_dir: Path, scripts_dir: Path) -> None:
    mode_scripts = {
        "bundle_forensics":    "run_system_cycle.py",
        "router_handoff":      "run_system_cycle.py",
        "full_meta_cycle":     "run_full_meta_cycle.py",
        "adaptive_meta_cycle": "run_adaptive_meta_cycle.py",
        "reaudit":             "run_adaptive_meta_cycle.py",
    }
    script = scripts_dir / mode_scripts[mode]
    extra_args = ["bundle_forensics"] if mode == "bundle_forensics" else \
                 ["router_handoff"] if mode == "router_handoff" else []
    cmd = ["python3", str(script), str(case_dir)] + extra_args
    print(f"[mode_selector] Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mode_selector.py <case_dir> [--execute]")
        sys.exit(1)

    case_dir = Path(sys.argv[1])
    execute = "--execute" in sys.argv

    if not case_dir.exists():
        print(f"Error: {case_dir} does not exist")
        sys.exit(1)

    mode = select_mode(case_dir)
    print(f"[mode_selector] Selected mode: {mode}")

    if execute:
        scripts_dir = Path(__file__).resolve().parent
        execute_mode(mode, case_dir, scripts_dir)
    else:
        print(f"[mode_selector] Dry run. Pass --execute to run.")
        print(f"[mode_selector] Would run: {mode}")
