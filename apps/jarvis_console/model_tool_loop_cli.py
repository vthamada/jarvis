"""Explicit report-reading model loop through Core; no login, refresh or retry."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace
from math import isfinite
from pathlib import Path
from threading import Event
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.generative_analysis_cli import _session_factory, _validate_options
from apps.jarvis_console.review_input import _requires_redaction, read_review_input
from apps.jarvis_console.runtime import ConsoleRuntime
from shared.model_inference import InferenceRequest, InferenceResult

INPUT_SCHEMA = "jarvis-model-tool-loop-v1"
OUTPUT_SCHEMA = "jarvis-model-tool-loop-result-v1"


def _invalid():
    raise ValueError("invalid_model_tool_loop_input")


class _AccountControlRefusal(Exception):
    def __init__(self, status, code):
        super().__init__(code)
        self.status = status
        self.code = code


class _LazyAccountPort:
    """Do not open even a selected account until the Core permits inference."""

    provider_id = "responses_plan"
    evidence_mode = "live"

    def __init__(self, credential_dir, profile_ref, model):
        self._selection = credential_dir, profile_ref, model
        self._port = None

    def infer(self, request, *, cancellation=None):
        if type(request) is not InferenceRequest:
            raise ValueError("invalid_account_inference_request")
        try:
            request = replace(request)
        except Exception:
            raise ValueError("invalid_account_inference_request") from None

        def refused(status, code):
            return InferenceResult(
                request.request_id, request.model, "responses_plan", status,
                error_code=code, evidence_mode="live",
            )

        def check_cancellation():
            if cancellation is None:
                return
            if not isinstance(cancellation, Event):
                raise _AccountControlRefusal("failed", "invalid_cancellation")
            cancelled = cancellation.is_set()
            if type(cancelled) is not bool:
                raise _AccountControlRefusal("failed", "invalid_cancellation")
            if cancelled:
                raise _AccountControlRefusal("cancelled", "cancelled")

        previous = None

        def now():
            nonlocal previous
            current = time.monotonic()
            if (type(current) not in {int, float} or not isfinite(current)
                    or (previous is not None and current < previous)):
                raise _AccountControlRefusal("failed", "invalid_clock")
            previous = current
            return current

        try:
            check_cancellation()
            deadline = now() + request.timeout_seconds

            def remaining():
                check_cancellation()
                budget = deadline - now()
                if budget <= 0:
                    raise _AccountControlRefusal("timed_out", "account_deadline_exceeded")
                return budget

            remaining()
            selected = self._port
            if selected is None:
                selected = _session_factory(*self._selection)
            remaining()
            if (getattr(selected, "provider_id", None) != "responses_plan"
                    or getattr(selected, "evidence_mode", None) != "live"
                    or not callable(getattr(selected, "infer", None))):
                self._port = None
                raise _AccountControlRefusal("failed", "account_binding_refused")
            budget = remaining()
            # Account loading and metadata checks belong to this round's budget.
            # Cache only after both metadata and cooperative controls are valid.
            self._port = selected
            result = selected.infer(
                replace(request, timeout_seconds=budget), cancellation=cancellation,
            )
            remaining()
            return result
        except _AccountControlRefusal as exc:
            return refused(exc.status, exc.code)
        except Exception:
            return refused("failed", "account_inference_failed")


def analyze_reports(document, *, reports, authorized=False, confirmed=False,
                    reports_confirmed=False, session_id, model, credential_dir, profile_ref,
                    timeout_seconds=30, include_content=False, core_factory=None,
                    port_factory=None, include_canonical_history=False):
    """Host-selected paths are never model arguments; consent is not authentication.

    The explicit port factory is a trusted test seam, not a credential search or
    live acceptance. Default account loading/catalog remain lazy behind Core.
    """
    try:
        _validate_options(
            authorized, confirmed, session_id, model, credential_dir, profile_ref,
            timeout_seconds, include_content, core_factory, port_factory,
        )
        if (type(include_canonical_history) is not bool
                or reports_confirmed is not True or type(reports) is not dict
                or not 1 <= len(reports) <= 3 or type(document) is not dict
                or set(document) != {"schema_version", "query"}
                or document["schema_version"] != INPUT_SCHEMA
                or type(document["query"]) is not str
                or not 1 <= len(document["query"]) <= 2048 or not document["query"].strip()
                or any(ord(c) < 32 and c not in "\r\n\t" for c in document["query"])):
            _invalid()
        query = document["query"]
        query.encode("utf-8", errors="strict")
        redactor = ConsoleRuntime(
            output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
        )
        if _requires_redaction(query, redactor):
            _invalid()
        ensure_src_paths()
        from operational_service.adapters.local_report_reader import LocalReportReader

        reader = LocalReportReader(dict(reports))  # lexical only; no report read
        port = (port_factory(credential_dir, profile_ref, model) if port_factory is not None
                else _LazyAccountPort(credential_dir, profile_ref, model))
        if (port.provider_id != "responses_plan"
                or port.evidence_mode not in {"injected_transport", "live"}):
            _invalid()
        return _run_report_loop(
            query, reader=reader, port=port, session_id=session_id, model=model,
            timeout_seconds=timeout_seconds, include_content=include_content,
            core_factory=core_factory, redactor=redactor, output_schema=OUTPUT_SCHEMA,
            include_canonical_history=include_canonical_history,
        )
    except Exception:
        raise ValueError("invalid_model_tool_loop_input") from None


def _run_report_loop(query, *, reader, port, session_id, model, timeout_seconds,
                     include_content, core_factory, redactor, output_schema,
                     cancellation=None, expected_provider_id=None, expected_evidence_mode=None,
                     include_canonical_history=False):
    """Shared canonical flow; only validated host compositions may select a port.

    Callers own provider selection, schema and input consent; neither documents
    nor model output choose them. This helper does not grant operational authority.
    """
    from datetime import UTC, datetime

    from orchestrator_service.model_tool_loop import ModelToolLoopConfig

    from apps.jarvis_console.source_review_cli import _default_core_factory
    from shared.contracts import InputContract
    from shared.types import ChannelType, InputType, RequestId, SessionId

    config = ModelToolLoopConfig(
        port=port, model=model, reader=reader,
        expected_provider_id=(port.provider_id if expected_provider_id is None
                              else expected_provider_id),
        expected_evidence_mode=(port.evidence_mode if expected_evidence_mode is None
                                else expected_evidence_mode),
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        include_canonical_history=include_canonical_history,
    )
    core = (core_factory or _default_core_factory)()
    previous = core.model_tool_loop
    if previous is not None:
        _invalid()
    principal = "user://local_operator"
    request_id = "req-model-tool-loop-" + uuid4().hex
    contract = InputContract(
        request_id=RequestId(request_id), session_id=SessionId(session_id),
        channel=ChannelType.CONSOLE, input_type=InputType.TEXT, content=query,
        timestamp=datetime.now(UTC).isoformat(), user_id=principal,
        canonical_user_ref=principal, surface_id="surface://local-model-tool-loop",
        surface_kind="console", surface_session_id=session_id,
        operator_identity_ref="operator://local_console",
        requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
    )
    core.model_tool_loop = config
    try:
        response = core.handle_input(contract)
    finally:
        core.model_tool_loop = previous
    if (response.request_id != request_id or response.session_id != session_id
            or any(getattr(response, name, False) is not None for name in (
                "operation_dispatch", "operation_result", "adapter_grant",
                "adapter_grant_claim",
                "action_confirmation_claim", "action_confirmation_challenge",
                "adapter_action_intent",
            ))):
        _invalid()
    turns = core.memory_service.repository.fetch_recent_turns(session_id, 10)
    if not turns:
        _invalid()
    turn = turns[-1]
    if (turn.session_id != session_id or turn.user_id != principal or turn.request_content != query
            or turn.response_text != response.response_text
            or turn.timestamp != response.memory_record.timestamp
            or response.memory_record.session_id != session_id
            or response.memory_record.user_id != principal
            or response.memory_record.record_type != "interaction_turn"
            or response.memory_record.payload.get("response_text") != turn.response_text):
        _invalid()
    synthesis_events = [e for e in response.events if e.event_name == "response_synthesized"]
    stored = core.observability_service.repository.list_events(
        limit=10, event_names=("response_synthesized",),
        request_id=request_id, session_id=session_id,
    )
    if (len(synthesis_events) != 1 or len(stored) != 1
            or stored[0].event_id != synthesis_events[0].event_id
            or stored[0].payload != synthesis_events[0].payload):
        _invalid()
    metadata = stored[0].payload
    status = metadata.get("model_tool_loop_status")
    if status not in {"completed", "withheld", "refused", "failed", "cancelled", "timed_out"}:
        _invalid()
    result = {
        "schema_version": output_schema, "status": "recorded", "authority": "none",
        "operator_authenticated": False, "runtime_capability_promoted": False,
        "canonical_turn_recorded": True, "operation_dispatched": False,
        "governance_decision": response.governance_decision.decision.value,
        **{key: metadata[key] for key in (
            "model_tool_loop_status", "model_tool_loop_error_code",
            "model_tool_loop_evidence_mode", "model_tool_loop_observation_count",
            "model_tool_loop_analysis_characters",
        )},
        "response_character_count": len(turn.response_text),
        "content_included": False, "content_withheld": False,
    }
    if include_content:
        if _requires_redaction(turn.response_text, redactor):
            result["content_withheld"] = True
        else:
            result.update(response_text=turn.response_text, content_included=True)
    encoded = json.dumps(result, ensure_ascii=True, allow_nan=False)
    if len(encoded) > 262144 or redactor.redact(encoded)[1]:
        _invalid()
    return result


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        _invalid()


def main(argv=None):
    parser = _SafeParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--confirm-input", action="store_true", required=True)
    parser.add_argument("--confirm-reports", action="store_true", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--credential-dir", type=Path, required=True)
    parser.add_argument("--profile-ref", required=True)
    parser.add_argument("--report", action="append", required=True, metavar="ID=ABSOLUTE_PATH")
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--include-content", action="store_true")
    parser.add_argument(
        "--include-canonical-history", action="store_true",
        help="Send bounded same-subject/session canonical history to the selected model.",
    )
    try:
        args = parser.parse_args(argv)
        reports = {}
        for selection in args.report:
            resource_id, separator, location = selection.partition("=")
            if not separator or resource_id in reports:
                _invalid()
            reports[resource_id] = Path(location)
        result = analyze_reports(
            read_review_input(), reports=reports, authorized=args.authorized,
            confirmed=args.confirm_input, reports_confirmed=args.confirm_reports,
            session_id=args.session_id, model=args.model, credential_dir=args.credential_dir,
            profile_ref=args.profile_ref, timeout_seconds=args.timeout_seconds,
            include_content=args.include_content,
            include_canonical_history=args.include_canonical_history,
        )
        print(json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"cancelled","authority":"none"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"invalid_model_tool_loop_input"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
