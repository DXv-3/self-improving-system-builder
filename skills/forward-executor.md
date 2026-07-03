name: forward-executor
version: 2.0.0
description: >
  Convert findings into a scored queue, execute, verify, persist, loop until
  blocked - then classify blockers, decide policy, split risky work into safe
  follow-ups, and pick a retry strategy instead of stopping.

runnable_pipeline:
  ingestion: [ingest_findings.py, reconcile_with_bundle_forensics.py, import_router_handoff.py]
  scoring: score_actions.py
  execution: execute_next.py
  verification: verify_result.py
  proof_verification: verify_proof.py
  persistence: persist_result.py
  looping: loop_until_blocked.py
  patch_generation: generate_patch_from_claim.py
  patch_application: auto_patch.py
  full_cycle: run_system_cycle.py
  meta_cycle: run_full_meta_cycle.py
  adaptive_layer:
    - blocker_classifier.py
    - approval_policy.py
    - split_risky_actions.py
    - retry_strategy.py
    - run_adaptive_meta_cycle.py

blocker_labels:
  - needs_permission
  - needs_external_resource
  - needs_safe_patch
  - downgrade_claim_now
  - needs_design_decision

retry_strategies:
  - reaudit_now
  - apply_downgrades_and_reaudit
  - await_approval_then_rerun
  - acquire_resources_then_rerun
  - perform_design_review

next_build_targets:
  - learning_memory.py
  - trust_update.py
  - mode_selector.py
  - run_operator_layer.py
  - multi-run learning tests
