"""Opt-in Core composition for one bounded, host-selected read-only tool.

This is not a general executor, credential broker, scheduler or recovery ledger.
The provider receives the current query, resource IDs and observed text, plus
bounded same-subject/session canonical history only under a separate host opt-in.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from threading import Event
from typing import Callable

from operational_service.adapters.local_report_reader import LocalReportReader
from synthesis_engine.generative_analysis import _SENSITIVE_INPUT

from orchestrator_service.canonical_history import select_canonical_history
from shared.model_inference import ModelInferencePort
from shared.model_tool_loop import (
    ToolAuthorization,
    ToolCall,
    ToolLoopContext,
    ToolLoopOutcome,
    ToolObservation,
    call_fingerprint,
    run_tool_loop,
)
from shared.types import PermissionDecision


@dataclass(frozen=True)
class ModelToolLoopConfig:
    """Trusted host opt-in; neither a model field nor an operator identity proof."""

    port: ModelInferencePort = field(repr=False)
    model: str
    reader: LocalReportReader = field(repr=False)
    expected_provider_id: str = "fixture"
    expected_evidence_mode: str = "fixture"
    timeout_seconds: float = 30.0
    max_tool_calls: int = 3
    cancellation: Event | None = field(default=None, repr=False)
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    include_canonical_history: bool = False

    def __post_init__(self):
        for value in (self.model, self.expected_provider_id):
            if (type(value) is not str or not 1 <= len(value) <= 160
                    or any(not 33 <= ord(c) <= 126 for c in value)):
                raise ValueError("invalid_tool_loop_configuration")
        if (not callable(getattr(self.port, "infer", None))
                or not isinstance(self.reader, LocalReportReader)
                or not 1 <= len(self.reader.resource_ids) <= 3
                or self.expected_evidence_mode not in {"fixture", "injected_transport", "live"}
                or type(self.timeout_seconds) not in {float, int}
                or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 120
                or type(self.max_tool_calls) is not int or not 1 <= self.max_tool_calls <= 3
                or (self.cancellation is not None and not isinstance(self.cancellation, Event))
                or type(self.include_canonical_history) is not bool
                or not callable(self.clock)):
            raise ValueError("invalid_tool_loop_configuration")


def _config_binding(config):
    return (
        id(config.port), config.model, id(config.reader),
        config.reader.configuration_fingerprint, tuple(config.reader.resource_ids),
        config.expected_provider_id, config.expected_evidence_mode,
        config.timeout_seconds, config.max_tool_calls, id(config.cancellation), id(config.clock),
        config.include_canonical_history,
    )


def run_core_tool_loop(core, config, contract, value, *, emit):
    """Recheck native governance and an exact ephemeral authorization before reads.

    Read-only results are not facts or grants. No effects are replayed and no
    crash-safe resumption is claimed. Ordinary canonical final/event persistence
    remains owned by handle_input after synthesis.
    """
    def withheld(code="scope_denied"):
        return ToolLoopOutcome(status="withheld", error_code=code), None

    if type(config) is not ModelToolLoopConfig:
        return withheld("invalid_configuration")
    try:
        if (not core.synthesis_engine.model_tool_loop_eligible(value)
                or contract.adapter_action_request is not None
                or value.reviewed_knowledge is not None):
            return withheld()
        if _SENSITIVE_INPUT.search(contract.content):
            return ToolLoopOutcome(status="refused", error_code="input_sensitive"), None
        configuration = _config_binding(config)
        execution_deadline = time.monotonic() + config.timeout_seconds
        engine, governance = core.synthesis_engine, core.governance_service
        memory, repository = core.memory_service, core.memory_service.repository

        def binding():
            # Hashes bind private identity; they do not anonymize it. They never
            # replace the Core's actual subject/permission checks.
            payload = [asdict(contract), asdict(value), configuration]
            return hashlib.sha256(json.dumps(
                payload, ensure_ascii=True, sort_keys=True, allow_nan=False, default=str,
                separators=(",", ":"),
            ).encode("ascii")).hexdigest()

        selected_binding = binding()

        def eligible():
            return (
                core.model_tool_loop is config
                and core.synthesis_engine is engine and core.governance_service is governance
                and core.memory_service is memory and memory.repository is repository
                and _config_binding(config) == configuration
                and binding() == selected_binding
                and engine.model_tool_loop_eligible(value)
            )

        def validate_publication():
            # The leaf's budget ends before native synthesis. Keep the original
            # deadline and consent/binding guards through actual publication.
            try:
                if not eligible():
                    return "context_changed"
                if config.cancellation is not None and config.cancellation.is_set():
                    return "cancelled"
                if time.monotonic() >= execution_deadline:
                    return "timed_out"
                return None
            except Exception:
                return "context_changed"

        def interruption():
            code = validate_publication()
            if code is None:
                return None
            return ToolLoopOutcome(
                status=code if code in {"cancelled", "timed_out"} else "refused",
                error_code=code,
            ), None

        history = ()
        if config.include_canonical_history:
            stopped = interruption()
            if stopped is not None:
                return stopped
            # This is a known-subject local composition, not authentication.
            # Never fall back to a session summary or a differently bound user.
            if (type(contract.user_id) is not str or not contract.user_id.strip()
                    or contract.user_id != contract.canonical_user_ref):
                return withheld("history_scope_denied")
            try:
                rows = repository.fetch_recent_turns(str(contract.session_id), 6)
            except Exception:
                return ToolLoopOutcome(status="failed", error_code="history_unavailable"), None
            stopped = interruption()
            if stopped is not None:
                return stopped
            try:
                history = select_canonical_history(
                    rows, subject_id=contract.user_id, session_id=str(contract.session_id),
                )
            except Exception:
                return ToolLoopOutcome(status="failed", error_code="history_unavailable"), None
            stopped = interruption()
            if stopped is not None:
                return stopped
            emit("model_tool_loop_history_selected", {
                "inspected_count": len(rows), "selected_count": len(history),
                "excluded_count": len(rows) - len(history),
                "character_count": sum(len(item.query) + len(item.response) for item in history),
                "authority": "none",
            })
            stopped = interruption()
            if stopped is not None:
                return stopped

        context = ToolLoopContext(
            request_id=str(contract.request_id), query=contract.content,
            binding_id=selected_binding, resource_ids=tuple(config.reader.resource_ids),
            history=history,
        )

        def authorize(call: ToolCall):
            fingerprint = call_fingerprint(context, call)
            if (not eligible() or call.tool != "read_local_report"
                    or call.resource_id not in context.resource_ids):
                return ToolAuthorization("block", fingerprint)
            assessment = governance.assess_model_tool_call(
                contract, context=context, call=call, plan=value.deliberative_plan,
                approved_resource_ids=context.resource_ids, requested_by_service=core.name,
                identity_mode=value.identity_mode,
                identity_signature=value.identity_profile.identity_signature,
                response_style=value.response_style,
            )
            decision = assessment.governance_decision.decision
            emit("model_tool_loop_governance_checked", {
                "decision": decision.value, "call_fingerprint": fingerprint,
                "tool": call.tool, "authority": "core_policy",
                "governance_check_id": str(assessment.governance_check.governance_check_id),
                "governance_decision_id": str(assessment.governance_decision.decision_id),
                "subject_type": assessment.governance_check.subject_type,
                "resource_id_sha256": hashlib.sha256(call.resource_id.encode("ascii")).hexdigest(),
            })
            if not eligible():
                return ToolAuthorization("block", fingerprint)
            return ToolAuthorization(decision.value, fingerprint)

        consumed = set()

        def execute(call: ToolCall, authorization: ToolAuthorization):
            fingerprint = call_fingerprint(context, call)
            if (not eligible() or authorization.decision != PermissionDecision.ALLOW.value
                    or authorization.fingerprint != fingerprint or fingerprint in consumed
                    or call.tool != "read_local_report"
                    or call.resource_id not in context.resource_ids):
                raise ValueError("tool_authorization_refused")
            # Consume before invoking the adapter. A failure is never retried by
            # this executor; the next turn requires a new normal Core request.
            consumed.add(fingerprint)
            text = config.reader.read(
                call.resource_id, cancellation=config.cancellation,
                deadline_monotonic=execution_deadline,
            )
            if (not eligible() or type(text) is not str or not text.strip()
                    or len(text.encode("utf-8", errors="strict")) > 8192
                    or _SENSITIVE_INPUT.search(text)):
                raise ValueError("tool_observation_refused")
            return ToolObservation(
                call_id=call.call_id, tool=call.tool, resource_id=call.resource_id,
                fingerprint=fingerprint, text=text,
            )

        stopped = interruption()
        if stopped is not None:
            return stopped
        remaining = execution_deadline - time.monotonic()
        if remaining <= 0:
            return ToolLoopOutcome(status="timed_out", error_code="timed_out"), None
        outcome = run_tool_loop(
            config.port, model=config.model, context=context,
            authorize=authorize, execute=execute, eligible=eligible, emit=emit,
            expected_provider_id=config.expected_provider_id,
            expected_evidence_mode=config.expected_evidence_mode,
            timeout_seconds=min(config.timeout_seconds, remaining),
            max_tool_calls=config.max_tool_calls,
            cancellation=config.cancellation, clock=config.clock,
        )
        if not eligible():
            return ToolLoopOutcome(status="refused", error_code="context_changed"), None
        if (outcome.status == "completed"
                and (_SENSITIVE_INPUT.search(outcome.analysis)
                     or any(_SENSITIVE_INPUT.search(c.quote) for c in outcome.citations))):
            return ToolLoopOutcome(status="refused", error_code="output_sensitive"), None
        return outcome, validate_publication
    except Exception:
        return ToolLoopOutcome(status="failed", error_code="tool_loop_unavailable"), None
