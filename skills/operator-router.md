name: operator-router
version: 1.0.0
description: >
  Inspect skills, plugins, hooks, and shell paths; rank the least-brittle
  execution path; preview before executing; record outcomes so trust is earned.

operating_habit: "Inspect first, route second, execute third, remember fourth."
workflow:
  - Discover
  - Inspect
  - Rank
  - Preview
  - Execute
  - Record
  - Promote-or-downgrade

reliability_states: [candidate, wrap, bypass, reliable]
integration: >
  Preview output imports via import_router_handoff.py into
  forward-executor action queue.
