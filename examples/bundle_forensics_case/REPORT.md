# System Run Report
Generated: 2026-07-03 (seeded)
Case: examples/bundle_forensics_case

**Enforcement Prompt:** Active (v1.0.0)

## What Happened
This is the seeded example case. Run `python3 run_operator_layer.py examples/bundle_forensics_case`
to generate a real report. This file will be overwritten by the first cycle.

## Claims in This Case
- C001: proof_gate — unverified
- C002: cost_control — reference_only
- C003: background_collection — reference_only
- C004: memory_persistence — unverified
- C005: config_loading — compiler_inferred

## Expected Cycle Behavior
- BFA-001, BFA-002, BFA-003, BFA-004 should execute (risk_level <= 4, file_write)
- BFA-005 should block (risk_level 7, manual)
- After cycle: 4 completed, 1 blocked
- Proof checks PROOF-01 through PROOF-04 should pass
- Retry strategy: await_approval_then_rerun (BFA-005 needs human)

## Before Marking This Done
- [ ] WHAT WE BUILT: run cycle and record commit SHA
- [ ] WHAT WILL BREAK: BFA-005 will always block until manually approved
- [ ] WHAT WE DO NOT KNOW: whether convergence holds across 5 cycles
