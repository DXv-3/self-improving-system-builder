# Magic Number Registry

Every number that affects execution behavior must be documented here.
No number is allowed to be 'just what felt right.'

## Current Registry

| Number | Location | Variable | Purpose | Chosen How | Calibration Status | Suggested Calibration Method |
|--------|----------|----------|---------|------------|--------------------|-----------------------------|
| 4 | execute_next.py | THRESHOLD | Auto-execute if risk_level <= this | Arbitrary session choice | UNCALIBRATED | Track actions executed at each risk level. If risk-5 actions succeed >80% of the time, raise threshold to 5. |
| 2 | loop_until_blocked.py | consecutive_failure_limit | Break loop after N consecutive failures | Arbitrary | UNCALIBRATED | After 10 runs, check if 2 is too aggressive (loop stops too early) or too lenient (wastes time on unresolvable actions). |
| 25 | loop_until_blocked.py | max_steps | Max loop iterations per cycle | Arbitrary | UNCALIBRATED | Measure actual steps used per cycle across 10 runs. Set to p95 + 10. |
| 3 | score_actions.py | dep_penalty | Risk delta per unmet dependency | Arbitrary | UNCALIBRATED | Check if dep_penalty=3 correctly prevents out-of-order execution. Reduce if safe actions are being over-penalized. |
| 0.80 | trust_update.py | HIGH_SUCCESS_RATE | Lower risk if category success rate above this | Estimated | UNCALIBRATED | Measure actual success rates. Adjust based on empirical data after 10+ cycles. |
| 0.30 | trust_update.py | LOW_SUCCESS_RATE | Raise risk if category success rate below this | Estimated | UNCALIBRATED | Same as above. |
| 5 | trust_update.py | MIN_SAMPLES | Minimum samples before adjusting risk | Estimated | UNCALIBRATED | Check if 5 samples is enough for stable signal vs. noise. |

## Calibration Method

1. Wire learning_memory.py into persist_result.py (record every cycle outcome)
2. After 10+ cycles, run: `python3 scripts/trust_update.py --preview`
3. Compare suggested adjustments against outcomes in learning_memory.jsonl
4. Update this registry with calibrated values and rationale
5. Bump version in magic_numbers.md when calibrated

## Version
v0.1 — all numbers uncalibrated. Calibration requires learning_memory.py to be wired.
