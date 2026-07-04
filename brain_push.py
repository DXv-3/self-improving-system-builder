"""brain_push.py — self-improving-system-builder → the-brain live sync.

Drop-in wrapper that:
  1. Writes learning events to local learning_memory.jsonl (existing behavior preserved)
  2. Simultaneously pushes every event to the-brain's SQLite via BrainSync
  3. Provides flush_existing() to backfill all historical .jsonl data

Usage — replace direct .jsonl writes with:
    from brain_push import push_learning, flush_existing

    # Write a new event (goes to .jsonl AND brain.db):
    push_learning(
        run_id=run_id,
        category="blocker",
        event_type="gate_failed",
        detail="IDKWIDK gate 3 blocked on missing provenance",
        outcome="blocked",
    )

    # On first run, backfill all historical data:
    flush_existing()  # reads learning_memory.jsonl → brain.db

Standalone backfill:
    python brain_push.py --flush
    python brain_push.py --tail     # watch .jsonl and push new lines live
    python brain_push.py --stats    # show brain.db learning_memory counts
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_JSONL_PATH = _REPO_ROOT / "learning_memory.jsonl"
_SOURCE = "self-improving-system-builder"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_brain():
    """Resolve and return BrainSync, or None if unavailable."""
    candidates = [
        _REPO_ROOT.parent / "the-brain",
        Path.home() / "the-brain",
        Path.home() / "repos" / "the-brain",
        Path.home() / "dev" / "the-brain",
        Path.home() / "projects" / "the-brain",
    ]
    import os
    env_path = os.environ.get("BRAIN_REPO_PATH", "")
    if env_path:
        candidates.insert(0, Path(env_path))

    for candidate in candidates:
        if (candidate / "brain_sync.py").exists():
            brain_str = str(candidate)
            if brain_str not in sys.path:
                sys.path.insert(0, brain_str)
            try:
                from brain_sync import BrainSync  # type: ignore
                return BrainSync()
            except Exception as exc:
                print(f"[brain_push] Import error: {exc}")
                return None

    print(
        "[brain_push] WARNING: the-brain not found. "
        "Set BRAIN_REPO_PATH env var to enable live sync. "
        "Events will continue writing to learning_memory.jsonl only."
    )
    return None


_brain = None
_brain_resolved = False


def _brain_client():
    global _brain, _brain_resolved
    if not _brain_resolved:
        _brain = _get_brain()
        _brain_resolved = True
    return _brain


def push_learning(
    run_id: str,
    category: str,
    event_type: str,
    detail: str,
    outcome: str,
    source: str = _SOURCE,
    also_write_jsonl: bool = True,
) -> bool:
    """
    Write a learning event to learning_memory.jsonl and push to brain.db.
    Returns True if brain write succeeded, False if brain unavailable (jsonl still written).
    """
    ts = _now()
    record = {
        "timestamp": ts,
        "run_id": run_id,
        "source": source,
        "category": category,
        "event_type": event_type,
        "detail": detail,
        "outcome": outcome,
    }

    # 1. Write to .jsonl (preserve existing behavior)
    if also_write_jsonl:
        try:
            with _JSONL_PATH.open("a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            print(f"[brain_push] .jsonl write error: {exc}")

    # 2. Push to brain.db
    brain = _brain_client()
    if brain is None:
        return False
    try:
        return brain.learn(
            run_id=run_id,
            source=source,
            category=category,
            event_type=event_type,
            detail=detail,
            outcome=outcome,
        )
    except Exception as exc:
        print(f"[brain_push] brain write error: {exc}")
        return False


def push_skill_update(
    run_id: str,
    skill_name: str,
    change_summary: str,
    outcome: str = "pass",
) -> bool:
    """
    Convenience wrapper for skill update events.
    Writes to brain as a 'skill' category event AND adds/updates the
    skill as a KG node linked to self-improving-system-builder.
    """
    ok = push_learning(
        run_id=run_id,
        category="skill",
        event_type="skill_updated",
        detail=f"Skill '{skill_name}': {change_summary}",
        outcome=outcome,
    )
    brain = _brain_client()
    if brain:
        try:
            brain.kg_add_node(
                node_id=f"skill:{skill_name}",
                node_type="skill",
                label=skill_name,
                properties={"updated_by": _SOURCE, "run_id": run_id},
            )
            brain.kg_add_edge(
                source_id=_SOURCE,
                target_id=f"skill:{skill_name}",
                relation="produces",
                weight=1.0,
            )
        except Exception:
            pass
    return ok


def push_idkwidk_gate(
    run_id: str,
    gate_number: int,
    gate_name: str,
    outcome: str,
    detail: str = "",
) -> bool:
    """Convenience wrapper for IDKWIDK 7-gate audit events."""
    return push_learning(
        run_id=run_id,
        category="audit",
        event_type=f"idkwidk_gate_{gate_number}:{gate_name}",
        detail=detail or f"IDKWIDK Gate {gate_number} ({gate_name}) → {outcome}",
        outcome=outcome,
    )


def flush_existing(jsonl_path: Path | None = None) -> int:
    """
    Backfill all records from learning_memory.jsonl into brain.db.
    Safe to call multiple times — uses INSERT OR IGNORE (deduplication
    is on run_id + event_type + timestamp unique index in brain_schema.sql).
    Returns count of newly inserted records.
    """
    path = jsonl_path or _JSONL_PATH
    if not path.exists():
        print(f"[brain_push] No .jsonl found at {path}")
        return 0

    brain = _brain_client()
    if brain is None:
        print("[brain_push] Cannot flush: brain.db not connected")
        return 0

    lines = [l for l in path.read_text().splitlines() if l.strip()]
    flushed = 0
    errors = 0
    for line in lines:
        try:
            r = json.loads(line)
            ok = brain.learn(
                run_id=r.get("run_id", ""),
                source=r.get("source", _SOURCE),
                category=r.get("category", "meta"),
                event_type=r.get("event_type", "unknown"),
                detail=r.get("detail", ""),
                outcome=r.get("outcome", "pass"),
            )
            if ok:
                flushed += 1
        except Exception as exc:
            errors += 1
            if errors <= 3:
                print(f"[brain_push] flush error: {exc}")
    print(f"[brain_push] Flushed {flushed}/{len(lines)} records ({errors} errors)")
    return flushed


def tail_and_push(
    jsonl_path: Path | None = None,
    poll_interval: float = 1.5,
) -> None:
    """
    Watch learning_memory.jsonl for new lines and push each one
    to brain.db in real time. Ctrl+C to stop.
    """
    path = jsonl_path or _JSONL_PATH
    print(f"[brain_push] Tailing {path} (Ctrl+C to stop)...")
    seen = 0
    if path.exists():
        seen = len([l for l in path.read_text().splitlines() if l.strip()])
        print(f"[brain_push] Skipping {seen} existing lines, watching for new ones.")

    while True:
        try:
            if path.exists():
                lines = [l for l in path.read_text().splitlines() if l.strip()]
                new_lines = lines[seen:]
                for line in new_lines:
                    try:
                        r = json.loads(line)
                        push_learning(
                            run_id=r.get("run_id", ""),
                            category=r.get("category", "meta"),
                            event_type=r.get("event_type", "unknown"),
                            detail=r.get("detail", ""),
                            outcome=r.get("outcome", "pass"),
                            source=r.get("source", _SOURCE),
                            also_write_jsonl=False,  # already in file
                        )
                        seen += 1
                        print(
                            f"  \u2192 pushed: {r.get('event_type')} "
                            f"[{r.get('outcome')}] run={r.get('run_id', '')[:12]}"
                        )
                    except Exception as exc:
                        print(f"  [error] {exc}")
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\n[brain_push] Tail stopped.")
            break


# ------------------------------------------------------------------ #
#  CLI                                                                #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="brain_push: sync self-improving-system-builder → the-brain"
    )
    parser.add_argument("--flush", action="store_true",
                        help="Backfill all existing learning_memory.jsonl into brain.db")
    parser.add_argument("--tail", action="store_true",
                        help="Watch learning_memory.jsonl and push new lines live")
    parser.add_argument("--stats", action="store_true",
                        help="Show brain.db learning_memory counts for this repo")
    parser.add_argument("--test", action="store_true",
                        help="Write a test event to brain.db")
    args = parser.parse_args()

    if args.flush:
        n = flush_existing()
        print(f"Done. {n} records flushed to brain.db.")

    elif args.tail:
        tail_and_push()

    elif args.stats:
        brain = _brain_client()
        if brain:
            records = brain.query_learning(source=_SOURCE, limit=1000)
            outcomes = {}
            for r in records:
                o = r.get("outcome", "unknown")
                outcomes[o] = outcomes.get(o, 0) + 1
            print(f"brain.db records for '{_SOURCE}': {len(records)} total")
            for k, v in sorted(outcomes.items()):
                print(f"  {k}: {v}")
        else:
            print("brain.db not connected.")

    elif args.test:
        import uuid
        run_id = f"brain_push_test_{uuid.uuid4().hex[:8]}"
        ok = push_learning(
            run_id=run_id,
            category="meta",
            event_type="connectivity_test",
            detail="brain_push CLI test event from self-improving-system-builder",
            outcome="pass",
        )
        print(f"Test event: {'written to brain.db' if ok else 'written to .jsonl only (brain offline)'}")
        ok2 = push_skill_update(run_id, "brain_push_integration", "initial wiring test")
        print(f"Skill update: {'OK' if ok2 else 'offline'}")

    else:
        parser.print_help()
