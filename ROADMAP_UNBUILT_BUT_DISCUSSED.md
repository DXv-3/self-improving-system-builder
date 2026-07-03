# Roadmap: Unbuilt But Discussed

These modules were explicitly identified as the highest-leverage next build
targets in the session that produced this system. Preserved so no idea dies.

## learning_memory.py
Persist blocker patterns, successful follow-up types, approval outcomes, retry
results, and cross-run lessons so the system improves across runs.

## trust_update.py
Convert repeated success/failure patterns into updated risk weights, preferred
follow-up types, and scoring adjustments.

## mode_selector.py
Choose among direct loop, bundle-forensics cycle, full meta-cycle, and adaptive
meta-cycle based on project state and evidence class distribution.

## run_operator_layer.py
Single top-level launcher that invokes the right mode and emits one canonical
report. Eliminates the need to know which sub-script to call.

## multi-run learning tests
Prove the system improves across runs instead of repeating the same blocker
transformations in a loop forever.
