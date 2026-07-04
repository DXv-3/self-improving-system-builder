"""Tests for scripts/brain_sync.py"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import brain_sync


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records))


def test_dry_run_no_db_needed(tmp_path, monkeypatch):
    local = tmp_path / "local.jsonl"
    _write_jsonl(local, [{"timestamp": "t", "run_id": "r1", "category": "success",
                          "event_type": "e", "detail": "d", "outcome": "pass"}])
    monkeypatch.setattr(brain_sync, "_LOCAL_JSONL", local)
    monkeypatch.setattr(brain_sync, "_SIBLING_JSONL", tmp_path / "missing.jsonl")
    result = brain_sync.main(tmp_path / "brain.db", dry_run=True)
    assert result["dry_run"] is True
    assert result["local"] == 1
    assert result["sibling"] == 0


def test_skip_when_no_db(tmp_path, monkeypatch):
    local = tmp_path / "local.jsonl"
    _write_jsonl(local, [{"timestamp": "t", "run_id": "r1", "category": "c",
                          "event_type": "e", "detail": "d", "outcome": "pass"}])
    monkeypatch.setattr(brain_sync, "_LOCAL_JSONL", local)
    monkeypatch.setattr(brain_sync, "_SIBLING_JSONL", tmp_path / "missing.jsonl")
    result = brain_sync.main(tmp_path / "no_such.db")
    assert result["skipped"] is True


def test_insert_into_db(tmp_path, monkeypatch):
    import sqlite3
    local = tmp_path / "local.jsonl"
    records = [
        {"timestamp": "2026-07-03T00:00:00Z", "run_id": f"r{i}",
         "category": "success", "event_type": "e", "detail": "d", "outcome": "pass"}
        for i in range(3)
    ]
    _write_jsonl(local, records)
    monkeypatch.setattr(brain_sync, "_LOCAL_JSONL", local)
    monkeypatch.setattr(brain_sync, "_SIBLING_JSONL", tmp_path / "missing.jsonl")
    db = tmp_path / "brain.db"
    db.touch()  # create empty db so sync proceeds
    result = brain_sync.main(db)
    assert result["inserted_local"] == 3
    assert result["inserted_sibling"] == 0
    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM learning_memory").fetchone()[0]
    assert count == 3
    conn.close()


def test_deduplication(tmp_path, monkeypatch):
    import sqlite3
    local = tmp_path / "local.jsonl"
    records = [
        {"timestamp": "2026-07-03T00:00:00Z", "run_id": "dup",
         "category": "c", "event_type": "e", "detail": "d", "outcome": "pass"}
    ] * 3  # same record 3 times
    _write_jsonl(local, records)
    monkeypatch.setattr(brain_sync, "_LOCAL_JSONL", local)
    monkeypatch.setattr(brain_sync, "_SIBLING_JSONL", tmp_path / "missing.jsonl")
    db = tmp_path / "brain.db"
    db.touch()
    brain_sync.main(db)
    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM learning_memory").fetchone()[0]
    assert count == 1  # only 1 after dedup
    conn.close()
