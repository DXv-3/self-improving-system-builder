#!/usr/bin/env python3
"""skill_exporter.py — Export self-improving system skill files to the-brain.

Skill files (skill.md operating manuals) are the learned knowledge of the
self-improving system. This exporter:

    1. Reads all skill.md files from the skills/ directory
    2. Writes each as a conversation ingest to brain.db (FTS5 searchable)
    3. Registers each skill as a node in the knowledge graph
    4. Links skills to the audit gates they govern
    5. Writes a skill_export_manifest.json as an artifact record

This means conductor can query the-brain for skills, and the KG shows
which skills govern which gates.

Usage:
    python skill_exporter.py                    # export all skills
    python skill_exporter.py --skill code_review # export one skill
    python skill_exporter.py --dry-run          # show what would be exported
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "harmony-engine-protocol"))
try:
    from brain_bus import BrainBusPublisher
    _BUS_AVAILABLE = True
except ImportError:
    _BUS_AVAILABLE = False

from audit_brain_bridge import AuditBrainBridge

SKILLS_DIR = Path(__file__).parent / "skills"
SESSION_PREFIX = "self-improving-skills"


def find_skill_files(skills_dir: Path = SKILLS_DIR) -> list[Path]:
    if not skills_dir.exists():
        return []
    md_files = list(skills_dir.rglob("*.md"))
    txt_files = list(skills_dir.rglob("*.txt"))
    return sorted(md_files + txt_files)


def export_skill(
    skill_path: Path,
    bridge: AuditBrainBridge,
    pub: BrainBusPublisher | None,
    dry_run: bool = False,
) -> bool:
    """Export a single skill file to brain.db."""
    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"  [skip] {skill_path.name}: {e}")
        return False

    skill_name = skill_path.name
    session_id = f"{SESSION_PREFIX}-{skill_name.replace('.md', '').replace('.txt', '').replace(' ', '_').lower()}"

    if dry_run:
        print(f"  [dry-run] Would export: {skill_name} ({len(content)} chars)")
        return True

    ok = True

    # 1. Ingest skill content as conversation (FTS5 searchable)
    if pub:
        pub.publish_ingest(
            session_id=session_id,
            role="assistant",
            content=f"SKILL: {skill_name}\n\n{content}",
            source="self-improving-system-builder",
        )

    # 2. Register as KG node
    bridge.kg_register_skill(skill_name)

    # 3. Artifact record for provenance
    if pub:
        pub.publish_artifact(
            artifact_name=skill_name,
            promotion_status="promoted",
            trace_id=bridge.run_id,
            notes=f"Exported from self-improving-system-builder skills/",
        )

    print(f"  [ok] {skill_name} ({len(content)} chars, session={session_id})")
    return ok


def export_all(
    skills_dir: Path = SKILLS_DIR,
    dry_run: bool = False,
    skill_filter: str = "",
) -> dict:
    run_id = f"skill-export-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    bridge = AuditBrainBridge(run_id=run_id)
    pub = BrainBusPublisher(source_repo="self-improving-system-builder") if _BUS_AVAILABLE else None

    skill_files = find_skill_files(skills_dir)
    if skill_filter:
        skill_files = [f for f in skill_files if skill_filter.lower() in f.name.lower()]

    print(f"[skill_exporter] Found {len(skill_files)} skill file(s) in {skills_dir}")
    if not skill_files:
        print("  No skill files found. Create skills/ directory with .md files.")
        return {"exported": 0, "skipped": 0, "run_id": run_id}

    exported = 0
    skipped = 0
    manifest = []

    for skill_path in skill_files:
        ok = export_skill(skill_path, bridge, pub, dry_run=dry_run)
        if ok:
            exported += 1
            manifest.append({"skill": skill_path.name, "path": str(skill_path)})
        else:
            skipped += 1

    # Write manifest as artifact
    if not dry_run and pub:
        manifest_content = json.dumps({
            "run_id": run_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total": exported,
            "skills": manifest,
        }, indent=2)
        # Write manifest to spool as a note (via learn event)
        pub.publish_learn(
            run_id=run_id,
            source="skill_exporter",
            category="export_manifest",
            event_type="SKILL_EXPORTED",
            detail=manifest_content[:1000],
            outcome="pass",
        )

    print(f"[skill_exporter] Done. Exported: {exported}, Skipped: {skipped}")
    return {"exported": exported, "skipped": skipped, "run_id": run_id}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export skill files to brain.db")
    parser.add_argument("--skill", default="", help="Filter: only export skills matching this name")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be exported without writing")
    parser.add_argument("--skills-dir", default=str(SKILLS_DIR), help="Path to skills directory")
    args = parser.parse_args()

    result = export_all(
        skills_dir=Path(args.skills_dir),
        dry_run=args.dry_run,
        skill_filter=args.skill,
    )
    sys.exit(0 if result["skipped"] == 0 else 1)
