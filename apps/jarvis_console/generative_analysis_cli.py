"""Explicit bounded model analysis through canonical Core; no login or refresh."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.review_input import _requires_redaction, read_review_input
from apps.jarvis_console.runtime import ConsoleRuntime

INPUT_SCHEMA = "jarvis-generative-analysis-v1"
OUTPUT_SCHEMA = "jarvis-generative-analysis-result-v1"


def _invalid():
    raise ValueError("invalid_generative_analysis_input")


def _validate_options(authorized, confirmed, session_id, model, credential_dir, profile_ref,
                      timeout_seconds, include_content, core_factory=None, port_factory=None):
    if (authorized is not True or confirmed is not True
            or type(session_id) is not str
            or re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", session_id) is None
            or type(include_content) is not bool
            or type(model) is not str or not 1 <= len(model) <= 160
            or any(ord(c) < 33 or ord(c) > 126 for c in model)
            or type(profile_ref) is not str
            or re.fullmatch(r"profile-[0-9a-f]{64}", profile_ref) is None
            or not isinstance(credential_dir, Path) or not credential_dir.is_absolute()
            or type(timeout_seconds) not in {int, float}
            or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 120
            or (core_factory is not None and not callable(core_factory))
            or (port_factory is not None and not callable(port_factory))):
        _invalid()


def _session_factory(credential_dir, profile_ref, model, *, telemetry=None):
    from inference_service.credential_store import SiwcCredentialStore
    from inference_service.oauth_http import SiwcHttpsClient
    from inference_service.session_inference_port import SessionInferencePort
    from inference_service.siwc_session import SiwcSession

    store = SiwcCredentialStore(credential_dir, authorized=True)
    selected = store.load_profile(profile_ref)
    session = SiwcSession(
        host_id=store.host_id(), client=SiwcHttpsClient(authorized=True), store=store,
    )
    session.load(client_id=selected.client_id, subject=selected.subject)
    options = dict(model=model, authorized=True)
    if telemetry is not None:
        options["telemetry"] = telemetry
    return SessionInferencePort(session, **options)


def analyze_document(document, *, authorized=False, confirmed=False, session_id,
                     model, credential_dir, profile_ref, timeout_seconds=30,
                     include_content=False, core_factory=None, port_factory=None):
    """Consent and strict input before storage; catalog is lazy after Core ALLOW.

    Factory injection is a trusted test seam, not an authenticated operator or
    live-model acceptance. The canonical persisted final is mandatory readback.
    """
    try:
        _validate_options(authorized, confirmed, session_id, model, credential_dir, profile_ref,
                          timeout_seconds, include_content, core_factory, port_factory)
        if (type(document) is not dict
                or set(document) != {"schema_version", "query"}
                or document["schema_version"] != INPUT_SCHEMA
                or type(document["query"]) is not str
                or not 1 <= len(document["query"]) <= 2048
                or not document["query"].strip()
                or any(ord(c) < 32 and c not in "\r\n\t" for c in document["query"])):
            _invalid()
        query = document["query"]
        query.encode("utf-8", errors="strict")
        ensure_src_paths()
        from executive_engine.engine import ExecutiveEngine
        from synthesis_engine.engine import SynthesisEngine

        from shared.contracts import InputContract
        from shared.types import ChannelType, InputType, RequestId, SessionId

        redactor = ConsoleRuntime(
            output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
        )
        if _requires_redaction(query, redactor):
            _invalid()
        request_id = "req-generative-analysis-" + uuid4().hex
        principal = "user://local_operator"
        contract = InputContract(
            request_id=RequestId(request_id), session_id=SessionId(session_id),
            channel=ChannelType.CONSOLE, input_type=InputType.TEXT, content=query,
            timestamp=datetime.now(UTC).isoformat(), user_id=principal,
            canonical_user_ref=principal,
            surface_id="surface://local-generative-analysis", surface_kind="console",
            surface_session_id=session_id, operator_identity_ref="operator://local_console",
            requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
        )
        directive = ExecutiveEngine().direct(contract)
        if (directive.intent != "analysis" or directive.requires_clarification
                or directive.should_execute_operation):
            _invalid()
        from apps.jarvis_console.source_review_cli import _default_core_factory

        port = (port_factory or _session_factory)(credential_dir, profile_ref, model)
        # Expected evidence is chosen by composition, never model output.
        if (port.provider_id != "responses_plan"
                or port.evidence_mode not in {"injected_transport", "live"}):
            _invalid()
        core = (core_factory or _default_core_factory)()
        core.synthesis_engine = SynthesisEngine(
            generative_port=port, generative_model=model,
            generative_provider_id=port.provider_id, generative_evidence_mode=port.evidence_mode,
            generative_timeout_seconds=timeout_seconds,
        )
        response = core.handle_input(contract)
        if (response.request_id != request_id or response.session_id != session_id
                or response.intent != "analysis"
                or any(getattr(response, name, False) is not None for name in (
                    "operation_dispatch", "operation_result", "adapter_grant",
                    "adapter_grant_claim", "action_confirmation_claim",
                    "action_confirmation_challenge", "adapter_action_intent",
                ))):
            _invalid()
        turns = core.memory_service.repository.fetch_recent_turns(session_id, 10)
        if not turns:
            _invalid()
        turn = turns[-1]
        if (turn.session_id != session_id or turn.user_id != principal
                or turn.request_content != query or turn.response_text != response.response_text
                or turn.intent != "analysis"
                or turn.timestamp != response.memory_record.timestamp
                or response.memory_record.session_id != session_id
                or response.memory_record.user_id != principal
                or response.memory_record.record_type != "interaction_turn"
                or response.memory_record.payload.get("response_text") != turn.response_text):
            _invalid()
        events = [event for event in response.events if event.event_name == "response_synthesized"]
        if len(events) != 1:
            _invalid()
        event = events[0]
        stored = core.observability_service.repository.list_events(
            limit=10, event_names=("governance_checked", "response_synthesized", "memory_recorded"),
            request_id=request_id, session_id=session_id,
        )
        matching = [item for item in stored if item.event_id == event.event_id]
        if len(matching) != 1 or matching[0].payload != event.payload:
            _invalid()
        if (len(stored) != 3
                or {item.event_name for item in stored} != {
                    "governance_checked", "response_synthesized", "memory_recorded",
                }):
            _invalid()
        by_name = {item.event_name: item.payload for item in stored}
        if (by_name["memory_recorded"].get("memory_record_id")
                != response.memory_record.memory_record_id
                or by_name["governance_checked"].get("decision")
                != response.governance_decision.decision.value):
            _invalid()
        metadata = event.payload
        status = metadata.get("generative_status")
        if status not in {"accepted", "withheld", "rejected"}:
            _invalid()
        payload = {
            "schema_version": OUTPUT_SCHEMA, "status": "recorded", "authority": "none",
            "operator_authenticated": False, "runtime_capability_promoted": False,
            "canonical_turn_recorded": True, "operation_dispatched": False,
            "governance_decision": response.governance_decision.decision.value,
            "generative_status": status,
            "generative_error_code": metadata.get("generative_error_code"),
            "generative_evidence_mode": metadata.get("generative_evidence_mode"),
            "generative_analysis_characters": metadata.get("generative_analysis_characters"),
            "response_character_count": len(turn.response_text),
            "content_included": False, "content_withheld": False,
        }
        if include_content:
            if _requires_redaction(turn.response_text, redactor):
                payload["content_withheld"] = True
            else:
                payload.update(response_text=turn.response_text, content_included=True)
        encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False)
        if len(encoded) > 262144 or redactor.redact(encoded)[1]:
            _invalid()
        return payload
    except Exception:
        raise ValueError("invalid_generative_analysis_input") from None


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        _invalid()


def main(argv=None):
    parser = _SafeParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--confirm-input", action="store_true", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--credential-dir", type=Path, required=True)
    parser.add_argument("--profile-ref", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--include-content", action="store_true")
    try:
        args = parser.parse_args(argv)
        _validate_options(
            args.authorized, args.confirm_input, args.session_id, args.model,
            args.credential_dir, args.profile_ref, args.timeout_seconds, args.include_content,
        )
        payload = analyze_document(
            read_review_input(), authorized=args.authorized, confirmed=args.confirm_input,
            session_id=args.session_id, model=args.model, credential_dir=args.credential_dir,
            profile_ref=args.profile_ref, timeout_seconds=args.timeout_seconds,
            include_content=args.include_content,
        )
        print(json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"cancelled","authority":"none"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"invalid_generative_analysis_input"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
