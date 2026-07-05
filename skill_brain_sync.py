"""
skill_brain_sync.py
--------------------
The shared bridge between self-improving-system-builder and the-brain KG.

This module is imported by:
  - loop.py                           (SIS, writes on every skill event)
  - operator_router/brain_skill_router (conductor, reads cached scores)
  - harmony_subscriber                 (conductor, writes from bus events)

It provides a single, stable API regardless of which end of the stack
is calling:

  WRITE side (SIS):
    record_skill_event(name, version, event_type, outcome_score, delta_summary)
    promote_skill(name, version, ...)
    demote_skill(name, version, ...)

  READ side (conductor / router):
    get_all_skill_scores()             → Dict[str, float]
    get_skill_history(name, limit=10)  → List[Dict]
    get_top_skills(n=5)                → List[Tuple[str, float]]

Storage layers (in priority order):
  1. the-brain KG (via MCP socket at BRAIN_MCP_URL, if reachable)
  2. Local SQLite sidecar (skill_brain_sync.db, always written)
  3. Harmony bus publish (fire-and-forget, so conductor gets real-time events)

If the-brain MCP is unreachable, the SQLite sidecar is the source of truth.
The conductor reads the sidecar via get_local_skill_scores() in its own DB.
"""

import json
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_lock = threading.Lock()
DB_PATH = Path(os.getenv("SKILL_SYNC_DB", "skill_brain_sync.db"))
_BRAIN_MCP_URL = os.getenv("BRAIN_MCP_URL", "http://localhost:8765")


# ---------------------------------------------------------------------------
# SQLite sidecar
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.executescript("""
        CREATE TABLE IF NOT EXISTS skill_events (
            event_id       TEXT PRIMARY KEY,
            skill_name     TEXT NOT NULL,
            skill_version  INTEGER NOT NULL DEFAULT 1,
            event_type     TEXT NOT NULL,
            outcome_score  REAL NOT NULL DEFAULT 0.0,
            delta_summary  TEXT,
            tags           TEXT,
            created_at     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS skill_scores (
            skill_name     TEXT PRIMARY KEY,
            avg_score      REAL NOT NULL DEFAULT 0.0,
            peak_score     REAL NOT NULL DEFAULT 0.0,
            event_count    INTEGER NOT NULL DEFAULT 0,
            last_event     TEXT NOT NULL,
            last_updated   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_skill_events_name
            ON skill_events(skill_name);
        CREATE INDEX IF NOT EXISTS idx_skill_scores_avg
            ON skill_scores(avg_score DESC);
    """)
    c.commit()
    return c


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _upsert_skill_score(
    conn: sqlite3.Connection,
    skill_name: str,
    outcome_score: float,
    event_type: str,
    now: str,
):
    """Update rolling avg and peak score for a skill."""
    existing = conn.execute(
        "SELECT avg_score, peak_score, event_count FROM skill_scores WHERE skill_name=?",
        (skill_name,)
    ).fetchone()

    if existing:
        old_avg = existing["avg_score"]
        old_peak = existing["peak_score"]
        count = existing["event_count"]
        # Exponential moving average (alpha=0.3) — recent events weighted more
        new_avg = 0.7 * old_avg + 0.3 * outcome_score
        new_peak = max(old_peak, outcome_score)
        conn.execute(
            "UPDATE skill_scores SET avg_score=?, peak_score=?, event_count=?, "
            "last_event=?, last_updated=? WHERE skill_name=?",
            (new_avg, new_peak, count + 1, event_type, now, skill_name),
        )
    else:
        conn.execute(
            "INSERT INTO skill_scores "
            "(skill_name, avg_score, peak_score, event_count, last_event, last_updated) "
            "VALUES (?, ?, ?, 1, ?, ?)",
            (skill_name, outcome_score, outcome_score, event_type, now),
        )


def _publish_to_harmony(event_id: str, skill_name: str, skill_version: int,
                        event_type: str, outcome_score: float, delta_summary: str):
    """Fire-and-forget harmony bus publish. Never raises."""
    try:
        matrix_path = os.getenv("MATRIX_PATH", "../MATRIX")
        import sys
        sys.path.insert(0, matrix_path)
        from harmony_publisher_base import HarmonyPublisher  # type: ignore
        pub = HarmonyPublisher()
        pub.publish("skill_event", {
            "event_id": event_id,
            "skill_name": skill_name,
            "skill_version": skill_version,
            "event_type": event_type,
            "outcome_score": outcome_score,
            "delta_summary": delta_summary,
            "source_repo": "self-improving-system-builder",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.debug("skill_brain_sync: harmony publish failed (non-fatal): %s", exc)


def _publish_to_brain(event_id: str, skill_name: str, skill_version: int,
                      event_type: str, outcome_score: float, delta_summary: str):
    """Write skill event to the-brain KG via MCP. Never raises."""
    try:
        import urllib.request
        payload = json.dumps({
            "operation": "kg_write",
            "node_type": "skill",
            "node_id": f"skill:{skill_name}:v{skill_version}",
            "properties": {
                "event_type": event_type,
                "outcome_score": outcome_score,
                "delta_summary": delta_summary,
                "event_id": event_id,
                "source": "self-improving-system-builder",
            },
        }).encode()
        req = urllib.request.Request(
            f"{_BRAIN_MCP_URL}/kg/write",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                logger.debug("skill_brain_sync: brain KG write OK for %s", skill_name)
    except Exception as exc:
        logger.debug("skill_brain_sync: brain KG write failed (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Public WRITE API
# ---------------------------------------------------------------------------

def record_skill_event(
    skill_name: str,
    skill_version: int = 1,
    event_type: str = "evaluated",
    outcome_score: float = 0.0,
    delta_summary: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """
    Record a skill lifecycle event (the core write call).

    Args:
        skill_name:     Short identifier, e.g. "code_review" or "deploy_agent".
        skill_version:  Monotonically increasing version int from skill.md YAML.
        event_type:     One of: promoted, demoted, evaluated, audited, patched.
        outcome_score:  Float in [0.0, 1.0]. 1.0 = perfect outcome.
        delta_summary:  Single-line human-readable description of what changed.
        tags:           Optional list of string tags for filtering.

    Returns:
        event_id (str UUID) for provenance tracking.
    """
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    tags_str = json.dumps(tags or [])

    with _lock:
        try:
            conn = _conn()
            conn.execute(
                "INSERT INTO skill_events "
                "(event_id, skill_name, skill_version, event_type, outcome_score, "
                "delta_summary, tags, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, skill_name, skill_version, event_type,
                 outcome_score, delta_summary, tags_str, now),
            )
            _upsert_skill_score(conn, skill_name, outcome_score, event_type, now)
            conn.commit()
            conn.close()
            logger.info(
                "skill_brain_sync: recorded %s event for '%s' v%d score=%.3f",
                event_type, skill_name, skill_version, outcome_score,
            )
        except Exception as exc:
            logger.warning("skill_brain_sync: SQLite write failed: %s", exc)

    # Async publish (both targets, non-blocking)
    t1 = threading.Thread(
        target=_publish_to_harmony,
        args=(event_id, skill_name, skill_version, event_type, outcome_score, delta_summary),
        daemon=True,
    )
    t2 = threading.Thread(
        target=_publish_to_brain,
        args=(event_id, skill_name, skill_version, event_type, outcome_score, delta_summary),
        daemon=True,
    )
    t1.start()
    t2.start()

    return event_id


def promote_skill(
    skill_name: str,
    skill_version: int,
    outcome_score: float,
    delta_summary: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """Convenience wrapper: record a 'promoted' event."""
    return record_skill_event(
        skill_name=skill_name,
        skill_version=skill_version,
        event_type="promoted",
        outcome_score=outcome_score,
        delta_summary=delta_summary,
        tags=tags,
    )


def demote_skill(
    skill_name: str,
    skill_version: int,
    outcome_score: float,
    delta_summary: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """Convenience wrapper: record a 'demoted' event."""
    return record_skill_event(
        skill_name=skill_name,
        skill_version=skill_version,
        event_type="demoted",
        outcome_score=outcome_score,
        delta_summary=delta_summary,
        tags=tags,
    )


def audit_skill(
    skill_name: str,
    skill_version: int,
    outcome_score: float,
    delta_summary: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """Convenience wrapper: record an 'audited' event (IDKWIDK gate pass/fail)."""
    return record_skill_event(
        skill_name=skill_name,
        skill_version=skill_version,
        event_type="audited",
        outcome_score=outcome_score,
        delta_summary=delta_summary,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Public READ API
# ---------------------------------------------------------------------------

def get_all_skill_scores() -> Dict[str, float]:
    """
    Return current avg_score for every tracked skill.
    Used by BrainSkillRouter in conductor.
    """
    try:
        conn = _conn()
        rows = conn.execute(
            "SELECT skill_name, avg_score FROM skill_scores ORDER BY avg_score DESC"
        ).fetchall()
        conn.close()
        return {row["skill_name"]: row["avg_score"] for row in rows}
    except Exception as exc:
        logger.warning("skill_brain_sync.get_all_skill_scores: %s", exc)
        return {}


def get_skill_history(
    skill_name: str,
    limit: int = 10,
    event_type_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return up to `limit` most recent events for a skill, newest first.
    Used by BrainSkillRouter to build skill_history_summary for prompt injection.
    """
    try:
        conn = _conn()
        if event_type_filter:
            rows = conn.execute(
                "SELECT * FROM skill_events WHERE skill_name=? AND event_type=? "
                "ORDER BY created_at DESC LIMIT ?",
                (skill_name, event_type_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM skill_events WHERE skill_name=? "
                "ORDER BY created_at DESC LIMIT ?",
                (skill_name, limit),
            ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.warning("skill_brain_sync.get_skill_history: %s", exc)
        return []


def get_top_skills(n: int = 5) -> List[Tuple[str, float]]:
    """Return the top-n skills by avg_score as (name, score) tuples."""
    scores = get_all_skill_scores()
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]


def get_skill_score(skill_name: str) -> float:
    """Return the current avg_score for a single skill (0.0 if not found)."""
    return get_all_skill_scores().get(skill_name, 0.0)


def get_skill_summary(skill_name: str) -> Dict[str, Any]:
    """
    Return a full summary dict for a skill: avg_score, peak_score,
    event_count, last_event, last_updated, recent_history (last 5).
    """
    try:
        conn = _conn()
        row = conn.execute(
            "SELECT * FROM skill_scores WHERE skill_name=?", (skill_name,)
        ).fetchone()
        conn.close()
        if not row:
            return {"skill_name": skill_name, "found": False}
        result = dict(row)
        result["recent_history"] = get_skill_history(skill_name, limit=5)
        result["found"] = True
        return result
    except Exception as exc:
        logger.warning("skill_brain_sync.get_skill_summary: %s", exc)
        return {"skill_name": skill_name, "found": False}
