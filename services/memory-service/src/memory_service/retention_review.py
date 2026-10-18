"""Pure, bounded operator review hints over canonical turns, never retention policy.

The caller's age horizon is a review filter only. This module cannot archive,
delete, revoke, consolidate, write memory or grant an action. Canonical lifecycle
decisions remain with the existing Core and memory governance.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum

from memory_service.recall import RecallScope, RecallSourceState, turn_source_ref
from memory_service.repository import StoredTurn

_REF = re.compile(r"stored-turn:sha256:[0-9a-f]{64}\Z")
_SOURCE_CHAR_LIMIT = 65536


class RetentionReviewReason(str, Enum):
    AGE_HORIZON_EXCEEDED = "age_horizon_exceeded"
    DECLARED_STALE = "declared_stale"
    DECLARED_REVOKED = "declared_revoked"
    EXPIRED = "expired"
    EXPLICITLY_SUPERSEDED = "explicitly_superseded"
    AMBIGUOUS_CORRECTION = "ambiguous_correction"


@dataclass(frozen=True)
class RetentionReviewItem:
    source_ref: str
    reasons: tuple[RetentionReviewReason, ...]
    version: int
    age_seconds: int


@dataclass(frozen=True)
class RetentionReviewPlan:
    status: str
    reason: str
    plan_hash: str | None = None
    inspected_count: int = 0
    scoped_count: int = 0
    unchanged_count: int = 0
    withheld_count: int = 0
    items: tuple[RetentionReviewItem, ...] = ()

    def metadata(self, *, include_refs: bool = False) -> dict[str, object]:
        """Return fresh safe containers; hashes of source refs require explicit opt-in."""
        if type(include_refs) is not bool:
            raise ValueError("invalid_include_refs")
        items = []
        for item in self.items:
            value: dict[str, object] = {
                "reasons": [reason.value for reason in item.reasons],
                "version": item.version,
                "age_seconds": item.age_seconds,
            }
            if include_refs:
                value["source_ref"] = item.source_ref
            items.append(value)
        return {
            "status": self.status, "reason": self.reason, "plan_hash": self.plan_hash,
            "inspected_count": self.inspected_count, "scoped_count": self.scoped_count,
            "unchanged_count": self.unchanged_count, "withheld_count": self.withheld_count,
            "candidate_count": len(items), "items": items,
            "authority": "none", "review_only": True, "mutation_performed": False,
            "planner": "bounded_retention_review_v1",
        }


def _utc(value: object) -> bool:
    return (type(value) is datetime and value.tzinfo is not None
            and value.utcoffset() == timedelta(0))


def _bounded_text(value: object, limit: int = 256) -> bool:
    return (type(value) is str and 0 < len(value) <= limit
            and not any(0xD800 <= ord(char) <= 0xDFFF for char in value))


def build_retention_review(
    turns: Iterable[StoredTurn], *, scope: RecallScope, max_candidates: int = 100,
    max_age_seconds: int = 30 * 86400,
    source_states: Mapping[str, RecallSourceState] | None = None,
    cancelled: Callable[[], bool] | None = None,
    deadline_monotonic: float | None = None,
    monotonic_clock: Callable[[], float] = time.monotonic,
) -> RetentionReviewPlan:
    """Plan metadata-only hints inside explicit trusted scope, with no side effects.

    Cancellation, errors and budget exhaustion discard the complete partial plan.
    Unknown/future timestamps and ambiguous correction components are withheld.
    A caller-declared lifecycle state is not authenticated provenance or permission.
    Only active unexpired children with increasing versions and nondecreasing UTC
    timestamps can establish an explicit supersession review signal.
    """
    def reject(reason: str) -> RetentionReviewPlan:
        return RetentionReviewPlan("cancelled" if reason == "cancelled" else "rejected", reason)

    def interruption() -> str | None:
        try:
            if cancelled is not None:
                stopped = cancelled()
                if type(stopped) is not bool:
                    return "control_unavailable"
                if stopped:
                    return "cancelled"
            if deadline_monotonic is not None:
                current = monotonic_clock()
                if type(current) not in (int, float) or not math.isfinite(current):
                    return "control_unavailable"
                if current >= deadline_monotonic:
                    return "deadline_exceeded"
        except Exception:
            return "control_unavailable"
        return None

    try:
        if (type(scope) is not RecallScope or not _bounded_text(scope.subject_id)
                or type(scope.session_ids) is not tuple or not 1 <= len(scope.session_ids) <= 32
                or any(not _bounded_text(item) for item in scope.session_ids)
                or len(set(scope.session_ids)) != len(scope.session_ids) or not _utc(scope.now)):
            return reject("invalid_scope")
        subject, sessions = scope.subject_id, scope.session_ids
        now = scope.now.astimezone(timezone.utc)
        if (type(max_candidates) is not int or not 1 <= max_candidates <= 1000
                or type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 366 * 86400
                or deadline_monotonic is not None and (
                    type(deadline_monotonic) not in (int, float)
                    or not math.isfinite(deadline_monotonic))
                or cancelled is not None and not callable(cancelled)
                or not callable(monotonic_clock)):
            return reject("invalid_limits")
        states: dict[str, RecallSourceState] = {}
        if source_states is not None:
            if not isinstance(source_states, Mapping) or len(source_states) > max_candidates:
                return reject("invalid_source_states")
            for index, (ref, state) in enumerate(source_states.items()):
                if (index >= max_candidates or type(ref) is not str or not _REF.fullmatch(ref)
                        or type(state) is not RecallSourceState
                        or type(state.status) is not str
                        or state.status not in {"active", "revoked", "stale"}
                        or type(state.version) is not int or not 1 <= state.version <= 1000000
                        or state.supersedes_ref is not None and (
                            type(state.supersedes_ref) is not str
                            or not _REF.fullmatch(state.supersedes_ref))
                        or state.expires_at is not None and not _utc(state.expires_at)):
                    return reject("invalid_source_states")
                expires_at = (state.expires_at.astimezone(timezone.utc)
                              if state.expires_at is not None else None)
                states[ref] = replace(state, expires_at=expires_at)
    except Exception:
        return reject("invalid_source_states")

    inspected = scoped = withheld = 0
    # No content or caller-owned list survives the row-reference boundary.
    records: dict[str, tuple[datetime, RecallSourceState]] = {}
    missing_timestamp_refs: set[str] = set()
    try:
        stopped = interruption()
        if stopped:
            return reject(stopped)
        for turn in turns:
            stopped = interruption()
            if stopped:
                return reject(stopped)
            inspected += 1
            if inspected > max_candidates:
                return reject("candidate_budget_exceeded")
            if type(turn) is not StoredTurn:
                return reject("invalid_source")
            # Scope precedes hashing, timestamp parsing or content access.
            if (type(turn.user_id) is not str or type(turn.session_id) is not str
                    or turn.user_id != subject or turn.session_id not in sessions):
                continue
            scoped += 1
            required = (turn.request_content, turn.response_text, turn.intent, turn.timestamp)
            optional = (turn.mission_id, turn.plan_summary, turn.recommended_task_type)
            if (any(type(value) is not str for value in required)
                    or any(value is not None and type(value) is not str for value in optional)
                    or type(turn.plan_steps) is not list or len(turn.plan_steps) > 100
                    or any(type(step) is not str for step in turn.plan_steps)):
                return reject("invalid_source")
            steps = tuple(turn.plan_steps)
            source_chars = sum(len(value or "") for value in (*required, *optional, *steps))
            if source_chars > _SOURCE_CHAR_LIMIT:
                return reject("source_budget_exceeded")
            # Copy mutable list before computing the existing canonical row reference.
            snapshot = replace(turn, plan_steps=list(steps))
            ref = turn_source_ref(snapshot)
            if ref in records or ref in missing_timestamp_refs:
                continue
            try:
                timestamp = datetime.fromisoformat(snapshot.timestamp.replace("Z", "+00:00"))
                valid_time = _utc(timestamp) and timestamp <= now
            except (ValueError, OverflowError):
                valid_time = False
            if not valid_time:
                missing_timestamp_refs.add(ref)
                withheld += 1
                continue
            records[ref] = (timestamp, states.get(ref, RecallSourceState()))
    except Exception:
        return reject("source_unavailable")

    children: dict[str, list[str]] = {}
    adjacency: dict[str, set[str]] = {ref: set() for ref in records}
    invalid: set[str] = set()
    superseded: set[str] = set()
    # Invalid timestamp children still declare an unresolved correction, never
    # silently establish an edge or leave a parent claimed unchanged.
    for ref in missing_timestamp_refs:
        parent = states.get(ref, RecallSourceState()).supersedes_ref
        if parent in records:
            invalid.add(parent)
    for ref, (timestamp, state) in records.items():
        stopped = interruption()
        if stopped:
            return reject(stopped)
        parent = state.supersedes_ref
        if parent is None:
            continue
        if parent not in records:
            invalid.add(ref)
            continue
        adjacency[ref].add(parent)
        adjacency[parent].add(ref)
        parent_time, parent_state = records[parent]
        children.setdefault(parent, []).append(ref)
        if (ref == parent or state.version <= parent_state.version or timestamp < parent_time
                or state.status != "active"
                or state.expires_at is not None and now >= state.expires_at):
            invalid.update((ref, parent))
        else:
            superseded.add(parent)
    invalid.update(parent for parent, refs in children.items() if len(refs) > 1)
    pending = list(invalid)
    while pending:
        stopped = interruption()
        if stopped:
            return reject(stopped)
        for neighbor in adjacency[pending.pop()]:
            if neighbor not in invalid:
                invalid.add(neighbor)
                pending.append(neighbor)
    items = []
    unchanged = 0
    for ref, (timestamp, state) in sorted(records.items()):
        stopped = interruption()
        if stopped:
            return reject(stopped)
        age = int((now - timestamp).total_seconds())
        reasons = []
        if ref in invalid:
            reasons.append(RetentionReviewReason.AMBIGUOUS_CORRECTION)
            withheld += 1
        else:
            if now - timestamp > timedelta(seconds=max_age_seconds):
                reasons.append(RetentionReviewReason.AGE_HORIZON_EXCEEDED)
            if state.status == "stale":
                reasons.append(RetentionReviewReason.DECLARED_STALE)
            if state.status == "revoked":
                reasons.append(RetentionReviewReason.DECLARED_REVOKED)
            if state.expires_at is not None and now >= state.expires_at:
                reasons.append(RetentionReviewReason.EXPIRED)
            if ref in superseded:
                reasons.append(RetentionReviewReason.EXPLICITLY_SUPERSEDED)
        if reasons:
            items.append(RetentionReviewItem(ref, tuple(reasons), state.version, age))
        else:
            unchanged += 1
    status = "needs_decision" if withheld else "review_ready" if items else "empty"
    reason = "withheld_sources" if withheld else "review_signals" if items else "no_review_signals"
    # Bind every inspected scoped reference/state, including currently unchanged
    # rows, to scope/as-of/horizon. This digest is identity, never an execution grant.
    payload = {
        "planner": "bounded_retention_review_v1", "subject": subject, "sessions": sorted(sessions),
        "now": now.astimezone(timezone.utc).isoformat(), "max_age_seconds": max_age_seconds,
        "records": [[ref, timestamp.isoformat(), state.status, state.version,
                     state.supersedes_ref,
                     state.expires_at.isoformat() if state.expires_at else None]
                    for ref, (timestamp, state) in sorted(records.items())],
        "withheld_refs": [[ref, state.status, state.version, state.supersedes_ref,
                           state.expires_at.isoformat() if state.expires_at else None]
                          for ref in sorted(missing_timestamp_refs)
                          for state in [states.get(ref, RecallSourceState())]],
        "status": status,
        "items": [[item.source_ref, list(item.reasons), item.version, item.age_seconds]
                  for item in items],
    }
    plan_hash = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    stopped = interruption()
    if stopped:
        return reject(stopped)
    return RetentionReviewPlan(status, reason, plan_hash, inspected, scoped, unchanged,
                               withheld, tuple(items))
