"""Inert host-selected activity binding; no authentication or execution authority.

Reads only an existing quiescent local ledger through the bounded reader. Host
scope is not Web identity. The HTTP consumer owns pairing, CSRF and its session
fence. This is not an adversarial Python sandbox or a concurrent-file snapshot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from apps.jarvis_console.job_activity_cli import build_job_activity

_FIXED = {
    "schema_version": "jarvis-job-activity-v1", "read_only": True,
    "authority": "none", "operator_authenticated": False,
    "scope_binding": "caller_supplied_not_authentication",
    "source_mode": "quiescent_existing_local_sqlite",
    "activity_scope": "explicit_selected_jobs_not_full_ledger",
}
_STATES = frozenset({"registered", "running", "succeeded", "failed",
                     "needs_decision", "cancelled", "expired"})
_EVIDENCE = frozenset({"fixture", "metadata_ledger"})
_PROGRESS = frozenset({"basis", "pending_count", "active_count",
                       "awaiting_decision_count", "terminal_count"})
MAX_RESPONSE_BYTES = 4096


class JobActivityUnavailable(ValueError):
    """Fixed refusal with no file path, selected references or source detail."""

    code = "job_activity_unavailable"

    def __init__(self):
        super().__init__(self.code)


@dataclass(frozen=True, repr=False)
class _Binding:
    authorized: bool
    database_path: Path
    actor_ref: str
    session_ref: str
    job_ids: tuple[str, ...]

    def snapshot(self):
        return (self.authorized, str(self.database_path), self.actor_ref,
                self.session_ref, self.job_ids)


def _config_valid(binding):
    # The console leaf initializes source paths before this shared import.
    from job_service.readonly import MAX_JOBS, _valid_ref

    path = binding.database_path
    return (
        binding.authorized is True
        and type(path) is type(Path()) and path.is_absolute()
        and ".." not in path.parts and not str(path).startswith(("\\\\", "//"))
        and not any(":" in part for part in path.parts[1:])
        and _valid_ref(binding.actor_ref) and _valid_ref(binding.session_ref)
        and type(binding.job_ids) is tuple and 1 <= len(binding.job_ids) <= MAX_JOBS
        and all(_valid_ref(job) for job in binding.job_ids)
        and len(set(binding.job_ids)) == len(binding.job_ids)
    )


def _counts(value, keys, selected):
    return (type(value) is dict and value.keys() == keys
            and all(type(number) is int and 0 <= number <= selected
                    for number in value.values())
            and sum(value.values()) == selected)


def _validated_result(product, selected):
    if (type(product) is not dict
            or product.keys() != _FIXED.keys() | {
                "selected_job_count", "status_counts", "evidence_counts",
                "attempts_recorded", "progress"}
            or any(type(product[key]) is not type(value) or product[key] != value
                   for key, value in _FIXED.items())
            or type(product["selected_job_count"]) is not int
            or product["selected_job_count"] != selected
            or not _counts(product["status_counts"], _STATES, selected)
            or not _counts(product["evidence_counts"], _EVIDENCE, selected)):
        raise JobActivityUnavailable()
    states, progress = product["status_counts"], product["progress"]
    if (type(product["attempts_recorded"]) is not int
            or not states["running"] <= product["attempts_recorded"] <= selected * 10
            or type(progress) is not dict or progress.keys() != _PROGRESS
            or type(progress["basis"]) is not str
            or progress["basis"] != "selected_ledger_states_not_execution_percentage"):
        raise JobActivityUnavailable()
    expected = {
        "pending_count": states["registered"], "active_count": states["running"],
        "awaiting_decision_count": states["needs_decision"],
        "terminal_count": sum(states[state] for state in
                              ("succeeded", "failed", "cancelled", "expired")),
    }
    if any(type(progress[key]) is not int or progress[key] != value
           for key, value in expected.items()):
        raise JobActivityUnavailable()
    encoded = json.dumps(product, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("ascii")) > MAX_RESPONSE_BYTES:
        raise JobActivityUnavailable()
    # A new metadata-only tree does not retain an upstream mutable result.
    return json.loads(encoded)


@dataclass(frozen=True, init=False, repr=False)
class JobActivityProfile:
    """Explicit immutable caller-owned config; construction performs no IO."""

    _binding: _Binding
    _reader: object
    _fence: object

    def __init__(self, *, authorized=False, database_path: Path, actor_ref: str,
                 session_ref: str, job_ids: tuple[str, ...]):
        binding = _Binding(authorized, database_path, actor_ref, session_ref, job_ids)
        if not _config_valid(binding):
            raise ValueError("invalid_job_activity_profile") from None
        # Retain an independent lexical path, not a caller-owned Path instance.
        binding = _Binding(authorized, Path(str(database_path)), actor_ref, session_ref, job_ids)
        original, builder = binding.snapshot(), build_job_activity

        def fence(profile):
            if (profile._binding is not binding or profile._reader is not reader
                    or profile._fence is not fence
                    or binding.snapshot() != original or not _config_valid(binding)):
                raise JobActivityUnavailable()

        def reader(profile):
            try:
                fence(profile)
                product = builder(Path(original[1]), authorized=True, actor_ref=original[2],
                                  session_ref=original[3], job_ids=original[4])
                fence(profile)
                result = _validated_result(product, len(original[4]))
                fence(profile)
                return result
            except Exception:
                raise JobActivityUnavailable() from None

        object.__setattr__(self, "_binding", binding)
        object.__setattr__(self, "_reader", reader)
        object.__setattr__(self, "_fence", fence)

    def __repr__(self):
        return "JobActivityProfile(authority='none', read_only=True, lazy=True)"

    def read(self) -> dict:
        """Read one bounded metadata projection; never retry or execute a job."""
        try:
            self._fence(self)
            result = self._reader(self)
            self._fence(self)
            return result
        except Exception:
            raise JobActivityUnavailable() from None
