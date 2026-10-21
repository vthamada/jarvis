"""Explicit local HTTP model -> Core -> selected read-only reports -> canonical final.

Loopback selects a destination, not private/local weights: the selected server may
forward prompts and report text to cloud providers. No discovery, model startup,
download, credentials, account access, fallback or operation dispatch is provided.
"""

from __future__ import annotations

import argparse
import json
import re
from math import isfinite
from pathlib import Path
from threading import Event

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.model_tool_loop_cli import _run_report_loop
from apps.jarvis_console.review_input import _requires_redaction, read_review_input
from apps.jarvis_console.runtime import ConsoleRuntime

INPUT_SCHEMA = "jarvis-local-model-tool-loop-v1"
OUTPUT_SCHEMA = "jarvis-local-model-tool-loop-result-v1"
_PROVIDER_ID = "chat_completions_local"
_PHASE_FIELDS = frozenset({"event", "phase", "elapsed_ms", "timing_mode"})
_TRANSPORT_PHASES = frozenset({
    "connect_complete", "request_sent", "first_byte", "headers_validated",
    "body_complete", "peer_closed",
})


class _PhaseDiagnostics:
    """Bounded best-effort host observations, never canonical or model evidence.

    Each component restarts its cumulative clock for every inference operation.
    Samples from different components/operations must not be subtracted as one
    span. An injected port may produce no observations; an empty list does not
    certify that an HTTP request, local weights or a real model ran.
    """

    def __init__(self):
        self._events = []

    def observer(self, component):
        if type(component) is not str or component not in {"transport", "provider"}:
            _invalid()
        phases = (_TRANSPORT_PHASES if component == "transport"
                  else frozenset({"provider_parse_complete"}))

        def collect(value):
            # Four bounded inference operations, six transport phases and one
            # provider phase each. Copy only exact primitive allowlisted fields.
            if (len(self._events) >= 28 or type(value) is not dict
                    or set(value) != _PHASE_FIELDS
                    or type(value["event"]) is not str
                    or value["event"] != "local_inference_phase"
                    or type(value["phase"]) is not str or value["phase"] not in phases
                    or type(value["elapsed_ms"]) is not int
                    or not 0 <= value["elapsed_ms"] <= 120_000
                    or type(value["timing_mode"]) is not str
                    or value["timing_mode"] not in {"live", "injected_clock"}):
                return
            self._events.append({
                "component": component, "event": "local_inference_phase",
                "phase": value["phase"], "elapsed_ms": value["elapsed_ms"],
                "timing_mode": value["timing_mode"],
            })

        return collect

    def snapshot(self):
        return [dict(event) for event in self._events]


def _invalid():
    raise ValueError("invalid_local_model_tool_loop_input")


def _host_selection(*, reports, authorized, confirmed, reports_confirmed,
                    upstream_egress_acknowledged, session_id, model, endpoint,
                    timeout_seconds, include_content, core_factory=None,
                    port_factory=None, cancellation=None, phase_observer=None):
    if (authorized is not True or confirmed is not True or reports_confirmed is not True
            or upstream_egress_acknowledged is not True
            or type(session_id) is not str
            or re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", session_id) is None
            or type(model) is not str or not 1 <= len(model) <= 160
            or any(not 33 <= ord(c) <= 126 for c in model) or "://" in model
            or type(timeout_seconds) not in {int, float} or not isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 120 or type(include_content) is not bool
            or type(reports) is not dict or not 1 <= len(reports) <= 3
            or (core_factory is not None and not callable(core_factory))
            or (port_factory is not None and not callable(port_factory))
            or (phase_observer is not None and not callable(phase_observer))
            or (cancellation is not None and not isinstance(cancellation, Event))):
        _invalid()
    ensure_src_paths()
    from inference_service.local_chat_transport import LocalChatHttpTransport
    from operational_service.adapters.local_report_reader import LocalReportReader

    # Both constructors are lexical/inert: no DNS, socket, stat or report read.
    # Even trusted test seams cannot bypass validation of the host destination.
    transport = LocalChatHttpTransport(endpoint=endpoint, phase_observer=phase_observer)
    reader = LocalReportReader(dict(reports))
    return transport, reader


def analyze_local_reports(document, *, reports, endpoint, model, session_id,
                          authorized=False, confirmed=False, reports_confirmed=False,
                          upstream_egress_acknowledged=False, timeout_seconds=30,
                          include_content=False, core_factory=None, port_factory=None,
                          cancellation=None, include_canonical_history=False,
                          include_phase_diagnostics=False, structured_tool_output=False,
                          hermes_context=False):
    """Explicit host composition; input/model fields never select network targets.

    ``port_factory(endpoint, model)`` is a trusted injected-transport test seam,
    not live-model evidence. Default ``live`` means actual local socket I/O only.
    Native Core admission remains before any inference or selected report read.
    Diagnostics are a separate host opt-in, never input/model-selected, and are
    returned as content-free metadata rather than stored in canonical memory.
    Structured output is another host opt-in for the default provider only:
    request a phase-bound fixed schema, without trusting endpoint compliance.
    Hermes context is a separate default-off wire replay experiment. It does
    not import the Hermes loop, retrieve memory or change the native tool protocol.
    """
    try:
        if (type(include_canonical_history) is not bool
                or type(include_phase_diagnostics) is not bool
                or type(structured_tool_output) is not bool
                or type(hermes_context) is not bool
                or ((structured_tool_output or hermes_context) and port_factory is not None)):
            _invalid()
        diagnostics = _PhaseDiagnostics() if include_phase_diagnostics else None
        transport, reader = _host_selection(
            reports=reports, endpoint=endpoint, model=model, session_id=session_id,
            authorized=authorized, confirmed=confirmed, reports_confirmed=reports_confirmed,
            upstream_egress_acknowledged=upstream_egress_acknowledged,
            timeout_seconds=timeout_seconds, include_content=include_content,
            core_factory=core_factory, port_factory=port_factory, cancellation=cancellation,
            phase_observer=(diagnostics.observer("transport") if diagnostics else None),
        )
        if (type(document) is not dict or set(document) != {"schema_version", "query"}
                or type(document["schema_version"]) is not str
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
        from inference_service.chat_completions_provider import ChatCompletionsInferenceProvider

        if port_factory is None:
            port = ChatCompletionsInferenceProvider(
                model=model, transport=transport, evidence_mode="live",
                phase_observer=(diagnostics.observer("provider") if diagnostics else None),
                structured_tool_output=structured_tool_output,
                hermes_context=hermes_context,
            )
            expected_evidence = "live"
        else:
            port = port_factory(endpoint, model)
            expected_evidence = "injected_transport"
            if (type(port.evidence_mode) is not str
                    or port.evidence_mode != expected_evidence):
                _invalid()
        # The default provider does not expose public evidence_mode metadata.
        # Its constructor bound the host-selected mode; only injected factories
        # declare metadata, and they cannot turn that declaration into live proof.
        if (type(port.provider_id) is not str or port.provider_id != _PROVIDER_ID
                or not callable(getattr(port, "infer", None))):
            _invalid()
        result = _run_report_loop(
            query, reader=reader, port=port, session_id=session_id, model=model,
            timeout_seconds=timeout_seconds, include_content=include_content,
            core_factory=core_factory, redactor=redactor, output_schema=OUTPUT_SCHEMA,
            cancellation=cancellation, expected_provider_id=_PROVIDER_ID,
            expected_evidence_mode=expected_evidence,
            include_canonical_history=include_canonical_history,
        )
        result.update(
            provider_id=_PROVIDER_ID, endpoint_scope="numeric_loopback_http",
            upstream_egress_possible=True, real_model_verified=False,
            local_weights_verified=False, account_used=False,
        )
        if diagnostics is not None:
            result.update(
                phase_diagnostics=diagnostics.snapshot(),
                phase_diagnostics_clock_scope="per_component_operation",
            )
        if structured_tool_output:
            result.update(structured_output_requested=True,
                          structured_output_schema="jarvis_tool_loop_v1")
        if hermes_context:
            result.update(hermes_context_requested=True,
                          hermes_context_scope="adapted_text_replay")
        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False)
        if len(encoded) > 262144 or redactor.redact(encoded)[1]:
            _invalid()
        return result
    except Exception:
        raise ValueError("invalid_local_model_tool_loop_input") from None


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        _invalid()


def main(argv=None):
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--confirm-input", action="store_true", required=True)
    parser.add_argument("--confirm-reports", action="store_true", required=True)
    parser.add_argument(
        "--acknowledge-upstream-egress", action="store_true", required=True,
        help="Acknowledge the local server may send query/report text to cloud providers.",
    )
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--report", action="append", required=True, metavar="ID=ABSOLUTE_PATH")
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--include-content", action="store_true")
    parser.add_argument(
        "--structured-tool-output", action="store_true",
        help=("Request the fixed local report-proposal JSON schema. Core still validates "
              "all tools and citations; no JSON repair, retries or native tools."),
    )
    parser.add_argument(
        "--hermes-context", action="store_true",
        help=("Experiment with the pinned Hermes-derived text replay of canonical history "
              "and current progress. No Hermes dispatcher or separate memory store."),
    )
    parser.add_argument(
        "--include-phase-diagnostics", action="store_true",
        help=("Return bounded content-free host phase samples; transport/provider "
              "clocks are separate per operation, not proof of a real model."),
    )
    parser.add_argument(
        "--include-canonical-history", action="store_true",
        help="Send bounded same-subject/session canonical history to the selected server.",
    )
    try:
        args = parser.parse_args(argv)
        reports = {}
        for selection in args.report:
            resource_id, separator, location = selection.partition("=")
            if not separator or resource_id in reports:
                _invalid()
            reports[resource_id] = Path(location)
        options = dict(
            reports=reports, endpoint=args.endpoint, model=args.model, session_id=args.session_id,
            authorized=args.authorized, confirmed=args.confirm_input,
            reports_confirmed=args.confirm_reports,
            upstream_egress_acknowledged=args.acknowledge_upstream_egress,
            timeout_seconds=args.timeout_seconds, include_content=args.include_content,
        )
        _host_selection(**options)  # Refuse invalid host choices before consuming stdin.
        result = analyze_local_reports(
            read_review_input(), **options,
            include_canonical_history=args.include_canonical_history,
            include_phase_diagnostics=args.include_phase_diagnostics,
            structured_tool_output=args.structured_tool_output,
            hermes_context=args.hermes_context,
        )
        print(json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"cancelled","authority":"none"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"invalid_local_model_tool_loop_input"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
