# self-improving-system-builder

Adaptive execution system with forensic truth-lineage, execution-forcing
meta-cycle, blocker classification, patch generation, and approval policy.

## Architecture

```
scripts/          Runnable Python modules (17 scripts)
schemas/          JSON schemas for all structured artifacts (5 schemas)
tests/            Pytest-compatible test suite (5 files, all verified passing)
examples/         Seeded example cases for bundle_forensics and router_handoff
skills/           Skill definitions for parent and sub-skills (6 files)
```

## Quick start

```bash
# Run full adaptive meta-cycle on the seeded bundle-forensics case
python3 scripts/run_adaptive_meta_cycle.py examples/bundle_forensics_case

# Run all tests
python3 -m pytest tests/ -v
```

## Execution modes

| Mode | Entry point | When to use |
|------|-------------|-------------|
| Bundle forensics | `run_system_cycle.py <case> bundle_forensics` | Verify a bundle before promotion |
| Router handoff | `run_system_cycle.py <case> router_handoff` | Import a router preview and execute |
| Full meta-cycle | `run_full_meta_cycle.py <case>` | Reconcile + patch + loop + classify |
| Adaptive meta-cycle | `run_adaptive_meta_cycle.py <case>` | Full cycle + policy + follow-ups + retry |

## Next build targets (discussed, not yet built)

- `learning_memory.py` — persist cross-run lessons and outcomes
- `trust_update.py` — update risk weights from repeated patterns
- `mode_selector.py` — auto-choose execution mode from project state
- `run_operator_layer.py` — single top-level launcher
- multi-run learning tests

## Evidence classes

| Class | Production allowed |
|-------|--------------------|
| runtime_proven | Yes |
| compiler_inferred | Only if labeled |
| reference_only | No |
| unverified | No |
| contradicted | No |
