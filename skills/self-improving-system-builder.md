# Skill: Self-Improving System Builder

## When to Use This Skill
Trigger this skill when a user asks you to:
- Build a "system," "pipeline," "router," or "orchestrator" that picks between multiple tools/skills/scripts to accomplish tasks.
- Create something that should "learn" from its own execution history (reliability tracking, recipe mining).
- Turn an ad-hoc set of scripts into a hardened, tested, packaged deliverable.
- Any request that implies: routing logic + safe execution + feedback loop + tests + packaging.

Do NOT use this skill for one-off scripts or single-purpose utilities with no routing/learning/registry component -- that's overkill.

## What This Skill Produces
A self-contained directory (packaged as a versioned zip, e.g. `<system-name>-v1.0.0.zip`) with this exact layout:

```
<system-name>/
├── README.md
├── Makefile
├── IDKWIDK.md              # see companion skill: idkwidk-audit-protocol.md
├── RESUME.md               # session continuity notes
├── session-open.sh         # activates audit protocol for the project
├── idkwidk-action-plan.py  # audit -> tracked actions
├── track-audit.py          # audit history log
├── test-idkwidk.py         # checks protocol files are present
├── scripts/
│   ├── route-task.py               # scores candidates, decides execution mode
│   ├── execute-plan-safe.py        # runs the plan with rollback + risk gating
│   ├── save-execution-result.sh    # appends outcome to execution-history.ndjson
│   ├── rebuild-reliability.py      # recomputes reliability from history
│   ├── mine-recipes.py             # promotes repeated shell-wins to skill candidates
│   ├── detect-skill-conflicts.py   # finds trigger collisions across skills
│   ├── import-existing-skill.py    # parses SKILL.md, scans scripts, detects side effects
│   ├── render-registry-summary.py  # human-readable registry stats
│   ├── build-unified-registry.sh   # scans all skill sources into one registry.json
│   └── run-router-cycle.sh         # glue: route -> execute -> save -> rebuild -> mine
└── tests/
    ├── test_smoke.py              # end-to-end happy path
    ├── test_conflict_detection.py # behavioral test on trigger collisions
    ├── test_skill_direct.py       # verifies high-confidence direct-execution path
    └── test_property_based.py     # stdlib-only fuzz testing (NO pip deps)
```

## Core Architecture Rules (carry these exactly)

### 1. Registry format
Every skill is represented as:
```json
{
  "name": "skill-name",
  "triggers": ["phrase one", "phrase two"],
  "scripts": ["run.sh"],
  "side_effects": ["delete", "possible_install", "git_mutation", "network", "writes", "possible_overwrite"],
  "reliability": "unknown | reliable | needs_wrapper | bypass",
  "path": "/abs/path/to/skill"
}
```

### 2. Scoring algorithm (route-task.py)
- +1.5 per matched trigger substring (case-insensitive), capped at 4.0.
- -2.0 if the skill has no triggers at all.
- -2.0 if score > 0 but the skill has no scripts (can't actually execute).
- +2.0 if `reliability == "reliable"`.
- -3.0 if `reliability == "bypass"` (known-broken skill -- actively avoid).
- -0.5 for each of `possible_overwrite` / `possible_install` present in side_effects (each also adds a risk_flag).
- Decision thresholds:
  - score >= 6.0 -> `execution_mode = "skill_direct"` (single clear winner)
  - score >= 3.0 -> `execution_mode = "skill_chain"` (top 3 candidates chained)
  - else -> `execution_mode = "shell_direct"` (fall back to task-class-specific shell commands)
- Task classification (simple keyword match) feeds shell fallback commands:
  - `scaffold_app`, `init_repo`, `inspect_environment`, `reverse_engineer_skill`, `unknown`.
- Every plan is written to `last-plan.json` AND printed as JSON to stdout -- always do both.

### 3. Safe execution (execute-plan-safe.py)
- Dangerous risk flags (`possible_overwrite`, `possible_install`, `git_mutation`, `delete`, `unknown_script_side_effects`) **block execution** unless `--allow-risky` is passed. Exit code 2 on block.
- Snapshot the workspace file tree before running; on failure (and if not `shell_direct`), roll back any newly created files/dirs.
- Respect a timeout per command (config default 120s) and truncate captured stdout/stderr (default 2000 bytes).
- Handle SIGINT/SIGTERM gracefully -- stop between commands, don't kill mid-write.
- Output must include `execution_result.status`, `chosen_mode`, `winner`, `commands_run`, `artifacts_found`, `should_save_recipe`, `should_draft_skill`.

### 4. Learning loop (the "self-improving" part)
1. `save-execution-result.sh` appends `{timestamp, task, task_class, execution_result}` to `execution-history.ndjson`.
2. `rebuild-reliability.py` recomputes each skill's reliability from history:
   - 0 total runs -> `unknown`
   - >=2 fails, 0 successes -> `bypass`
   - >=3 successes, 0 fails -> `reliable`
   - fails > successes -> `needs_wrapper`
   - else -> `unknown`
3. `mine-recipes.py` looks for task_classes where `shell_direct` won >=3 times with successful outcomes, and proposes promoting the common commands into a new skill (`recommended_skill_name = "auto-" + task_class`).
4. `detect-skill-conflicts.py` finds any trigger string claimed by more than one skill.

### 5. Testing philosophy (non-negotiable)
Always ship four kinds of tests:
1. **Conflict/unit test** -- smallest possible behavioral test on the riskiest pure-logic script.
2. **Smoke test** -- full pipeline, one pass, happy path, temp dirs only.
3. **Direct-path test** -- proves the best case routing decision (skill_direct) fires correctly, with explicit score threshold assertions.
4. **Property-based test** -- write WITHOUT pip dependencies (no Hypothesis). Use stdlib `random` + `string`, seed it (`random.seed(42)`), generate random task strings with special chars/unicode, random registries, random histories. Assert invariants, not exact outputs. Run 50-200+ iterations.

### 6. Packaging
- Ship a `Makefile` with: `test`, `lint`, `audit-status`, `audit-done ID=n`, `audit-reset`.
- Set executable permissions on all `.sh` and `.py` entrypoints before packaging.
- Strip `__pycache__` before zipping.
- Name archive `<system-name>-vX.Y.Z.zip`. Re-run full test suite as final sanity check.
- Always include `README.md` and `RESUME.md`.

## Mistakes to Avoid
- Don't hardcode absolute paths -- always resolve via `os.getenv` with a sensible default under `$HOME`.
- Don't let `execute-plan-safe.py` silently run risky commands -- `--allow-risky` is the entire safety model.
- Don't test only the happy path -- property-based test catches shell-injection inputs and malformed registries.
- Don't forget to write BOTH stdout AND file (`last-plan.json`, `last-execution.json`).
- Don't treat "no pip available" as a reason to skip a testing layer -- reimplement with stdlib.

## Adapting to a New Domain
- Registry entries become whatever your routable unit is; keep `triggers`, `reliability`, `side_effects` as universal fields.
- Keep the four-tier scoring bands -- they generalize to any confidence-gated dispatcher.
- Keep the rollback-on-failure + risk-flag-gating pattern -- it's the core safety primitive.
- Always close the loop with `idkwidk-audit-protocol.md` before declaring the system done.
