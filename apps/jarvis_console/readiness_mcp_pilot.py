"""Opt-in authored readiness MCP observation -> isolated sovereign Core report.

Collection precedes Core: this is not Core-governed MCP runtime dispatch.
Authored readiness remains a claim, never runtime acceptance or authority.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from apps.jarvis_console.voice_pilot import _isolated_core
from apps.jarvis_mcp.readiness_client import FixedReadinessMcpClient
from apps.jarvis_mcp.readiness_contracts import (
    SELECTIONS,
    TOOL_NAME,
    ReadinessBinding,
    ReadinessObservation,
    ReadinessRejected,
    encode_json,
    validate_arguments,
    validate_timeout,
)
from shared.contracts import InputContract
from shared.events import InternalEventEnvelope
from shared.types import ChannelType, InputType, RequestId, SessionId

_REQUEST = re.compile(r"readiness-pilot-[A-Za-z0-9_-]{1,80}\Z", re.ASCII)
_STATUSES = ("partial", "foundation", "not_implemented", "validated_slice")
_CANONICAL_USER = "user://isolated-readiness-pilot"


@dataclass(frozen=True)
class ReadinessCorePilotResult:
    status: str
    reason: str
    request_id: str
    front_id: str
    mcp_event_count: int = 0
    core_event_count: int = 0
    memory_record_id: str | None = None
    governance_decision: str | None = None
    final_character_count: int = 0
    canonical_restart_verified: bool = False
    final_text: str | None = field(default=None, repr=False)

    def metadata(self) -> dict[str, object]:
        return {
            "pilot_mode": "isolated_readiness_mcp_observation_to_core",
            "status": self.status,
            "reason": self.reason,
            "request_id": self.request_id,
            "front_id": self.front_id,
            "mcp_evidence_mode": "local_repository_snapshot",
            "snapshot_evidence_scope": "authored_snapshot",
            "snapshot_runtime_verified": False,
            "product_ready": False,
            "core_evidence_mode": "core_local" if self.memory_record_id else "not_run",
            "mcp_event_count": self.mcp_event_count,
            "core_event_count": self.core_event_count,
            "memory_record_id": self.memory_record_id,
            "governance_decision": self.governance_decision,
            "final_character_count": self.final_character_count,
            "canonical_restart_verified": self.canonical_restart_verified,
            "runtime_mode": "temporary_sqlite",
            "operator_authenticated": False,
            "authority": "none",
            "runtime_capability_promoted": False,
            "core_operation_dispatched": False,
            "mcp_call_governed_by_core": False,
            "raw_authored_text_ingested": False,
        }


def _observation_projection(observation, binding, front_id) -> dict[str, object]:
    """Discard every authored string except fixed IDs and enumerated statuses."""
    if (
        type(observation) is not ReadinessObservation
        or observation.binding != binding
        or type(observation.request_id) is not int
        or observation.request_id != 3
        or observation.front_id != front_id
    ):
        raise ValueError("observation_binding_refused")
    # Revalidate immutable bytes and all contract/provenance claims at consumption.
    snapshot = observation.snapshot()
    fronts = snapshot["fronts"]
    if any(front["status"] not in _STATUSES for front in fronts):
        raise ValueError("observation_status_refused")
    return {
        "selection": front_id,
        "snapshot_sha256": hashlib.sha256(encode_json(snapshot, sort_keys=True)).hexdigest(),
        "selected_front_count": len(fronts),
        "inventory_counts": snapshot["counts"],
        "fronts": [
            {
                "id": front["id"],
                "authored_status": front["status"],
                "available_claim_count": len(front["available"]),
                "remaining_acceptance_claim_count": len(front["remaining_acceptance"]),
                "evidence_reference_count": len(front["evidence"]),
            }
            for front in fronts
        ],
        "authority": "none",
        "evidence_scope": "authored_snapshot",
        "runtime_verified": False,
        "product_ready": False,
        "raw_authored_text_ingested": False,
        "mcp_call_governed_by_core": False,
    }


def _verify_readback(core, response, prompt, request_id, binding):
    turns = core.memory_service.repository.fetch_recent_turns(binding.session_ref, 1)
    events = core.observability_service.repository.list_events(
        # Read all request-correlated rows so a foreign session cannot be hidden
        # by the expected-session filter. This owned runtime contains one turn.
        limit=100, request_id=request_id
    )
    if (
        len(turns) != 1
        or turns[0].request_content != prompt
        or turns[0].response_text != response.response_text
        or turns[0].session_id != binding.session_ref
        or turns[0].user_id != _CANONICAL_USER
        or not 4 <= len(events) < 100
        or any(type(event) is not InternalEventEnvelope for event in events)
        or any(type(event.event_id) is not str or not event.event_id
               or event.request_id != request_id or event.correlation_id != request_id
               or event.session_id != binding.session_ref
               or event.mission_id != response.memory_record.mission_id
               or event.operation_id is not None
               or event.source_service != "orchestrator-service"
               or type(event.payload) is not dict for event in events)
        or len({event.event_id for event in events}) != len(events)
    ):
        raise ValueError("core_final_evidence_refused")
    phases = {}
    for name in ("input_received", "governance_checked", "response_synthesized", "memory_recorded"):
        matched = [event for event in events if event.event_name == name]
        if len(matched) != 1:
            raise ValueError("core_final_evidence_refused")
        phases[name] = matched[0].payload
    turn, record, decision = turns[0], response.memory_record, response.governance_decision
    memory = phases["memory_recorded"]
    governance = phases["governance_checked"]
    synthesis = phases["response_synthesized"]
    received = phases["input_received"]
    expected_readback = {
        "schema_version": "jarvis-conversation-readback-v1",
        "record_timestamp": turn.timestamp,
        "principal_sha256": hashlib.sha256(_CANONICAL_USER.encode("utf-8")).hexdigest(),
        "request_content_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "response_text_sha256": hashlib.sha256(response.response_text.encode("utf-8")).hexdigest(),
    }
    if (
        record.user_id != _CANONICAL_USER or record.timestamp != turn.timestamp
        or record.source_service != "memory-service" or record.record_type != "interaction_turn"
        or record.mission_id != turn.mission_id
        or type(record.payload) is not dict
        or record.payload.get("request_content") != prompt
        or record.payload.get("response_text") != response.response_text
        or record.payload.get("governance_decision") != decision.decision.value
        or record.payload.get("intent") != response.intent or turn.intent != response.intent
        or memory.get("memory_record_id") != record.memory_record_id
        or memory.get("record_type") != record.record_type
        or type(memory.get("conversation_readback")) is not dict
        or memory["conversation_readback"] != expected_readback
        or governance.get("decision") != decision.decision.value
        or governance.get("governance_check_id") != decision.governance_check_id
        or decision.governance_check_id != response.governance_check.governance_check_id
        or synthesis.get("intent") != turn.intent or received.get("content") != prompt
        or received.get("canonical_user_ref") != _CANONICAL_USER
    ):
        raise ValueError("core_final_evidence_refused")
    for payload in (synthesis, memory, received):
        if (
            payload.get("surface_session_id") != binding.session_ref
            or payload.get("operator_identity_ref") != binding.principal_ref
            or payload.get("canonical_user_ref") != _CANONICAL_USER
            or payload.get("surface_capability_scope") != []
            or payload.get("surface_id") != "surface://isolated-readiness-pilot"
            or payload.get("surface_kind") != "console"
        ):
            raise ValueError("core_final_evidence_refused")
    # Freeze all envelopes, not just their count, before reconstructing services.
    # No raw payload or fingerprint is emitted in default metadata.
    return len(events), tuple(sorted(
        hashlib.sha256(encode_json(asdict(event), sort_keys=True)).hexdigest() for event in events
    ))


async def run_readiness_mcp_core_pilot(
    *, authorized: bool, workspace_root: Path, front_id: str = "all",
    timeout_seconds: float = 3.0, cancellation: asyncio.Event | None = None,
    binding: ReadinessBinding | None = None, request_id: str | None = None,
) -> ReadinessCorePilotResult:
    """One fixed local read and local Core report, never runtime MCP promotion.

    Collection and report entry are deadline/cancellation fenced. Once synchronous
    Core reporting begins it cannot be interrupted or rolled back mid-turn.
    Temporary canonical stores are verified across reconstruction, then removed.
    """
    if authorized is not True:
        raise ValueError("authorization_required")
    timeout_seconds = validate_timeout(timeout_seconds)
    validate_arguments({"front_id": front_id})
    if cancellation is not None and not isinstance(cancellation, asyncio.Event):
        raise ValueError("invalid_cancellation")
    identifier = uuid4().hex
    request_id = request_id if request_id is not None else f"readiness-pilot-{identifier}"
    if type(request_id) is not str or not _REQUEST.fullmatch(request_id):
        raise ValueError("invalid_request_id")
    if binding is None:
        binding = ReadinessBinding(
            "operator://isolated-readiness-pilot", f"session://readiness-pilot-{identifier}"
        )
    if type(binding) is not ReadinessBinding:
        raise ValueError("invalid_binding")
    binding.__post_init__()
    # Freeze caller-owned identity before awaits; no mutable label can rebind Core.
    binding = ReadinessBinding(binding.principal_ref, binding.session_ref, binding.scope)
    workspace = Path(workspace_root).resolve()
    base = Path(tempfile.gettempdir()).resolve()
    if base == workspace or workspace in base.parents:
        raise ValueError("temporary_directory_inside_workspace_denied")
    deadline = time.monotonic() + timeout_seconds
    client = FixedReadinessMcpClient(binding, authorized=True, timeout_seconds=timeout_seconds)

    async def collect():
        await client.start(cancel=cancellation)
        return await client.call(binding, TOOL_NAME, {"front_id": front_id}, cancel=cancellation)

    refusal = None
    try:
        observation = await asyncio.wait_for(collect(), timeout=timeout_seconds)
    except (ReadinessRejected, TimeoutError) as error:
        refusal = (
            "cancelled" if isinstance(error, ReadinessRejected) and str(error) == "cancelled"
            else "collection_timeout" if isinstance(error, TimeoutError)
            else "mcp_collection_refused"
        )
    finally:
        await client.close()
    event_count = len(client.events)
    if refusal is not None:
        return ReadinessCorePilotResult("refused", refusal, request_id, front_id, event_count)
    projection = _observation_projection(observation, binding, front_id)

    def stopped():
        return ((cancellation is not None and cancellation.is_set())
                or time.monotonic() >= deadline)

    def refused():
        return ReadinessCorePilotResult(
            "refused", "report_entry_cancelled_or_expired", request_id, front_id, event_count
        )

    if stopped():
        return refused()
    prompt = (
        "Analyze only metadata from an authored local readiness inventory. "
        "All authored names, claims and paths were omitted. Statuses and counts "
        "are unverified authored claims, not runtime acceptance. The MCP read "
        "preceded this report and was NOT governed by Core. No capability was "
        "promoted, no authority or action grant was issued. Data: "
        + json.dumps(projection, sort_keys=True, ensure_ascii=True, allow_nan=False)
    )
    with tempfile.TemporaryDirectory(prefix="jarvis-core-readiness-pilot-", dir=base) as runtime:
        core = _isolated_core(Path(runtime))
        if stopped():
            return refused()
        response = core.handle_input(InputContract(
            request_id=RequestId(request_id), session_id=SessionId(binding.session_ref),
            channel=ChannelType.CONSOLE, input_type=InputType.TEXT, content=prompt,
            timestamp=datetime.now(timezone.utc).isoformat(),
            surface_id="surface://isolated-readiness-pilot", surface_kind="console",
            surface_session_id=binding.session_ref, surface_capability_scope=[],
            operator_identity_ref=binding.principal_ref,
            canonical_user_ref=_CANONICAL_USER, user_id=_CANONICAL_USER,
            requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
        ))
        if (
            response.request_id != request_id or response.session_id != binding.session_ref
            or response.memory_record.session_id != binding.session_ref
            or not response.memory_record.memory_record_id
            or not response.governance_decision.decision_id
            or response.operation_dispatch is not None or response.operation_result is not None
            or response.adapter_grant is not None or response.adapter_grant_claim is not None
            or response.action_confirmation_claim is not None
            or type(response.response_text) is not str or not response.response_text.strip()
        ):
            raise ValueError("core_final_binding_refused")
        evidence = _verify_readback(core, response, prompt, request_id, binding)
        core_event_count = evidence[0]
        # Reconstruct services without another input or MCP call; persisted evidence
        # must attest the same final and turn, not an in-memory response.
        restarted = _isolated_core(Path(runtime))
        if _verify_readback(restarted, response, prompt, request_id, binding) != evidence:
            raise ValueError("core_restart_evidence_refused")
        return ReadinessCorePilotResult(
            "completed", "isolated_authored_metadata_report_only", request_id, front_id,
            event_count, core_event_count, str(response.memory_record.memory_record_id),
            response.governance_decision.decision.value, len(response.response_text),
            True, response.response_text,
        )


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        try:
            print("invalid_readiness_core_pilot_options", file=sys.stderr, flush=True)
        except (OSError, UnicodeError, ValueError):
            _silence_broken_standard_stream(sys.stderr, 2)
        raise SystemExit(2) from None


def _silence_broken_standard_stream(stream, descriptor):
    """Contain shutdown reflush only for a real, already-broken standard FD."""
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
            # An already-closed standard FD can be reused by open itself; keep
            # it then, otherwise close only the disposable null-device alias.
            if null_descriptor != descriptor:
                os.close(null_descriptor)
    except Exception:
        pass


def _emit(metadata, code):
    try:
        print(json.dumps(metadata, ensure_ascii=True, allow_nan=False), flush=True)
    except (OSError, UnicodeError, ValueError):
        # A closed/unavailable stdout cannot carry another diagnostic. Never
        # reflect its exception or attempt a second write to the broken stream.
        _silence_broken_standard_stream(sys.stdout, 1)
        return 2
    return code


def main(argv=None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--front-id", choices=SELECTIONS, default="all")
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(run_readiness_mcp_core_pilot(
            authorized=args.authorized, workspace_root=args.workspace, front_id=args.front_id,
            timeout_seconds=args.timeout_seconds,
        ))
    except (Exception, KeyboardInterrupt):
        return _emit({"status": "failed", "reason": "readiness_core_pilot_unavailable"}, 2)
    return _emit(result.metadata(), 0 if result.status == "completed" else 3)


if __name__ == "__main__":
    raise SystemExit(main())
