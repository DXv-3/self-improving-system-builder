# Skill: Conversation-to-System Pipeline

## What This Skill Is

This is the **parent meta-skill**. It describes how to take any conversation —
regardless of domain — and turn it into a zero-loss, git-backed, skill-packaged,
audited, and tested system such that the conversation itself becomes safely deletable.

It produced both `self-improving-system-builder.md` and `idkwidk-audit-protocol.md`.
Those are its outputs. This skill is the process that generates outputs like those.

## When to Use This Skill

Trigger this skill when:
- A user says anything like "make sure nothing is lost," "we can delete everything
  above this," "push it to GitHub," or "turn this into something reusable."
- A conversation has been going long enough to have produced multiple artifacts,
  decisions, or ideas that would be painful to reconstruct from scratch.
- A user is ending or pausing a session and wants continuity guaranteed.
- A user explicitly asks for a `skill.md` extraction.
- A user asks you to "continue from where we left off" — that phrase signals the
  prior output was NOT yet self-sufficient and something was lost or incomplete.

Do NOT use this skill for short, single-exchange conversations with no artifacts.

## Core Principle (verbatim — carry this exactly)

> "No idea ever dies."

Every artifact, every out-of-scope idea, every discussed-but-not-built item, every
pivot, and every constraint gets captured. The output of this skill must be
self-sufficient: someone with zero access to the prior conversation must be able to
fully reconstruct and continue the work from the output alone.

## The Test

After producing output, ask:
> "Can we delete everything above this output, including this prompt, and lose nothing?"

If the answer is no, the skill is not done. Keep going.

---

## Inputs Required

1. **The full conversation** — reread it completely, from first message to last. Do
   not rely on memory or summaries. Do not skip the beginning.
2. **The user's GitHub identity** — get it via `get_me` MCP tool if not known.
3. **The target repo** — either existing (check via `get_file_contents`) or to create
   (use `create_repository`, then `push_files`).

---

## Phase 1: Conversation Analysis (do silently before writing anything)

### 1A. Reconstruct the arc at two levels simultaneously

**Street level** — capture concrete artifacts:
- Every script, file, template, prompt, schema, command written or described
- Every decision made and the reason given
- Every constraint stated ("no pip dependencies," "stdlib only," "must exit code 2")
- Every exact wording that is reusable (copy verbatim, do not paraphrase)
- Every artifact name, file path, and directory structure

**High level** — identify the deeper pattern:
- Where did the conversation start vs. where did it end?
- What problem was the user *actually* trying to solve (not just the surface ask)?
- What did the user keep coming back to, refining, or pushing harder on?
- What pivots happened, and what do those pivots reveal about the real goal?
- What is the one sentence that captures "what this conversation was REALLY about"?

### 1B. Identify all candidate skills

List every reusable capability embedded in the conversation. Include obvious and
non-obvious candidates. Examples from practice:
- A prompt-writing skill
- A product-ideation skill
- A GitHub research skill
- A conversation-to-skill extraction skill (this skill)
- A meta-prompt library building skill
- A property-based testing skill
- A zero-loss archiving skill
- A higher-order synthesis skill

### 1C. Choose the best packaging

- Pick the skill(s) that are most **reusable**, **high-leverage**, and **faithful**
  to the full conversation — not just the last thing discussed.
- If multiple strong skills exist: produce multiple `skill.md` files with a clear
  parent-child relationship if applicable.
- The meta-skill (how the process works) is almost always more valuable than any
  single object-level skill it produced.

---

## Phase 2: Produce the System Artifacts

### 2A. The skill.md files

Each skill.md must be a **complete operating manual**, not a summary. It must teach
a future agent:
- When to use this capability
- What inputs it needs
- How to think through the task
- How to execute it step by step
- What outputs to produce
- What mistakes to avoid
- How to adapt when the situation changes

**Do not paraphrase away reusable exact language.** If the conversation produced a
specific prompt template, scoring algorithm, JSON schema, or gate structure — include
it verbatim inside the skill.md. That is the "gold" that makes the skill useful.

### 2B. The runnable code

If the conversation produced executable code (scripts, tests, configs), the
skill.md files alone are insufficient. You must also produce the full runnable
system — every file, complete, not stubbed.

Checklist for runnable system completeness:
- [ ] All scripts present and syntactically valid (`py_compile`, `bash -n`)
- [ ] All tests present and passing (run them, report results)
- [ ] All config/protocol files present (Makefile, IDKWIDK.md, README.md, RESUME.md)
- [ ] Executable permissions set on `.sh` and `.py` entrypoints
- [ ] `__pycache__` stripped
- [ ] Packaged as a zip AND a git bundle (two formats = two safety nets)

### 2C. The IDEAS.md

Always produce an `IDEAS.md` file that captures:
1. Everything that WAS built (inventory)
2. Everything discussed but NOT built (out-of-scope items, with enough detail to
   reconstruct the idea later)
3. The meta-pattern identified ("what this conversation was REALLY about")
4. Any open questions or unresolved forks

This file is the "no idea ever dies" guarantee. It is not optional.

### 2D. The RESUME.md

Always produce a `RESUME.md` that contains:
- What was being done when the session ended
- What is complete vs. what is still open
- Where all files live (paths, repo URL)
- The exact next action a new session should take

The RESUME.md is what lets a future AI session (or human) pick up cold, with zero
context, and continue without missing a beat.

---

## Phase 3: Zero-Loss Archiving to GitHub

### 3A. Check if the repo already exists

Never assume the repo doesn't exist. Always call `get_file_contents` first.
In practice, the repo often already exists from a prior session.

### 3B. Create repo if needed

```python
# Use MCP tool: create_repository
{
  "name": "<repo-name>",
  "description": "<one sentence from the meta-pattern>",
  "private": true,
  "autoInit": false  # CRITICAL: false, or push will fail with merge conflict
}
```

### 3C. Push files

Use `push_files` MCP tool to push all files in a single commit. Preferred commit
message format:
```
<system-name> v<version>: <one-line summary of what changed>

Files: <count> | Tests: all passing | Skill: packaged
```

If the repo already exists and has content, check which files are newer/different
and push only the delta, or push to a new branch and open a PR if changes are significant.

### 3D. Verify

After pushing, call `get_file_contents` on the root and at least one subdirectory
to confirm the files are actually there. Do not declare success until verified.

### 3E. Produce the git bundle (local backup)

```bash
git bundle create <system-name>.bundle --all
git bundle verify <system-name>.bundle  # must print "The bundle is okay"
```

A verified bundle means: even if GitHub goes down, the full history is preserved.

---

## Phase 4: Final Verification

Run this checklist before declaring done:

```
[ ] Skill.md files: complete, not stubbed, exact wording preserved
[ ] Runnable code: all files present, syntax clean, tests passing
[ ] IDEAS.md: all discussed items captured, nothing silently dropped
[ ] RESUME.md: next session can pick up cold
[ ] GitHub: repo exists, files verified live via get_file_contents
[ ] Git bundle: produced and verified
[ ] The test passes: "delete everything above, lose nothing" → TRUE
```

If any box is unchecked, continue. Do not declare done prematurely.

---

## User Behavior Patterns to Recognize and Handle

| User says | What it actually means | How to respond |
|-----------|----------------------|----------------|
| "Push it. Push real." | Prior delivery was promises, not actions | Use MCP tools to actually push, verify live |
| "Continue." / "/continue" | Prior output was incomplete or cut off | Resume mid-stream, no recap, maximum progress |
| "Is it safe to delete everything?" | Verify self-sufficiency of output | Run the checklist, be honest if not ready |
| "No idea ever dies." | Capture everything, including out-of-scope | Produce IDEAS.md with full inventory |
| "Make the next statement true: we can delete..." | Zero-loss guarantee required | Do not respond until ALL phases complete |

---

## Mistakes to Avoid

- **Declaring done too early.** The most common failure. "Done" means the checklist
  passes, not "I wrote a response."
- **Skill.md without runnable code.** An operating manual that describes scripts
  without including them is a stub, not a deliverable.
- **Paraphrasing exact language.** If the conversation produced a specific scoring
  algorithm, gate structure, or prompt — copy it verbatim.
- **Assuming the repo doesn't exist.** Always call `get_file_contents` first.
- **Skipping IDEAS.md.** Out-of-scope items discussed but not built are real artifacts.
- **Promising a push instead of pushing.** If MCP GitHub tools are available, use
  them. If auth is unavailable, produce a git bundle + exact one-command push
  instructions, not a multi-step tutorial.
- **Recapping instead of continuing.** When the user says "continue," the next token
  should be the continuation, not a summary of what came before.

---

## Prior-Session Skills in This Repo (reconciliation note)

The repo at github.com/DXv-3/self-improving-system-builder contains skills from
prior sessions that are complementary and should not be deleted:
- `bundle-forensics.md` — git bundle inspection/recovery
- `code-hardening-audit.md` — security hardening walkthrough
- `conversation-to-system-extractor.md` — earlier cut of this skill (superseded by this file)
- `forward-executor.md` — forward execution / planning layer
- `operator-router.md` — earlier cut of the router skill
- `repo-healing-operator.md` — repo repair operations
- `idkwidk-protocol.md` — earlier stub of the IDKWIDK protocol

This file (`conversation-to-system-pipeline.md`) supersedes `conversation-to-system-extractor.md`
and `operator-router.md` as the canonical, complete versions.

---

## Companion Skills

- `self-improving-system-builder.md` — the object-level system this skill produced
- `idkwidk-audit-protocol.md` — the audit gate system used to verify completeness

Run the IDKWIDK audit (companion skill) at the end of Phase 2 and before Phase 3.
The audit is what catches what you missed before you ship it.
