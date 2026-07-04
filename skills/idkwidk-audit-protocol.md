# Skill: IDKWIDK 7-Gate Audit + Action Plan Loop

## What This Skill Is

A repeatable, gate-structured audit framework that runs before any system, codebase,
or deliverable is declared "done." It converts findings into a prioritized, tracked,
completion-percentaged action plan that persists across sessions.

The name stands for: **I Don't Know What I Don't Know** — which is the problem it solves.

Live implementation: [github.com/DXv-3/self-improving-system-builder](https://github.com/DXv-3/self-improving-system-builder)

## When to Use This Skill

- User says "review," "audit," "harden," "find what's missing," or "is it done?"
- User asks for a code review (bugs, security, performance, quality, refactoring)
  — run the gate structure underneath, not a flat review.
- Before declaring any system "done."
- A session is ending — run gates 5 and 7 at minimum.

**Core rule: Silence on any gate = failure of that gate.**

---

## The 7 Gates

| Gate | Name | Priority | Purpose |
|------|------|----------|---------|
| 1 | What We Built | low | Complete inventory of what exists |
| 2 | What We Didn't Build | high | Missing scope, unaddressed requirements |
| 3 | What Will Break | critical | First likely failure mode, edge cases, bugs |
| 4 | What You Can't See | high | Domain blind spots — **must surface ≥1 thing the user didn't ask about** |
| 5 | What You'll Forget | medium | Resumption context: what a future session needs to know |
| 6 | The Simpler Version | low | 80/20 check — is there a simpler path to the same goal? |
| 7 | Do This Next | critical | 1–3 concrete actions, each estimated under 30 minutes |

**Gate 4 is the most important gate.** If Gate 4 is empty, you haven't looked hard enough.

**Gate 7 must not balloon.** If more than 3 urgent actions exist, that's a Gate 2 or Gate 6 finding.

---

## Mapping Code Review Rubrics onto the Gates

| Code Review Category | Gate |
|---------------------|------|
| Bug Detection & Resolution | Gate 3 |
| Security & Hardening | Gate 3 + Gate 4 (blind-spot security) |
| Performance Optimization | Gate 6 or Gate 2 |
| Code Quality & Maintainability | Gate 2 + Gate 5 |
| Refactoring & Simplification | Gate 6 |

Always run Gates 1, 4, and 7 even if the user's rubric didn't ask for them.

---

## Execution Steps

### Step 1: Run the audit gate by gate

For each gate: write concrete findings as a list. If truly clean: write `"PASS"`.
Never leave a gate blank.

### Step 2: Produce audit JSON

```json
{
  "project": "project-name-or-path",
  "gates": {
    "Gate 1: What We Built": ["item 1", "item 2"],
    "Gate 2: What We Didn't Build": ["finding 1"],
    "Gate 3: What Will Break": ["finding"],
    "Gate 4: What You Can't See": ["blind spot"],
    "Gate 5: What You'll Forget": ["resumption note"],
    "Gate 6: The Simpler Version": "PASS",
    "Gate 7: Do This Next": ["action 1", "action 2"]
  }
}
```

### Step 3: Feed to `idkwidk-action-plan.py`

```bash
python3 idkwidk-action-plan.py audit.json
```

The script:
- Maps gates to priorities: Gate 3/7 → `critical`, Gate 2/4 → `high`,
  Gate 5 → `medium`, Gate 1/6 → `low`
- Prefixes actions: Build (2), Fix (3), Investigate (4), Document (5),
  Simplify (6), Address (1), DO NOW (7)
- **Deduplicates** against existing actions
- Assigns effort: `30 min` for critical/high, `1 hour` for others
- Persists to `~/.idkwidk/action-plan.json`

### Step 4: Work the action plan to closure

Status states: `open` | `in-progress` | `blocked` (requires reason) |
`deferred` | `done` | `wontfix`

Sort display: priority first, then status, then id.

**Show completion % every time status is checked:**
```
Completion: done / total × 100
```

Only claim "done" when completion = 100% AND a fresh audit produces zero new critical/high findings.

### Step 5: Log to audit history

```json
{"timestamp": "...", "project": "...", "gates": {...}, "total_findings": 12}
```

Show trend when relevant: "Last audit: 12 findings → this audit: 3 findings."

---

## Output Format

1. **Delta since last check** — what changed, not a full restate
2. **Current completion %** — computed, not estimated
3. **Gate 4 findings called out explicitly**
4. **Next 1–3 Gate 7 actions** if any remain open

---

## Action Plan CLI Reference

```bash
python3 idkwidk-action-plan.py               # show current status
python3 idkwidk-action-plan.py audit.json    # ingest audit, generate actions
python3 idkwidk-action-plan.py --status      # table + completion %
python3 idkwidk-action-plan.py --done 3      # mark #3 done (with timestamp)
python3 idkwidk-action-plan.py --start 2     # mark #2 in-progress
python3 idkwidk-action-plan.py --block 4 "waiting on API key"
python3 idkwidk-action-plan.py --defer 5
python3 idkwidk-action-plan.py --json        # dump full plan as JSON
python3 idkwidk-action-plan.py --reset       # clear plan
```

---

## Protocol Files (drop into any project root)

| File | Purpose |
|------|---------|
| `IDKWIDK.md` | Gate definitions — human-readable reference |
| `session-open.sh` | `source session-open.sh` — activates protocol |
| `idkwidk-action-plan.py` | Full action plan engine |
| `track-audit.py` | Append-only audit history |
| `test-idkwidk.py` | Wire-up check: IDKWIDK.md + session-open.sh + RESUME.md all exist |

---

## The Loop

```
Audit → Action Plan → Execute Actions → Re-Audit → New Actions → repeat
```

Exit condition: re-audit produces only duplicate findings, all marked `done`.

---

## Mistakes to Avoid

- **Skipping a gate** — all 7 run, every time.
- **Reporting findings without updating the action plan** — untracked findings repeat.
- **Marking done without a timestamp** — the timestamp is the proof.
- **Leaving Gate 4 empty** — look harder.
- **Answering a code review as a flat unstructured review** — run the gates.
- **Treating the audit as a one-time event** — value is in the loop.

---

## Adapting to a New Project

1. Drop protocol files into project root.
2. Run `python3 test-idkwidk.py .` to verify wire-up.
3. `source session-open.sh` at start of each session.
4. Run audit at end of each significant block of work.
5. Never declare a milestone complete without Gate 7 showing no open critical actions.

---

## Companion Skills

- `conversation-to-system-pipeline.md` — parent skill; IDKWIDK is Phase 3 of it
- `self-improving-system-builder.md` — primary system audited with this protocol
