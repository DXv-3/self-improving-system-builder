# Zero Loss Recovery Prompt

Produce the smallest set of artifacts that lets all prior chat be deleted without losing operational value. Preserve exact files, next steps, proofs, risks, and resume order.

## Template

You are acting as a zero-loss recovery agent. Review this entire conversation and produce:
1. A complete file manifest of everything that was built or discussed.
2. A `SESSION_STATE_ZERO_LOSS.md` containing exact file states, next actions, confirmed proofs, and resume order.
3. A list of everything that would be lost if the chat were deleted right now.
4. Ready-to-push code for anything that was drafted but not yet committed.

Do not summarize. Do not omit anything. Treat every code block as a push candidate.
