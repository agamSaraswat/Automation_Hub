#!/usr/bin/env python3
"""
run_web.py — Launch FastAPI backend + Vite frontend as concurrent subprocesses.

Usage:
  python run_web.py             # Start both (default)
  python run_web.py --backend   # Backend only  (uvicorn on :8000)
  python run_web.py --frontend  # Frontend only (Vite on :5173)

Ctrl+C cleanly terminates both processes.
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"

_NPM = "npm.cmd" if sys.platform.startswith("win") else "npm"

BACKEND_CMD: list[str] = [
    sys.executable, "-m", "uvicorn",
    "src.web.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
]
FRONTEND_CMD: list[str] = [_NPM, "run", "dev"]


# ── single-service helpers ────────────────────────────────

def _run_backend() -> int:
    return subprocess.call(BACKEND_CMD, cwd=REPO_ROOT)


def _run_frontend() -> int:
    return subprocess.call(FRONTEND_CMD, cwd=FRONTEND_DIR)


# ── concurrent runner ─────────────────────────────────────

def _run_both() -> int:
    backend  = subprocess.Popen(BACKEND_CMD,  cwd=REPO_ROOT)
    frontend = subprocess.Popen(FRONTEND_CMD, cwd=FRONTEND_DIR)

    print("🚀  Backend  → http://localhost:8000")
    print("🚀  Frontend → http://localhost:5173")
    print("Press Ctrl+C to stop both.\n", flush=True)

    def _shutdown(sig=None, frame=None) -> None:
        print("\nShutting down…", flush=True)
        for proc in (frontend, backend):
            if proc.poll() is None:
                proc.terminate()
        # Give each process up to 5 s to exit gracefully, then force-kill
        deadline = time.monotonic() + 5.0
        for proc in (frontend, backend):
            remaining = max(0.0, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    # Monitor: re-raise if either child exits unexpectedly
    while True:
        rc_b = backend.poll()
        rc_f = frontend.poll()

        if rc_b is not None:
            print(f"\n[backend] exited with code {rc_b}", flush=True)
            _shutdown()

        if rc_f is not None:
            print(f"\n[frontend] exited with code {rc_f}", flush=True)
            _shutdown()

        # Sleep briefly; the signal handler will fire on Ctrl+C
        try:
            time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            _shutdown()

    return 0  # unreachable


# ── entry point ───────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start Automation Hub web services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  (default)    Backend on :8000 + Frontend on :5173
  --backend    uvicorn only
  --frontend   Vite only
        """,
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--backend",  action="store_true", help="Start backend only")
    g.add_argument("--frontend", action="store_true", help="Start frontend only")
    args = parser.parse_args()

    if args.backend:
        return _run_backend()
    if args.frontend:
        return _run_frontend()
    return _run_both()


if __name__ == "__main__":
    raise SystemExit(main())
