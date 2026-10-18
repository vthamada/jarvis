"""Opt-in, metadata-only activity for explicitly selected existing local jobs.

This standalone reader never creates a store, bootstraps Core, reconciles a
lease, or executes a job. Scope labels bind reads; they are not authentication.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from apps.jarvis_console.job_inspect_cli import build_job_inspection as _inspect  # noqa: E402

_STATES = ("registered", "running", "succeeded", "failed", "needs_decision",
           "cancelled", "expired")
_OUTCOMES = (None, "succeeded", "failed", "needs_decision", "cancelled", "deadline_expired",
             "attempts_exhausted", "retry_requested")
_BASE = {
    "schema_version": "jarvis-job-inspection-v1", "read_only": True,
    "authority": "none", "scope_binding": "caller_supplied_not_authentication",
    "source_mode": "quiescent_existing_local_sqlite",
}
_JOB_KEYS = frozenset({
    "event", "status", "version", "fencing", "attempts", "max_attempts", "lease_present",
    "last_outcome", "evidence_mode", "action_authority", "automatic_execution",
})


class JobActivityError(ValueError):
    """One fixed refusal code, never identifiers, paths or source exceptions."""


def _refuse() -> None:
    raise JobActivityError("job_activity_refused")


def _job_valid(job: object) -> bool:
    if type(job) is not dict or job.keys() != _JOB_KEYS:
        return False
    if any(type(job[field]) is not str for field in ("event", "status", "evidence_mode")):
        return False
    if job["status"] not in _STATES or job["last_outcome"] not in _OUTCOMES:
        return False
    if job["last_outcome"] is not None and type(job["last_outcome"]) is not str:
        return False
    if (job["event"], job["evidence_mode"]) not in {
        ("fixture_job_state", "fixture"), ("job_state", "metadata_ledger"),
    }:
        return False
    if job["action_authority"] is not False or job["automatic_execution"] is not False:
        return False
    if type(job["lease_present"]) is not bool:
        return False
    if job["lease_present"] != (job["status"] == "running"):
        return False
    if any(type(job[field]) is not int for field in
           ("version", "fencing", "attempts", "max_attempts")):
        return False
    return (
        1 <= job["max_attempts"] <= 10
        and 0 <= job["attempts"] <= job["max_attempts"]
        and job["attempts"] <= job["fencing"] <= job["version"] < 2**60
        and (job["status"] != "running" or job["attempts"] > 0)
    )


def build_job_activity(
    database_path: Path, *, actor_ref: str, session_ref: str, job_ids: tuple[str, ...],
    authorized: bool = False,
) -> dict:
    """Summarize 1..32 explicit scoped jobs without disclosing their references.

    ``authorized`` records the operator's permission to inspect the local file;
    neither it nor caller-supplied actor/session labels establishes identity or
    a Core grant. Counts cover only selected IDs, not the full ledger. A running
    stale lease remains running; no estimated execution percentage is invented.
    """
    try:
        if authorized is not True or type(job_ids) is not tuple or not 1 <= len(job_ids) <= 32:
            _refuse()
        product = _inspect(database_path, actor_ref=actor_ref, session_ref=session_ref,
                           job_ids=job_ids, include_refs=False)
        if type(product) is not dict or product.keys() != _BASE.keys() | {"job_count", "jobs"}:
            _refuse()
        if any(type(product[key]) is not type(value) or product[key] != value
               for key, value in _BASE.items()):
            _refuse()
        if (type(product["job_count"]) is not int or product["job_count"] != len(job_ids)
                or type(product["jobs"]) is not list or len(product["jobs"]) != len(job_ids)
                or any(not _job_valid(job) for job in product["jobs"])):
            _refuse()
        counts = dict.fromkeys(_STATES, 0)
        evidence = {"fixture": 0, "metadata_ledger": 0}
        attempts = 0
        for job in product["jobs"]:
            counts[job["status"]] += 1
            evidence[job["evidence_mode"]] += 1
            attempts += job["attempts"]
        return {
            "schema_version": "jarvis-job-activity-v1", "read_only": True,
            "authority": "none", "operator_authenticated": False,
            "scope_binding": _BASE["scope_binding"], "source_mode": _BASE["source_mode"],
            "activity_scope": "explicit_selected_jobs_not_full_ledger",
            "selected_job_count": len(job_ids), "status_counts": counts,
            "evidence_counts": evidence, "attempts_recorded": attempts,
            "progress": {
                "basis": "selected_ledger_states_not_execution_percentage",
                "pending_count": counts["registered"], "active_count": counts["running"],
                "awaiting_decision_count": counts["needs_decision"],
                "terminal_count": sum(counts[state] for state in
                                      ("succeeded", "failed", "cancelled", "expired")),
            },
        }
    except Exception:
        raise JobActivityError("job_activity_refused") from None


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        # Default argparse errors may echo private option values or source paths.
        _refuse()


def _silence_broken_standard_stream(stream, descriptor: int) -> None:
    """Prevent CPython shutdown from flushing a known broken standard FD again.

    Only a real TextIOWrapper over stdout/stderr is eligible. Never interpret
    duck-typed test streams or an arbitrary descriptor as permission to redirect.
    Keep the wrapper: its pending buffer can safely flush to the null device.
    """
    try:
        if type(stream) is not io.TextIOWrapper:
            return
        observed = stream.fileno()
        if type(observed) is not int or observed != descriptor or descriptor not in (1, 2):
            return
        null_descriptor = os.open(os.devnull, os.O_WRONLY)
        try:
            if null_descriptor != descriptor:
                os.dup2(null_descriptor, descriptor)
        finally:
            # If the standard FD was already closed, open may reuse its number.
            # In that case it is now the intended target, not a disposable alias.
            if null_descriptor != descriptor:
                os.close(null_descriptor)
    except Exception:
        # No secondary output or reflection if the host cannot redirect the FD.
        pass


def _report_refusal() -> int:
    try:
        print('{"error_code": "job_activity_refused"}', file=sys.stderr, flush=True)
    except (OSError, UnicodeError, ValueError):
        _silence_broken_standard_stream(sys.stderr, 2)
    except Exception:
        pass
    return 2


def main(argv=None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--job-db", required=True, type=Path)
    parser.add_argument("--actor-ref", required=True)
    parser.add_argument("--session-ref", required=True)
    parser.add_argument("--job-id", required=True, action="append")
    try:
        args = parser.parse_args(argv)
        result = build_job_activity(args.job_db, actor_ref=args.actor_ref,
                                    session_ref=args.session_ref, job_ids=tuple(args.job_id),
                                    authorized=args.authorized)
        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False)
    except Exception:
        return _report_refusal()
    try:
        print(encoded, flush=True)
    except (OSError, UnicodeError, ValueError):
        _silence_broken_standard_stream(sys.stdout, 1)
        return _report_refusal()
    except Exception:
        return _report_refusal()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
