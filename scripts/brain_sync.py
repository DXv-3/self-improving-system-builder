"""brain_sync.py

Bridge: reads learning_memory.jsonl from self-improving-system-builder
and (optionally) from forward-executor-system, then writes all records
into the-brain's SQLite database (brain.db).

Runs as a no-op if brain.db doesn't exist yet — safe to call in cycle.yml.
When the-brain gets a proper schema, this script will populate it automatically.

Usage:
    python3 scripts/brain_sync.py [--db /path/to/brain.db]
    python3 scripts/brain_sync.py --dry-run
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOCAL_JSONL = _REPO_ROOT / "learning_memory.jsonl"
# Sibling repo path (works if both repos are cloned side by side)
_SIBLING_JSONL = _REPO_ROOT.parent / "forward-executor-system" / "forward_executor" / "learning_memory.jsonl"
_DEFAULT_DB = _REPO_ROOT.parent / "the-brain" / "brain.db"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    records = []
    for l in lines:
        try:
            records.append(json.loads(l))
        except Exception:
            pass
    return records


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_memory (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            run_id    TEXT,
            source    TEXT,
            category  TEXT,
            event_type TEXT,
            detail    TEXT,
            outcome   TEXT,
            synced_at TEXT
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_run_event
        ON learning_memory(run_id, event_type, timestamp)
    """)
    conn.commit()


def sync_records(conn: sqlite3.Connection, records: list[dict], source: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for r in records:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO learning_memory
                (timestamp, run_id, source, category, event_type, detail, outcome, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get("timestamp", ""),
                r.get("run_id", ""),
                source,
                r.get("category", ""),
                r.get("event_type", ""),
                r.get("detail", ""),
                r.get("outcome", ""),
                now,
            ))
            inserted += conn.execute("SELECT changes()").fetchone()[0]
        except Exception:
            pass
    conn.commit()
    return inserted


def main(db_path: Path, dry_run: bool = False) -> dict:
    local = read_jsonl(_LOCAL_JSONL)
    sibling = read_jsonl(_SIBLING_JSONL)
    total = len(local) + len(sibling)

    if dry_run:
        print(f"Dry run: {len(local)} local records, {len(sibling)} sibling records (total {total})")
        print(f"DB target: {db_path}")
        print(f"DB exists: {db_path.exists()}")
        return {"dry_run": True, "local": len(local), "sibling": len(sibling)}

    if not db_path.exists():
        print(f"brain.db not found at {db_path} — skipping sync (no-op)")
        return {"skipped": True, "reason": "brain.db not found"}

    conn = sqlite3.connect(str(db_path))
    ensure_schema(conn)
    ins_local = sync_records(conn, local, "self-improving-system-builder")
    ins_sibling = sync_records(conn, sibling, "forward-executor-system")
    conn.close()

    result = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "local_records_found": len(local),
        "sibling_records_found": len(sibling),
        "inserted_local": ins_local,
        "inserted_sibling": ins_sibling,
    }
    print(f"Brain sync complete: +{ins_local} local, +{ins_sibling} sibling")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(_DEFAULT_DB))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(Path(args.db), dry_run=args.dry_run)
