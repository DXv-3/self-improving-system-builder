#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path

def parse_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

def classify_result(result: str) -> str:
    if result == "completed": return "completed"
    if result == "dry_run": return "dry_run"
    if isinstance(result, str) and result.startswith("failed:"): return "failed"
    return "other"

def summarize(rows: list[dict]) -> str:
    total = len(rows)
    counts: dict[str, int] = defaultdict(int)
    by_mode: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    last_run = None
    last_success_mode = None
    for row in rows:
        mode = row.get("mode", "unknown")
        ts = row.get("timestamp")
        result = classify_result(str(row.get("result", "")))
        counts[result] += 1
        by_mode[mode]["total"] += 1
        by_mode[mode][result] += 1
        if ts and (last_run is None or ts > last_run):
            last_run = ts
        if result == "completed" and ts:
            if last_success_mode is None or ts >= last_success_mode[0]:
                last_success_mode = (ts, mode)
    lines = [
        "# Operator Log Summary", "",
        f"- Total cycles: {total}",
        f"- Completed: {counts['completed']}",
        f"- Failed: {counts['failed']}",
        f"- Dry runs: {counts['dry_run']}",
        f"- Last run: {last_run or 'N/A'}",
        f"- Last successful mode: {last_success_mode[1] if last_success_mode else 'N/A'}",
        "", "## By Mode",
    ]
    for mode in sorted(by_mode):
        t = by_mode[mode]["total"]
        c = by_mode[mode]["completed"]
        f = by_mode[mode]["failed"]
        d = by_mode[mode]["dry_run"]
        rate = f"{(f / t * 100):.1f}%" if t else "N/A"
        lines.append(
            f"- {mode}: {t} runs, {c} completed, {f} failed, {d} dry runs, failure rate {rate}"
        )
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize operator_log.jsonl into markdown.")
    parser.add_argument("log_path", help="Path to operator_log.jsonl")
    parser.add_argument("--out", default=None, help="Output markdown path")
    args = parser.parse_args()
    log_path = Path(args.log_path)
    report = summarize(parse_jsonl(log_path))
    out_path = Path(args.out) if args.out else log_path.parent / "OPERATOR_LOG_SUMMARY.md"
    out_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Written -> {out_path}")

if __name__ == "__main__":
    main()
