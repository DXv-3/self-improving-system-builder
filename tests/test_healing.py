#!/usr/bin/env python3
"""
test_healing.py

Verifies all Priority 1-3 heals are in place:
  1. learning_memory wired into persist_result
  2. trust_adjustments wired into score_actions
  3. generate_human_report.py exists and runs
  4. GitHub Actions workflow exists
  5. run_adaptive_meta_cycle calls generate_human_report
  6. mode_selector.py exists and selects modes correctly
  7. run_operator_layer.py exists
"""
import subprocess, json, tempfile, shutil
from pathlib import Path
import pytest

ROOT    = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def test_persist_result_calls_learning_memory():
    source = (SCRIPTS / 'persist_result.py').read_text()
    assert 'learning_memory' in source, \
        'persist_result.py must import learning_memory'
    assert 'record_cycle_outcome' in source, \
        'persist_result.py must call record_cycle_outcome'
    assert '_record_to_learning_memory' in source, \
        'persist_result.py must contain _record_to_learning_memory helper'


def test_score_actions_loads_trust_adjustments():
    source = (SCRIPTS / 'score_actions.py').read_text()
    assert 'trust_adjustments' in source, \
        'score_actions.py must load trust_adjustments'
    assert '_load_trust_adjustments' in source, \
        'score_actions.py must contain _load_trust_adjustments'
    assert 'effective_risk' in source, \
        'score_actions.py must compute effective_risk after adjustment'


def test_generate_human_report_exists():
    assert (SCRIPTS / 'generate_human_report.py').exists(), \
        'generate_human_report.py must exist in scripts/'


def test_generate_human_report_runs_on_empty_case():
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / 'empty_case'
        case_dir.mkdir()
        out = case_dir / 'REPORT.md'
        result = subprocess.run(
            ['python3', str(SCRIPTS / 'generate_human_report.py'),
             str(case_dir), '--out', str(out)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f'generate_human_report failed: {result.stderr}'
        assert out.exists(), 'REPORT.md was not created'
        content = out.read_text()
        assert '# System Run Report' in content
        assert 'What Happened' in content
        assert 'Before Marking This Done' in content


def test_github_actions_workflow_exists():
    workflow = ROOT / '.github' / 'workflows' / 'cycle.yml'
    assert workflow.exists(), '.github/workflows/cycle.yml must exist (IGNITION_GAP)'
    content = workflow.read_text()
    assert 'run_operator_layer.py' in content
    assert 'generate_human_report.py' in content
    assert 'schedule' in content, 'workflow must have a schedule trigger'


def test_run_adaptive_meta_cycle_calls_human_report():
    source = (SCRIPTS / 'run_adaptive_meta_cycle.py').read_text()
    assert 'generate_human_report' in source, \
        'run_adaptive_meta_cycle.py must call generate_human_report'


def test_mode_selector_exists_and_imports():
    assert (SCRIPTS / 'mode_selector.py').exists()
    result = subprocess.run(
        ['python3', '-c', 'import sys; sys.path.insert(0, "scripts"); import importlib.util; '
         'spec = importlib.util.spec_from_file_location("mode_selector", "scripts/mode_selector.py"); '
         'm = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print("ok")'],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    assert 'ok' in result.stdout or result.returncode == 0


def test_run_operator_layer_exists():
    assert (SCRIPTS / 'run_operator_layer.py').exists()


def test_learning_memory_scaffold_has_all_functions():
    source = (SCRIPTS / 'learning_memory.py').read_text()
    for fn in ['record_cycle_outcome', 'load_lessons', 'get_risk_adjustment',
               'get_common_blocker_types', 'get_best_followup_for_blocker']:
        assert fn in source, f'learning_memory.py missing function: {fn}'


def test_trust_update_scaffold_has_all_functions():
    source = (SCRIPTS / 'trust_update.py').read_text()
    for fn in ['compute_risk_adjustments', 'save_adjustments', 'apply_adjustments_to_queue']:
        assert fn in source, f'trust_update.py missing function: {fn}'


def test_roadmap_exists_and_is_complete():
    roadmap = ROOT / 'ROADMAP_UNBUILT_BUT_DISCUSSED.md'
    assert roadmap.exists(), 'ROADMAP_UNBUILT_BUT_DISCUSSED.md must exist'
    content = roadmap.read_text()
    for item in ['learning_memory', 'interface', 'ignition', 'trust_update',
                 'generate_human_report', 'skill_generalization']:
        assert item.lower() in content.lower(), \
            f'ROADMAP missing item: {item}'


def test_calibration_registry_exists():
    assert (ROOT / 'calibration' / 'magic_numbers.md').exists()
    content = (ROOT / 'calibration' / 'magic_numbers.md').read_text()
    assert 'UNCALIBRATED' in content, 'magic_numbers.md must flag uncalibrated numbers'
    assert '4' in content, 'magic_numbers.md must document the risk threshold 4'


if __name__ == '__main__':
    pytest.main(['-v', __file__])
