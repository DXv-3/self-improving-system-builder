"""
tests/test_conductor_shell.py — Tests for the supervised subprocess launcher.

All tests mock subprocess.Popen — no actual child processes are started.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import conductor_shell as cs


@pytest.fixture(autouse=True)
def tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "BUILD_WATCH_DIR", tmp_path / ".build-watch")
    monkeypatch.setattr(cs, "STATUS_FILE", tmp_path / ".build-watch" / "conductor_shell.status.json")
    # Suppress brain_client calls
    monkeypatch.setattr(cs, "_report_health", lambda *a, **k: None)
    # Suppress conductor registration
    monkeypatch.setattr(cs, "_try_conductor_register", lambda: None)
    return tmp_path


def _mock_proc(exit_code: int = 0, pid: int = 12345):
    proc = MagicMock()
    proc.pid = pid
    proc.poll.return_value = None
    proc.wait.return_value = exit_code
    return proc


# ---------------------------------------------------------------------------
# Test 1: Clean launch and exit
# ---------------------------------------------------------------------------

def test_clean_exit_no_restart(tmp_dirs):
    """Child exits 0 — supervisor should stop without restarting."""
    proc = _mock_proc(exit_code=0)
    with patch("subprocess.Popen", return_value=proc) as mock_popen:
        cs.run_supervised(interval=60, once=False, max_restarts=5)
    mock_popen.assert_called_once()
    status = json.loads(cs.STATUS_FILE.read_text())
    assert status["state"] == "done"
    assert status["restart_count"] == 0


# ---------------------------------------------------------------------------
# Test 2: Crash → restart → clean exit
# ---------------------------------------------------------------------------

def test_crash_then_clean_exit(tmp_dirs, monkeypatch):
    """Child crashes once, then exits cleanly on second run."""
    monkeypatch.setattr(cs, "INITIAL_BACKOFF_S", 0.0)  # no sleep in tests
    monkeypatch.setattr(cs, "MAX_BACKOFF_S", 0.0)
    outcomes = [1, 0]  # first crash, then clean
    procs = [_mock_proc(exit_code=c, pid=1000 + i) for i, c in enumerate(outcomes)]
    call_count = 0

    def fake_popen(*args, **kwargs):
        nonlocal call_count
        p = procs[call_count]
        call_count += 1
        return p

    with patch("subprocess.Popen", side_effect=fake_popen), \
         patch("time.sleep"):
        cs.run_supervised(interval=60, max_restarts=5)

    assert call_count == 2
    status = json.loads(cs.STATUS_FILE.read_text())
    assert status["state"] == "done"
    assert status["restart_count"] == 1


# ---------------------------------------------------------------------------
# Test 3: Max restarts → sys.exit(1)
# ---------------------------------------------------------------------------

def test_max_restarts_gives_up(tmp_dirs, monkeypatch):
    monkeypatch.setattr(cs, "INITIAL_BACKOFF_S", 0.0)
    monkeypatch.setattr(cs, "MAX_BACKOFF_S", 0.0)
    always_crash = [_mock_proc(exit_code=1) for _ in range(4)]
    idx = 0

    def fake_popen(*a, **k):
        nonlocal idx
        p = always_crash[idx % len(always_crash)]
        idx += 1
        return p

    with patch("subprocess.Popen", side_effect=fake_popen), \
         patch("time.sleep"), \
         pytest.raises(SystemExit) as exc_info:
        cs.run_supervised(interval=60, max_restarts=3)

    assert exc_info.value.code == 1
    status = json.loads(cs.STATUS_FILE.read_text())
    assert status["state"] == "failed"


# ---------------------------------------------------------------------------
# Test 4: --once flag → no restart even on crash
# ---------------------------------------------------------------------------

def test_once_flag_no_restart(tmp_dirs):
    proc = _mock_proc(exit_code=42)
    with patch("subprocess.Popen", return_value=proc) as mock_popen:
        cs.run_supervised(interval=60, once=True, max_restarts=10)
    mock_popen.assert_called_once()
    status = json.loads(cs.STATUS_FILE.read_text())
    assert status["state"] == "done"


# ---------------------------------------------------------------------------
# Test 5: Status file written with correct PID
# ---------------------------------------------------------------------------

def test_status_file_has_pid(tmp_dirs):
    proc = _mock_proc(exit_code=0, pid=99999)
    written_statuses = []

    original_write = cs._write_status
    def capturing_write(state, restart_count, child_pid, backoff):
        written_statuses.append((state, child_pid))
        original_write(state, restart_count, child_pid, backoff)

    with patch("subprocess.Popen", return_value=proc), \
         patch.object(cs, "_write_status", side_effect=capturing_write):
        cs.run_supervised(interval=60, once=False, max_restarts=5)

    pids_written = [pid for _, pid in written_statuses]
    assert 99999 in pids_written


# ---------------------------------------------------------------------------
# Test 6: Backoff doubles on each crash
# ---------------------------------------------------------------------------

def test_backoff_doubles(tmp_dirs, monkeypatch):
    monkeypatch.setattr(cs, "INITIAL_BACKOFF_S", 1.0)
    monkeypatch.setattr(cs, "MAX_BACKOFF_S", 10.0)
    outcomes = [1, 1, 1, 0]
    procs = [_mock_proc(exit_code=c) for c in outcomes]
    idx = 0
    sleep_calls = []

    def fake_popen(*a, **k):
        nonlocal idx
        p = procs[idx % len(procs)]
        idx += 1
        return p

    def fake_sleep(s):
        sleep_calls.append(s)

    with patch("subprocess.Popen", side_effect=fake_popen), \
         patch("time.sleep", side_effect=fake_sleep):
        cs.run_supervised(interval=60, max_restarts=10)

    # Backoff should be 1.0, 2.0, 4.0 for the three crashes
    assert sleep_calls == [1.0, 2.0, 4.0]


# ---------------------------------------------------------------------------
# Test 7: build-watch events written
# ---------------------------------------------------------------------------

def test_build_watch_events_written(tmp_dirs):
    proc = _mock_proc(exit_code=0)
    with patch("subprocess.Popen", return_value=proc):
        cs.run_supervised(interval=60, once=False, max_restarts=5)

    events_file = cs.BUILD_WATCH_DIR / "events.jsonl"
    assert events_file.exists()
    lines = events_file.read_text().strip().splitlines()
    assert len(lines) >= 2  # at least start + done
    events = [json.loads(l) for l in lines]
    kinds = [e["kind"] for e in events]
    assert "plan" in kinds
    assert "done" in kinds
