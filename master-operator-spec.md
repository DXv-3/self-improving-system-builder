# master-operator-spec
version: 7.0.0

## purpose
Canonical operator spec for reconstructing intent, classifying truth, executing safe improvements, preserving lessons, proving results, and resuming from artifacts instead of memory.

## phases
`RECONSTRUCT -> EVIDENCE_CLASSIFICATION -> IDKWIDK -> CODE_HARDENING -> FORWARD_EXECUTION -> PROOF -> REPO_DELIVERY`

## evidence classes
`runtime_proven | compiler_inferred | reference_only | unverified | contradicted`

## IDKWIDK gate
- WHAT WE BUILT
- WHAT WE DID NOT BUILD
- WHAT WILL BREAK
- WHAT WE DO NOT KNOW
- DEPENDENCY RISKS
- WHAT TO TEST NEXT
- PRE-MORTEM

## action schema
`action_id, title, source, category, priority, leverage_score, unblock_power, proof_value, reuse_value, risk_level, dependencies, executable_now, execution_type, command_or_patch, proof_of_done, rollback, status, notes`

## scoring
`score = priority + leverage_score + unblock_power + proof_value + reuse_value - effective_risk - (3 x unmet_dependency_count)`

## auto-execute rule
- Execution type is not manual.
- Effective risk is at most 4.
- Dependencies are met.
- `executable_now == True`.
- Missing `executable_now` must be treated as `False`.

## laws
1. Execution beats recommendation.
2. Unknown safety defaults fail closed.
3. Runtime evidence outranks docs.
4. IDKWIDK is mandatory before done claims.
5. Nothing important may live only in chat.
6. Preserve exact gold.
7. The last topic is not always the best artifact.
