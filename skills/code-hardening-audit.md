name: code-hardening-audit
version: 1.0.0
description: >
  Full bug, security, performance, and maintainability review that always
  delivers corrected, tested code - never commentary alone.

review_dimensions:
  - bug_detection_and_resolution: root cause plus corrected code for each bug.
  - security_and_hardening: input validation, safe defaults, no silent failure conversions.
  - performance_optimization: remove redundant passes, measure gains.
  - code_quality_and_maintainability: no rhetorical stubs as implementation.
  - refactoring_and_simplification: reduce technical debt.

anti_patterns_to_flag:
  - hardcoded sandbox-specific paths
  - try/except silently converting failure into false success
  - pass where docs claim a live feature
  - proof gates that cannot reject
  - in-memory persistence claimed as durable

deliverable_contract:
  - Corrected code, not just observations.
  - Tests for every fixed behavior.
  - Explicit verdict: production-ready / improved-but-blocked / non-functional.
