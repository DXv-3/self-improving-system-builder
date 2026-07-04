# Self-Improving System Builder

A self-contained task routing and execution system with a built-in learning loop.

## Quick Start

```bash
make test
make lint
source session-open.sh
```

## Core Loop

```
route-task.py → execute-plan-safe.py → save-execution-result.sh
     ↑                                         ↓
registry.json ← rebuild-reliability.py ← execution-history.ndjson
                        ↓
                 mine-recipes.py (promotes shell wins to new skills)
```
