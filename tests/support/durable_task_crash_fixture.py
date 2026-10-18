"""Owned child process: real local Core/SQLite, abrupt exit at one fixed boundary.

Only the integration tests invoke this helper. It never accepts a prompt,
command, model, credential, arbitrary executor or production database.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.jarvis_console.bootstrap import ensure_src_paths  # noqa: E402

ensure_src_paths()

from job_service.durable import DurableCoreJobStore  # noqa: E402

from apps.jarvis_console.durable_task_runner import DurableCoreJobRunner  # noqa: E402
from apps.jarvis_console.voice_pilot import _isolated_core  # noqa: E402

STAGES = {"before_dispatch": 71, "after_dispatch": 72, "after_core_commit": 73}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--clock", required=True)
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--actor-ref", required=True)
    parser.add_argument("--session-ref", required=True)
    options = parser.parse_args(argv)
    runtime = Path(options.runtime)
    if not runtime.is_absolute() or not runtime.is_dir() or runtime.is_relative_to(ROOT):
        return 90
    now = datetime.fromisoformat(options.clock)
    store = DurableCoreJobStore(runtime / "jobs.db", clock=lambda: now)
    core = _isolated_core(runtime)

    def crash(*_args, **_kwargs):
        # The preceding public operation has committed and closed its SQLite
        # connection. No Python exception handler, finally or worker cleanup runs.
        os._exit(STAGES[options.stage])

    if options.stage == "before_dispatch":
        store.start_dispatch = crash
    elif options.stage == "after_dispatch":
        core.handle_input = crash
    else:
        store.finish_task = crash
    try:
        DurableCoreJobRunner(store, core, "owned-crash-worker").run_once(
            options.job_id,
            actor_ref=options.actor_ref,
            session_ref=options.session_ref,
            expected_version=0,
            authorized=True,
            lease_seconds=0.001,
        )
    except Exception:
        return 91  # Content-free setup/contract failure, not the requested crash.
    return 92  # The fixed failpoint was not reached.


if __name__ == "__main__":
    raise SystemExit(main())
