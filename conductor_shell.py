"""
conductor_shell.py — Managed subprocess launcher for trigger_dispatcher.py.

Positions trigger_dispatcher as a supervised child process under the
conductor-protocol-v2 operator-router model:

  conductor_shell (supervisor)
    └── trigger_dispatcher.py --watch --interval N  (child)
          └── improve_skill()  (called per skill candidate)
                └── model_caller  (Z.AI / Anthropic / OpenAI / Ollama)
                └── brain_client  (the-brain MCP)

Features:
  - Supervises the child process; restarts on non-zero exit with exponential
    backoff (1s → 2s → 4s → … capped at MAX_BACKOFF_S)
  - Forwards SIGTERM / SIGINT cleanly to child before exiting
  - Reports health checkpoints to the-brain via brain_client
  - Emits build-watch events on start / stop / restart / give-up
  - Respects CONDUCTOR_MAX_RESTARTS env var (default 10)
  - Integrates with conductor-protocol-v2 operator-router if that repo
    is present at CONDUCTOR_PATH (optional — graceful degradation)

Usage:
  python3 conductor_shell.py                     # uses env var defaults
  python3 conductor_shell.py --interval 30       # faster cycles
  python3 conductor_shell.py --once              # single pass, no restart
  python3 conductor_shell.py --dry-run           # pass --dry-run to child
  python3 conductor_shell.py --status            # show supervisor status
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
BUILD_WATCH_DIR = Path(os.environ.get("BUILD_WATCH_DIR", ROOT / ".build-watch"))
STATUS_FILE = BUILD_WATCH_DIR / "conductor_shell.status.json"

DEFAULT_INTERVAL = int(os.environ.get("DISPATCHER_INTERVAL", "60"))
DEFAULT_MAX_RESTARTS = int(os.environ.get("CONDUCTOR_MAX_RESTARTS", "10"))
INITIAL_BACKOFF_S = 1.0
MAX_BACKOFF_S = 120.0


# ---------------------------------------------------------------------------
# build-watch event emitter
# ---------------------------------------------------------------------------

def _emit(msg: str, kind: str = "note", files: list[str] | None = None):
    try:
        BUILD_WATCH_DIR.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "msg": f"[conductor_shell] {msg}",
            "files": files or [],
        }
        with (BUILD_WATCH_DIR / "events.jsonl").open("a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as exc:
        log.debug("build-watch emit failed: %s", exc)


# ---------------------------------------------------------------------------
# Brain health reporter
# ---------------------------------------------------------------------------

def _report_health(state: str, restart_count: int, child_pid: Optional[int]):
    try:
        from brain_client import BrainClient
        client = BrainClient()
        client.store({
            "type": "conductor_health",
            "component": "trigger_dispatcher",
            "state": state,
            "restart_count": restart_count,
            "child_pid": child_pid,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        log.debug("brain health report failed: %s", exc)


# ---------------------------------------------------------------------------
# Conductor-protocol-v2 optional integration
# ---------------------------------------------------------------------------

def _try_conductor_register(component: str = "trigger_dispatcher"):
    """
    If conductor-protocol-v2 is present at CONDUCTOR_PATH, register this
    component with its operator-router so it appears in the routing table.
    Fails silently if conductor is absent or unavailable.
    """
    conductor_path = os.environ.get("CONDUCTOR_PATH", "../conductor-protocol-v2")
    router_mod = Path(conductor_path) / "operator_router.py"
    if not router_mod.exists():
        log.debug("conductor-protocol-v2 not found at %s — skipping registration", conductor_path)
        return
    try:
        sys.path.insert(0, conductor_path)
        import importlib
        router = importlib.import_module("operator_router")
        if hasattr(router, "register"):
            router.register(
                name=component,
                kind="subprocess_supervisor",
                description="Supervised trigger_dispatcher — LLM skill improvement loop",
                health_url=None,  # health reported via brain_client instead
            )
            log.info("[conductor_shell] Registered with conductor operator-router")
    except Exception as exc:
        log.debug("conductor registration failed (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Status file
# ---------------------------------------------------------------------------

def _write_status(state: str, restart_count: int, child_pid: Optional[int], backoff: float):
    BUILD_WATCH_DIR.mkdir(parents=True, exist_ok=True)
    status = {
        "state": state,
        "restart_count": restart_count,
        "child_pid": child_pid,
        "backoff_s": round(backoff, 1),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def _show_status():
    if STATUS_FILE.exists():
        print(STATUS_FILE.read_text())
    else:
        print(json.dumps({"state": "not_started", "message": "conductor_shell has not run yet"}))


# ---------------------------------------------------------------------------
# Child builder
# ---------------------------------------------------------------------------

def _build_child_cmd(
    interval: int,
    dry_run: bool,
    once: bool,
) -> list[str]:
    cmd = [sys.executable, str(ROOT / "trigger_dispatcher.py")]
    if once:
        cmd.append("--once")
    else:
        cmd += ["--watch", "--interval", str(interval)]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------

_current_child: Optional[subprocess.Popen] = None
_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    if _current_child and _current_child.poll() is None:
        log.info("[conductor_shell] Forwarding signal %d to child PID %d", signum, _current_child.pid)
        _current_child.send_signal(signum)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ---------------------------------------------------------------------------
# Supervisor loop
# ---------------------------------------------------------------------------

def run_supervised(
    interval: int = DEFAULT_INTERVAL,
    dry_run: bool = False,
    once: bool = False,
    max_restarts: int = DEFAULT_MAX_RESTARTS,
):
    global _current_child, _shutdown_requested

    _try_conductor_register()
    cmd = _build_child_cmd(interval, dry_run, once)
    restart_count = 0
    backoff = INITIAL_BACKOFF_S

    log.info("[conductor_shell] Starting supervised child: %s", " ".join(cmd))
    _emit(f"Supervisor starting: {' '.join(cmd)}", kind="plan")

    while not _shutdown_requested:
        log.info("[conductor_shell] Launching child (restart #%d)", restart_count)
        _write_status("running", restart_count, None, backoff)

        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=os.environ.copy(),
        )
        _current_child = proc
        _write_status("running", restart_count, proc.pid, backoff)
        _emit(f"Child launched: PID {proc.pid} (restart #{restart_count})", kind="plan")
        _report_health("running", restart_count, proc.pid)

        exit_code = proc.wait()
        _current_child = None

        if _shutdown_requested:
            log.info("[conductor_shell] Shutdown requested — exiting cleanly (child exit=%d)", exit_code)
            _write_status("stopped", restart_count, None, 0)
            _emit("Supervisor stopped cleanly", kind="done")
            _report_health("stopped", restart_count, None)
            break

        if exit_code == 0 or once:
            log.info("[conductor_shell] Child exited cleanly (code=%d)", exit_code)
            _write_status("done", restart_count, None, 0)
            _emit(f"Child exited cleanly (code={exit_code})", kind="done")
            _report_health("done", restart_count, None)
            break

        restart_count += 1
        log.warning(
            "[conductor_shell] Child crashed (exit=%d). Restart %d/%d in %.1fs …",
            exit_code, restart_count, max_restarts, backoff,
        )
        _emit(
            f"Child crashed (exit={exit_code}). Restart {restart_count}/{max_restarts} in {backoff:.1f}s",
            kind="note",
        )
        _report_health("restarting", restart_count, None)
        _write_status("restarting", restart_count, None, backoff)

        if restart_count >= max_restarts:
            log.error(
                "[conductor_shell] Max restarts (%d) reached — giving up. "
                "Check logs and restart manually.",
                max_restarts,
            )
            _emit(
                f"GIVE UP: max restarts ({max_restarts}) reached. Manual intervention required.",
                kind="done",
            )
            _report_health("failed", restart_count, None)
            _write_status("failed", restart_count, None, 0)
            sys.exit(1)

        time.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF_S)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    ap = argparse.ArgumentParser(
        description="Supervised launcher for trigger_dispatcher.py via conductor-protocol-v2."
    )
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                    help=f"Watch cycle interval in seconds (default {DEFAULT_INTERVAL})")
    ap.add_argument("--once", action="store_true",
                    help="Run one pass then exit (no restart loop)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Pass --dry-run to trigger_dispatcher (no mutations written)")
    ap.add_argument("--max-restarts", type=int, default=DEFAULT_MAX_RESTARTS,
                    help=f"Max crash restarts before giving up (default {DEFAULT_MAX_RESTARTS})")
    ap.add_argument("--status", action="store_true",
                    help="Print current supervisor status and exit")
    args = ap.parse_args()

    if args.status:
        _show_status()
        sys.exit(0)

    run_supervised(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
        max_restarts=args.max_restarts,
    )
