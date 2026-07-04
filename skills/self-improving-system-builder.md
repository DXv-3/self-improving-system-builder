# Skill: Self-Improving System Builder

## What This Skill Is

An operating manual for building a **self-improving task router**: a system that
receives a natural-language task, scores candidate skills/scripts against it, executes
the best match safely (with rollback), logs outcomes, and gets smarter over time by
updating reliability scores and promoting repeated shell wins into new skills.

Live implementation: [github.com/DXv-3/self-improving-system-builder](https://github.com/DXv-3/self-improving-system-builder)

## When to Use This Skill

Trigger when a user asks to build any of the following:
- A "system," "pipeline," "router," or "orchestrator" that picks between multiple
  tools, skills, scripts, or commands.
- Something that should "learn" or "get better" from its own execution history.
- A hardened, tested, packaged version of an ad-hoc collection of scripts.
- Anything implying: routing logic + safe execution + feedback loop + tests + packaging.

Do NOT use for single-purpose one-off scripts.

---

## Directory Layout (exact — replicate this structure)

```
<system-name>/
├── README.md
├── Makefile
├── IDKWIDK.md
├── RESUME.md
├── IDEAS.md
├── session-open.sh
├── idkwidk-action-plan.py
├── track-audit.py
├── test-idkwidk.py
├── scripts/
│   ├── route-task.py
│   ├── execute-plan-safe.py
│   ├── save-execution-result.sh
│   ├── rebuild-reliability.py
│   ├── mine-recipes.py
│   ├── detect-skill-conflicts.py
│   ├── import-existing-skill.py
│   ├── render-registry-summary.py
│   ├── build-unified-registry.sh
│   └── run-router-cycle.sh
└── tests/
    ├── test_conflict_detection.py
    ├── test_smoke.py
    ├── test_skill_direct.py
    └── test_property_based.py
```

---

## Core Architecture

### 1. Registry Schema (exact)

```json
{
  "name": "skill-name",
  "triggers": ["phrase one", "phrase two"],
  "scripts": ["run.sh"],
  "side_effects": ["delete", "possible_install", "git_mutation", "network",
                   "writes", "possible_overwrite"],
  "reliability": "unknown",
  "path": "/absolute/path/to/skill"
}
```

`reliability` states: `unknown` | `reliable` | `needs_wrapper` | `bypass`

### 2. Scoring Algorithm (`route-task.py`) — exact values

```python
score = 0

for trig in triggers:
    if trig.lower() in task.lower():
        score += 1.5
score = min(score, 4.0)           # cap at 4.0

if not triggers:        score -= 2.0
if score > 0 and not scripts: score -= 2.0

if reliability == "reliable":   score += 2.0
if reliability == "bypass":     score -= 3.0

if "possible_overwrite" in side_effects: score -= 0.5
if "possible_install"   in side_effects: score -= 0.5
```

**Decision thresholds:**

| Score | Mode | Meaning |
|-------|------|--------|
| >= 6.0 | `skill_direct` | Single clear winner, execute it |
| >= 3.0 | `skill_chain` | Top 3 candidates chained |
| < 3.0  | `shell_direct` | Fall back to task-class shell commands |

**Task classification keywords (shell fallback):**

| Class | Keywords |
|-------|----------|
| `scaffold_app` | scaffold, create app, demo app, init project |
| `init_repo` | init repo, git init, git setup |
| `inspect_environment` | inspect, analyze, what is, show me |
| `reverse_engineer_skill` | reverse engineer, understand skill |
| `unknown` | (default) |

**Output contract:** write to `last-plan.json` AND print JSON to stdout. Both. Always.

### 3. Safe Execution (`execute-plan-safe.py`)

**Risk flag gate (non-negotiable):**
```python
DANGEROUS = {"possible_overwrite", "possible_install", "git_mutation",
             "delete", "unknown_script_side_effects"}

if risk_flags & DANGEROUS and not allow_risky:
    print(json.dumps({"status": "blocked", "reason": "requires --allow-risky"}))
    sys.exit(2)   # exit code 2 = blocked, not failed
```

**Rollback:** snapshot workspace before execution. On failure, delete files created during the run.

**Timeouts + output truncation:**
- Per-command timeout: configurable, default 120 seconds
- Captured stdout/stderr: truncated to 2000 bytes by default

**Signal handling:** catch SIGINT/SIGTERM, stop cleanly between commands.

**Required output fields:**
```json
{
  "execution_result": {
    "status": "success | failed | blocked",
    "chosen_mode": "skill_direct | skill_chain | shell_direct",
    "winner": "<skill name or 'shell'>",
    "commands_run": ["cmd1", "cmd2"],
    "artifacts_found": ["relative/path/to/created/file"],
    "should_save_recipe": true,
    "should_draft_skill": false
  }
}
```

### 4. Learning Loop

```
save-execution-result.sh
  └─ appends {timestamp, task, task_class, execution_result}
     to execution-history.ndjson

rebuild-reliability.py
  └─ 0 runs          → unknown
     ≥2 fail, 0 win  → bypass      (-3.0 score penalty)
     ≥3 win, 0 fail  → reliable    (+2.0 score bonus)
     fail > win      → needs_wrapper
     else            → unknown

mine-recipes.py
  └─ task_classes where shell_direct won ≥3 times
     → proposes recommended_skill_name = "auto-" + task_class
     → lists common_commands to seed the new skill's script

detect-skill-conflicts.py
  └─ trigger claimed by >1 skill → surface before causing ambiguous routing
```

Run order after every execution:
```bash
save-execution-result.sh → rebuild-reliability.py → mine-recipes.py
```

### 5. Testing — Four Tiers (non-negotiable)

**Tier 1 — Conflict/Unit:** trigger collision detection. Assert exact conflict count.

**Tier 2 — Smoke:** full pipeline, one pass, happy path. Temp dirs only.
Assert each stage produces valid output for the next.

**Tier 3 — Direct-path:** explicitly assert `score >= 6.0` and `execution_mode == "skill_direct"`.

**Tier 4 — Property-based (stdlib only, no pip):**
```python
import random, string
random.seed(42)  # reproducible

# Generate:
# - Random task strings including special chars: " ' ` $ ; & | ( ) { } < > ! # \n \t
# - Unicode: é 中 こ س अ ☃ … (zero-width space)
# - Random registries: 0-20 skills, random triggers/scripts/side_effects/reliability
# - Random execution histories

# Assert INVARIANTS:
# - No crashes (returncode == 0) on any input
# - Valid JSON always returned
# - Required fields always present
# - Scores within [-10, 10]
# - execution_mode always in known set
# - risk_flags always subset of known set
# - task string preserved end-to-end through save

# Run 50-200+ iterations. Report: pass rate, first 100 chars of any failure
```

Why no pip: zero-dependency = portable, no setup, no version conflicts.

### 6. Makefile Targets (minimum required)

```makefile
test:              # runs all 4 tiers
test-smoke:        # tier 2 alone
test-conflict:     # tier 1 alone
test-skill-direct: # tier 3 alone
test-property N=200: # tier 4, N iterations
lint:              # py_compile every .py, bash -n every .sh
audit-status:      # show IDKWIDK action plan + completion %
audit-done ID=n:   # mark action #n done
audit-reset:       # clear action plan
```

### 7. Path Convention

```python
data_root = Path(os.getenv("GROK_PLUGIN_DATA",
                 str(Path.home() / ".grok" / "operator-router")))
```

Never hardcode absolute paths.

### 8. Packaging Checklist

```
[ ] chmod 755 all .sh and .py entrypoints
[ ] Strip __pycache__
[ ] Produce <system-name>-vX.Y.Z.zip
[ ] Produce <system-name>.bundle (git bundle --all)
[ ] git bundle verify → "The bundle is okay"
[ ] Re-run full test suite against packaged directory
[ ] Report pass/fail table before declaring done
[ ] README.md, RESUME.md, IDEAS.md all present
```

---

## Mistakes to Avoid

- **Hardcoding paths** — always use env var with `$HOME`-based default.
- **Silently running risky commands** — `--allow-risky` gate is the entire safety model.
- **Testing only the happy path** — Tier 4 exists for malformed/adversarial inputs.
- **Writing to stdout only** — always write `last-plan.json` AND print to stdout.
- **Skipping property-based testing** — build it with stdlib; the constraint is a feature.
- **Treating `bypass` as just another state** — it scores -3.0 and should essentially never win.

---

## Companion Skills

- `conversation-to-system-pipeline.md` — the parent skill
- `idkwidk-audit-protocol.md` — run before declaring done
