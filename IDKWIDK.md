# IDKWIDK Protocol

## The 7 Gates

| Gate | Name | Priority | Rule |
|------|------|----------|------|
| 1 | What We Built | low | Complete inventory |
| 2 | What We Didn't Build | high | Missing scope |
| 3 | What Will Break | critical | First failure mode |
| 4 | What You Can't See | high | Must surface 1+ unasked thing |
| 5 | What You'll Forget | medium | 3-day / 3-week resumption context |
| 6 | The Simpler Version | low | 80/20 check |
| 7 | Do This Next | critical | 1-3 actions, each under 30 min |

## Rules
- Always run. "Outside scope" is a reason to run, not skip.
- Silence = failure. Every gate must have content or "PASS".
- Gate 4 must surface at least 1 thing the user didn't ask about.
- Gate 7 feeds `idkwidk-action-plan.py` and becomes tracked actions.
