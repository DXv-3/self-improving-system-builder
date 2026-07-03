#!/usr/bin/env python3
import subprocess, tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

def test_execute_next_defaults_fail_closed():
    source = (SCRIPTS / "execute_next.py").read_text()
    assert (
        "a.get('executable_now', False)" in source
        or 'a.get("executable_now", False)' in source
    ), "execute_next.py must default executable_now to False, not True"

def test_run_extractor_exists_and_shows_usage():
    path = SCRIPTS / "run_extractor.py"
    assert path.exists(), "scripts/run_extractor.py must exist"
    result = subprocess.run(["python3", str(path)], capture_output=True, text=True)
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    assert "usage:" in combined or "--context" in combined

def test_operator_log_summary_exists():
    assert (SCRIPTS / "operator_log_summary.py").exists(), "scripts/operator_log_summary.py must exist"

def test_operator_log_summary_tiny_sample():
    sample = "\n".join([
        '{"timestamp":"2026-07-03T00:00:00Z","mode":"adaptive_meta_cycle","result":"completed"}',
        '{"timestamp":"2026-07-03T06:00:00Z","mode":"reaudit","result":"failed: boom"}',
        '{"timestamp":"2026-07-03T12:00:00Z","mode":"adaptive_meta_cycle","result":"dry_run"}',
    ]) + "\n"
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "operator_log.jsonl"
        log_path.write_text(sample)
        out_path = Path(tmpdir) / "OPERATOR_LOG_SUMMARY.md"
        result = subprocess.run(
            ["python3", str(SCRIPTS / "operator_log_summary.py"),
             str(log_path), "--out", str(out_path)],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        assert result.returncode == 0, result.stderr
        content = out_path.read_text()
        assert "# Operator Log Summary" in content
        assert "Total cycles: 3" in content
        assert "adaptive_meta_cycle" in content
        assert "reaudit" in content

if __name__ == "__main__":
    pytest.main(["-v", __file__])
