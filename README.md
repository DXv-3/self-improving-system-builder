# Self-Improving System Builder v1.0.0

A complete, tested, and audited system for routing tasks to the best available skill,
executing safely with rollback, learning from outcomes, and packaging reusable
operating manuals (skill.md) for future agents.

## Quick Start

```bash
cd self-improving-system-builder
make test        # runs all 4 test suites
make lint        # syntax-checks every script
source session-open.sh  # activates IDKWIDK audit protocol
```

## Structure

```
./
├── README.md                        # this file
├── IDEAS.md                         # everything discussed, nothing lost
├── .gitignore
├── self-improving-system-builder/
│   ├── IDKWIDK.md                   # 7-gate audit protocol definition
│   ├── Makefile                     # test / lint / audit targets
│   ├── README.md
│   ├── RESUME.md                    # session continuity — pick up cold
│   ├── idkwidk-action-plan.py       # audit → tracked action plan
│   ├── session-open.sh              # activate audit protocol
│   ├── test-idkwidk.py              # verify protocol files present
│   ├── track-audit.py               # append-only audit history
│   ├── scripts/
│   │   ├── route-task.py            # score candidates, decide execution mode
│   │   ├── execute-plan-safe.py     # run plan with rollback + risk gating
│   │   ├── save-execution-result.sh # append outcome to history
│   │   ├── rebuild-reliability.py   # recompute reliability from history
│   │   ├── mine-recipes.py          # promote shell-wins to skill candidates
│   │   ├── detect-skill-conflicts.py# find trigger collisions
│   │   ├── import-existing-skill.py # parse SKILL.md + detect side effects
│   │   ├── render-registry-summary.py
│   │   ├── build-unified-registry.sh
│   │   └── run-router-cycle.sh      # glue: route→execute→save→rebuild→mine
│   └── tests/
│       ├── test_conflict_detection.py
│       ├── test_smoke.py
│       ├── test_skill_direct.py
│       └── test_property_based.py   # stdlib-only, no pip, 200 iterations
└── skills/
    ├── self-improving-system-builder.md   # reusable operating manual
    └── idkwidk-audit-protocol.md          # reusable audit skill
```

## Test Results (verified before push)
- `test_conflict_detection.py` — PASS
- `test_smoke.py` — PASS  
- `test_skill_direct.py` — PASS
- `test_property_based.py` — PASS (100% pass rate, 200 iterations)
