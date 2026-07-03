# Interface Layer Spec

Status: UNBUILT — closes INTERFACE_GAP blind spot.

## The Problem
Every artifact in this system is a developer tool:
  - CLI scripts with sys.argv
  - JSON files requiring schema knowledge
  - GitHub repos requiring git

A non-engineer cannot run, understand, or trust the output.
This system cannot be sold, shared, or used by anyone except its builder
until this layer exists.

## The Minimum Interface

A non-engineer must be able to:
  1. Run one command (no flags, no config files to edit)
  2. Read the output without knowing JSON schemas
  3. Understand what was done and what is still blocked
  4. Know what to do next without reading code

## Implementation Options

### Option A: generate_human_report.py (recommended first)
  Input:  loop_summary.json + next_blockers.md + retry_strategy.json
  Output: REPORT.md in plain English
  Format:
    # What Happened
    {N} actions completed. {M} actions blocked.
    
    # What Was Built
    {list of completed action titles}
    
    # What Is Blocked (and why)
    {list of blocker titles with plain-English reason}
    
    # What To Do Next
    {retry_strategy in plain English}
    
    # What Was Not Built
    {ROADMAP items}

### Option B: serve.py
  Flask endpoint at localhost:8080
  Serves progress_snapshot.md rendered as HTML
  No authentication for local use
  Auto-refresh every 30 seconds during active cycle

### Option C: Slack/email digest
  After each cycle, POST loop_summary to a webhook
  Requires SLACK_WEBHOOK_URL env var
  Zero UI overhead, works for async teams

## Decision Required
Option A has no dependencies and can be built in < 50 lines.
Implement Option A before calling this system usable by anyone other than the builder.
