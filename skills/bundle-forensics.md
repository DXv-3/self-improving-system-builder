name: bundle-forensics
version: 1.0.0
description: >
  Reverse-engineer how a bundle was produced and classify every claim by
  evidence quality, gating production promotion until claims are runtime-proven.

when_to_use:
  - A production-ready bundle needs verification before being trusted.
  - Trace material shows how the artifact was assembled.

workflow:
  - Ingest trace and artifact.
  - Extract file reads, commands, generation markers into compiler_trace.json.
  - Parse bundle into atomic claims in claim_map.json.
  - Classify each claim against evidence classes.
  - Diff vs runtime_evidence.json to produce drift_report.
  - Gate: PROMOTE / HOLD / BLOCK with exact blocking claims listed.

mandatory_outputs:
  - PROVENANCE.md, compiler_trace.json, claim_map.json,
    runtime_evidence.json, drift_report.md, promotion_gate.json
