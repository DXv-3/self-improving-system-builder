#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json

COMPLETED = {'completed', 'skipped'}


def _load_trust_adjustments(scripts_dir: Path) -> dict[str, float]:
    """
    Load risk adjustments from trust_update.py output.
    Returns empty dict if adjustments file doesn't exist yet
    (safe — no adjustment is applied until trust_update.py has data).
    """
    adj_path = Path('trust_adjustments.json')
    if not adj_path.exists():
        # also check relative to scripts dir
        adj_path = scripts_dir.parent / 'trust_adjustments.json'
    if adj_path.exists():
        try:
            import json
            data = json.loads(adj_path.read_text())
            return {k: float(v) for k, v in data.get('adjustments', {}).items()}
        except Exception:
            pass
    return {}


def score_action(action: dict, completed_ids: set, trust_adjustments: dict) -> dict:
    dep_penalty = sum(
        1 for d in action.get('dependencies', []) if d not in completed_ids
    ) * 3

    # Apply trust adjustment to risk_level (calibrated from historical outcomes)
    cat = action.get('category', '')
    risk_adj = trust_adjustments.get(cat, 0.0)
    effective_risk = max(0.0, float(action.get('risk_level', 0)) + risk_adj)

    score = (
        float(action.get('priority',       0))
        + float(action.get('leverage_score', 0))
        + float(action.get('unblock_power',  0))
        + float(action.get('proof_value',    0))
        + float(action.get('reuse_value',    0))
        - effective_risk
        - dep_penalty
    )
    action['score']               = round(score, 2)
    action['dependency_penalty']  = dep_penalty
    action['blocked_by_dependencies'] = dep_penalty > 0
    action['effective_risk']      = round(effective_risk, 2)
    if risk_adj != 0.0:
        action['trust_adjustment'] = risk_adj
    return action


def main(queue_path: str, out_path: str) -> None:
    queue = load_json(queue_path)
    scripts_dir = Path(__file__).resolve().parent
    trust_adjustments = _load_trust_adjustments(scripts_dir)
    completed_ids = {
        a['action_id'] for a in queue['actions']
        if a.get('status') in COMPLETED
    }
    queue['actions'] = sorted(
        [score_action(a, completed_ids, trust_adjustments) for a in queue['actions']],
        key=lambda x: (-x.get('score', 0), x['action_id'])
    )
    save_json(out_path, queue)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
