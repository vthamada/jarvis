"""Bounded lexical selection of canonical turns; never authority or parallel memory.

Scope and lifecycle metadata must come from trusted composition, not from recalled
text or guessed identifier prefixes. This module reads supplied rows only.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from memory_service.repository import StoredTurn


@dataclass(frozen=True)
class RecallScope:
    subject_id: str
    session_ids: tuple[str, ...]
    now: datetime


@dataclass(frozen=True)
class RecallLimits:
    max_candidates: int = 100
    max_items: int = 4
    max_query_chars: int = 2048
    max_source_chars: int = 16384
    max_output_chars: int = 4096
    max_age_seconds: int = 30 * 86400
    deadline_monotonic: float | None = None


@dataclass(frozen=True)
class RecallSourceState:
    """Trusted lifecycle metadata, never extracted from a turn's prose.

    Explicit corrections need both rows, increasing version and nondecreasing
    timestamp. Competing correction branches are withheld as ambiguous. Versions
    describe caller-provided correction lineage, not a new canonical registry.
    """

    status: str = "active"
    version: int = 1
    supersedes_ref: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class RecallEvidence:
    source_ref: str
    session_id: str
    timestamp: str
    age_seconds: int
    request_content: str
    response_text: str
    matching_tokens: tuple[str, ...]
    reasons: tuple[str, ...]
    version: int
    truncated: bool
    content_role: str = "untrusted_evidence_only"


@dataclass(frozen=True)
class RecallSelection:
    status: str
    items: tuple[RecallEvidence, ...] = ()
    inspected_count: int = 0
    exclusions: tuple[tuple[str, int], ...] = ()
    selector: str = "bounded_lexical_v1"
    authority: str = "none"


def turn_source_ref(turn: StoredTurn) -> str:
    """Content-addressed row reference, not a database primary key or permission."""
    payload = [
        turn.session_id, turn.mission_id, turn.user_id, turn.request_content,
        turn.intent, turn.response_text, turn.timestamp, turn.plan_summary,
        turn.plan_steps, turn.recommended_task_type,
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "stored-turn:sha256:" + hashlib.sha256(encoded).hexdigest()


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return set(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def _date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone_required")
    return parsed.astimezone(timezone.utc)


def _aware(value: datetime) -> bool:
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() is not None)


def select_readonly_recall(
    turns: Iterable[StoredTurn],
    *,
    scope: RecallScope,
    query: str,
    limits: RecallLimits = RecallLimits(),
    source_states: Mapping[str, RecallSourceState] | None = None,
    cancelled: Callable[[], bool] | None = None,
    monotonic_clock: Callable[[], float] = time.monotonic,
) -> RecallSelection:
    """Select evidence inside an explicit subject/session scope, with no writes.

    Cancellation, invalid inputs, scan exhaustion or deadline discard all partial
    output. Lexical overlap is not semantic truth, contradiction resolution,
    authentication or authorization to use tools. Content cannot change scope.
    """
    exclusions: Counter[str] = Counter()
    inspected = 0

    def result(status: str, items: tuple[RecallEvidence, ...] = ()) -> RecallSelection:
        return RecallSelection(status, items, inspected, tuple(sorted(exclusions.items())))

    def stop() -> str | None:
        try:
            if cancelled is not None and cancelled():
                return "cancelled"
            if (limits.deadline_monotonic is not None
                    and monotonic_clock() >= limits.deadline_monotonic):
                return "deadline_exceeded"
        except Exception:
            return "control_unavailable"
        return None

    if (
        not isinstance(scope, RecallScope) or not isinstance(scope.subject_id, str)
        or not scope.subject_id or len(scope.subject_id) > 256
        or not isinstance(scope.session_ids, tuple) or not 1 <= len(scope.session_ids) <= 32
        or any(not isinstance(s, str) or not s or len(s) > 256 for s in scope.session_ids)
        or len(set(scope.session_ids)) != len(scope.session_ids) or not _aware(scope.now)
        or not isinstance(limits, RecallLimits)
    ):
        return result("invalid_scope")
    bounds = (
        (limits.max_candidates, 1, 1000), (limits.max_items, 1, 32),
        (limits.max_query_chars, 1, 8192), (limits.max_source_chars, 1, 65536),
        (limits.max_output_chars, 1, 65536), (limits.max_age_seconds, 1, 366 * 86400),
    )
    if any(type(v) is not int or not lo <= v <= hi for v, lo, hi in bounds):
        return result("invalid_limits")
    if limits.deadline_monotonic is not None and (
        type(limits.deadline_monotonic) not in {int, float}
        or not (-float("inf") < limits.deadline_monotonic < float("inf"))
    ):
        return result("invalid_limits")
    if not isinstance(query, str) or not 1 <= len(query) <= limits.max_query_chars:
        return result("invalid_query")
    query_tokens = _tokens(query)
    if not query_tokens:
        return result("invalid_query")
    if source_states is not None and (
        not isinstance(source_states, Mapping) or len(source_states) > limits.max_candidates
    ):
        return result("invalid_source_states")
    states = source_states if source_states is not None else {}
    now = scope.now.astimezone(timezone.utc)
    candidates: dict[str, tuple[StoredTurn, datetime, RecallSourceState]] = {}
    declared_targets: set[str] = set()
    try:
        interruption = stop()
        if interruption:
            return result(interruption)
        for turn in turns:
            interruption = stop()
            if interruption:
                return result(interruption)
            inspected += 1
            if inspected > limits.max_candidates:
                return result("candidate_budget_exceeded")
            if not isinstance(turn, StoredTurn):
                return result("invalid_source")
            # Do not hash, tokenize or expose unrelated subjects' content.
            if turn.user_id != scope.subject_id or turn.session_id not in scope.session_ids:
                exclusions["out_of_scope"] += 1
                continue
            values = (turn.request_content, turn.response_text, turn.intent, turn.timestamp)
            if any(not isinstance(value, str) for value in values):
                return result("invalid_source")
            if sum(len(value) for value in values) > limits.max_source_chars:
                return result("source_budget_exceeded")
            # Source references cover optional row fields too: bound those before serialization.
            if (turn.plan_summary is not None and not isinstance(turn.plan_summary, str)
                    or not isinstance(turn.plan_steps, list)
                    or len(turn.plan_steps) > 100
                    or any(not isinstance(step, str) for step in turn.plan_steps)
                    or any(value is not None and not isinstance(value, str)
                           for value in (turn.mission_id, turn.recommended_task_type))
                    or len(turn.plan_summary or "") + sum(map(len, turn.plan_steps))
                    + len(turn.mission_id or "") + len(turn.recommended_task_type or "")
                    > limits.max_source_chars):
                return result("invalid_source")
            ref = turn_source_ref(turn)
            state = states.get(ref, RecallSourceState())
            if (not isinstance(state, RecallSourceState)
                    or state.status not in {"active", "revoked", "stale"}
                    or type(state.version) is not int or not 1 <= state.version <= 1000000
                    or state.supersedes_ref is not None and (
                        not isinstance(state.supersedes_ref, str)
                        or len(state.supersedes_ref) > 256)
                    or state.expires_at is not None and not _aware(state.expires_at)):
                return result("invalid_source_states")
            if state.supersedes_ref is not None:
                declared_targets.add(state.supersedes_ref)
            if state.status != "active":
                exclusions[state.status] += 1
                continue
            if state.expires_at is not None and now >= state.expires_at:
                exclusions["expired"] += 1
                continue
            try:
                timestamp = _date(turn.timestamp)
            except (TypeError, ValueError, OverflowError):
                exclusions["invalid_timestamp"] += 1
                continue
            if timestamp > now:
                exclusions["future_timestamp"] += 1
                continue
            if now - timestamp > timedelta(seconds=limits.max_age_seconds):
                exclusions["stale"] += 1
                continue
            if ref in candidates:
                exclusions["duplicate"] += 1
            candidates[ref] = (turn, timestamp, state)
    except Exception:
        return result("source_unavailable")

    # Explicit correction edges are validated against eligible, scoped canonical rows.
    # Invalid/competing branches withhold their entire connected component, including
    # the old row: never silently fall back to a possibly superseded fact.
    adjacency: dict[str, set[str]] = {ref: set() for ref in candidates}
    children: dict[str, list[str]] = {}
    invalid: set[str] = set()
    superseded: set[str] = set()
    for ref, (_, timestamp, state) in candidates.items():
        interruption = stop()
        if interruption:
            return result(interruption)
        parent = state.supersedes_ref
        if parent is None:
            continue
        if parent not in candidates:
            invalid.add(ref)
            continue
        adjacency[ref].add(parent)
        adjacency[parent].add(ref)
        _, parent_time, parent_state = candidates[parent]
        if ref == parent or state.version <= parent_state.version or timestamp < parent_time:
            invalid.update((ref, parent))
        children.setdefault(parent, []).append(ref)
        superseded.add(parent)
    invalid.update(parent for parent, refs in children.items() if len(refs) > 1)
    pending = list(invalid)
    while pending:
        interruption = stop()
        if interruption:
            return result(interruption)
        for neighbor in adjacency[pending.pop()]:
            if neighbor not in invalid:
                invalid.add(neighbor)
                pending.append(neighbor)
    ranked = []
    for ref, (turn, timestamp, state) in candidates.items():
        interruption = stop()
        if interruption:
            return result(interruption)
        if ref in invalid:
            exclusions["ambiguous_correction"] += 1
            continue
        if ref in superseded:
            exclusions["superseded"] += 1
            continue
        if ref in declared_targets:
            exclusions["correction_unavailable"] += 1
            continue
        overlap = tuple(sorted(
            query_tokens & _tokens(turn.request_content + " " + turn.response_text),
        ))
        if not overlap:
            exclusions["no_lexical_match"] += 1
            continue
        ranked.append((ref, turn, timestamp, state, overlap))
    ranked.sort(key=lambda item: (-len(item[4]), -item[2].timestamp(), item[0]))
    output = []
    remaining = limits.max_output_chars
    for ref, turn, timestamp, state, overlap in ranked[:limits.max_items]:
        if remaining <= 0:
            exclusions["output_budget"] += 1
            break
        request = turn.request_content[:remaining]
        remaining -= len(request)
        response = turn.response_text[:remaining]
        remaining -= len(response)
        reasons = ("exact_subject_session_scope", "lexical_overlap", "fresh_source")
        if state.supersedes_ref is not None:
            reasons += ("explicit_correction",)
        output.append(RecallEvidence(
            ref, turn.session_id, turn.timestamp, int((now - timestamp).total_seconds()),
            request, response, overlap, reasons, state.version,
            len(request) < len(turn.request_content) or len(response) < len(turn.response_text),
        ))
    interruption = stop()
    if interruption:
        return result(interruption)
    ambiguous = bool(invalid or exclusions["correction_unavailable"])
    status = "selected" if output else "needs_decision" if ambiguous else "no_match"
    return result(status, tuple(output))
