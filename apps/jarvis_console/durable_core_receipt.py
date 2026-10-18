"""Read an existing, exactly correlated native Core final; never execute a task.

Only known, quiescent local SQLite stores are inspected in read-only snapshots.
The receipt is a consistency binding, not authentication, a grant, a signature,
or proof that a past action was exactly-once. Missing flush evidence is unknown.
"""

from __future__ import annotations

import json
import re
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from hashlib import sha256
from math import isfinite
from pathlib import Path

from job_service.store import JobStoreError, _ref, _utc

from apps.jarvis_console.conversation_export import (
    MAX_EVENT_BYTES,
    _file_state,
    _open,
    _payload,
    _read,
    _stamp,
    _text,
)

_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_REQUIRED = frozenset({"input_received", "governance_checked", "response_synthesized",
                       "memory_recorded"})
_FIELDS = ("job_id", "actor_ref", "session_ref", "input_text", "input_sha256", "request_id",
           "core_session_id", "phase", "started_at", "deadline", "binding_sha256",
           "receipt_sha256")
_ACTIVE_EVENTS = frozenset({
    "operation_dispatched", "operation_completed", "operation_executed",
    "adapter_grant_issued", "adapter_grant_claimed", "adapter_action_intent_declared",
    "action_confirmation_claimed", "action_confirmation_challenge_created",
    "specialists_dispatched", "specialists_completed", "domain_specialist_completed",
    "specialist_shadow_mode_completed", "specialist_shared_memory_linked",
})
_EMPTY_KEYS = frozenset({
    "operation_id", "adapter_grant", "adapter_grant_id", "adapter_grant_claim",
    "adapter_action_request", "action_confirmation_claim", "action_confirmation_challenge",
    "selected_specialists", "specialist_contributions", "specialist_contribution_count",
    "specialist_count", "specialist_used", "specialist_used_count",
    "mind_domain_specialist_active_specialist",
})


def _refuse() -> None:
    raise JobStoreError("durable_receipt_refused")


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8", errors="strict")).hexdigest()


@dataclass(frozen=True)
class VerifiedCoreReceipt:
    request_id: str
    memory_record_id: str
    response_text: str = field(repr=False)
    query_sha256: str
    response_sha256: str
    receipt_sha256: str
    outcome: str
    timestamp: str
    event_count: int


def _task_values(task) -> tuple:
    values = tuple(getattr(task, key) for key in _FIELDS)
    data = dict(zip(_FIELDS, values, strict=True))
    for name in ("job_id", "actor_ref", "session_ref"):
        _ref(data[name])
    for name in ("request_id", "core_session_id"):
        value = data[name]
        if type(value) is not str or not 1 <= len(value) <= 160 or any(
            not 33 <= ord(char) <= 126 for char in value
        ):
            _refuse()
    if (_text(data["input_text"], 2048) != data["input_text"]
            or data["input_sha256"] != _digest(data["input_text"])
            or type(data["binding_sha256"]) is not str
            or not _HASH.fullmatch(data["binding_sha256"])
            or data["phase"] not in {"prepared", "started", "uncertain", "completed"}
            or (data["receipt_sha256"] is not None and (
                type(data["receipt_sha256"]) is not str
                or not _HASH.fullmatch(data["receipt_sha256"])
            ))):
        _refuse()
    deadline = _utc(data["deadline"])
    started = data["started_at"]
    if started is None:
        if data["phase"] != "prepared":
            _refuse()
    elif _utc(started) > deadline:
        _refuse()
    if data["phase"] == "completed" and data["receipt_sha256"] is None:
        _refuse()
    return values


def _no_active_markers(name: str, payload: dict) -> None:
    if (name in _ACTIVE_EVENTS or name.startswith(("model_tool_loop_", "adapter_execution_"))
            or name.startswith("action_confirmation_") or name.startswith("model_")):
        _refuse()
    if name == "specialist_subflow_completed" and any(
        type(payload.get(key)) is not int or payload[key] != 0
        for key in ("selection_count", "invocation_count", "contribution_count",
                    "live_contribution_count")
    ):
        _refuse()
    for key, value in payload.items():
        if key in _EMPTY_KEYS and value not in (None, False, 0, [], {}):
            _refuse()
        if key == "capability_decision_selected_capabilities":
            if type(value) is not list or any(item != "core_reasoning" for item in value):
                _refuse()
        if key == "capability_decision_selected_mode":
            if value != "core_guidance_only":
                _refuse()
        if key in {"extractive_status", "generative_status", "model_tool_loop_status"}:
            if value != "disabled":
                _refuse()
        if key in {"extractive_excerpt_count", "generative_analysis_characters",
                   "model_tool_loop_observation_count", "model_tool_loop_analysis_characters"}:
            if type(value) is not int or value != 0:
                _refuse()


def _received_matches_task(received, task):
    if (received.get("content") != task.input_text
            or received.get("canonical_user_ref") != f"user://{task.actor_ref}"
            or received.get("operator_identity_ref") != f"operator://{task.actor_ref}"
            or received.get("channel") != "console"
            or received.get("surface_id") != "surface://durable-core-task"
            or received.get("surface_kind") != "console"
            or received.get("surface_session_id") != task.core_session_id
            or received.get("surface_capability_scope") != []
            or received.get("requested_autonomy_level") != "assist_only"
            or received.get("max_autonomy_level") != "assist_only"):
        _refuse()


def _scan_events(events, task, check):
    cursor = events.execute(
        "SELECT event_name, timestamp, source_service, request_id, correlation_id, session_id, "
        "mission_id, operation_id, CASE WHEN length(CAST(payload AS BLOB)) <= ? "
        "THEN payload ELSE NULL END AS payload FROM internal_events "
        "WHERE request_id = ? OR correlation_id = ? LIMIT 513",
        (MAX_EVENT_BYTES, task.request_id, task.request_id),
    )
    required: dict[str, dict] = {}
    count = size = 0
    while (row := cursor.fetchone()) is not None:
        check()
        count += 1
        if count > 512 or row["payload"] is None:
            _refuse()
        size += len(row["payload"].encode("utf-8", errors="strict"))
        if size > 4_194_304:
            _refuse()
        if (row["request_id"] != task.request_id or row["correlation_id"] != task.request_id
                or row["session_id"] != task.core_session_id or row["mission_id"] is not None
                or row["source_service"] != "orchestrator-service"
                or row["operation_id"] is not None or task.started_at is None
                or not task.started_at <= _stamp(row["timestamp"]) <= task.deadline):
            _refuse()
        payload = _payload(row["payload"])
        name = row["event_name"]
        if type(name) is not str:
            _refuse()
        _no_active_markers(name, payload)
        if name == "input_received":
            _received_matches_task(payload, task)
        if name == "response_synthesized" and any(
            payload.get(key) != "disabled" for key in (
                "extractive_status", "generative_status", "model_tool_loop_status",
            )
        ):
            _refuse()
        if name in _REQUIRED:
            if name in required:
                _refuse()
            required[name] = payload
    return count, required


def find_core_receipt(core, task) -> VerifiedCoreReceipt | None:
    """Find a complete final or return unknown; never call Core or write a store."""
    try:
        from memory_service.repository import SqliteMemoryRepository
        from observability_service.repository import ObservabilityRepository
        from orchestrator_service.service import OrchestratorService

        original = _task_values(task)
        if (not isinstance(core, OrchestratorService)
                or type(core.memory_service.repository) is not SqliteMemoryRepository
                or type(core.observability_service.repository) is not ObservabilityRepository
                or core.model_tool_loop is not None
                or core.synthesis_engine._inference_port is not None
                or core.synthesis_engine._generative_port is not None):
            _refuse()
        memory_path = Path(core.memory_service.repository.database_path)
        events_path = Path(core.observability_service.repository.database_path)
        previous = time.monotonic()
        if type(previous) not in {int, float} or not isfinite(previous):
            _refuse()
        lookup_deadline = previous + 10.0

        def check():
            nonlocal previous
            now = time.monotonic()
            if (type(now) not in {int, float} or not isfinite(now) or now < previous
                    or now >= lookup_deadline or _task_values(task) != original):
                _refuse()
            previous = now

        check()
        paths = (memory_path, events_path)
        before = tuple(_file_state(path) for path in paths)
        if memory_path.resolve() == events_path.resolve():
            _refuse()
        receipt = None
        with ExitStack() as stack:
            memory = _open(memory_path, stack, check, "interaction_turns")
            claims = _open(memory_path, stack, check, "runtime_request_claims")
            events = _open(events_path, stack, check, "internal_events")
            rows = claims.execute(
                "SELECT request_id, session_id, claimed_at FROM runtime_request_claims "
                "WHERE request_id = ? LIMIT 2", (task.request_id,),
            ).fetchall()
            count, payloads = _scan_events(events, task, check)
            if not rows:
                if count or task.phase == "completed":
                    _refuse()
            else:
                if (len(rows) != 1 or rows[0]["request_id"] != task.request_id
                        or rows[0]["session_id"] != task.core_session_id
                        or task.started_at is None
                        or not task.started_at <= _stamp(rows[0]["claimed_at"]) <= task.deadline):
                    _refuse()
                if set(payloads) != _REQUIRED:
                    if task.phase == "completed":
                        _refuse()
                else:
                    receipt = _complete_receipt(memory, events, task, count, check)
            check()
        if tuple(_file_state(path) for path in paths) != before:
            _refuse()
        check()
        return receipt
    except Exception:
        pass
    # Deliberately outside the handler: no leaked SQL/path exception context.
    raise JobStoreError("durable_receipt_refused") from None


def _complete_receipt(memory, events, task, count, check):
    principal = f"user://{task.actor_ref}"
    query, response, stamp, _intent, decision, _generation, record = _read(
        memory, events, session_id=task.core_session_id, request_id=task.request_id,
        principal_ref=principal, check=check, allow_conditional=True,
    )
    if (query != task.input_text or _digest(query) != task.input_sha256
            or not task.started_at <= _stamp(stamp) <= task.deadline):
        _refuse()
    # These sovereign render markers cannot occur in a native-only receipt.
    from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER, REVIEWED_EVIDENCE_MARKER

    if GENERATIVE_ANALYSIS_MARKER in response or REVIEWED_EVIDENCE_MARKER in response:
        _refuse()
    response_hash = _digest(response)
    receipt_hash = _digest(json.dumps({
        "schema_version": "jarvis-durable-core-receipt-v1", "binding_sha256": task.binding_sha256,
        "job_id": task.job_id, "request_id": task.request_id,
        "session_id": task.core_session_id, "memory_record_id": record,
        "query_sha256": task.input_sha256, "response_sha256": response_hash,
        "decision": decision, "timestamp": stamp,
    }, sort_keys=True, ensure_ascii=True, separators=(",", ":")))
    if task.phase == "completed" and task.receipt_sha256 != receipt_hash:
        _refuse()
    return VerifiedCoreReceipt(
        request_id=task.request_id, memory_record_id=record, response_text=response,
        query_sha256=task.input_sha256, response_sha256=response_hash,
        receipt_sha256=receipt_hash,
        outcome="succeeded" if decision == "allow" else "needs_decision",
        timestamp=stamp, event_count=count,
    )
