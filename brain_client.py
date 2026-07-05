"""brain_client.py — locates the-brain and returns a SelfImproverBridge instance.

This module is the single place where self-improving-system-builder resolves
the path to the-brain. It does NOT require the-brain to be pip-installed;
it resolves the repo by convention or environment variable.

Resolution order for BRAIN_DIR:
    1. BRAIN_DIR environment variable (explicit)
    2. BRAIN_DB_PATH environment variable (extract parent dirs)
    3. ../the-brain relative to this file (sibling repo convention)
    4. ~/vinny-stack/the-brain (monorepo convention)
    5. ~/the-brain (standalone clone)

Usage:
    from brain_client import get_bridge, BRAIN_AVAILABLE

    bridge = get_bridge()   # returns SelfImproverBridge or None
    if bridge:
        patterns = bridge.get_skills_needing_review()
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def _resolve_brain_dir() -> Optional[Path]:
    """Find the the-brain repo directory."""
    # 1. Explicit env var
    if ev := os.environ.get("BRAIN_DIR"):
        p = Path(ev)
        if p.exists():
            return p

    # 2. Derive from BRAIN_DB_PATH
    if db := os.environ.get("BRAIN_DB_PATH"):
        for parent in Path(db).parents:
            if (parent / "brain_sync.py").exists():
                return parent

    # 3. Sibling repo (most common dev layout: repos cloned side by side)
    sibling = Path(__file__).parent.parent / "the-brain"
    if sibling.exists() and (sibling / "brain_sync.py").exists():
        return sibling

    # 4. vinny-stack monorepo
    mono = Path.home() / "vinny-stack" / "the-brain"
    if mono.exists() and (mono / "brain_sync.py").exists():
        return mono

    # 5. Home directory clone
    home = Path.home() / "the-brain"
    if home.exists() and (home / "brain_sync.py").exists():
        return home

    return None


# Resolve at import time
BRAIN_DIR = _resolve_brain_dir()
BRAIN_AVAILABLE = BRAIN_DIR is not None

if BRAIN_AVAILABLE and str(BRAIN_DIR) not in sys.path:
    sys.path.insert(0, str(BRAIN_DIR))


def get_bridge(db_path: str | None = None):
    """Return a SelfImproverBridge instance, or None if the-brain is not found.

    Args:
        db_path: Optional explicit path to brain.db. If None, uses
                 BRAIN_DB_PATH env var or BrainSync default.

    Returns:
        SelfImproverBridge instance, or None.
    """
    if not BRAIN_AVAILABLE:
        print(
            "[brain_client] WARNING: the-brain not found. "
            f"Set BRAIN_DIR env var. Searched: {_search_paths()}"
        )
        return None

    try:
        from self_improver_bridge import SelfImproverBridge  # type: ignore
        return SelfImproverBridge(db_path=db_path or os.environ.get("BRAIN_DB_PATH"))
    except ImportError as e:
        print(f"[brain_client] Import error from {BRAIN_DIR}: {e}")
        return None
    except Exception as e:
        print(f"[brain_client] Failed to initialize bridge: {e}")
        return None


def _search_paths() -> list[str]:
    """Return the list of paths that were searched, for debugging."""
    return [
        str(Path(__file__).parent.parent / "the-brain"),
        str(Path.home() / "vinny-stack" / "the-brain"),
        str(Path.home() / "the-brain"),
        "$BRAIN_DIR",
        "$BRAIN_DB_PATH/../..",
    ]


if __name__ == "__main__":
    print(f"BRAIN_DIR:       {BRAIN_DIR}")
    print(f"BRAIN_AVAILABLE: {BRAIN_AVAILABLE}")
    bridge = get_bridge()
    if bridge:
        print(f"Bridge:          OK — {type(bridge).__name__}")
        print(f"Brain DB:        {bridge.brain.db_path if hasattr(bridge.brain, 'db_path') else 'unknown'}")
    else:
        print("Bridge:          UNAVAILABLE")
        print(f"Searched paths:  {_search_paths()}")
