"""Explicit CLI composition uses synthetic inference and actual isolated Core stores."""

import json
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
from operational_service.adapters.local_report_reader import LocalReportReader

from apps.jarvis_console import model_tool_loop_cli as module
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

QUERY = "Compare documentation and observability pilot reports."
REPORT = "CLI_REPORT_SENTINEL: baseline evidence is recorded."
ANALYSIS = "CLI_ANALYSIS_SENTINEL: The selected report records baseline evidence."
MODEL = "synthetic-cli-tool-model"
PROFILE = "profile-" + "a" * 64


def _document(query=QUERY):
    return {"schema_version": module.INPUT_SCHEMA, "query": query}


def _options(tmp_path):
    return {
        "authorized": True, "confirmed": True, "reports_confirmed": True,
        "session_id": "model-tool-cli-session", "model": MODEL,
        "credential_dir": tmp_path / "unopened", "profile_ref": PROFILE,
        "reports": {"documentation": tmp_path / "selected-report.txt"},
    }


def _forbidden(*_args, **_kwargs):
    pytest.fail("a denied boundary attempted account, report, or factory I/O")


class _Port:
    provider_id = "responses_plan"
    evidence_mode = "injected_transport"

    def __init__(self):
        self.calls = []
        self.raw_outputs = []

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        if len(self.calls) == 1:
            value = {"kind": "tool_call", "call_id": "report-read-1",
                     "tool": "read_local_report",
                     "arguments": {"resource_id": "documentation"}}
        elif len(self.calls) == 2:
            value = {"kind": "final", "analysis": ANALYSIS,
                     "citations": [{"call_id": "report-read-1", "quote": REPORT}]}
        else:
            pytest.fail("the CLI attempted unexpected additional inference")
        text = json.dumps(value)
        self.raw_outputs.append(text)
        return InferenceResult(
            request_id=request.request_id, model=request.model, provider_id=self.provider_id,
            status="completed", text=text, evidence_mode=self.evidence_mode,
        )


def _composition(tmp_path, monkeypatch):
    options = _options(tmp_path)
    options["reports"]["documentation"].write_text(REPORT, encoding="utf-8")
    core = _isolated_core(tmp_path / "runtime")
    port = _Port()
    selections = []

    def factory(*selection):
        selections.append(selection)
        return port

    monkeypatch.setattr(module, "_session_factory", _forbidden)
    return options, core, port, factory, selections


@pytest.mark.parametrize("field,value", [
    ("authorized", False), ("authorized", 1), ("confirmed", False), ("confirmed", 1),
    ("reports_confirmed", False), ("reports_confirmed", 1),
    ("session_id", ""), ("session_id", "x" * 81), ("session_id", "a/b"),
    ("model", ""), ("model", "model with spaces"), ("model", "é"),
    ("profile_ref", "profile-bad"), ("profile_ref", "../private"),
    ("credential_dir", Path("relative")), ("credential_dir", "C:/private"),
    ("timeout_seconds", 0), ("timeout_seconds", 121), ("timeout_seconds", True),
    ("timeout_seconds", float("nan")), ("include_content", 1),
])
def test_invalid_options_and_missing_consents_refuse_before_any_factory(
    tmp_path, monkeypatch, field, value
):
    options = _options(tmp_path)
    options[field] = value
    monkeypatch.setattr(module, "_session_factory", _forbidden)
    monkeypatch.setattr(LocalReportReader, "read", _forbidden)
    with pytest.raises(ValueError, match="^invalid_model_tool_loop_input$"):
        module.analyze_reports(_document(), **options,
                               core_factory=_forbidden, port_factory=_forbidden)
    assert not (tmp_path / "unopened").exists()


@pytest.mark.parametrize("document", [
    {}, [], None, {"query": QUERY}, {"schema_version": "other", "query": QUERY},
    {"schema_version": module.INPUT_SCHEMA, "query": ""},
    {"schema_version": module.INPUT_SCHEMA, "query": " "},
    {"schema_version": module.INPUT_SCHEMA, "query": "x" * 2049},
    {"schema_version": module.INPUT_SCHEMA, "query": "\ud800"},
    {"schema_version": module.INPUT_SCHEMA, "query": "query\x00"},
    {"schema_version": module.INPUT_SCHEMA, "query": QUERY, "tools": []},
])
def test_invalid_input_schema_and_query_refuse_before_factories(tmp_path, document):
    with pytest.raises(ValueError, match="^invalid_model_tool_loop_input$"):
        module.analyze_reports(document, **_options(tmp_path),
                               core_factory=_forbidden, port_factory=_forbidden)


@pytest.mark.parametrize("case", [
    "empty", "too_many", "not_dict", "invalid_id", "unicode_id", "long_id",
    "relative_path", "string_path", "alternate_stream", "parent_component",
])
def test_invalid_report_catalog_is_rejected_before_account_or_core_factory(tmp_path, case):
    options = _options(tmp_path)
    path = tmp_path / "not-read.txt"
    catalogs = {
        "empty": {},
        "too_many": {f"report-{index}": path for index in range(4)},
        "not_dict": [("documentation", path)],
        "invalid_id": {"../escape": path},
        "unicode_id": {"documentação": path},
        "long_id": {"a" * 65: path},
        "relative_path": {"documentation": Path("relative.txt")},
        "string_path": {"documentation": str(path)},
        "alternate_stream": {"documentation": tmp_path / "report.txt:private"},
        "parent_component": {"documentation": tmp_path / ".." / "report.txt"},
    }
    options["reports"] = catalogs[case]
    with pytest.raises(ValueError, match="^invalid_model_tool_loop_input$"):
        module.analyze_reports(_document(), **options,
                               core_factory=_forbidden, port_factory=_forbidden)
    assert not options["credential_dir"].exists()


@pytest.mark.parametrize("query", [
    "Compare documentation. password=synthetic-secret",
    "Compare documentation at C:/private/source.txt",
])
def test_sensitive_query_never_constructs_a_port_or_core(tmp_path, query):
    with pytest.raises(ValueError, match="^invalid_model_tool_loop_input$"):
        module.analyze_reports(_document(query), **_options(tmp_path),
                               core_factory=_forbidden, port_factory=_forbidden)


@pytest.mark.parametrize("query,decision", [
    ("Analyze policy evidence in read-only mode.", "defer_for_validation"),
    ("Delete every database now.", "block"),
])
def test_default_account_is_lazy_under_native_defer_and_block(
    tmp_path, monkeypatch, query, decision
):
    core = _isolated_core(tmp_path / "runtime")
    options = _options(tmp_path)
    # Neither the report nor credential directory exists: selecting is lexical.
    monkeypatch.setattr(module, "_session_factory", _forbidden)
    monkeypatch.setattr(LocalReportReader, "read", _forbidden)
    payload = module.analyze_reports(_document(query), **options, core_factory=lambda: core)
    assert payload["status"] == "recorded"
    assert payload["governance_decision"] == decision
    assert payload["model_tool_loop_status"] == "withheld"
    assert payload["model_tool_loop_observation_count"] == 0
    assert payload["canonical_turn_recorded"] is True
    assert core.model_tool_loop is None
    assert not options["credential_dir"].exists()
    assert not options["reports"]["documentation"].exists()


@pytest.mark.parametrize("include_content", [False, True])
def test_cli_composition_reads_real_report_and_verifies_canonical_final(
    tmp_path, monkeypatch, include_content
):
    options, core, port, factory, selections = _composition(tmp_path, monkeypatch)
    payload = module.analyze_reports(
        _document(), **options, include_content=include_content,
        core_factory=lambda: core, port_factory=factory,
    )
    assert payload["schema_version"] == module.OUTPUT_SCHEMA
    assert payload["status"] == "recorded"
    assert payload["governance_decision"] == "allow"
    assert payload["model_tool_loop_status"] == "completed"
    assert payload["model_tool_loop_evidence_mode"] == "injected_transport"
    assert payload["model_tool_loop_observation_count"] == 1
    assert payload["model_tool_loop_analysis_characters"] == len(ANALYSIS)
    assert payload["authority"] == "none"
    assert payload["operator_authenticated"] is False
    assert payload["runtime_capability_promoted"] is False
    assert payload["operation_dispatched"] is False
    assert payload["canonical_turn_recorded"] is True
    assert payload["content_included"] is include_content
    assert payload["content_withheld"] is False
    assert ("response_text" in payload) is include_content
    assert selections == [(options["credential_dir"], PROFILE, MODEL)]
    assert len(port.calls) == 2
    assert port.calls[0].request_id != port.calls[1].request_id
    assert json.loads(port.calls[0].messages[0].content)["observations"] == []
    assert json.loads(port.calls[1].messages[0].content)["observations"][0]["text"] == REPORT
    assert core.model_tool_loop is None
    assert not options["credential_dir"].exists()

    restarted = _isolated_core(tmp_path / "runtime")
    turns = restarted.memory_service.repository.fetch_recent_turns(options["session_id"], 10)
    assert len(turns) == 1
    turn = turns[-1]
    assert turn.request_content == QUERY
    assert turn.user_id == "user://local_operator"
    assert GENERATIVE_ANALYSIS_MARKER in turn.response_text
    assert payload["response_character_count"] == len(turn.response_text)
    if include_content:
        assert payload["response_text"] == turn.response_text
    else:
        encoded = json.dumps(payload)
        assert REPORT not in encoded and ANALYSIS not in encoded and QUERY not in encoded

    events = restarted.observability_service.repository.list_events(
        session_id=options["session_id"], limit=100,
    )
    assert any(event.event_name == "response_synthesized" for event in events)
    metadata = json.dumps([event.payload for event in events], default=str)
    for private in (REPORT, ANALYSIS, *port.raw_outputs, str(options["credential_dir"])):
        assert private not in metadata
    for request in port.calls:
        prompt = request.instructions + request.messages[0].content
        assert str(options["reports"]["documentation"]) not in prompt
        assert str(options["credential_dir"]) not in prompt
        assert PROFILE not in prompt


def test_temporary_core_configuration_is_restored_when_handle_raises(tmp_path, monkeypatch):
    options, core, port, factory, _ = _composition(tmp_path, monkeypatch)

    def broken(_contract):
        assert core.model_tool_loop is not None
        raise RuntimeError("PRIVATE_FACTORY_FAILURE_AND_CONTENT")

    monkeypatch.setattr(core, "handle_input", broken)
    with pytest.raises(ValueError, match="^invalid_model_tool_loop_input$") as caught:
        module.analyze_reports(_document(), **options,
                               core_factory=lambda: core, port_factory=factory)
    assert "PRIVATE" not in str(caught.value)
    assert core.model_tool_loop is None
    assert port.calls == []


def test_existing_core_loop_scope_is_not_overwritten(tmp_path, monkeypatch):
    options, core, port, factory, _ = _composition(tmp_path, monkeypatch)
    previous = object()
    core.model_tool_loop = previous
    monkeypatch.setattr(core, "handle_input", _forbidden)
    with pytest.raises(ValueError, match="^invalid_model_tool_loop_input$"):
        module.analyze_reports(_document(), **options,
                               core_factory=lambda: core, port_factory=factory)
    assert core.model_tool_loop is previous
    assert port.calls == []


def test_include_content_cannot_publish_a_forged_final_over_canonical_record(tmp_path, monkeypatch):
    options, core, _port, factory, _ = _composition(tmp_path, monkeypatch)
    handle = core.handle_input
    monkeypatch.setattr(core, "handle_input", lambda contract:
                        replace(handle(contract), response_text="forged-private-final"))
    with pytest.raises(ValueError, match="^invalid_model_tool_loop_input$"):
        module.analyze_reports(_document(), **options, include_content=True,
                               core_factory=lambda: core, port_factory=factory)
    assert core.model_tool_loop is None


def _argv(options):
    return [
        "--authorized", "--confirm-input", "--confirm-reports",
        "--session-id", options["session_id"], "--model", options["model"],
        "--credential-dir", str(options["credential_dir"]),
        "--profile-ref", options["profile_ref"],
        "--report", "documentation=" + str(options["reports"]["documentation"]),
    ]


@pytest.mark.parametrize("case", [
    "unknown", "duplicate_report", "malformed_report", "no_authorized",
    "no_input_confirmation", "no_reports_confirmation",
])
def test_main_parser_refusals_are_content_free_and_do_not_read_input(
    tmp_path, monkeypatch, capsys, case
):
    options = _options(tmp_path)
    argv = _argv(options)
    if case == "unknown":
        argv.extend(["--private-argument", "PRIVATE_ARGUMENT_SENTINEL"])
    elif case == "duplicate_report":
        argv.extend(["--report", "documentation=" + str(tmp_path / "PRIVATE_REPORT_SENTINEL")])
    elif case == "malformed_report":
        argv[-1] = "PRIVATE_REPORT_SENTINEL_WITHOUT_SEPARATOR"
    else:
        flag = {"no_authorized": "--authorized", "no_input_confirmation": "--confirm-input",
                "no_reports_confirmation": "--confirm-reports"}[case]
        argv.remove(flag)
    monkeypatch.setattr(module, "read_review_input", _forbidden)
    monkeypatch.setattr(module, "analyze_reports", _forbidden)
    monkeypatch.setattr(module, "_session_factory", _forbidden)
    assert module.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "status": "refused", "error_code": "invalid_model_tool_loop_input",
    }
    assert "PRIVATE" not in captured.out
    assert str(tmp_path) not in captured.out


def test_main_prints_default_metadata_from_real_isolated_composition(tmp_path, monkeypatch, capsys):
    options, core, port, factory, _ = _composition(tmp_path, monkeypatch)
    analyze = module.analyze_reports

    def composed(document, **kwargs):
        return analyze(document, **kwargs, core_factory=lambda: core, port_factory=factory)

    monkeypatch.setattr(module, "analyze_reports", composed)
    monkeypatch.setattr(module, "read_review_input", lambda: _document())
    assert module.main(_argv(options)) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    result = json.loads(captured.out)
    assert result["model_tool_loop_status"] == "completed"
    assert result["canonical_turn_recorded"] is True
    assert result["content_included"] is False
    assert "response_text" not in result
    assert REPORT not in captured.out and ANALYSIS not in captured.out
    assert len(port.calls) == 2
    assert core.model_tool_loop is None


class _LiveDelegate:
    provider_id = "responses_plan"
    evidence_mode = "live"

    def __init__(self):
        self.calls = []
        self.after_infer = lambda: None

    def infer(self, request, *, cancellation=None):
        self.calls.append((request, cancellation))
        self.after_infer()
        return InferenceResult(
            request.request_id, request.model, self.provider_id, "completed",
            text="private completed provider output", evidence_mode=self.evidence_mode,
        )


def _lazy_request(*, request_id="lazy-request-one", timeout=30):
    return InferenceRequest(
        request_id=request_id, model=MODEL,
        messages=(InferenceMessage("user", "private request data"),),
        instructions="private fixed instructions", timeout_seconds=timeout, max_output_chars=512,
    )


def _lazy_composition(tmp_path, monkeypatch, *, elapsed=0, cancel_during_factory=None):
    clock = [0.0]
    delegate = _LiveDelegate()
    selections = []

    def factory(*selection):
        selections.append(selection)
        clock[0] += elapsed
        if cancel_during_factory is not None:
            cancel_during_factory.set()
        return delegate

    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module, "_session_factory", factory)
    lazy = module._LazyAccountPort(tmp_path / "unopened", PROFILE, MODEL)
    return lazy, delegate, clock, selections


def test_lazy_account_setup_cannot_start_delegate_after_whole_request_budget(tmp_path, monkeypatch):
    lazy, delegate, _clock, selections = _lazy_composition(tmp_path, monkeypatch, elapsed=35)
    request = _lazy_request(timeout=30)
    result = lazy.infer(request)
    assert result.status == "timed_out"
    assert result.text == ""
    assert result.request_id == request.request_id and result.model == request.model
    assert result.provider_id == "responses_plan" and result.evidence_mode == "live"
    assert len(selections) == 1
    assert delegate.calls == []
    assert lazy._port is None
    assert not (tmp_path / "unopened").exists()


def test_lazy_account_setup_is_subtracted_without_changing_request_binding(tmp_path, monkeypatch):
    lazy, delegate, _clock, selections = _lazy_composition(tmp_path, monkeypatch, elapsed=7)
    cancellation = Event()
    request = _lazy_request(timeout=30)
    result = lazy.infer(request, cancellation=cancellation)
    assert result.status == "completed"
    assert len(selections) == len(delegate.calls) == 1
    delegated, passed_cancellation = delegate.calls[0]
    assert delegated.timeout_seconds == 23
    assert replace(delegated, timeout_seconds=request.timeout_seconds) == request
    assert delegated.messages is request.messages
    assert passed_cancellation is cancellation
    assert result.request_id == request.request_id and result.model == request.model
    assert lazy._port is delegate


@pytest.mark.parametrize("when", ["before", "factory"])
def test_lazy_account_cancellation_prevents_followup_io(tmp_path, monkeypatch, when):
    cancellation = Event()
    if when == "before":
        cancellation.set()
    lazy, delegate, _clock, selections = _lazy_composition(
        tmp_path, monkeypatch, elapsed=7,
        cancel_during_factory=cancellation if when == "factory" else None,
    )
    result = lazy.infer(_lazy_request(), cancellation=cancellation)
    assert result.status == "cancelled" and result.text == ""
    assert len(selections) == (0 if when == "before" else 1)
    assert delegate.calls == []
    assert lazy._port is None


def test_lazy_cached_account_uses_each_rounds_supplied_budget_without_reloading(
    tmp_path, monkeypatch
):
    lazy, delegate, clock, selections = _lazy_composition(tmp_path, monkeypatch, elapsed=7)
    assert lazy.infer(_lazy_request(timeout=30)).status == "completed"
    clock[0] = 100
    second = _lazy_request(request_id="lazy-request-two", timeout=11)
    result = lazy.infer(second)
    assert result.status == "completed" and result.request_id == "lazy-request-two"
    assert len(selections) == 1
    assert [request.timeout_seconds for request, _ in delegate.calls] == [23, 11]


@pytest.mark.parametrize("field,value", [
    ("provider_id", "other-provider"), ("evidence_mode", "injected_transport"),
])
def test_lazy_account_invalid_metadata_is_neither_cached_nor_delegated(
    tmp_path, monkeypatch, field, value
):
    lazy, delegate, _clock, selections = _lazy_composition(tmp_path, monkeypatch)
    setattr(delegate, field, value)
    result = lazy.infer(_lazy_request())
    assert result.status == "failed" and result.text == ""
    assert result.error_code == "account_binding_refused"
    assert len(selections) == 1
    assert delegate.calls == []
    assert lazy._port is None


@pytest.mark.parametrize("boundary", ["factory", "delegate"])
def test_lazy_account_exceptions_are_content_free(tmp_path, monkeypatch, boundary):
    lazy, delegate, _clock, _selections = _lazy_composition(tmp_path, monkeypatch)

    def broken(*_args, **_kwargs):
        raise RuntimeError("PRIVATE_CREDENTIAL_PATH_AND_PROVIDER_MESSAGE")

    if boundary == "factory":
        monkeypatch.setattr(module, "_session_factory", broken)
    else:
        monkeypatch.setattr(delegate, "infer", broken)
    result = lazy.infer(_lazy_request())
    assert result.status == "failed" and result.text == ""
    assert result.error_code == "account_inference_failed"
    assert "PRIVATE" not in repr(result)


@pytest.mark.parametrize("expired", [False, True])
def test_lazy_delegate_late_completion_or_cancellation_cannot_publish_prose(
    tmp_path, monkeypatch, expired
):
    lazy, delegate, clock, _selections = _lazy_composition(tmp_path, monkeypatch)
    cancellation = Event()

    def finish_late():
        if expired:
            clock[0] = 31
        else:
            cancellation.set()

    delegate.after_infer = finish_late
    result = lazy.infer(_lazy_request(timeout=30), cancellation=cancellation)
    assert result.status == ("timed_out" if expired else "cancelled")
    assert result.text == ""
    assert len(delegate.calls) == 1
