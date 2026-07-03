name: self-improving-system-builder
version: 3.0.0
description: >
  Turn any conversation, audit, bundle, or half-finished prototype into a
  tested, hardened, forensically verified, and self-executing system.
  Five fused layers: routing, blind-spot auditing, truth-lineage forensics,
  code hardening, and adaptive forward execution. Never stops at
  recommendations when a safe action can be taken instead.

core_thesis: >
  The job is never summarization. Convert chaos into an operating manual,
  claims into evidence classes, audits into executable actions, and actions
  into completed verified logged progress repeating until truly blocked.

sub_skills:
  - operator-router
  - idkwidk-protocol
  - bundle-forensics
  - code-hardening-audit
  - forward-executor

workflow:
  - Phase 1 Reconstruct: rebuild the arc, do not trust the polished surface.
  - Phase 2 Classify: run bundle-forensics evidence classification.
  - Phase 3 Audit: run code-hardening-audit + IDKWIDK against real implementation.
  - Phase 4 Queue: forward-executor ingests findings into a scored queue.
  - Phase 5 Execute: loop_until_blocked, verify, persist, re-rank, repeat.
  - Phase 6 Adapt: classify blockers, decide policy, split into safe follow-ups.
  - Phase 7 Package: emit canonical deliverables so a future session is self-sufficient.

evidence_classes:
  runtime_proven: "production_allowed: true"
  compiler_inferred: "production_allowed: only_if_labeled"
  reference_only: "production_allowed: false"
  unverified: "production_allowed: false"
  contradicted: "production_allowed: false"

action_scoring: "score = leverage + unblock_power + proof_value + reuse_value - risk - dependency_penalty"

hard_stop_conditions:
  - explicit user stop
  - no executable actions remain
  - required dependency missing with no safe downgrade
  - risk exceeds threshold and no safe follow-up exists
  - repeated failure without new information

mistakes_to_avoid:
  - Treating a polished bundle as proof of runtime behavior.
  - Ending a turn with you should do X when X is safely executable.
  - Marking a proof gate valid when it cannot reject.
  - Picking the most recent topic as the skill instead of the deepest reusable pattern.
  - Declaring complete without answering all IDKWIDK gates.

closing_rule: >
  Only stop when every phase has run, every claim has an evidence class,
  the action queue is empty or genuinely blocked, and no honest next move
  sentence can be written.
