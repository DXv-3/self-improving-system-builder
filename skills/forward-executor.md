# forward-executor
version: 2.0.0

description: >
  Convert any set of findings, claims, or audit results into a scored action
  queue, execute safe actions immediately, verify outcomes, persist results,
  loop until genuinely blocked, then classify blockers, generate safe
  follow-up actions, decide approval policy, and emit a retry strategy.
  Never stops at 'here is what needs to be done.'

core_thesis: >
  Execution is not a phase that comes after planning. It is the plan.

---

## ACTION SCHEMA

Required fields:
  action_id, title, source, category, priority (0-10),
  leverage_score (0-10), unblock_power (0-10), proof_value (0-10),
  reuse_value (0-10), risk_level (0-10), dependencies ([action_ids]),
  executable_now (bool), execution_type (command|file_write|python|manual),
  command_or_patch (string), proof_of_done (string),
  rollback (string), status (pending|running|completed|blocked|failed|skipped),
  notes (string)

## SCORING FORMULA

  score = priority + leverage_score + unblock_power + proof_value + reuse_value
          - risk_level - (3 x count_of_unmet_dependencies)

  Sort descending. Re-rank after every single execution.

## EXECUTION RULES

  Auto-execute if: execution_type != manual AND risk_level <= 4 AND deps met
  command:    subprocess.run(cmd, shell=True, cwd=case_dir)
  python:     subprocess.run(['python3', '-c', code], cwd=case_dir)
  file_write: parse 'path::content', write with parent mkdir -p
  manual:     immediately blocked

## LOOP LOGIC

  max_steps: 25 | consecutive_failure_limit: 2
  LOOP: score -> choose_next -> execute -> update_status ->
        verify -> persist -> if consecutive_failures>=2: break

## BLOCKER CLASSIFICATION

  needs_permission:         'approval' | 'risk above auto threshold'
  needs_external_resource:  'dependency' | 'network' | 'credential'
  needs_safe_patch:         'contradicted' | 'rewrite' | 'cost' | 'config'
  downgrade_claim_now:      'reference-only' | 'downgrade production label'
  needs_design_decision:    default

## APPROVAL POLICY

  downgrade_claim_now      -> auto_downgrade_claim
  needs_permission         -> request_human_approval
  needs_external_resource  -> request_resource
  needs_safe_patch         -> auto_generate_safe_patch
  needs_design_decision    -> request_design_decision

## FOLLOW-UP GENERATION

  Always:               approval_requests/{action_id}.md
  downgrade_claim_now:  claim_downgrades/{action_id}.md
  needs_permission:     implementation_plans/{action_id}.md
  needs_external_resource: resource_requests/{action_id}.md
  needs_design_decision: design_decisions/{action_id}.md

## RETRY STRATEGY

  0 blocked + 1+ completed -> reaudit_now
  auto_downgrade in decisions -> apply_downgrades_and_reaudit
  request_human in decisions -> await_approval_then_rerun
  request_resource in decisions -> acquire_resources_then_rerun
  else -> perform_design_review

## MISTAKES TO AVOID

  - Generating recommendations instead of executing when risk <= 4
  - Not re-ranking after each execution
  - Treating manual execution type as 'just try it'
  - Not appending to execution_log.jsonl
  - Setting rollback: 'N/A'
  - Classifying everything as needs_design_decision
