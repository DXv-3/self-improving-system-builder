#!/usr/bin/env python3
"""
test_healing.py

Verifies all heals are structurally in place.
12 concrete assertions, one per heal.
Run: pytest tests/test_healing.py -v
"""
import subprocess, json, tempfile
from pathlib import Path
import pytest

ROOT    = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
EXAMPLE = ROOT / 'examples' / 'bundle_forensics_case'


def test_persist_result_calls_learning_memory():
    source = (SCRIPTS / 'persist_result.py').read_text()
    assert 'from learning_memory import record_cycle_outcome' in source
    assert '_record_to_learning_memory' in source
    assert 'learning_memory_error' in source, \
        'persist_result must log learning_memory failures to execution_log, not swallow them'


def test_score_actions_loads_trust_adjustments():
    source = (SCRIPTS / 'score_actions.py').read_text()
    assert '_load_trust_adjustments' in source
    assert 'effective_risk' in source
    assert 'trust_adjustments' in source


def test_generate_human_report_exists():
    assert (SCRIPTS / 'generate_human_report.py').exists()


def test_generate_human_report_runs_on_empty_case():
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / 'empty_case'
        case_dir.mkdir()
        out = case_dir / 'REPORT.md'
        result = subprocess.run(
            ['python3', str(SCRIPTS / 'generate_human_report.py'),
             str(case_dir), '--out', str(out)],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        assert result.returncode == 0, f'generate_human_report failed: {result.stderr}'
        assert out.exists()
        content = out.read_text()
        assert '# System Run Report' in content
        assert 'What Happened' in content
        assert 'Before Marking This Done' in content


def test_github_actions_workflow_exists():
    workflow = ROOT / '.github' / 'workflows' / 'cycle.yml'
    assert workflow.exists(), '.github/workflows/cycle.yml must exist (closes IGNITION_GAP)'
    content = workflow.read_text()
    assert 'run_operator_layer.py' in content
    assert 'generate_human_report.py' in content
    assert 'schedule' in content
    assert 'workflow_dispatch' in content


def test_run_adaptive_meta_cycle_calls_human_report():
    source = (SCRIPTS / 'run_adaptive_meta_cycle.py').read_text()
    assert 'generate_human_report' in source


def test_mode_selector_has_sys_path_fix():
    source = (SCRIPTS / 'mode_selector.py').read_text()
    assert 'sys.path.insert' in source, \
        'mode_selector.py must insert scripts dir onto sys.path'


def test_mode_selector_handles_list_and_dict_blocked():
    source = (SCRIPTS / 'mode_selector.py').read_text()
    assert 'isinstance(blocked, list)' in source, \
        'mode_selector must handle both list and dict forms of blocked_actions.json'


def test_mode_selector_runs_dry_on_example_case():
    """mode_selector must run without error on the seeded example case."""
    result = subprocess.run(
        ['python3', str(SCRIPTS / 'mode_selector.py'), str(EXAMPLE)],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    assert result.returncode == 0, f'mode_selector failed: {result.stderr}'
    assert 'Selected mode:' in result.stdout


def test_example_case_has_required_files():
    required = [
        'action_queue.json',
        'claim_map.json',
        'drift_report.json',
        'runtime_evidence.json',
        'proof_checks.json',
        'enforcement_active.json',
    ]
    for fname in required:
        assert (EXAMPLE / fname).exists(), \
            f'examples/bundle_forensics_case/{fname} is required but missing'


def test_example_case_action_queue_is_valid():
    queue = json.loads((EXAMPLE / 'action_queue.json').read_text())
    assert 'actions' in queue
    assert len(queue['actions']) >= 4, 'Example case needs at least 4 actions'
    # Verify one action is intentionally blocked (manual/high-risk) for pipeline testing
    blocked_candidates = [
        a for a in queue['actions']
        if a.get('risk_level', 0) > 4 or a.get('execution_type') == 'manual'
    ]
    assert blocked_candidates, \
        'Example case must have at least one high-risk/manual action to test blocker pipeline'


def test_roadmap_exists_and_is_complete():
    roadmap = ROOT / 'ROADMAP_UNBUILT_BUT_DISCUSSED.md'
    assert roadmap.exists()
    content = roadmap.read_text()
    for item in ['learning_memory', 'interface', 'ignition',
                 'trust_update', 'generate_human_report', 'skill_generalization']:
        assert item.lower() in content.lower(), f'ROADMAP missing item: {item}'


if __name__ == '__main__':
    pytest.main(['-v', __file__])
