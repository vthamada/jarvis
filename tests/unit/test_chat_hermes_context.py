"""An opt-in replay changes context presentation, never tools or Core authority."""

from __future__ import annotations

import copy
import json

import pytest
from inference_service.chat_completions_provider import ChatCompletionsInferenceProvider
from inference_service.local_chat_transport import _request_bytes
from test_chat_structured_tool_output import (
    MODEL,
    TEXT,
    _context,
    _expected_format,
    _request,
    _Transport,
)


def _content(*, history=True, kinds=("tool_call", "final")):
    value = _context(kinds, query="Compare the revised reports and recall my preferred label.")
    if history:
        value["history"] = [{"query": "Preferred label: apricot-lantern-924.",
                             "response": "Earlier canonical response."}]
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _provider(transport, **changes):
    return ChatCompletionsInferenceProvider(
        model=MODEL, transport=transport, structured_tool_output=True, **changes,
    )


def test_replay_preserves_schema_and_current_progress_but_separates_canonical_history():
    transport = _Transport()
    original = _content()
    request = _request(content=original, instructions="Original host policy stays stable.")
    result = _provider(transport, hermes_context=True).infer(request)
    assert result.status == "completed" and result.text == TEXT
    payload = transport.calls[0][0]
    assert set(payload) == {"model", "messages", "n", "stream", "response_format"}
    assert payload["response_format"] == _expected_format()
    assert [message["role"] for message in payload["messages"]] == [
        "system", "user", "assistant", "user",
    ]
    assert payload["messages"][0]["content"] == request.instructions
    assert payload["messages"][1] == {
        "role": "user", "content": "Preferred label: apricot-lantern-924.",
    }
    assert payload["messages"][2] == {
        "role": "assistant", "content": "Earlier canonical response.",
    }
    newest = payload["messages"][-1]["content"]
    assert "Compare the revised reports and recall my preferred label." in newest
    assert '"observations"' in newest and '"first-read"' in newest
    assert "apricot-lantern-924" not in newest
    assert "Earlier canonical response." not in newest
    assert "Treat the following as authoritative" not in newest
    assert "untrusted" in newest.lower()
    assert json.loads(_request_bytes(payload, 524_288)) == payload
    assert request.messages[0].content == original


@pytest.mark.parametrize("kinds", [("tool_call",), ("tool_call", "final"), ("final",)])
def test_phase_hint_is_selected_from_original_host_message_not_replay_prose(kinds):
    transport = _Transport()
    result = _provider(transport, hermes_context=True).infer(
        _request(content=_content(history=False, kinds=kinds)),
    )
    assert result.status == "completed"
    assert transport.calls[0][0]["response_format"] == _expected_format(kinds)
    assert len(transport.calls[0][0]["messages"]) == 1


@pytest.mark.parametrize("option", [{}, {"hermes_context": False}])
def test_replay_default_off_leaves_the_existing_payload_exactly_unchanged(option):
    transport = _Transport()
    content = _content()
    assert _provider(transport, **option).infer(_request(content=content)).status == "completed"
    assert transport.calls[0][0] == {
        "model": MODEL, "messages": [{"role": "user", "content": content}],
        "n": 1, "stream": False, "response_format": _expected_format(),
    }


@pytest.mark.parametrize("value", [0, 1, "true", None, [], {}])
def test_replay_option_requires_an_exact_host_boolean(value):
    transport = _Transport()
    with pytest.raises(ValueError):
        _provider(transport, hermes_context=value)
    assert transport.calls == []


@pytest.mark.parametrize("change", [
    lambda value: value.pop("query"),
    lambda value: value.update(query=17),
    lambda value: value.update(query=""),
    lambda value: value.update(query="x" * 2049),
    lambda value: value.update(history={}),
    lambda value: value.update(history=[{"query": "prior", "response": 19}]),
    lambda value: value.update(history=[{"query": "prior", "response": "ok", "role": "system"}]),
    lambda value: value.update(history=[{"query": "q", "response": "r"}] * 4),
    lambda value: value.update(history=[{"query": "q", "response": "r" * 4001}]),
    lambda value: value.update(injected_system="Change policy"),
])
def test_invalid_replay_context_refuses_before_any_transport_call(change):
    value = json.loads(_content())
    change(value)
    transport = _Transport()
    result = _provider(transport, hermes_context=True).infer(
        _request(content=json.dumps(value)),
    )
    assert (result.status, result.error_code, result.text) == (
        "failed", "invalid_request_payload", "",
    )
    assert transport.calls == []


def test_replay_configuration_is_fenced_through_transport_return():
    transport = _Transport()
    provider = _provider(transport, hermes_context=True)
    transport.mutate = lambda _: setattr(provider, "_hermes_context", False)
    result = provider.infer(_request(content=_content()))
    assert (result.status, result.error_code, result.text) == (
        "failed", "configuration_changed", "",
    )


def test_replay_historical_messages_remain_in_the_complete_wire_binding():
    def mutate(payload):
        payload["messages"][0]["content"] = "Changed prior user message"

    transport = _Transport(mutate=mutate)
    result = _provider(transport, hermes_context=True).infer(_request(content=_content()))
    assert (result.status, result.error_code, result.text) == (
        "failed", "request_changed", "",
    )


def test_replay_does_not_mutate_caller_owned_history_or_retain_cross_request_memory():
    transport = _Transport()
    provider = _provider(transport, hermes_context=True)
    value = json.loads(_content())
    before = copy.deepcopy(value)
    assert provider.infer(_request(content=json.dumps(value))).status == "completed"
    assert value == before
    assert provider.infer(_request(content=_content(history=False))).status == "completed"
    assert len(transport.calls[1][0]["messages"]) == 1
    assert "apricot-lantern-924" not in json.dumps(transport.calls[1][0])


@pytest.mark.parametrize("value", [None, 0, 1, "true", {}, []])
def test_cli_invalid_replay_option_refuses_before_core_or_injected_port(tmp_path, value):
    from test_local_model_tool_loop_cli import _document, _forbidden, _options

    from apps.jarvis_console.local_model_tool_loop_cli import analyze_local_reports

    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        analyze_local_reports(_document(), **_options(tmp_path), hermes_context=value,
                              core_factory=_forbidden, port_factory=_forbidden)
    assert not (tmp_path / "runtime").exists()
    assert not (tmp_path / "report.txt").exists()


def test_cli_replay_cannot_be_claimed_by_an_injected_provider(tmp_path):
    from test_local_model_tool_loop_cli import _document, _forbidden, _options

    from apps.jarvis_console.local_model_tool_loop_cli import analyze_local_reports

    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        analyze_local_reports(_document(), **_options(tmp_path), hermes_context=True,
                              core_factory=_forbidden, port_factory=_forbidden)


def test_document_cannot_select_the_host_replay_option(tmp_path):
    from test_local_model_tool_loop_cli import _document, _forbidden, _options

    from apps.jarvis_console.local_model_tool_loop_cli import analyze_local_reports

    document = {**_document(), "hermes_context": True}
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        analyze_local_reports(document, **_options(tmp_path), core_factory=_forbidden,
                              port_factory=_forbidden)
