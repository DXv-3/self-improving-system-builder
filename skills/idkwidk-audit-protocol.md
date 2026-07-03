# Skill: IDKWIDK 7-Gate Audit + Action Plan Loop

## When to Use This Skill
Use this skill whenever a user asks you to:
- "Review," "audit," "harden," or "find what's missing" in a system, codebase, or deliverable.
- Do a comprehensive code review covering bugs, security, performance, quality, and refactoring.
- Declare something "done" -- this skill should run *before* any completion claim, not after.

Core rule: **"Outside scope" is a reason to run this audit, not a reason to skip it.** Silence on any gate = failure of that gate.

## The 7 Gates

| Gate | Name | Priority | Purpose |
|------|------|----------|---------|
| 1 | What We Built | low | Complete inventory of what exists |
| 2 | What We Didn't Build | high | Missing scope, unaddressed requirements |
| 3 | What Will Break | critical | First likely failure mode, edge cases, bugs |
| 4 | What You Can't See | high | Domain blind spots — must surface 1+ thing the user didn't ask about |
| 5 | What You'll Forget | medium | Resumption context: 3 days / 3 weeks out |
| 6 | The Simpler Version | low | 80/20 check |
| 7 | Do This Next | critical | 1-3 actions, each under 30 minutes |

## Mapping Code Review Rubrics onto Gates
- Bug Detection & Resolution -> Gate 3
- Security & Hardening -> Gate 3 / Gate 4
- Performance Optimization -> Gate 6 or Gate 2
- Code Quality & Maintainability -> Gate 2 and Gate 5
- Refactoring & Simplification -> Gate 6
- Always run Gate 1, Gate 4, Gate 7 even if the rubric didn't ask for them.

## Execution Steps
1. Go gate-by-gate. Write concrete findings as a list. If truly clean, write `"PASS"` -- never leave blank.
2. Convert to JSON audit object:
```json
{
  "gates": {
    "Gate 2: What We Didn't Build": ["finding one"],
    "Gate 3: What Will Break": ["finding"],
    "Gate 4: What You Can't See": ["finding"],
    "Gate 7: Do This Next": ["action 1", "action 2"]
  }
}
```
3. Feed to `idkwidk-action-plan.py <audit.json>`, which:
   - Maps gates to priorities: Gate 3/7 -> critical, Gate 2/4 -> high, Gate 5 -> medium, Gate 1/6 -> low.
   - Prefixes actions: Build (2), Fix (3), Investigate (4), Document (5), Simplify (6), DO NOW (7).
   - Deduplicates, assigns effort estimates, persists to `~/.idkwidk/action-plan.json`.
4. Work to closure (100%), not just "acceptable":
   - States: `open`, `in-progress`, `blocked`, `deferred`, `done`, `wontfix`.
   - Sort: priority first, then status, then id.
   - Show completion % every status check.
5. Close the loop: Audit -> Action Plan -> Execute -> Re-audit -> repeat.
6. Log every audit to `audit-history.ndjson` (timestamp, project, gates, total_findings).

## Output Format
1. Delta since last check (not full restate).
2. Current completion percentage (computed, not estimated).
3. Gate 4 blind spots called out explicitly.
4. Next 1-3 Gate 7 actions if open.

## Mistakes to Avoid
- Never skip a gate because the request framing didn't ask for it.
- Never report findings without updating the action plan.
- Never mark `done` without a timestamp.
- Don't let Gate 7 balloon past 3 items.
- Always use gate structure even for "review and optimize" style requests.

## Adapting to a New Project
- Drop `IDKWIDK.md`, `session-open.sh`, `idkwidk-action-plan.py` into any project root.
- `test-idkwidk.py` verifies `IDKWIDK.md`, `session-open.sh`, and `RESUME.md` exist.
- Composes with `self-improving-system-builder.md`: audit what you built, feed findings back.
