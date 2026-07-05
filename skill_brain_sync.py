"""
skill_brain_sync.py
-------------------
The closed-loop bridge: self-improving-system-builder → the-brain.

Every skill promotion, demotion, mutation, or audit gate result is:
  1. Written to the-brain's SQLite knowledge graph as a KG node + edge
  2. Published to the harmony bus as a `skill_event` envelope
  3. Appended to a local learning_memory.jsonl mirror (backwards compat)
  4. Optionally read back from the-brain for context before the next improvement cycle

Design principles:
  - Never crashes the caller. All brain/harmony writes are fire-and-forget with logged fallback.
  - brain_client.py is used for direct SQLite writes; harmony publisher for bus events.
  - ModelRouter (from zai-wrap model_gateway) is used for any LLM calls in this module.
  - Zero circular imports: this module imports from brain_client, not from improve_skill.
"""

import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SkillEvent:
    """Canonical event envelope for every skill lifecycle moment."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""           # promoted | demoted | mutated | gate_pass | gate_fail | imported
    skill_name: str = ""
    skill_version: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trigger: str = ""              # what caused this event (task_type, audit gate id, etc.)
    outcome_score: float = 0.0     # 0.0–1.0 quality signal
    delta_summary: str = ""        # human-readable description of what changed
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_repo: str = "self-improving-system-builder"


@dataclass
class BrainSkillNode:
    """KG node written to the-brain for each unique skill."""
    node_id: str = ""
    skill_name: str = ""
    current_version: int = 1
    last_promoted: Optional[str] = None
    last_demoted: Optional[str] = None
    promotion_count: int = 0
    demotion_count: int = 0
    avg_outcome_score: float = 0.0
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Brain client wrapper (graceful fallback if the-brain is not reachable)
# ---------------------------------------------------------------------------

class BrainWriter:
    """
    Thin wrapper around brain_client.py that adds KG node/edge semantics
    for skill events. Falls back silently to local JSONL if brain is absent.
    """

    def __init__(self):
        self._client = None
        self._available = False
        self._local_mirror = Path(os.getenv("SKILL_BRAIN_MIRROR", "learning_memory.jsonl"))
        self._init_client()

    def _init_client(self):
        try:
            import brain_client  # noqa: F401 — available in SIS repo
            self._client = brain_client
            self._available = True
            logger.info("BrainWriter: brain_client connected")
        except ImportError:
            logger.warning("BrainWriter: brain_client not found — falling back to local JSONL mirror")
        except Exception as exc:
            logger.warning("BrainWriter: brain_client init failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_skill_event(self, event: SkillEvent) -> bool:
        """Write a skill event to the-brain KG and harmony bus."""
        payload = asdict(event)
        success = False

        # 1. Brain KG write
        if self._available:
            try:
                self._client.upsert_node(
                    node_type="skill_event",
                    node_id=f"skill_event:{event.event_id}",
                    properties=payload,
                )
                # Link event → skill node
                skill_node_id = f"skill:{event.skill_name}"
                self._client.upsert_node(
                    node_type="skill",
                    node_id=skill_node_id,
                    properties={
                        "skill_name": event.skill_name,
                        "last_event_type": event.event_type,
                        "last_event_ts": event.timestamp,
                        "last_outcome_score": event.outcome_score,
                    },
                )
                self._client.upsert_edge(
                    from_id=f"skill_event:{event.event_id}",
                    to_id=skill_node_id,
                    edge_type="event_for_skill",
                )
                success = True
                logger.debug("BrainWriter: wrote skill_event %s to KG", event.event_id)
            except Exception as exc:
                logger.warning("BrainWriter: KG write failed: %s", exc)

        # 2. Harmony bus publish
        self._publish_to_harmony(payload)

        # 3. Local JSONL mirror (always)
        self._append_local(payload)

        return success

    def read_skill_history(self, skill_name: str, limit: int = 20) -> List[Dict]:
        """
        Read recent skill events from the-brain for context before next improvement.
        Falls back to scanning local JSONL if brain unavailable.
        """
        if self._available:
            try:
                results = self._client.query_nodes(
                    node_type="skill_event",
                    filters={"skill_name": skill_name},
                    order_by="timestamp",
                    limit=limit,
                )
                if results:
                    return results
            except Exception as exc:
                logger.warning("BrainWriter: read_skill_history KG query failed: %s", exc)

        # Fallback: scan local JSONL
        return self._read_local_history(skill_name, limit)

    def read_all_skill_scores(self) -> Dict[str, float]:
        """
        Return {skill_name: avg_outcome_score} for all skills.
        Used by trigger_dispatcher to weight routing decisions.
        """
        if self._available:
            try:
                nodes = self._client.query_nodes(node_type="skill", filters={}, limit=500)
                return {
                    n["skill_name"]: n.get("last_outcome_score", 0.0)
                    for n in nodes
                    if "skill_name" in n
                }
            except Exception as exc:
                logger.warning("BrainWriter: read_all_skill_scores failed: %s", exc)

        # Fallback: aggregate from JSONL
        scores: Dict[str, List[float]] = {}
        for record in self._iter_local():
            name = record.get("skill_name")
            score = record.get("outcome_score", 0.0)
            if name:
                scores.setdefault(name, []).append(score)
        return {k: sum(v) / len(v) for k, v in scores.items()}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _publish_to_harmony(self, payload: Dict):
        try:
            # Try MATRIX harmony_publisher_base first (preferred shared transport)
            sys.path.insert(0, os.getenv("MATRIX_PATH", "../MATRIX"))
            from harmony_publisher_base import HarmonyPublisher  # noqa
            pub = HarmonyPublisher()
            pub.publish("skill_event", payload)
        except Exception:
            pass  # harmony bus is optional; local JSONL is the safety net

    def _append_local(self, payload: Dict):
        try:
            with self._local_mirror.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as exc:
            logger.warning("BrainWriter: local JSONL append failed: %s", exc)

    def _read_local_history(self, skill_name: str, limit: int) -> List[Dict]:
        results = [
            r for r in self._iter_local()
            if r.get("skill_name") == skill_name
        ]
        return results[-limit:]

    def _iter_local(self):
        if not self._local_mirror.exists():
            return
        with self._local_mirror.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue


# ---------------------------------------------------------------------------
# Module-level singleton (import and use directly)
# ---------------------------------------------------------------------------

_brain_writer: Optional[BrainWriter] = None


def get_brain_writer() -> BrainWriter:
    global _brain_writer
    if _brain_writer is None:
        _brain_writer = BrainWriter()
    return _brain_writer


# ---------------------------------------------------------------------------
# Convenience functions (called by improve_skill.py and trigger_dispatcher.py)
# ---------------------------------------------------------------------------

def record_skill_promoted(
    skill_name: str,
    version: int,
    outcome_score: float,
    delta_summary: str,
    trigger: str = "improve_skill",
    metadata: Optional[Dict] = None,
) -> SkillEvent:
    event = SkillEvent(
        event_type="promoted",
        skill_name=skill_name,
        skill_version=version,
        trigger=trigger,
        outcome_score=outcome_score,
        delta_summary=delta_summary,
        metadata=metadata or {},
    )
    get_brain_writer().write_skill_event(event)
    logger.info("[skill_brain_sync] PROMOTED %s v%d score=%.3f", skill_name, version, outcome_score)
    return event


def record_skill_demoted(
    skill_name: str,
    version: int,
    outcome_score: float,
    reason: str,
    trigger: str = "audit",
) -> SkillEvent:
    event = SkillEvent(
        event_type="demoted",
        skill_name=skill_name,
        skill_version=version,
        trigger=trigger,
        outcome_score=outcome_score,
        delta_summary=reason,
    )
    get_brain_writer().write_skill_event(event)
    logger.info("[skill_brain_sync] DEMOTED %s v%d reason=%s", skill_name, version, reason)
    return event


def record_gate_result(
    skill_name: str,
    gate_id: str,
    passed: bool,
    score: float,
    detail: str = "",
) -> SkillEvent:
    event = SkillEvent(
        event_type="gate_pass" if passed else "gate_fail",
        skill_name=skill_name,
        trigger=gate_id,
        outcome_score=score,
        delta_summary=detail,
    )
    get_brain_writer().write_skill_event(event)
    return event


def record_skill_mutated(
    skill_name: str,
    version: int,
    mutation_summary: str,
    model_used: str = "",
    score: float = 0.0,
) -> SkillEvent:
    event = SkillEvent(
        event_type="mutated",
        skill_name=skill_name,
        skill_version=version,
        trigger="improve_skill",
        outcome_score=score,
        delta_summary=mutation_summary,
        metadata={"model_used": model_used},
    )
    get_brain_writer().write_skill_event(event)
    return event


def get_skill_history(skill_name: str, limit: int = 20) -> List[Dict]:
    """Pull recent history for a skill from the-brain (for context injection)."""
    return get_brain_writer().read_skill_history(skill_name, limit)


def get_all_skill_scores() -> Dict[str, float]:
    """Return {skill_name: score} dict for routing weight decisions."""
    return get_brain_writer().read_all_skill_scores()
