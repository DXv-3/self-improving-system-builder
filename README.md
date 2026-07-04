# Self-Improving System Builder v1.0.0

A trigger-routed, self-improving task dispatcher with a 7-gate audit protocol, safe/rollback execution, reliability learning loop, and 4-tier test suite.

## Quick Start

```bash
cd self-improving-system-builder
make test        # Run all 4 test suites
make lint        # Syntax check every script
source session-open.sh  # Activate IDKWIDK audit protocol
```

## What's Inside

| Path | Purpose |
|------|---------|
| `scripts/route-task.py` | Scores registry skills against a task, picks execution mode |
| `scripts/execute-plan-safe.py` | Runs the plan with rollback + risk-flag gating |
| `scripts/save-execution-result.sh` | Appends outcome to execution-history.ndjson |
| `scripts/rebuild-reliability.py` | Recomputes reliability scores from history |
| `scripts/mine-recipes.py` | Promotes repeated shell-wins to skill candidates |
| `scripts/detect-skill-conflicts.py` | Finds trigger collisions across skills |
| `scripts/import-existing-skill.py` | Parses SKILL.md, scans scripts, detects side effects |
| `scripts/render-registry-summary.py` | Human-readable registry stats |
| `scripts/build-unified-registry.sh` | Scans all skill sources into one registry.json |
| `scripts/run-router-cycle.sh` | Glue: route -> execute -> save -> rebuild -> mine |
| `tests/test_conflict_detection.py` | Behavioral test: trigger collision detection |
| `tests/test_smoke.py` | End-to-end happy path |
| `tests/test_skill_direct.py` | High-confidence skill_direct execution path |
| `tests/test_property_based.py` | stdlib-only fuzz test, 200 iterations, no pip deps |
| `idkwidk-action-plan.py` | 7-gate audit -> tracked action plan |
| `track-audit.py` | Append-only audit history log |
| `session-open.sh` | Activates IDKWIDK protocol by walking up directory tree |
| `IDKWIDK.md` | 7-gate definitions |
| `RESUME.md` | Session continuity notes |

## Architecture

### Scoring (route-task.py)
- `+1.5` per matched trigger (capped at 4.0), `-2.0` no triggers, `-2.0` no scripts
- `+2.0` reliable, `-3.0` bypass, `-0.5` each risky side effect
- `>= 6.0` → skill_direct | `>= 3.0` → skill_chain | else → shell_direct

### Learning Loop
1. Save outcome → `execution-history.ndjson`
2. Rebuild reliability from history (unknown / reliable / needs_wrapper / bypass)
3. Mine recipes: shell_direct wins ≥3 → promote to auto-skill candidate

### Safety
- Risk flags block execution unless `--allow-risky` passed (exit 2)
- Workspace snapshot before run; rollback on failure
- Graceful SIGINT/SIGTERM handling
