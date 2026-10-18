# ruff: noqa: E402
"""Explicit local durable native tasks; no scheduler, OAuth, model or tool activation."""

from __future__ import annotations

import argparse
import json
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.review_input import _requires_redaction, read_review_input
from apps.jarvis_console.runtime import ConsoleRuntime

ensure_src_paths()

from job_service import JobStoreError
from job_service.durable import DurableCoreJobStore
from job_service.store import _ref, _version

from apps.jarvis_console.conversation_export import _text
from apps.jarvis_console.durable_core_receipt import find_core_receipt
from apps.jarvis_console.durable_task_runner import SCHEMA, DurableCoreJobRunner
from apps.jarvis_console.voice_pilot import _isolated_core

INPUT_SCHEMA = "jarvis-durable-core-input-v1"
_MARKER = b"jarvis-durable-core-runtime-v1\n"


def _invalid():
    raise JobStoreError("durable_task_cli_refused")


def _safe_node(path, *, directory=False):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            or (directory and not stat.S_ISDIR(info.st_mode))
            or (not directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1))):
        _invalid()
    return True


def _runtime(path, *, create):
    """Trusted-host path preflight, not an adversarial descriptor sandbox or encryption."""
    if (not isinstance(path, Path) or not path.is_absolute()
            or path in {Path(path.anchor), Path.home()} or ".." in path.parts
            or str(path).startswith(("\\\\", "//"))
            or any(":" in p for p in path.parts[1:])
            or any("onedrive" in p.casefold() for p in path.parts)):
        _invalid()
    for parent in path.parents:
        if not _safe_node(parent, directory=True) or (parent / ".git").exists():
            _invalid()
    if path.resolve().is_relative_to(ROOT.resolve()) or (path / ".git").exists():
        _invalid()
    exists = _safe_node(path, directory=True)
    if not exists:
        if not create:
            _invalid()
        path.mkdir(mode=0o700)
    if os.name == "posix":
        info = path.stat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            _invalid()
    marker = path / "durable-runtime.marker"
    if not _safe_node(marker):
        if not create or any(path.iterdir()):
            _invalid()
        # Runtime data, not a repository source file. Never replace an existing marker.
        with marker.open("xb") as stream:
            stream.write(_MARKER)
    elif marker.stat().st_size != len(_MARKER) or marker.read_bytes() != _MARKER:
        _invalid()
    for name in ("jobs.db", "memory.db", "events.db"):
        for suffix in ("", "-wal", "-shm", "-journal"):
            _safe_node(path / (name + suffix))
    for name in ("artifacts",):
        _safe_node(path / name, directory=True)
    return path


def _document(value):
    if (type(value) is not dict or set(value) != {"schema_version", "query"}
            or value["schema_version"] != INPUT_SCHEMA or type(value["query"]) is not str
            or not 1 <= len(value["query"]) <= 2048 or not value["query"].strip()
            or any(ord(c) < 32 and c not in "\n\r\t" for c in value["query"])):
        _invalid()
    if len(value["query"].encode("utf-8", "strict")) > 2048:
        _invalid()
    _text(value["query"], 2048)
    if _requires_redaction(value["query"], ConsoleRuntime(
        output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
    )):
        _invalid()
    return value["query"]


def operate_task(operation, *, runtime_dir, job_id, actor_ref, session_ref,
                 authorized=False, confirmed=False, document=None, expected_version=None,
                 deadline_seconds=600, lease_seconds=120, include_content=False):
    """Persist only confirmed input; recovered output is reread from canonical Core memory."""
    if (authorized is not True or operation not in {"submit", "resume", "cancel", "pause"}
            or type(include_content) is not bool
            or (operation != "resume" and include_content)):
        _invalid()
    for value in (job_id, actor_ref, session_ref):
        _ref(value)
    query = None
    if operation == "submit":
        if (confirmed is not True or expected_version is not None
                or type(deadline_seconds) is not int or not 1 <= deadline_seconds <= 86400):
            _invalid()
        query = _document(document)
    else:
        if document is not None:
            _invalid()
        _version(expected_version)
    if (type(lease_seconds) not in {int, float} or not 0 < lease_seconds <= 120):
        _invalid()
    runtime = _runtime(runtime_dir, create=operation == "submit")
    store = DurableCoreJobStore(runtime / "jobs.db")
    scope = {"actor_ref": actor_ref, "session_ref": session_ref}
    if operation == "submit":
        snapshot = store.register_task(
            job_id, input_text=query,
            deadline=datetime.now(UTC) + timedelta(seconds=deadline_seconds),
            **scope,
        )
    elif operation in {"cancel", "pause"}:
        # Check exact durable task binding before mutating the existing ledger.
        store.load_task(job_id, **scope)
        snapshot = getattr(store, operation)(
            job_id, expected_version=expected_version, **scope,
        )
    else:
        # Resume requires an already initialized canonical runtime. A submitted
        # but never dispatched task legitimately has no Core database yet.
        task = store.load_task(job_id, **scope)
        snapshot = store.get(job_id, **scope)
        if snapshot.version != expected_version:
            raise JobStoreError("version_conflict")
        if (snapshot.status == "running" and snapshot.lease_until is not None
                and store._now() < snapshot.lease_until.timestamp()):
            result = DurableCoreJobRunner._report(snapshot, task)
            result.update(evidence_mode="active_claim", content_included=False,
                          content_withheld=False)
            return result
        core = _isolated_core(runtime)
        result = DurableCoreJobRunner(store, core, "local-durable-worker").resume(
            job_id, authorized=True, expected_version=expected_version,
            lease_seconds=lease_seconds, **scope,
        )
        result.update(content_included=False, content_withheld=False)
        if include_content and result["result_recorded"]:
            task = store.load_task(job_id, **scope)
            receipt = find_core_receipt(core, task)
            if receipt is None or receipt.receipt_sha256 != task.receipt_sha256:
                _invalid()
            redactor = ConsoleRuntime(
                output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
            )
            if _requires_redaction(receipt.response_text, redactor):
                result["content_withheld"] = True
            else:
                result.update(content_included=True, response_text=receipt.response_text)
        return result
    task = store.load_task(job_id, **scope)
    return {
        "schema_version": SCHEMA, "job": snapshot.telemetry(), "checkpoint_phase": task.phase,
        "core_invoked": False, "input_persisted": True, "content_included": False,
        "content_withheld": False, "automatic_execution": False, "action_authority": False,
        "operator_authenticated": False, "runtime_capability_promoted": False,
    }


class _SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        _invalid()


def main(argv=None):
    parser = _SafeParser(description=__doc__)
    parser.add_argument("operation", choices=("submit", "resume", "cancel", "pause"))
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--confirm-input", action="store_true")
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--actor-ref", required=True)
    parser.add_argument("--session-ref", required=True)
    parser.add_argument("--expected-version", type=int)
    parser.add_argument("--deadline-seconds", type=int, default=600)
    parser.add_argument("--lease-seconds", type=float, default=120)
    parser.add_argument("--include-content", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = operate_task(
            args.operation, runtime_dir=args.runtime_dir, job_id=args.job_id,
            actor_ref=args.actor_ref, session_ref=args.session_ref, authorized=args.authorized,
            confirmed=args.confirm_input,
            document=read_review_input() if args.operation == "submit" else None,
            expected_version=args.expected_version, deadline_seconds=args.deadline_seconds,
            lease_seconds=args.lease_seconds, include_content=args.include_content,
        )
        print(json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"durable_task_interrupted"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"durable_task_cli_refused"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
