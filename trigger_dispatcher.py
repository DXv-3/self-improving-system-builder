#!/usr/bin/env python3
"""trigger_dispatcher.py — entrypoint for self-improving-system-builder.

This is the single command that runs the self-improvement loop.

What it does each cycle:
    1. Connects to the-brain via SelfImproverBridge
    2. Syncs local learning_memory.jsonl into brain.db (convergence)
    3. Reads failure patterns from conductor-protocol-v2 runs
    4. For each skill needing review, runs the improvement protocol
    5. Writes skill mutation outcomes back to the brain
    6. Emits an updated failure feed for external tooling

Usage:
    python trigger_dispatcher.py --once          # one cycle and exit
    python trigger_dispatcher.py --watch         # continuous, every 60s
    python trigger_dispatcher.py --watch --interval 30
    python trigger_dispatcher.py --dry-run       # show candidates, no mutations
    python trigger_dispatcher.py --status        # print loop health and exit

Environment variables:
    BRAIN_DIR              Path to the-brain repo (default: ../the-brain)
    BRAIN_DB_PATH          Path to brain.db (default: $BRAIN_DIR/data/brain.db)
    BRAIN_FAILURE_FEED_PATH  Output path for failure feed JSONL (default: /tmp/brain_failure_feed.jsonl)
    SIB_MIN_FAILURES       Minimum failures to trigger improvement (default: 3)
    SIB_INTERVAL_SECONDS   Watch mode loop interval (default: 60)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ------------------------------------------------------------------ #
#  Bootstrap: locate the-brain and import the bridge                 #
# ------------------------------------------------------------------ #

from brain_client import get_bridge, BRAIN_AVAILABLE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ #
#  JSONL sync: local learning_memory.jsonl → brain.db               #
# ------------------------------------------------------------------ #

def sync_local_jsonl_to_brain(bridge, jsonl_path: str = "learning_memory.jsonl") -> int:
    """One-way sync: local JSONL events → brain.db.

    Safe to call repeatedly — duplicate events may land in brain.db but
    will not cause errors. The brain's query_learning() naturally deduplicates
    by returning most-recent-first.

    Returns: number of lines synced.
    """
    path = Path(jsonl_path)
    if not path.exists() or bridge is None:
        return 0

    rid = f"sync_{uuid.uuid4().hex[:8]}"
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            bridge.brain.learn(
                run_id=event.get("run_id") or rid,
                source=event.get("source", "self-improving-system-builder"),
                category=event.get("category", "local_memory"),
                event_type=event.get("event_type") or event.get("type", "unknown"),
                detail=event.get("detail") or json.dumps(
                    {k: v for k, v in event.items() if k not in
                     ("run_id", "source", "category", "event_type", "type", "detail", "outcome")}
                ),
                outcome=event.get("outcome") or event.get("result", "info"),
            )
            count += 1
        except Exception as e:
            print(f"[sync_jsonl] skipping malformed line: {e}")
    return count


# ------------------------------------------------------------------ #
#  Skill improvement protocol                                         #
# ------------------------------------------------------------------ #

def improve_skill(bridge, candidate: dict, run_id: str, dry_run: bool = False) -> str:
    """Attempt to improve a skill flagged by the brain.

    This is the hook where your actual improvement logic lives.
    Currently implements a 'flag for manual review' strategy as a safe default.
    Replace the body of this function with your LLM-based mutation logic,
    prompt rewriting, gate threshold adjustment, etc.

    Returns: outcome string ('improved' | 'reverted' | 'tested' | 'failed')
    """
    skill = candidate["skill"]
    failures = candidate["failure_count"]
    rate = candidate["failure_rate"]

    print(f"  → [{skill}] {failures} failures ({rate:.0%} rate) | last: {candidate.get('last_failure', 'unknown')[:19]}")

    if dry_run:
        print(f"    [dry-run] would attempt improvement for {skill}")
        return "tested"

    # ----------------------------------------------------------------
    # TODO: Replace this block with your real improvement logic.
    #
    # Examples of what to do here:
    #   - Load the skill's .md file from skills/ directory
    #   - Send it + failure evidence to Claude/GPT for rewrite suggestions
    #   - Apply the rewrite if confidence > threshold
    #   - Run a test against the conductor to validate improvement
    #   - Return 'improved' if pass rate went up, 'reverted' if it didn't
    #
    # For now: mark as 'tested' (reviewed but no automated fix applied)
    # ----------------------------------------------------------------

    skill_path = Path("skills") / f"{skill}.md"
    if skill_path.exists():
        detail = f"Reviewed {skill}.md — {failures} conductor failures at {rate:.0%} rate. Flagged for manual prompt revision."
        outcome = "tested"
    else:
        detail = f"Skill file skills/{skill}.md not found — {failures} failures recorded. Gate config may need threshold adjustment."
        outcome = "tested"

    print(f"    Outcome: {outcome} | {detail[:80]}")
    return outcome


# ------------------------------------------------------------------ #
#  Main improvement cycle                                             #
# ------------------------------------------------------------------ #

def run_improvement_cycle(
    min_failures: int = 3,
    dry_run: bool = False,
    jsonl_path: str = "learning_memory.jsonl",
    failure_feed_path: str = "/tmp/brain_failure_feed.jsonl",
) -> dict:
    """Run one full improvement cycle. Returns a summary dict."""
    run_id = f"sib_{uuid.uuid4().hex[:8]}"
    started = _now()
    bridge = get_bridge() if BRAIN_AVAILABLE else None

    summary = {
        "run_id": run_id,
        "started": started,
        "brain_available": bridge is not None,
        "synced_events": 0,
        "candidates_found": 0,
        "improvements_attempted": 0,
        "outcomes": {},
    }

    print(f"\n[trigger_dispatcher] Cycle {run_id} started at {started[:19]}")
    print(f"  Brain: {'CONNECTED' if bridge else 'UNAVAILABLE (local-only mode)'}")

    # Step 1: Sync local JSONL into brain
    if bridge:
        synced = sync_local_jsonl_to_brain(bridge, jsonl_path)
        summary["synced_events"] = synced
        if synced:
            print(f"  Synced {synced} local events → brain.db")

    # Step 2: Read failure patterns
    candidates = bridge.get_skills_needing_review(min_failures=min_failures) if bridge else []
    summary["candidates_found"] = len(candidates)
    print(f"  Skills needing review: {len(candidates)}")

    # Step 3: Improve each candidate
    for candidate in candidates:
        summary["improvements_attempted"] += 1
        skill = candidate["skill"]

        outcome = improve_skill(bridge, candidate, run_id, dry_run=dry_run)
        summary["outcomes"][skill] = outcome

        if bridge and not dry_run:
            bridge.update_skill_from_outcome(
                skill_name=skill,
                outcome=outcome,
                mutation_detail=f"Cycle {run_id}: {outcome} after {candidate['failure_count']} failures",
                run_id=run_id,
            )

    # Step 4: Emit failure feed for external tooling / harmony
    if bridge and not dry_run:
        feed_path = os.environ.get("BRAIN_FAILURE_FEED_PATH", failure_feed_path)
        n = bridge.emit_failure_feed(feed_path, min_failures=min_failures)
        print(f"  Failure feed: {n} patterns → {feed_path}")

    summary["completed"] = _now()
    print(f"  Done. {summary['improvements_attempted']} attempted, outcomes: {summary['outcomes'] or 'none'}")
    return summary


# ------------------------------------------------------------------ #
#  Status check                                                        #
# ------------------------------------------------------------------ #

def print_status() -> None:
    """Print current brain loop health and exit."""
    bridge = get_bridge() if BRAIN_AVAILABLE else None
    if not bridge:
        print("[status] Brain unavailable. Set BRAIN_DIR env var and ensure the-brain is installed.")
        return

    patterns = bridge.read_failure_patterns(min_failures=1)
    mutations = bridge.get_recent_skill_mutations(limit=10)

    print(f"\n{'='*55}")
    print(f"  SELF-IMPROVING SYSTEM BUILDER — STATUS")
    print(f"{'='*55}")
    print(f"  Brain DB:     {os.environ.get('BRAIN_DB_PATH', 'default location')}")
    print(f"  Skills with failures: {len([p for p in patterns if p['failure_count'] >= 3])} (≥3 failures)")
    print(f"  Recent mutations:     {len(mutations)}")
    print(f"{'='*55}")

    if patterns:
        print("\n  Failure Patterns:")
        for p in patterns[:10]:
            flag = "🔴" if p["failure_count"] >= 5 else ("🟠" if p["failure_count"] >= 3 else "🟡")
            print(f"  {flag} {p['skill']:30s} {p['failure_count']:3d} failures ({p['failure_rate']:.0%})")

    if mutations:
        print("\n  Recent Skill Mutations:")
        for m in mutations[:5]:
            print(f"  • {(m.get('event_type') or '?'):40s} [{m.get('outcome','?')}] {(m.get('created_at') or '')[:19]}")

    print()


# ------------------------------------------------------------------ #
#  CLI                                                                 #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="self-improving-system-builder entrypoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--watch", action="store_true", help="Run continuously")
    parser.add_argument("--dry-run", action="store_true", help="Show candidates without mutating skills")
    parser.add_argument("--status", action="store_true", help="Print current health and exit")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("SIB_INTERVAL_SECONDS", "60")),
                        help="Seconds between cycles in watch mode (default: 60)")
    parser.add_argument("--min-failures", type=int, default=int(os.environ.get("SIB_MIN_FAILURES", "3")),
                        help="Minimum failure count to trigger improvement (default: 3)")
    parser.add_argument("--jsonl", default="learning_memory.jsonl",
                        help="Path to local learning_memory.jsonl to sync")
    args = parser.parse_args()

    if args.status:
        print_status()
        sys.exit(0)

    if args.watch:
        print(f"[trigger_dispatcher] Watch mode: cycling every {args.interval}s (Ctrl+C to stop)")
        cycle = 0
        while True:
            cycle += 1
            print(f"\n[cycle {cycle}]")
            try:
                run_improvement_cycle(
                    min_failures=args.min_failures,
                    dry_run=args.dry_run,
                    jsonl_path=args.jsonl,
                )
            except KeyboardInterrupt:
                print("\n[trigger_dispatcher] Stopped.")
                sys.exit(0)
            except Exception as e:
                print(f"[trigger_dispatcher] Cycle error (continuing): {e}")
            time.sleep(args.interval)
    else:
        # --once or default
        summary = run_improvement_cycle(
            min_failures=args.min_failures,
            dry_run=args.dry_run,
            jsonl_path=args.jsonl,
        )
        sys.exit(0)
