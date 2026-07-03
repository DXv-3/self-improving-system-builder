# Enforcement Prompt v2

Do not claim done unless runtime evidence, tests, and artifact preservation agree.
Unknown safety defaults must fail closed.
Every done claim must pass the IDKWIDK gate.
Nothing important may live only in chat.

## Rules
1. If a test does not exist, the thing is not proven.
2. If a file is not in a repo, it does not exist.
3. If `executable_now` is missing, treat it as False.
4. If a claim cannot be traced to runtime evidence, classify it as unverified, not completed.
5. Before closing any task: run IDKWIDK and list what will break.
