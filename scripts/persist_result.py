#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, save_json, append_jsonl


def _record_to_learning_memory(queue: dict, result: dict, case_dir: Path) -> None:
    """
    Wire learning_memory.record_cycle_outcome() after every persist.
    Closes the MEMORY_GAP: cross-run knowledge now accumulates.
    """
    try:
        from learning_memory import record_cycle_outcome
        completed = [a for a in queue['actions'] if a.get('status') == 'completed']
        blocked   = [a for a in queue['actions'] if a.get('status') in {'blocked', 'failed'}]
        # blocker_patterns: list of {action_id, label, notes}
        blocker_patterns = [
            {
                'action_id': b['action_id'],
                'label': b.get('blocker_label', 'unknown'),
                'notes': b.get('notes', ''),
            }
            for b in blocked
        ]
        # successful follow-up types from completed actions
        successful_followup_types = list({
            a.get('execution_type', '') for a in completed
            if 'SPINNER' in a.get('action_id', '') or 'FOLLOWUP' in a.get('action_id', '')
        })
        # claim resolutions: completed actions mapped to their source claim
        claim_resolutions = [
            {'action_id': a['action_id'], 'category': a.get('category', ''), 'source': a.get('source', '')}
            for a in completed
        ]
        # retry strategy from file if present
        retry_path = case_dir / 'retry_strategy.json'
        retry_strategy = 'unknown'
        if retry_path.exists():
            rs = load_json(str(retry_path))
            retry_strategy = rs.get('strategy', 'unknown')

        cycle_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{result.get('action_id', 'none')}"
        record_cycle_outcome(
            cycle_id=cycle_id,
            blocker_patterns=blocker_patterns,
            successful_followup_types=successful_followup_types,
            approval_outcomes=[],
            retry_strategy=retry_strategy,
            claim_resolutions=claim_resolutions,
        )
    except Exception as e:
        # learning_memory is an enhancement, never block execution on it
        pass


def main(queue_path, verified_result_path, case_dir):
    case = Path(case_dir)
    case.mkdir(parents=True, exist_ok=True)
    queue  = load_json(queue_path)
    result = load_json(verified_result_path)

    append_jsonl(case / 'execution_log.jsonl', result)

    completed = [a for a in queue['actions'] if a.get('status') == 'completed']
    blocked   = [a for a in queue['actions'] if a.get('status') in {'blocked', 'failed'}]
    pending   = [a for a in queue['actions'] if a.get('status') == 'pending']

    save_json(case / 'completed_actions.json', completed)
    save_json(case / 'blocked_actions.json',   blocked)
    save_json(case / 'pending_actions.json',   pending)

    (case / 'progress_snapshot.md').write_text(
        f'# Progress Snapshot\n\n'
        f'- Completed: {len(completed)}\n'
        f'- Blocked/Failed: {len(blocked)}\n'
        f'- Pending: {len(pending)}\n'
        f'- Last action: {result.get("action_id", "none")}\n'
        f'- Verified: {result.get("verified", False)}\n'
    )

    lines = ['# Next Blockers\n']
    lines += [
        f"- {b['action_id']}: {b.get('title', '')} :: {b.get('notes', '')}"
        for b in blocked
    ] or ['- None currently blocked.']
    (case / 'next_blockers.md').write_text('\n'.join(lines) + '\n')

    # Wire learning memory — MEMORY_GAP now closed
    _record_to_learning_memory(queue, result, case)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
