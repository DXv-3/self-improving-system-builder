#!/usr/bin/env python3
"""audit_brain_bridge.py — Self-improving system → brain.db integration.

Every IDKWIDK 7-gate audit run, every skill mutation, every task dispatch
outcome, and every self-improvement cycle gets logged to brain.db via
the harmony brain bus. This turns the self-improving system's learning
into queryable, conductor-readable history.

What gets written per audit cycle:
    - Gate 1–7 pass/fail outcomes (individual learn() events per gate)
    - Skill file mutations: old version → new version (artifact records)
    - Task dispatch outcomes (learn() events with model + latency)
    - Improvement cycle summaries (aggregate pass rates, skill delta)
    - Heartbeat pings so dashboard.py shows system status

Usage:
    from audit_brain_bridge import AuditBrainBridge

    bridge = AuditBrainBridge(run_id="audit-2026-07-04-001")

    # At the start of an audit run
    bridge.run_started(task_type="code_review", model="grok-3")

    # For each gate
    bridge.gate_result(gate_num=1, passed=True, detail="syntax valid")
    bridge.gate_result(gate_num=2, passed=False, detail="test failed: assert error")

    # When a skill file is updated
    bridge.skill_mutated(skill_name="code_review.md",
                         change_summary="Added edge case for empty input")

    # At the end of an audit run
    bridge.run_completed(gates_passed=6, gates_failed=1,
                         improvement_delta=0.14)
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "harmony-engine-protocol"))
try:
    from brain_bus import BrainBusPublisher
    _BUS_AVAILABLE = True
except ImportError:
    _BUS_AVAILABLE = False


GATE_NAMES = {
    1: "syntax_check",
    2: "test_pass",
    3: "regression_check",
    4: "performance_check",
    5: "security_scan",
    6: "skill_alignment",
    7: "human_review",
}


class AuditBrainBridge:
    """Write IDKWIDK audit gate outcomes and skill mutations to brain.db."""

    def __init__(self, run_id: str = "", source_repo: str = "self-improving-system-builder"):
        self.run_id = run_id or f"audit-{str(uuid.uuid4())[:8]}"
        self.source_repo = source_repo
        self._pub: BrainBusPublisher | None = None
        if _BUS_AVAILABLE:
            self._pub = BrainBusPublisher(source_repo=source_repo)
        self._gates_passed = 0
        self._gates_failed = 0
        self._start_time = datetime.now(timezone.utc)

    def _learn(self, event_type: str, category: str, detail: str, outcome: str) -> bool:
        if self._pub is None:
            print(f"[audit_bridge][no-bus] {event_type}: {detail[:80]}")
            return False
        return self._pub.publish_learn(
            run_id=self.run_id,
            source=self.source_repo,
            category=category,
            event_type=event_type,
            detail=detail,
            outcome=outcome,
        )

    def run_started(
        self,
        task_type: str = "",
        model: str = "",
        total_gates: int = 7,
    ) -> bool:
        """Log that an audit run has started."""
        detail = json.dumps({
            "task_type": task_type,
            "model": model,
            "total_gates": total_gates,
            "started_at": self._start_time.isoformat(),
        })
        ok = self._learn("AUDIT_STARTED", "audit_lifecycle", detail, "info")
        # Also ping so dashboard shows system alive
        if self._pub:
            self._pub.publish_ping(
                subsystem_name=self.source_repo,
                status="running",
                run_id=self.run_id,
            )
        return ok

    def gate_result(
        self,
        gate_num: int,
        passed: bool,
        detail: str = "",
        duration_ms: float = 0.0,
        model: str = "",
    ) -> bool:
        """Log a single gate pass or fail.

        Gate number must be 1-7. This maps to the IDKWIDK protocol:
            Gate 1: syntax_check
            Gate 2: test_pass
            Gate 3: regression_check
            Gate 4: performance_check
            Gate 5: security_scan
            Gate 6: skill_alignment
            Gate 7: human_review
        """
        gate_name = GATE_NAMES.get(gate_num, f"gate_{gate_num}")
        event_type = "GATE_PASSED" if passed else "GATE_FAILED"
        outcome = "pass" if passed else "fail"
        if passed:
            self._gates_passed += 1
        else:
            self._gates_failed += 1

        full_detail = json.dumps({
            "gate_num": gate_num,
            "gate_name": gate_name,
            "detail": detail[:300],
            "duration_ms": round(duration_ms, 1),
            "model": model,
        })
        return self._learn(event_type, "gate", full_detail, outcome)

    def skill_mutated(
        self,
        skill_name: str,
        change_summary: str = "",
        version_before: str = "",
        version_after: str = "",
        lines_changed: int = 0,
    ) -> bool:
        """Log a skill file mutation (learning from this audit cycle)."""
        # Record as artifact for provenance
        if self._pub:
            self._pub.publish_artifact(
                artifact_name=skill_name,
                promotion_status="promoted",
                trace_id=self.run_id,
                notes=change_summary[:200],
            )
        return self._learn(
            event_type="SKILL_EXPORTED",
            category="skill_mutation",
            detail=json.dumps({
                "skill_name": skill_name,
                "change_summary": change_summary[:300],
                "version_before": version_before,
                "version_after": version_after,
                "lines_changed": lines_changed,
            }),
            outcome="pass",
        )

    def task_dispatched(
        self,
        task_type: str,
        model: str,
        outcome: str,
        latency_ms: float = 0.0,
        error: str = "",
    ) -> bool:
        """Log a task dispatch outcome (model call result from self-improving loop)."""
        return self._learn(
            event_type="GATE_PASSED" if outcome == "pass" else "GATE_FAILED",
            category="task_dispatch",
            detail=json.dumps({
                "task_type": task_type,
                "model": model,
                "latency_ms": round(latency_ms, 1),
                "error": error[:200],
            }),
            outcome=outcome,
        )

    def run_completed(
        self,
        gates_passed: int | None = None,
        gates_failed: int | None = None,
        improvement_delta: float = 0.0,
        notes: str = "",
    ) -> bool:
        """Log audit run completion with aggregate stats."""
        passed = gates_passed if gates_passed is not None else self._gates_passed
        failed = gates_failed if gates_failed is not None else self._gates_failed
        total = passed + failed
        pass_rate = round(passed / total, 3) if total > 0 else 0.0
        duration_s = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        detail = json.dumps({
            "gates_passed": passed,
            "gates_failed": failed,
            "total_gates": total,
            "pass_rate": pass_rate,
            "improvement_delta": round(improvement_delta, 4),
            "duration_seconds": round(duration_s, 2),
            "notes": notes[:200],
        })
        outcome = "pass" if failed == 0 else ("fail" if pass_rate < 0.5 else "pass")
        ok = self._learn("AUDIT_COMPLETED", "audit_lifecycle", detail, outcome)
        if self._pub:
            self._pub.publish_ping(
                subsystem_name=self.source_repo,
                status="completed",
                run_id=self.run_id,
            )
        return ok

    def route_adjusted(
        self,
        original_model: str,
        new_model: str,
        reason: str = "",
        source: str = "brain_query",
    ) -> bool:
        """Log when self-improving system's own routing was adjusted by the brain."""
        return self._learn(
            event_type="ROUTE_ADJUSTED",
            category="routing",
            detail=json.dumps({
                "original_model": original_model,
                "new_model": new_model,
                "reason": reason[:200],
                "source": source,
            }),
            outcome="info",
        )

    def kg_register_skill(self, skill_name: str, skill_type: str = "operating_manual") -> bool:
        """Add a skill node to the knowledge graph."""
        if self._pub is None:
            return False
        node_id = f"skill:{skill_name.replace('.md', '').replace(' ', '_').lower()}"
        return self._pub.publish_kg_node(
            node_id=node_id,
            node_type="skill",
            label=skill_name,
            properties={"skill_type": skill_type, "run_id": self.run_id},
        )

    def kg_link_skill_to_gate(self, skill_name: str, gate_num: int) -> bool:
        """Add a GOVERNS edge: skill → gate in the knowledge graph."""
        if self._pub is None:
            return False
        skill_id = f"skill:{skill_name.replace('.md', '').replace(' ', '_').lower()}"
        gate_id = f"gate:{self.run_id}:gate_{gate_num}"
        return self._pub.publish_kg_edge(
            source_id=skill_id,
            target_id=gate_id,
            relation="GOVERNS",
            weight=1.0,
        )
