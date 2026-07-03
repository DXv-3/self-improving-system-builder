name: idkwidk-protocol
version: 1.1.0
description: >
  Permanent blind-spot audit run before any completion claim.

required_gates:
  - What we built.
  - What we did not build.
  - What will break.
  - What we do not know.
  - Dependency risks.
  - What to test next.
  - Pre-mortem: assume failure in 3 months - 5 causes, kill criteria.

rule: "No task is complete until every gate has a concrete non-generic answer."
