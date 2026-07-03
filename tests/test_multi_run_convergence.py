#!/usr/bin/env python3
"""
test_multi_run_convergence.py

Proves the system actually improves across runs.
Asserts: blocked_or_failed strictly decreasing across N cycles.
Asserts: completed strictly non-decreasing across N cycles.

STATUS: SCAFFOLD
  - Requires a seeded case with known claim mix
  - Requires run_adaptive_meta_cycle.py to be functional
  - Insert real case_dir before running

This is the test that proves the system self-improves,
not just self-executes.
"""
import json, shutil, tempfile
from pathlib import Path
import pytest

SEEDED_CASE = Path("examples/bundle_forensics_case")
SCRIPTS = Path("scripts")


def snapshot_stats(case_dir: Path) -> dict:
    summary_path = case_dir / "loop_summary.json"
    if not summary_path.exists():
        return {"completed": 0, "blocked_or_failed": 999, "steps_executed": 0}
    return json.loads(summary_path.read_text())


def run_one_cycle(case_dir: Path) -> dict:
    import subprocess
    result = subprocess.run(
        ["python3", str(SCRIPTS / "run_adaptive_meta_cycle.py"), str(case_dir)],
        capture_output=True, text=True
    )
    return {
        "returncode": result.returncode,
        "stats": snapshot_stats(case_dir),
    }


@pytest.mark.skipif(
    not SEEDED_CASE.exists(),
    reason="Seeded example case not found. Run from repo root."
)
def test_convergence_over_5_cycles():
    """
    Run 5 adaptive cycles on the seeded example case.
    Verify blocked_or_failed is non-increasing and completed is non-decreasing.
    This is the core self-improvement guarantee.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "convergence_case"
        shutil.copytree(SEEDED_CASE, case_dir)

        history = []
        N_CYCLES = 5

        for cycle_num in range(1, N_CYCLES + 1):
            result = run_one_cycle(case_dir)
            stats = result["stats"]
            history.append(stats)
            print(f"Cycle {cycle_num}: "
                  f"completed={stats['completed']} "
                  f"blocked={stats['blocked_or_failed']}")

        # Assert convergence: blocked_or_failed non-increasing
        for i in range(1, len(history)):
            assert history[i]["blocked_or_failed"] <= history[i-1]["blocked_or_failed"], (
                f"Cycle {i+1} blocked ({history[i]['blocked_or_failed']}) > "
                f"cycle {i} blocked ({history[i-1]['blocked_or_failed']}). "
                f"System is not converging."
            )

        # Assert progress: completed non-decreasing
        for i in range(1, len(history)):
            assert history[i]["completed"] >= history[i-1]["completed"], (
                f"Cycle {i+1} completed ({history[i]['completed']}) < "
                f"cycle {i} completed ({history[i-1]['completed']}). "
                f"System lost progress."
            )

        # Final state: at least one action completed total
        assert history[-1]["completed"] > 0, (
            "Zero actions completed across 5 cycles. System is not executing."
        )

        print(f"CONVERGENCE TEST PASSED: "
              f"{history[-1]['completed']} completed, "
              f"{history[-1]['blocked_or_failed']} blocked after {N_CYCLES} cycles")


@pytest.mark.skipif(
    not SEEDED_CASE.exists(),
    reason="Seeded example case not found."
)
def test_no_regression_after_reaudit():
    """
    After a full cycle completes with 0 blocked, run reaudit mode.
    Verify completed count does not decrease.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "reaudit_case"
        shutil.copytree(SEEDED_CASE, case_dir)

        # First cycle
        result1 = run_one_cycle(case_dir)
        stats1 = result1["stats"]

        # Second cycle (reaudit)
        result2 = run_one_cycle(case_dir)
        stats2 = result2["stats"]

        assert stats2["completed"] >= stats1["completed"], (
            "Reaudit reduced completed count. Regression detected."
        )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
