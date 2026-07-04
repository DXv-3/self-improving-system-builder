# self-improving-system-builder

A self-improving task router with IDKWIDK 7-gate audit protocol, confidence-scored
routing engine, safe rollback execution, outcome-driven learning loop, and a
4-tier stdlib-only test suite.

## Quick Start

```bash
git clone https://github.com/DXv-3/self-improving-system-builder
cd self-improving-system-builder
make test       # runs all 4 test suites
make lint       # syntax-checks every script
source session-open.sh  # activates IDKWIDK audit protocol
```

## What's Inside

| Path | Contents |
|------|----------|
| `scripts/` | 10 executable scripts: route-task, execute-plan-safe, save-execution-result, rebuild-reliability, mine-recipes, detect-skill-conflicts, import-existing-skill, render-registry-summary, build-unified-registry, run-router-cycle |
| `tests/` | 4 test suites: conflict detection, smoke, skill_direct path, property-based (stdlib, no pip) |
| `idkwidk-action-plan.py` | Converts audit findings into prioritized, tracked action plan |
| `track-audit.py` | Append-only audit history log |
| `skills/` | Two reusable skill.md operating manuals |

## Architecture

```
Task String
    │
    ▼
route-task.py  ──── registry.json ──── scoring engine
    │                                  (+1.5/trigger, cap 4.0,
    ▼                                   +2.0 reliable, -3.0 bypass)
last-plan.json
    │
    ▼
execute-plan-safe.py  ─── risk gate (blocks unless --allow-risky)
    │                 ─── workspace snapshot + rollback on failure
    ▼
save-execution-result.sh ─► execution-history.ndjson
    │
    ▼
rebuild-reliability.py   ─► updates reliability state per skill
    │
    ▼
mine-recipes.py          ─► promotes shell_direct wins to skill candidates
```

## The IDKWIDK Protocol

Before any task is declared done, run the 7-gate audit:
1. What We Built  2. What We Didn't Build  3. What Will Break
4. What You Can't See  5. What You'll Forget  6. The Simpler Version
7. Do This Next

Gate 7 outputs feed directly into `idkwidk-action-plan.py` as tracked actions.

## License
MIT
