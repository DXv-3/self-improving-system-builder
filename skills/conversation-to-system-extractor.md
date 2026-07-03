# conversation-to-system-extractor
version: 1.0.0

description: >
  Extract a tested, pushed, self-executing system from any conversation,
  audit, or partial prototype.

core_insight: >
  Most conversations contain a system waiting to be extracted. The surface
  topic is rarely the most valuable thing to package.

when_to_use:
  - A long conversation ended and you want to preserve its value for a future agent
  - Someone asks you to continue where we left off with no context
  - A prototype exists but no one can explain its intended behavior
  - An audit produced findings but no runnable remediation path

---

## ANALYSIS PROTOCOL

### Step 1: Reconstruct the Arc
  Where did the user START?  
  What problem were they ACTUALLY solving?  
  What PIVOTS happened?  
  What ARTIFACTS were produced?  
  What did the user keep OPTIMIZING FOR?

### Step 2: Identify Candidate Skills
  List every reusable capability hidden in the conversation:
    obvious:     The literal last topic discussed
    structural:  The workflow or process the conversation followed
    meta:        The way the user thinks and makes decisions
    tooling:     Specific scripts, schemas, or templates that generalize
    packaging:   The delivery mechanism (repo push, skill file, roadmap)

### Step 3: Choose What to Package
  Pick the skill(s) that are most_reusable, highest_leverage, most_faithful.
  Do NOT pick the last thing discussed if something earlier was deeper.

### Step 4: Preserve the Gold
  Never paraphrase: scoring formulas, schema field names, threshold values,
  error classifications, workflow step names.

### Step 5: Extract the Implicit
  Capture how the user thinks:
    depth_preference, directness_preference, leverage_preference,
    tooling_preference, iteration_style, packaging_style

---

## SKILL FILE REQUIRED SECTIONS

  name, version, description, core_thesis, when_to_use,
  inputs (required + optional), outputs (by mode/phase),
  phases/workflow (goal + steps + rules + anti-patterns),
  mistakes_to_avoid, hard_stop_conditions, next_build_targets

---

## COMMON EXTRACTION FAILURES

  surface_topic_capture:    Packaging the last thing discussed
  transcript_summary:       Writing what happened instead of an operating manual
  gold_paraphrasing:        Rewriting exact formulas/schemas in your own words
  skeletal_output:          Section headers with one-line placeholders
  implicit_assumption_loss: Capturing what was said but not how the user thinks
  no_roadmap:               Not preserving ideas that were discussed but not built

---

## HARD STOP CONDITIONS

  A future agent reading only this skill must be able to:
    - Understand when to use it
    - Execute the complete workflow without guessing
    - Produce the same quality as the original session
    - Know exactly what was not built and why
