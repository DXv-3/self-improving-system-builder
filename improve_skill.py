"""
improve_skill.py — LLM-powered skill mutation engine.

Works as follows:
  1. Load skill record from brain (via brain_client) or fallback JSONL.
  2. Load recent failure examples for this skill from learning_memory.jsonl.
  3. Build a structured mutation prompt.
  4. Call the model (ModelCaller — Z.AI > Anthropic > OpenAI > Ollama).
  5. Parse + validate the JSON diff the model returns.
  6. Gate through IDKWIDK 7-gate auditor.
  7. Apply patch: update brain + write skill file to disk.
  8. Emit a build-watch event so the dashboard shows the mutation live.
  9. Append outcome to learning_memory.jsonl.

Can be called standalone:
    python3 improve_skill.py --skill context_spinner --dry-run
    python3 improve_skill.py --skill context_spinner --provider anthropic

Or imported:
    from improve_skill import improve_skill
    result = improve_skill(skill_name="context_spinner")
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from model_caller import CallSpec, ModelCaller, ModelCallerError

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file's location
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
LEARNING_MEMORY = ROOT / "learning_memory.jsonl"
SKILLS_DIR = ROOT / "skills"
BUILD_WATCH_DIR = Path(os.environ.get("BUILD_WATCH_DIR", ROOT / ".build-watch"))


# ---------------------------------------------------------------------------
# IDKWIDK 7-Gate Auditor
# ---------------------------------------------------------------------------

GATE_NAMES = [
    "G1:NotEmpty",
    "G2:ValidJSON",
    "G3:HasRationale",
    "G4:NoRegression",
    "G5:ScopeContained",
    "G6:SafeOps",
    "G7:DeltaReasonable",
]

FORBIDDEN_OPS = [
    "os.system", "subprocess", "eval(", "exec(",
    "__import__", "open(\"/etc", "open('/etc",
    "rm -rf", "shutil.rmtree",
]


class IDKWIDKRejection(ValueError):
    pass


class SkillMutationAuditor:
    """
    Gates a proposed skill mutation through 7 checks.
    Raises IDKWIDKRejection with the failing gate name on any failure.
    All 7 gates must pass for the mutation to be accepted.
    """

    def audit(self, original: dict, mutation: dict) -> None:
        self._g1_not_empty(mutation)
        self._g2_valid_structure(mutation)
        self._g3_has_rationale(mutation)
        self._g4_no_regression(original, mutation)
        self._g5_scope_contained(original, mutation)
        self._g6_safe_ops(mutation)
        self._g7_delta_reasonable(original, mutation)

    def _g1_not_empty(self, m: dict):
        if not m or not m.get("patch"):
            raise IDKWIDKRejection("G1:NotEmpty — mutation patch is empty")

    def _g2_valid_structure(self, m: dict):
        required = {"patch", "rationale", "expected_improvement"}
        missing = required - m.keys()
        if missing:
            raise IDKWIDKRejection(f"G2:ValidJSON — missing keys: {missing}")

    def _g3_has_rationale(self, m: dict):
        r = str(m.get("rationale", "")).strip()
        if len(r) < 20:
            raise IDKWIDKRejection("G3:HasRationale — rationale too short (< 20 chars)")

    def _g4_no_regression(self, original: dict, m: dict):
        # Expected improvement must claim positive direction
        ei = str(m.get("expected_improvement", "")).lower()
        if any(neg in ei for neg in ["worse", "degrade", "reduce accuracy", "decrease"]):
            raise IDKWIDKRejection("G4:NoRegression — expected_improvement signals regression")

    def _g5_scope_contained(self, original: dict, m: dict):
        # Patch must only touch keys that exist in the original skill OR add new keys
        # that are sub-keys of known schema fields (steps, examples, constraints)
        patch = m.get("patch", {})
        known_top = set(original.keys()) | {"steps", "examples", "constraints", "notes", "triggers"}
        rogue = [k for k in patch if k not in known_top]
        if rogue:
            raise IDKWIDKRejection(f"G5:ScopeContained — patch touches unknown top-level keys: {rogue}")

    def _g6_safe_ops(self, m: dict):
        text = json.dumps(m)
        for op in FORBIDDEN_OPS:
            if op in text:
                raise IDKWIDKRejection(f"G6:SafeOps — forbidden operation found: {op!r}")

    def _g7_delta_reasonable(self, original: dict, m: dict):
        # Mutation should not increase total size by more than 3× the original
        orig_size = len(json.dumps(original))
        patch_size = len(json.dumps(m.get("patch", {})))
        if orig_size > 0 and patch_size > orig_size * 3:
            raise IDKWIDKRejection(
                f"G7:DeltaReasonable — patch ({patch_size}B) is >3× original ({orig_size}B)"
            )


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

MUTATION_SYSTEM = """\
You are a skill mutation engine for a self-improving AI system.
Your job: given a skill definition and recent failure examples, produce a
minimal, targeted improvement to the skill.

Rules:
- Output ONLY valid JSON. No markdown fences, no explanation outside the JSON.
- The JSON must have exactly three top-level keys:
  1. "patch"            — dict of key→value changes to apply to the skill
  2. "rationale"        — string, ≥ 20 chars, explains what was wrong and why this fixes it
  3. "expected_improvement" — string, describes the positive outcome if applied
- Do NOT invent new top-level keys beyond the skill's existing schema.
- Do NOT include any shell commands, eval(), or file system operations.
- Keep the patch minimal: only touch what needs to change.
- If the skill is fine and no mutation is warranted, return:
  {"patch": {}, "rationale": "No improvement identified.", "expected_improvement": "No change expected."}
"""


def _build_mutation_prompt(skill_name: str, skill_record: dict, failures: list[dict]) -> str:
    failure_block = "\n".join(
        f"  [{i+1}] trigger={f.get('trigger','?')} outcome={f.get('outcome','?')} note={f.get('note','')}"
        for i, f in enumerate(failures[:5])
    ) or "  (no recent failures — optimise for general improvement)"

    return (
        f"SKILL NAME: {skill_name}\n\n"
        f"CURRENT SKILL DEFINITION:\n{json.dumps(skill_record, indent=2)}\n\n"
        f"RECENT FAILURES (last 5):\n{failure_block}\n\n"
        "Produce the mutation JSON now."
    )


# ---------------------------------------------------------------------------
# Brain interaction
# ---------------------------------------------------------------------------

def _load_skill_from_brain(skill_name: str) -> Optional[dict]:
    """Try to load skill via brain_client. Returns None if unavailable."""
    try:
        from brain_client import BrainClient
        client = BrainClient()
        records = client.query(f"skill:{skill_name}", limit=1)
        if records:
            return records[0]
    except Exception as exc:
        log.debug("brain_client unavailable: %s", exc)
    return None


def _load_skill_from_disk(skill_name: str) -> dict:
    """Fallback: load skill from skills/ directory."""
    candidates = list(SKILLS_DIR.glob(f"{skill_name}*.json")) + \
                 list(SKILLS_DIR.glob(f"{skill_name}*.md"))
    if candidates:
        f = candidates[0]
        text = f.read_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"name": skill_name, "raw": text[:2000]}
    return {"name": skill_name, "steps": [], "notes": "no definition found"}


def _load_skill(skill_name: str) -> dict:
    record = _load_skill_from_brain(skill_name)
    if record:
        return record
    return _load_skill_from_disk(skill_name)


def _load_failures(skill_name: str) -> list[dict]:
    """Load recent failures for this skill from learning_memory.jsonl."""
    failures = []
    if not LEARNING_MEMORY.exists():
        return failures
    for line in LEARNING_MEMORY.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if (
                skill_name in str(entry.get("skill", ""))
                and entry.get("outcome") in ("failure", "error", "rejected")
            ):
                failures.append(entry)
        except json.JSONDecodeError:
            pass
    return failures[-10:]  # most recent 10


def _push_patch_to_brain(skill_name: str, patch: dict, mutation_id: str) -> bool:
    """Write the accepted patch back to the brain."""
    try:
        from brain_client import BrainClient
        client = BrainClient()
        client.store({
            "type": "skill_mutation",
            "skill": skill_name,
            "mutation_id": mutation_id,
            "patch": patch,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return True
    except Exception as exc:
        log.warning("Could not push patch to brain: %s", exc)
        return False


def _apply_patch_to_disk(skill_name: str, original: dict, patch: dict) -> Optional[Path]:
    """Merge patch into original and write to skills/ dir."""
    SKILLS_DIR.mkdir(exist_ok=True)
    merged = {**original, **patch}
    path = SKILLS_DIR / f"{skill_name}.json"
    path.write_text(json.dumps(merged, indent=2))
    return path


# ---------------------------------------------------------------------------
# build-watch event emitter
# ---------------------------------------------------------------------------

def _emit_build_watch_event(msg: str, kind: str = "edit", files: list[str] | None = None):
    """Append a structured event to .build-watch/events.jsonl."""
    try:
        BUILD_WATCH_DIR.mkdir(parents=True, exist_ok=True)
        events_file = BUILD_WATCH_DIR / "events.jsonl"
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "msg": msg,
            "files": files or [],
        }
        with events_file.open("a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as exc:
        log.debug("build-watch emit failed: %s", exc)


# ---------------------------------------------------------------------------
# Outcome logger
# ---------------------------------------------------------------------------

def _log_outcome(
    skill_name: str,
    mutation_id: str,
    outcome: str,
    gate: Optional[str],
    patch: dict,
    latency_ms: float,
    provider: str,
):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "skill": skill_name,
        "mutation_id": mutation_id,
        "outcome": outcome,
        "gate_failed": gate,
        "patch_keys": list(patch.keys()),
        "latency_ms": round(latency_ms, 1),
        "provider": provider,
    }
    with LEARNING_MEMORY.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Core public function
# ---------------------------------------------------------------------------

def improve_skill(
    skill_name: str,
    dry_run: bool = False,
    provider: Optional[str] = None,
    model_hint: Optional[str] = None,
) -> dict:
    """
    Run one improvement cycle for the named skill.

    Returns a result dict:
      {
        "skill": str,
        "mutation_id": str,
        "outcome": "applied" | "rejected" | "no_change" | "error",
        "gate_failed": str | None,
        "patch": dict,
        "rationale": str,
        "provider": str,
        "latency_ms": float,
        "dry_run": bool,
      }
    """
    mutation_id = str(uuid.uuid4())[:8]
    t0 = time.monotonic()
    auditor = SkillMutationAuditor()
    caller = ModelCaller(preferred_provider=provider)

    log.info("[improve_skill] Starting cycle: skill=%s mutation_id=%s dry_run=%s",
             skill_name, mutation_id, dry_run)
    _emit_build_watch_event(
        f"improve_skill: starting cycle for '{skill_name}' [{mutation_id}]",
        kind="plan",
    )

    # 1. Load skill + failures
    skill_record = _load_skill(skill_name)
    failures = _load_failures(skill_name)
    log.debug("Loaded skill (%d keys), %d failures", len(skill_record), len(failures))

    # 2. Build prompt + call model
    prompt = _build_mutation_prompt(skill_name, skill_record, failures)
    spec = CallSpec(
        system=MUTATION_SYSTEM,
        user=prompt,
        max_tokens=1024,
        temperature=0.35,
        model_hint=model_hint,
    )

    try:
        result = caller.call(spec)
    except ModelCallerError as exc:
        latency_ms = (time.monotonic() - t0) * 1000
        _emit_build_watch_event(f"improve_skill: model call failed — {exc}", kind="note")
        _log_outcome(skill_name, mutation_id, "error", None, {}, latency_ms, "none")
        return {
            "skill": skill_name, "mutation_id": mutation_id,
            "outcome": "error", "gate_failed": None, "patch": {},
            "rationale": str(exc), "provider": "none",
            "latency_ms": latency_ms, "dry_run": dry_run,
        }

    latency_ms = (time.monotonic() - t0) * 1000

    # 3. Parse model output — strip markdown fences if present
    raw = result.text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    try:
        mutation = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Model returned non-JSON: %s ...", raw[:200])
        _emit_build_watch_event(
            f"improve_skill: model returned invalid JSON [{mutation_id}]", kind="note"
        )
        _log_outcome(skill_name, mutation_id, "error", "parse", {}, latency_ms, result.provider)
        return {
            "skill": skill_name, "mutation_id": mutation_id,
            "outcome": "error", "gate_failed": "parse",
            "patch": {}, "rationale": f"JSON parse error: {exc}",
            "provider": result.provider, "latency_ms": latency_ms, "dry_run": dry_run,
        }

    patch = mutation.get("patch", {})
    rationale = mutation.get("rationale", "")

    # 4. No-change short circuit
    if not patch:
        log.info("[improve_skill] Model returned empty patch — no change warranted")
        _emit_build_watch_event(
            f"improve_skill: no improvement identified for '{skill_name}'", kind="note"
        )
        _log_outcome(skill_name, mutation_id, "no_change", None, {}, latency_ms, result.provider)
        return {
            "skill": skill_name, "mutation_id": mutation_id,
            "outcome": "no_change", "gate_failed": None,
            "patch": {}, "rationale": rationale,
            "provider": result.provider, "latency_ms": latency_ms, "dry_run": dry_run,
        }

    # 5. IDKWIDK gate audit
    try:
        auditor.audit(skill_record, mutation)
    except IDKWIDKRejection as exc:
        gate = str(exc).split(" — ")[0]
        log.warning("[improve_skill] IDKWIDK rejected at %s: %s", gate, exc)
        _emit_build_watch_event(
            f"improve_skill: mutation REJECTED at {gate} for '{skill_name}' [{mutation_id}]",
            kind="note",
        )
        _log_outcome(skill_name, mutation_id, "rejected", gate, patch, latency_ms, result.provider)
        return {
            "skill": skill_name, "mutation_id": mutation_id,
            "outcome": "rejected", "gate_failed": gate,
            "patch": patch, "rationale": rationale,
            "provider": result.provider, "latency_ms": latency_ms, "dry_run": dry_run,
        }

    # 6. Apply (unless dry run)
    if not dry_run:
        pushed = _push_patch_to_brain(skill_name, patch, mutation_id)
        written_path = _apply_patch_to_disk(skill_name, skill_record, patch)
        _emit_build_watch_event(
            f"improve_skill: applied mutation [{mutation_id}] to '{skill_name}' "
            f"(brain={'ok' if pushed else 'skipped'}, disk={written_path})",
            kind="edit",
            files=[str(written_path)] if written_path else [],
        )
        log.info("[improve_skill] Applied: brain=%s disk=%s", pushed, written_path)
    else:
        _emit_build_watch_event(
            f"improve_skill: DRY-RUN — would apply [{mutation_id}] to '{skill_name}'",
            kind="note",
        )
        log.info("[improve_skill] Dry-run — patch NOT applied")

    _log_outcome(skill_name, mutation_id, "applied", None, patch, latency_ms, result.provider)
    return {
        "skill": skill_name, "mutation_id": mutation_id,
        "outcome": "applied" if not dry_run else "dry_run_ok",
        "gate_failed": None, "patch": patch, "rationale": rationale,
        "provider": result.provider, "latency_ms": round(latency_ms, 1),
        "dry_run": dry_run,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ap = argparse.ArgumentParser(description="Run one LLM-powered skill improvement cycle.")
    ap.add_argument("--skill", required=True, help="Skill name (e.g. context_spinner)")
    ap.add_argument("--dry-run", action="store_true", help="Parse + audit but do not apply")
    ap.add_argument("--provider", default=None,
                    choices=["zai", "anthropic", "openai", "ollama"],
                    help="Force a specific provider")
    ap.add_argument("--model", default=None, help="Override model name")
    ap.add_argument("--json", action="store_true", help="Print result as JSON")
    args = ap.parse_args()

    r = improve_skill(
        skill_name=args.skill,
        dry_run=args.dry_run,
        provider=args.provider,
        model_hint=args.model,
    )

    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Skill:    {r['skill']}")
        print(f"Outcome:  {r['outcome']}  (mutation_id={r['mutation_id']})")
        print(f"Provider: {r['provider']}  ({r['latency_ms']:.0f}ms)")
        if r['gate_failed']:
            print(f"Gate:     FAILED at {r['gate_failed']}")
        print(f"Rationale: {r['rationale'][:200]}")
        if r['patch']:
            print(f"Patch keys: {list(r['patch'].keys())}")
        print(f"{'='*60}\n")
