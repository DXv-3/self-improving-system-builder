# ROADMAP: Unbuilt But Discussed

Everything discussed in this session that was not fully implemented.
Do not re-discover. Do not re-discuss. Build these in order.

---

## Priority 1: Wire the Loop Closed

### learning_memory.py → persist_result.py integration
  Status: SCAFFOLDED (scripts/learning_memory.py exists)
  What's missing: Wire `record_cycle_outcome()` into `persist_result.py`
    after every cycle completes. Currently learning_memory.py exists
    but nothing calls it. Cross-run learning is silent.
  Risk if unbuilt: Every run starts from zero. System cannot improve.
  Effort: ~20 lines in persist_result.py

### learning_memory.py → score_actions.py integration
  Status: SCAFFOLDED
  What's missing: Wire `get_risk_adjustment()` into score_actions.py
    before scoring. Currently trust_update.py computes adjustments
    but score_actions.py never reads them.
  Risk if unbuilt: Trust calibration has no effect on execution.
  Effort: ~10 lines in score_actions.py

### multi_run_convergence_test — real data
  Status: SCAFFOLDED (tests/test_multi_run_convergence.py exists)
  What's missing: A seeded case where convergence is testable.
    The scaffold exists but the assertions need a real case_dir
    with known claim types and expected resolution paths.
  Risk if unbuilt: No proof the system self-improves.
  Effort: seed a case + 1 test run to verify

---

## Priority 2: Build the Interface Layer

### generate_human_report.py
  Status: SPECIFIED (interface_layer/spec.md)
  What's missing: The script itself. ~50 lines of Python.
    Reads loop_summary.json + next_blockers.md + retry_strategy.json
    Outputs REPORT.md in plain English.
  Risk if unbuilt: System is unusable by anyone except the builder.
  Effort: ~50 lines

### serve.py (optional after generate_human_report.py)
  Status: SPECIFIED (interface_layer/spec.md)
  What's missing: Flask/FastAPI app serving progress_snapshot.md
  Risk if unbuilt: No web interface (acceptable if generate_human_report.py exists)
  Effort: ~30 lines

---

## Priority 3: Build the Ignition Layer

### GitHub Actions cycle workflow
  Status: SPECIFIED (ignition/trigger_spec.md)
  What's missing: .github/workflows/cycle.yml
    Schedule: every 6 hours + on push to examples/
    Runs: python3 run_operator_layer.py examples/bundle_forensics_case
  Risk if unbuilt: System only self-improves when manually triggered.
  Effort: ~20 lines YAML

### operator_log.jsonl analysis
  Status: run_operator_layer.py writes operator_log.jsonl
  What's missing: A script to summarize it for humans
    (how many cycles ran, which modes, success rates)
  Effort: ~30 lines

---

## Priority 4: Calibration

### trust_update.py activation
  Status: SCAFFOLDED (scripts/trust_update.py exists)
  What's missing: 10+ cycles of learning_memory.jsonl data to calibrate against.
    Cannot calibrate until learning_memory.py is wired (Priority 1).
  Dependency: learning_memory.py integration

### magic_numbers.md — move from UNCALIBRATED to CALIBRATED
  Status: Registry exists (calibration/magic_numbers.md)
  What's missing: Empirical data from 10+ runs
  Dependency: learning_memory.py + trust_update.py activation

---

## Priority 5: Skill Generalization

### test_skill_generalization.py — activate with real conversation
  Status: SCAFFOLDED (tests/test_skill_generalization.py exists)
  What's missing: A real different conversation inserted into DIFFERENT_CONVERSATION
    and a run_extractor.py CLI script to call
  Risk if unbuilt: conversation-to-system-extractor skill is unverified
    for generalization. It may only work for the original conversation.
  Effort: insert conversation + 1 test run

### run_extractor.py CLI
  Status: NOT BUILT
  What's missing: A CLI that takes a conversation file and outputs a skill.md
    Wraps the analysis protocol from conversation-to-system-extractor.md
    into a runnable script
  Effort: ~100 lines

---

## Deferred Design Decisions

### Risk threshold = 4 calibration
  Current: hardcoded in execute_next.py
  Decision needed: Should this be configurable per case_dir?
    Some projects are higher risk tolerance than others.
  Suggested: Add optional `risk_threshold` field to enforcement_active.json

### Consecutive failure limit = 2
  Current: hardcoded in loop_until_blocked.py
  Decision needed: Is 2 too aggressive for large queues?
  Suggested: Make configurable, default 2, allow override in case_dir config

### Interface layer delivery mechanism
  Current: 3 options specified, none chosen
  Decision needed: generate_human_report.py vs serve.py vs webhook
  Recommended: Build generate_human_report.py first (no dependencies)

---

## Ideas That Came Up But Were Not Scoped

### Monetization / non-engineer user path
  Discussed: The system has no path to a paying user yet.
  Question posed: 'What does someone pay for here?'
  Not scoped: Pricing, distribution, onboarding
  Minimum to address: interface_layer + ignition_layer both must exist first

### Skill deduplication / canonicalization
  Discussed: When multiple skills cover overlapping ground,
    how do you deduplicate and decide what to keep?
  Referenced: User's prior work on deduping LLM outputs across models
  Not built: A 'skill deduper' that takes N skill files and produces 1 canonical version

### Multi-agent parallelization
  Discussed in prior sessions: Running multiple forward-executor instances
    on different claim subsets in parallel
  Not scoped in this session: dependency graph prevents naive parallelization
  Requires: mode_selector.py + dependency resolution before parallelizing

---

_Last updated: 2026-07-03_  
_Session: self-improving-system-builder v3.0.0 + enforcement prompt + context_spinner_
