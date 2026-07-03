#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_json, save_json, append_jsonl


def _record_to_learning_memory(queue: dict, result: dict, case_dir: Path) -> None:
    """
    Wire learning_memory.record_cycle_outcome() after every persist.
    Closes MEMORY_GAP: cross-run knowledge now accumulates.
    Failures are logged to execution_log.jsonl rather than swallowed silently.
    """
    try:
        from learning_memory import record_cycle_outcome
        completed = [a for a in queue['actions'] if a.get('status') == 'completed']
        blocked   = [a for a in queue['actions'] if a.get('status') in {'blocked', 'failed'}]

        blocker_patterns = [
            {
                'action_id': b['action_id'],
                'label':     b.get('blocker_label', 'unknown'),
                'notes':     b.get('notes', ''),
            }
            for b in blocked
        ]
        successful_followup_types = list({
            a.get('execution_type', '') for a in completed
            if 'SPINNER' in a.get('action_id', '') or 'FOLLOWUP' in a.get('action_id', '')
        })
        claim_resolutions = [
            {
                'action_id': a['action_id'],
                'category':  a.get('category', ''),
                'source':    a.get('source', ''),
            }
            for a in completed
        ]
        retry_strategy = 'unknown'
        retry_path = case_dir / 'retry_strategy.json'
        if retry_path.exists():
            try:
                retry_strategy = load_json(str(retry_path)).get('strategy', 'unknown')
            except Exception:
                pass

        cycle_id = (
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
            f"-{result.get('action_id', 'none')}"
        )
        record_cycle_outcome(
            cycle_id=cycle_id,
            blocker_patterns=blocker_patterns,
            successful_followup_types=successful_followup_types,
            approval_outcomes=[],
            retry_strategy=retry_strategy,
            claim_resolutions=claim_resolutions,
        )
    except Exception as exc:
        # Log the failure instead of silently swallowing it.
        # This makes MEMORY_GAP failures visible in the audit trail.
        append_jsonl(
            case_dir / 'execution_log.jsonl',
            {
                'event':   'learning_memory_error',
                'error':   str(exc),
                'action':  result.get('action_id', 'unknown'),
                'ts':      datetime.now(timezone.utc).isoformat(),
            }
        )


def main(queue_path: str, verified_result_path: str, case_dir_str: str) -> None:
    case   = Path(case_dir_str)
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

    # Wire: MEMORY_GAP now closed — exceptions are logged, never silently swallowed
    _record_to_learning_memory(queue, result, case)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
