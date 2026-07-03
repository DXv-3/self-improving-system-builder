# IDEAS.md — Everything Discussed, Nothing Lost

This file exists so that no idea raised across the conversation is silently dropped,
even if it wasn't built into the final system.

## Built and Included in This Repo
- Self-Improving System Builder: a trigger-routed task dispatcher with scoring,
  safe/rollback execution, a learning loop (reliability tracking + recipe mining),
  and a 4-tier test suite (conflict, smoke, skill_direct, property-based/stdlib-only).
- IDKWIDK 7-Gate Audit Protocol: a repeatable audit framework (What We Built / Didn't
  Build / Will Break / Can't See / Will Forget / Simpler Version / Do This Next) with
  a persistent, gate-prioritized action-plan tracker and completion-percentage reporting.
- Two `skill.md` operating manuals distilling both of the above into reusable,
  domain-agnostic instructions for a future agent.

## Discussed but Explicitly Out of Scope (not built here, noted for continuity)
- A screenshot showed a separate, unrelated skill session: `create-skybridge`,
  scaffolding a "skill-trigger-hub" demo app (npm-based, package.json present).
  This was correctly identified as a different skill/task and was NOT folded into
  the self-improving-system-builder or IDKWIDK protocol. If this should become its
  own tracked system in the future, it deserves its own repo/skill.md rather than
  being merged into this one.
- The "Code Review and Optimization Guidelines" rubric (bugs, security, performance,
  quality, refactoring) was mapped onto the IDKWIDK gates rather than answered as a
  flat one-off review, on the reasoning that the gate-mapped version is reusable and
  the flat version is disposable. If a literal, single-pass code review deliverable
  is still wanted (not gate-mapped), that is still an open, unexecuted request.

## Meta-Pattern Identified
The real throughline of the conversation was never a single script — it was a
repeatable *method*: turn any raw idea into a routed, safety-gated, self-improving,
tested, audited, and packaged system, then distill the method itself into a
transferable skill.md so it doesn't need to be reasoned out again from scratch.
