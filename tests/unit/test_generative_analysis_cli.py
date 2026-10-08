"""Explicit opt-in command validates before I/O and returns canonical readback."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from apps.jarvis_console import generative_analysis_cli as module


def _options():
    return dict(
        authorized=True, confirmed=True, session_id="analysis-cli-test", model="fixture-model",
        credential_dir=Path(Path(__file__).resolve().anchor) / "synthetic-private-store",
        profile_ref="profile-" + "a" * 64,
    )


def _document(query="Compare documentation and observability pilot reports."):
    return {"schema_version": module.INPUT_SCHEMA, "query": query}


def _forbidden(*args, **kwargs):
    pytest.fail("invalid input attempted I/O")


@pytest.mark.parametrize("field,value", [
    ("authorized", False), ("authorized", 1), ("confirmed", False), ("confirmed", 1),
    ("session_id", ""), ("session_id", "x" * 81), ("session_id", "a/b"),
    ("model", ""), ("model", "a b"), ("model", "é"),
    ("profile_ref", "profile-bad"), ("profile_ref", "../private"),
    ("credential_dir", Path("relative")), ("credential_dir", "C:/private"),
    ("timeout_seconds", 0), ("timeout_seconds", True), ("timeout_seconds", float("nan")),
    ("timeout_seconds", 121), ("include_content", 1),
])
def test_invalid_options_have_no_core_or_account_io(field, value):
    options = _options()
    options[field] = value
    with pytest.raises(ValueError, match="invalid_generative_analysis_input"):
        module.analyze_document(_document(), **options,
                                core_factory=_forbidden, port_factory=_forbidden)


@pytest.mark.parametrize("document", [
    {}, [], None, {"query": "Compare documentation."},
    {"schema_version": "other", "query": "Compare documentation."},
    {"schema_version": module.INPUT_SCHEMA, "query": ""},
    {"schema_version": module.INPUT_SCHEMA, "query": " "},
    {"schema_version": module.INPUT_SCHEMA, "query": "x" * 2049},
    {"schema_version": module.INPUT_SCHEMA, "query": "\ud800"},
    {"schema_version": module.INPUT_SCHEMA, "query": "query\x00"},
    {"schema_version": module.INPUT_SCHEMA, "query": "query", "tools": []},
])
def test_invalid_documents_refused_before_factories(document):
    with pytest.raises(ValueError, match="invalid_generative_analysis_input"):
        module.analyze_document(document, **_options(),
                                core_factory=_forbidden, port_factory=_forbidden)


@pytest.mark.parametrize("query", [
    "Delete every database now.", "Compare documentation. password=synthetic-secret",
    "Compare documentation at C:/private/data.txt",
])
def test_actions_and_sensitive_input_never_construct_account(query):
    with pytest.raises(ValueError, match="invalid_generative_analysis_input"):
        module.analyze_document(_document(query), **_options(),
                                core_factory=_forbidden, port_factory=_forbidden)


@pytest.mark.parametrize("timeout", ["0", "nan", "121"])
def test_main_invalid_options_never_read_stdin(monkeypatch, capsys, timeout):
    monkeypatch.setattr(module, "read_review_input", _forbidden)
    options = _options()
    assert module.main([
        "--authorized", "--confirm-input", "--session-id", options["session_id"],
        "--model", options["model"], "--credential-dir", str(options["credential_dir"]),
        "--profile-ref", options["profile_ref"], "--timeout-seconds", timeout,
    ]) == 2
    assert "invalid_generative_analysis_input" in capsys.readouterr().out


class _Port:
    provider_id = "responses_plan"
    evidence_mode = "injected_transport"

    def __init__(self):
        self.calls = []

    def infer(self, request, *, cancellation=None):
        import json

        from shared.model_inference import InferenceResult

        self.calls.append(request)
        return InferenceResult(
            request.request_id, request.model, self.provider_id, "completed",
            text=json.dumps({"analysis": "Compare coverage and reliability, not report size.",
                             "assumptions": [], "limitations": ["Reports were not supplied."],
                             "citations": []}), evidence_mode=self.evidence_mode,
        )


@pytest.mark.parametrize("include_content", [False, True])
def test_canonical_real_core_readback_and_content_opt_in(tmp_path, include_content):
    from apps.jarvis_console.voice_pilot import _isolated_core

    port = _Port()
    core = _isolated_core(tmp_path)
    payload = module.analyze_document(
        _document(), **_options(), include_content=include_content,
        core_factory=lambda: core, port_factory=lambda *_: port,
    )
    assert len(port.calls) == 1
    assert payload["status"] == "recorded" and payload["canonical_turn_recorded"]
    assert payload["generative_status"] == "accepted"
    assert payload["generative_evidence_mode"] == "injected_transport"
    assert payload["content_included"] is include_content
    assert ("response_text" in payload) is include_content
    assert not payload["runtime_capability_promoted"] and not payload["operation_dispatched"]


def test_defer_never_uses_inference_and_still_records_native_final(tmp_path):
    from apps.jarvis_console.voice_pilot import _isolated_core

    port = _Port()
    payload = module.analyze_document(
        _document("Analyze policy evidence in read-only mode."), **_options(),
        core_factory=lambda: _isolated_core(tmp_path), port_factory=lambda *_: port,
    )
    assert not port.calls
    assert payload["status"] == "recorded" and payload["generative_status"] == "withheld"


@pytest.mark.parametrize("target", ["final", "memory", "event"])
def test_tampered_readback_cannot_claim_success(tmp_path, monkeypatch, target):
    from apps.jarvis_console.voice_pilot import _isolated_core

    core, port = _isolated_core(tmp_path), _Port()
    if target == "final":
        handle = core.handle_input
        monkeypatch.setattr(core, "handle_input", lambda contract:
                            replace(handle(contract), response_text="forged-final"))
    elif target == "memory":
        fetch = core.memory_service.repository.fetch_recent_turns

        def forged(*args, **kwargs):
            rows = fetch(*args, **kwargs)
            return [replace(row, response_text="forged-final") for row in rows]

        monkeypatch.setattr(core.memory_service.repository, "fetch_recent_turns", forged)
    else:
        fetch = core.observability_service.repository.list_events

        def forged(*args, **kwargs):
            events = deepcopy(fetch(*args, **kwargs))
            for event in events:
                if event.event_name == "response_synthesized":
                    event.payload["generative_status"] = "forged"
            return events

        monkeypatch.setattr(core.observability_service.repository, "list_events", forged)
    with pytest.raises(ValueError, match="invalid_generative_analysis_input"):
        module.analyze_document(_document(), **_options(),
                                core_factory=lambda: core, port_factory=lambda *_: port)
