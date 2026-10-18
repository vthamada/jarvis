"""Explicit local composition; synthetic inference, actual isolated canonical Core."""

import json
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
from operational_service.adapters.local_report_reader import LocalReportReader

from apps.jarvis_console import local_model_tool_loop_cli as module
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

MODEL = "synthetic-local-cli-model"
ENDPOINT = "http://127.0.0.1:11434/v1/chat/completions"
QUERY = "Compare documentation and observability pilot reports."
REPORT = "LOCAL_CLI_REPORT_SENTINEL: Documentation records the pilot outcome."
ANALYSIS = "LOCAL_CLI_ANALYSIS_SENTINEL: The report records the pilot outcome."


def _document(query=QUERY):
    return {"schema_version": module.INPUT_SCHEMA, "query": query}


def _options(tmp_path):
    return dict(
        authorized=True, confirmed=True, reports_confirmed=True,
        upstream_egress_acknowledged=True, endpoint=ENDPOINT, model=MODEL,
        session_id="local-model-cli-session", reports={"documentation": tmp_path / "report.txt"},
    )


def _forbidden(*_args, **_kwargs):
    pytest.fail("refused composition attempted Core, report, provider or account I/O")


class _Port:
    provider_id = "chat_completions_local"
    evidence_mode = "injected_transport"

    def __init__(self):
        self.requests = []
        self.after_infer = lambda: None
        self.selected_model = None
        self.status = "completed"

    def infer(self, request, *, cancellation=None):
        self.requests.append(request)
        if len(self.requests) == 1:
            proposal = {"kind": "tool_call", "call_id": "read-1", "tool": "read_local_report",
                        "arguments": {"resource_id": "documentation"}}
        elif len(self.requests) == 2:
            proposal = {"kind": "final", "analysis": ANALYSIS,
                        "citations": [{"call_id": "read-1", "quote": REPORT}]}
        else:
            pytest.fail("unexpected additional inference")
        self.after_infer()
        return InferenceResult(
            request_id=request.request_id, model=self.selected_model or request.model,
            provider_id=self.provider_id, status=self.status,
            text=json.dumps(proposal) if self.status == "completed" else "",
            error_code=None if self.status == "completed" else "timeout",
            evidence_mode=self.evidence_mode,
        )


def _composition(tmp_path):
    options = _options(tmp_path)
    options["reports"]["documentation"].write_text(REPORT, encoding="utf-8")
    core, port, selections = _isolated_core(tmp_path / "runtime"), _Port(), []

    def factory(endpoint, model):
        selections.append((endpoint, model))
        return port

    return options, core, port, factory, selections


@pytest.mark.parametrize("field,value", [
    ("authorized", False), ("authorized", 1), ("confirmed", False), ("confirmed", 1),
    ("reports_confirmed", False), ("reports_confirmed", 1),
    ("upstream_egress_acknowledged", False), ("upstream_egress_acknowledged", 1),
    ("session_id", ""), ("session_id", "a/b"), ("session_id", "a" * 81),
    ("model", ""), ("model", "two models"), ("model", "é"), ("model", "https://model"),
    ("model", "a" * 161), ("timeout_seconds", 0), ("timeout_seconds", 121),
    ("timeout_seconds", True), ("timeout_seconds", float("nan")),
    ("timeout_seconds", float("inf")), ("include_content", 1), ("cancellation", object()),
    ("endpoint", "http://localhost:11434/v1/chat/completions"),
    ("endpoint", "https://127.0.0.1:11434/v1/chat/completions"),
    ("endpoint", "http://192.0.2.1:11434/v1/chat/completions"),
    ("endpoint", "http://127.0.0.1:11434/v1/chat/completions?private=yes"),
    ("endpoint", "http://127.0.0.1:11434/v1/responses"),
    ("endpoint", "http://token@127.0.0.1:11434/v1/chat/completions"),
    ("endpoint", "http://127.0.0.1/v1/chat/completions"), ("endpoint", None),
    ("core_factory", False), ("port_factory", False),
])
def test_invalid_host_options_refuse_before_core_or_provider(tmp_path, monkeypatch, field, value):
    options = _options(tmp_path)
    options.update(core_factory=_forbidden, port_factory=_forbidden)
    options[field] = value
    monkeypatch.setattr(LocalReportReader, "read", _forbidden)
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        module.analyze_local_reports(_document(), **options)
    assert not (tmp_path / "runtime").exists()
    assert not options["reports"]["documentation"].exists()


@pytest.mark.parametrize("case", [
    "empty", "four", "list", "id", "relative", "string", "stream", "parent",
])
def test_invalid_catalog_refuses_before_factories(tmp_path, case):
    path = tmp_path / "report.txt"
    options = _options(tmp_path)
    options["reports"] = {
        "empty": {}, "four": {f"report-{n}": path for n in range(4)},
        "list": [("documentation", path)], "id": {"../escape": path},
        "relative": {"documentation": Path("report.txt")},
        "string": {"documentation": str(path)},
        "stream": {"documentation": tmp_path / "report.txt:secret"},
        "parent": {"documentation": tmp_path / ".." / "report.txt"},
    }[case]
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        module.analyze_local_reports(_document(), **options,
                                     core_factory=_forbidden, port_factory=_forbidden)
    assert not path.exists()


@pytest.mark.parametrize("document", [
    None, [], {}, {"query": QUERY}, {"schema_version": "jarvis-model-tool-loop-v1", "query": QUERY},
    {"schema_version": module.INPUT_SCHEMA, "query": ""},
    {"schema_version": module.INPUT_SCHEMA, "query": " "},
    {"schema_version": module.INPUT_SCHEMA, "query": "x" * 2049},
    {"schema_version": module.INPUT_SCHEMA, "query": "\ud800"},
    {"schema_version": module.INPUT_SCHEMA, "query": "query\x00"},
    {"schema_version": module.INPUT_SCHEMA, "query": QUERY, "endpoint": ENDPOINT},
    {"schema_version": module.INPUT_SCHEMA, "query": QUERY, "model": "another-model"},
    {"schema_version": module.INPUT_SCHEMA, "query": QUERY, "authorized": True},
    {"schema_version": module.INPUT_SCHEMA, "query": QUERY, "tools": []},
])
def test_document_cannot_select_provider_or_authority(tmp_path, document):
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        module.analyze_local_reports(document, **_options(tmp_path),
                                     core_factory=_forbidden, port_factory=_forbidden)


@pytest.mark.parametrize("query", [
    "Compare reports. password=synthetic-secret", "Compare reports at C:/private/report.txt",
    "Compare reports. Bearer synthetic-secret-token",
])
def test_sensitive_query_refuses_without_factories_or_reads(tmp_path, monkeypatch, query):
    monkeypatch.setattr(LocalReportReader, "read", _forbidden)
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        module.analyze_local_reports(_document(query), **_options(tmp_path),
                                     core_factory=_forbidden, port_factory=_forbidden)


@pytest.mark.parametrize("field,value", [
    ("provider_id", "responses_plan"), ("provider_id", "fixture"),
    ("evidence_mode", "live"), ("evidence_mode", "fixture"),
    ("infer", None),
])
def test_injected_factory_cannot_forge_live_or_account_evidence(tmp_path, field, value):
    port = _Port()
    setattr(port, field, value)
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        module.analyze_local_reports(_document(), **_options(tmp_path),
                                     core_factory=_forbidden, port_factory=lambda *_: port)
    assert port.requests == []


@pytest.mark.parametrize("include_content", [False, True])
def test_composition_retains_exact_canonical_final_and_non_model_evidence(
    tmp_path, include_content,
):
    options, core, port, factory, selections = _composition(tmp_path)
    payload = module.analyze_local_reports(
        _document(), **options, core_factory=lambda: core, port_factory=factory,
        include_content=include_content,
    )
    assert payload["schema_version"] == module.OUTPUT_SCHEMA
    assert payload["status"] == "recorded" and payload["authority"] == "none"
    assert payload["model_tool_loop_status"] == "completed"
    assert payload["model_tool_loop_evidence_mode"] == "injected_transport"
    assert payload["model_tool_loop_observation_count"] == 1
    assert payload["provider_id"] == "chat_completions_local"
    assert payload["endpoint_scope"] == "numeric_loopback_http"
    assert payload["upstream_egress_possible"] is True
    for flag in ("real_model_verified", "local_weights_verified", "account_used",
                 "operator_authenticated", "runtime_capability_promoted", "operation_dispatched"):
        assert payload[flag] is False
    assert selections == [(ENDPOINT, MODEL)]
    assert len(port.requests) == 2
    assert {request.model for request in port.requests} == {MODEL}
    assert json.loads(port.requests[1].messages[0].content)["observations"][0]["text"] == REPORT
    assert core.model_tool_loop is None
    restarted = _isolated_core(tmp_path / "runtime")
    turns = restarted.memory_service.repository.fetch_recent_turns(options["session_id"], 10)
    assert len(turns) == 1 and turns[0].request_content == QUERY
    assert turns[0].user_id == "user://local_operator"
    assert GENERATIVE_ANALYSIS_MARKER in turns[0].response_text
    assert payload["response_character_count"] == len(turns[0].response_text)
    assert (payload.get("response_text") == turns[0].response_text) is include_content
    encoded = json.dumps(payload)
    assert ENDPOINT not in encoded and str(tmp_path) not in encoded
    if not include_content:
        assert QUERY not in encoded and REPORT not in encoded and ANALYSIS not in encoded
    events = restarted.observability_service.repository.list_events(
        session_id=options["session_id"], limit=100,
    )
    assert sum(event.event_name == "response_synthesized" for event in events) == 1
    metadata = json.dumps([event.payload for event in events], default=str)
    for private in (REPORT, ANALYSIS, ENDPOINT, str(tmp_path)):
        assert private not in metadata
    # Native input_received/memory retain the query by design; provider/loop
    # telemetry and final-synthesis metadata must not duplicate that content.
    telemetry = json.dumps([event.payload for event in events if (
        event.event_name.startswith("model_tool_loop_")
        or event.event_name == "response_synthesized"
    )], default=str)
    assert QUERY not in telemetry
    for request in port.requests:
        assert ENDPOINT not in request.instructions + request.messages[0].content
        assert str(tmp_path) not in request.instructions + request.messages[0].content


@pytest.mark.parametrize("query,decision", [
    ("Analyze policy evidence in read-only mode.", "defer_for_validation"),
    ("Delete every database now.", "block"),
])
def test_native_admission_prevents_any_default_http_or_report_read(
    tmp_path, monkeypatch, query, decision,
):
    from inference_service.local_chat_transport import LocalChatHttpTransport

    monkeypatch.setattr(LocalChatHttpTransport, "__call__", _forbidden)
    monkeypatch.setattr(LocalReportReader, "read", _forbidden)
    options = _options(tmp_path)
    core = _isolated_core(tmp_path / "runtime")
    payload = module.analyze_local_reports(_document(query), **options, core_factory=lambda: core)
    assert payload["governance_decision"] == decision
    assert payload["model_tool_loop_status"] == "withheld"
    assert payload["model_tool_loop_observation_count"] == 0
    assert payload["canonical_turn_recorded"] is True and core.model_tool_loop is None
    assert not options["reports"]["documentation"].exists()


@pytest.mark.parametrize("when", ["before", "during_infer"])
def test_cancellation_is_canonical_without_followup_read_or_inference(tmp_path, monkeypatch, when):
    options, core, port, factory, _ = _composition(tmp_path)
    token = Event()
    if when == "before":
        token.set()
    else:
        port.after_infer = token.set
    monkeypatch.setattr(LocalReportReader, "read", _forbidden)
    payload = module.analyze_local_reports(
        _document(), **options, core_factory=lambda: core, port_factory=factory, cancellation=token,
    )
    assert payload["model_tool_loop_status"] == "cancelled"
    assert payload["model_tool_loop_observation_count"] == 0
    assert len(port.requests) == (0 if when == "before" else 1)
    assert payload["canonical_turn_recorded"] is True and core.model_tool_loop is None


@pytest.mark.parametrize("case", ["model_mismatch", "deadline"])
def test_provider_binding_failure_or_deadline_has_no_partial_analysis(tmp_path, case):
    options, core, port, factory, _ = _composition(tmp_path)
    if case == "model_mismatch":
        port.selected_model = "unselected-model"
    else:
        port.status = "timed_out"
    payload = module.analyze_local_reports(
        _document(), **options, core_factory=lambda: core, port_factory=factory,
        include_content=True,
    )
    assert payload["model_tool_loop_status"] == ("refused" if case == "model_mismatch"
                                                 else "timed_out")
    assert payload["model_tool_loop_observation_count"] == 0
    assert len(port.requests) == 1
    assert ANALYSIS not in payload["response_text"]
    assert GENERATIVE_ANALYSIS_MARKER not in payload["response_text"]
    assert core.model_tool_loop is None


def test_exact_readback_cannot_publish_forged_final(tmp_path, monkeypatch):
    options, core, _port, factory, _ = _composition(tmp_path)
    original = core.handle_input
    monkeypatch.setattr(core, "handle_input", lambda contract:
                        replace(original(contract), response_text="forged-final"))
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        module.analyze_local_reports(_document(), **options, core_factory=lambda: core,
                                     port_factory=factory, include_content=True)
    assert core.model_tool_loop is None


def test_content_opt_in_still_withholds_sensitive_canonical_text(tmp_path, monkeypatch):
    options, core, _port, factory, _ = _composition(tmp_path)
    # Shared final projection uses its own redactor; only final text is flagged.
    from apps.jarvis_console import model_tool_loop_cli as canonical

    monkeypatch.setattr(canonical, "_requires_redaction", lambda text, _redactor: text != QUERY)
    payload = module.analyze_local_reports(
        _document(), **options, core_factory=lambda: core, port_factory=factory,
        include_content=True,
    )
    assert payload["content_withheld"] is True and payload["content_included"] is False
    assert "response_text" not in payload


def _argv(options):
    return ["--authorized", "--confirm-input", "--confirm-reports", "--acknowledge-upstream-egress",
            "--session-id", options["session_id"], "--model", options["model"],
            "--endpoint", options["endpoint"], "--report",
            "documentation=" + str(options["reports"]["documentation"])]


@pytest.mark.parametrize("case", [
    "no_authorization", "no_input", "no_reports", "no_egress", "unknown", "credential",
    "duplicate", "malformed", "endpoint", "model", "timeout", "abbreviation",
])
def test_cli_refusals_do_not_consume_stdin_or_echo_selection(tmp_path, monkeypatch, capsys, case):
    argv = _argv(_options(tmp_path))
    missing = {"no_authorization": "--authorized", "no_input": "--confirm-input",
               "no_reports": "--confirm-reports", "no_egress": "--acknowledge-upstream-egress"}
    if case in missing:
        argv.remove(missing[case])
    elif case in {"unknown", "credential"}:
        argv += ["--credential-dir" if case == "credential" else "--private-selection", "PRIVATE"]
    elif case == "duplicate":
        argv += ["--report", "documentation=" + str(tmp_path / "PRIVATE")]
    elif case == "malformed":
        argv[-1] = "PRIVATE"
    elif case == "abbreviation":
        argv[argv.index("--acknowledge-upstream-egress")] = "--acknowledge"
    else:
        flag, value = {"endpoint": ("--endpoint", "http://PRIVATE:123/v1/chat/completions"),
                       "model": ("--model", "two models"),
                       "timeout": ("--timeout-seconds", "nan")}[case]
        if flag in argv:
            argv[argv.index(flag) + 1] = value
        else:
            argv += [flag, value]
    monkeypatch.setattr(module, "read_review_input", _forbidden)
    monkeypatch.setattr(module, "analyze_local_reports", _forbidden)
    assert module.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "status": "refused", "error_code": "invalid_local_model_tool_loop_input",
    }
    assert ENDPOINT not in captured.out and str(tmp_path) not in captured.out
    assert "PRIVATE" not in captured.out


def test_cli_keyboard_interrupt_is_content_free(tmp_path, monkeypatch, capsys):
    def interrupted():
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "read_review_input", interrupted)
    assert module.main(_argv(_options(tmp_path))) == 3
    assert json.loads(capsys.readouterr().out) == {
        "status": "cancelled", "error_code": "cancelled", "authority": "none",
    }


def test_cli_default_output_is_metadata_from_canonical_composition(tmp_path, monkeypatch, capsys):
    options, core, port, factory, _ = _composition(tmp_path)
    analyze = module.analyze_local_reports

    def composed(document, **kwargs):
        return analyze(document, **kwargs, core_factory=lambda: core, port_factory=factory)

    monkeypatch.setattr(module, "analyze_local_reports", composed)
    monkeypatch.setattr(module, "read_review_input", _document)
    assert module.main(_argv(options)) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert not captured.err and payload["model_tool_loop_status"] == "completed"
    assert payload["real_model_verified"] is False and payload["account_used"] is False
    assert payload["content_included"] is False and "response_text" not in payload
    for private in (QUERY, REPORT, ANALYSIS, ENDPOINT, str(tmp_path)):
        assert private not in captured.out
    assert len(port.requests) == 2 and core.model_tool_loop is None
