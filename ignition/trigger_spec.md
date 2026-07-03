# Ignition Layer Spec

Status: UNBUILT — closes IGNITION_GAP blind spot.

## The Problem
The system executes adaptive cycles but only when manually triggered.
Without an ignition layer, 'self-improving' means 'improves when someone remembers to run it.'

## Options to Evaluate

| Option | Implementation | Trigger | Risk |
|--------|---------------|---------|------|
| Cron job | `crontab -e` entry calling `run_operator_layer.py` | Time-based | Low — no code changes |
| File watcher | `watchdog` on case_dir for new claim files | Event-based | Low — pip install watchdog |
| HTTP endpoint | FastAPI POST /trigger calling run_operator_layer.py | On-demand | Medium — needs server |
| Post-commit hook | `.git/hooks/post-commit` script | Git push | Low — local only |
| GitHub Actions | `.github/workflows/cycle.yml` on push | Push/schedule | Low — no local deps |

## Recommended: GitHub Actions (lowest friction)

Create `.github/workflows/cycle.yml`:
```yaml
name: Self-Improving Cycle
on:
  push:
    paths: ['examples/**', 'scripts/**']
  schedule:
    - cron: '0 */6 * * *'  # every 6 hours
jobs:
  cycle:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install pytest
      - run: python3 run_operator_layer.py examples/bundle_forensics_case
```

## Decision Required
Choose one option and implement it.
Risk if unresolved: System only self-improves when manually triggered.
This is the IGNITION_GAP. It is the #1 gap between 'runs once' and 'self-improving.'
