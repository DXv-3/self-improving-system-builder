name: repo-healing-operator
version: 1.0.0
description: Inspect an in-progress repo, find the highest-leverage breakpoints, and patch them in the right order.
core_thesis: The right next fix comes from tracing the actual execution chain, not guessing.
when_to_use:
  - When a repo mostly exists but fails in small critical ways.
  - When tests, scripts, and scaffolds disagree about actual state.
inputs:
  required:
    - Repo tree
    - Tests
    - Entrypoints
  optional:
    - Roadmaps
    - Prior chat artifacts
outputs:
  - Ranked fix list
  - Patches
  - Proof of improvement
workflow:
  - Trace the real execution path.
  - Find fail-open defaults and broken assumptions.
  - Fix the highest-leverage issue first.
  - Add tests that lock in the repair.
  - Record what remains scaffolded.
mistakes_to_avoid:
  - Guessing from filenames.
  - Treating docs as proof.
  - Fixing cosmetic issues before blockers.
hard_stop_conditions:
  - The repo has a reproducible pass/fail signal and the next fix is explicit.
