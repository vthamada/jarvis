"""Adversarial validation of bounded unverified generative prose."""

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from threading import Event

import pytest
from synthesis_engine import generative_analysis as module
from synthesis_engine.generative_analysis import (
    GENERATIVE_ANALYSIS_MARKER,
    GenerativeContext,
    GenerativeOutcome,
    analyze_input,
)

from shared.model_inference import InferenceResult

CONTENT = "Compare documentation and observability pilot reports."
CONTEXT = GenerativeContext("request-human-1", CONTENT)


def candidate(**changes):
    value = {
        "analysis": "Documentation defines expectations; "
        "telemetry helps evaluate observed behavior.",
        "assumptions": ["The two reports concern the same pilot."],
        "limitations": ["No actual report contents were supplied."],
        "citations": [],
    }
    value.update(changes)
    return value


class Port:
    def __init__(self, value=None, *, text=None, changes=None, hook=None):
        self.value = value if value is not None else candidate()
        self.text = text
        self.changes = changes or {}
        self.hook = hook
        self.requests = []

    def infer(self, request, *, cancellation=None):
        self.requests.append(request)
        if self.hook:
            self.hook(request, cancellation)
        values = dict(
            request_id=request.request_id,
            model=request.model,
            provider_id="fixture",
            status="completed",
            text=self.text if self.text is not None else json.dumps(self.value),
            evidence_mode="fixture",
        )
        values.update(self.changes)
        return InferenceResult(**values)


def run(port=None, context=CONTEXT, **kwargs):
    return analyze_input(port or Port(), model="fixture-analysis", context=context, **kwargs)


def assert_rejected(outcome, code=None):
    assert outcome.status == "rejected"
    if code:
        assert outcome.error_code == code
    assert outcome.evidence_mode is None
    assert outcome.analysis_character_count == 0
    assert outcome.render() == ""
    assert CONTENT not in repr(outcome)


def test_acceptance_contains_new_prose_and_explicit_nonauthority_label():
    port = Port()
    outcome = run(port)
    assert outcome.status == "accepted"
    assert outcome.error_code is None
    assert outcome.evidence_mode == "fixture"
    assert outcome.analysis_character_count == len(candidate()["analysis"])
    assert outcome.render().startswith(GENERATIVE_ANALYSIS_MARKER)
    assert "execution receipts" in outcome.render()
    assert "Documentation defines expectations" in outcome.render()
    assert len(port.requests) == 1
    assert "Documentation defines expectations" not in repr(outcome)
    assert CONTENT not in repr(CONTEXT)


def test_context_is_frozen():
    with pytest.raises(FrozenInstanceError):
        CONTEXT.content = "changed"


def test_request_contains_only_current_input_and_reviewed_quote():
    context = GenerativeContext("id", CONTENT, "reviewed:sha256:abcdef", "Clean reviewed passage.")
    port = Port()
    assert run(port, context).status == "accepted"
    request = port.requests[0]
    payload = json.loads(request.messages[0].content)
    assert payload == {
        "schema_version": 1,
        "sources": [
            {
                "source_ref": "input:sha256:" + hashlib.sha256(CONTENT.encode()).hexdigest(),
                "text": CONTENT,
            },
            {"source_ref": context.source_ref, "text": context.quote},
        ],
    }
    assert len(request.messages) == 1
    assert request.max_output_chars == 16000
    assert "current input" in request.instructions
    assert "id" not in payload


@pytest.mark.parametrize(
    "content", ["x" * 16000, "á" * 16000, "😀" * 16000], ids=["ascii", "accent", "nonbmp"]
)
def test_unicode_input_character_boundary_is_not_artificially_ascii_expanded(content):
    assert run(context=GenerativeContext("id", content)).status == "accepted"


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", ""),
        ("request_id", "x" * 257),
        ("request_id", True),
        ("content", ""),
        ("content", "  "),
        ("content", "x" * 16001),
        ("content", None),
        ("content", ["secret"]),
        ("content", "\ud800"),
        ("source_ref", "ref"),
        ("quote", "quote"),
    ],
    ids=lambda value: type(value).__name__,
)
def test_invalid_context_never_invokes_port(field, value):
    port = Port()
    assert_rejected(run(port, replace(CONTEXT, **{field: value})), "invalid_context")
    assert not port.requests


@pytest.mark.parametrize(
    "ref,quote",
    [
        ("", "text"),
        ("ref has space", "text"),
        ("r" * 161, "text"),
        ("ref", ""),
        ("ref", "x" * 513),
        ("ref", "\udfff"),
        ("ref", 123),
        (123, "text"),
    ],
    ids=lambda value: type(value).__name__,
)
def test_invalid_reviewed_quote_binding_never_invokes_port(ref, quote):
    port = Port()
    assert_rejected(run(port, GenerativeContext("id", CONTENT, ref, quote)), "invalid_context")
    assert not port.requests


def test_reviewed_ref_cannot_shadow_current_input():
    ref = "input:sha256:" + hashlib.sha256(CONTENT.encode()).hexdigest()
    port = Port()
    assert_rejected(run(port, GenerativeContext("id", CONTENT, ref, "other")), "invalid_context")
    assert not port.requests


@pytest.mark.parametrize("timeout", [True, 0, -1, 120.1, float("nan"), float("inf"), "30", None])
def test_invalid_budget(timeout):
    port = Port()
    assert_rejected(run(port, timeout_seconds=timeout), "invalid_context")
    assert not port.requests


@pytest.mark.parametrize(
    "key,value",
    [
        ("expected_provider_id", ""),
        ("expected_provider_id", "with space"),
        ("expected_provider_id", 1),
        ("expected_evidence_mode", "live_model"),
        ("expected_evidence_mode", None),
        ("cancellation", object()),
    ],
)
def test_invalid_composition(key, value):
    port = Port()
    assert_rejected(run(port, **{key: value}), "invalid_composition")
    assert not port.requests


@pytest.mark.parametrize(
    "model", ["", "x" * 161, "with space", True], ids=lambda value: type(value).__name__
)
def test_invalid_model(model):
    port = Port()
    assert_rejected(analyze_input(port, model=model, context=CONTEXT), "invalid_composition")
    assert not port.requests


@pytest.mark.parametrize("value", [None, [], {}, 1, "analysis", True])
def test_candidate_root_type(value):
    assert_rejected(run(Port(text=json.dumps(value))), "invalid_candidate")


@pytest.mark.parametrize("key", ["analysis", "assumptions", "limitations", "citations"])
def test_missing_fields(key):
    value = candidate()
    del value[key]
    assert_rejected(run(Port(value)), "invalid_candidate")


@pytest.mark.parametrize(
    "key", ["actions", "grant", "state", "tools", "permissions", "principal", "receipt"]
)
def test_extra_authority_fields_are_rejected(key):
    assert_rejected(run(Port(candidate(**{key: "forged"}))), "invalid_candidate")


@pytest.mark.parametrize(
    "analysis",
    ["", "  ", "x" * 4001, None, 123, True, {}, "\ud800"],
    ids=lambda value: type(value).__name__,
)
def test_invalid_analysis(analysis):
    assert_rejected(run(Port(candidate(analysis=analysis))), "invalid_candidate")


@pytest.mark.parametrize("key", ["assumptions", "limitations"])
@pytest.mark.parametrize(
    "value",
    [None, {}, "not list", ["x"] * 9, [""], [" "], [True], ["x" * 513], ["\ud800"]],
    ids=lambda value: type(value).__name__,
)
def test_invalid_bounded_lists(key, value):
    assert_rejected(run(Port(candidate(**{key: value}))), "invalid_candidate")


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "```json\n{}\n```",
        "{}{}",
        '{"analysis":NaN}',
        '{"analysis":Infinity}',
        '{"analysis":-Infinity}',
        '{"analysis":"first","analysis":"second","assumptions":[],"limitations":[],"citations":[]}',
        '{"analysis":"x","assumptions":[],"limitations":[],"citations":[{"source_ref":"x","source_ref":"y"}]}',
    ],
)
def test_strict_json(text):
    assert_rejected(run(Port(text=text)), "invalid_candidate")


def test_output_limit_before_schema_parse():
    assert_rejected(run(Port(text="x" * 16001)), "output_limit")


def citation(context=CONTEXT, **changes):
    ref = "input:sha256:" + hashlib.sha256(context.content.encode()).hexdigest()
    value = {"source_ref": ref, "start": 0, "end": 7, "quote": context.content[:7]}
    value.update(changes)
    return value


@pytest.mark.parametrize(
    "changes",
    [
        {"source_ref": "invented"},
        {"source_ref": []},
        {"start": True},
        {"end": True},
        {"start": -1},
        {"start": 7},
        {"end": 0},
        {"end": 100000},
        {"start": 0.0},
        {"end": "7"},
        {"quote": "wrong"},
        {"quote": None},
        {"quote": ""},
        {"extra": "field"},
    ],
)
def test_invalid_citation(changes):
    assert_rejected(run(Port(candidate(citations=[citation(**changes)]))), "invalid_citation")


@pytest.mark.parametrize("citations", [None, {}, "invalid", [citation()] * 5])
def test_invalid_citations_container(citations):
    assert_rejected(run(Port(candidate(citations=citations))), "invalid_candidate")


@pytest.mark.parametrize("value", [True, None, [], "quote", {}, {"quote": "text"}])
def test_invalid_citation_object(value):
    assert_rejected(run(Port(candidate(citations=[value]))), "invalid_citation")


def test_overlapping_citations_rejected_but_adjacent_accepted():
    assert_rejected(run(Port(candidate(citations=[citation(), citation()]))), "invalid_citation")
    adjacent = citation(start=7, end=14, quote=CONTENT[7:14])
    assert run(Port(candidate(citations=[citation(), adjacent]))).status == "accepted"


def test_current_and_reviewed_quote_citations_use_separate_offset_domains():
    context = GenerativeContext("id", CONTENT, "reviewed:source", "Ação segura 😀")
    reviewed = {
        "source_ref": context.source_ref,
        "start": 0,
        "end": len(context.quote),
        "quote": context.quote,
    }
    outcome = run(Port(candidate(citations=[citation(context), reviewed])), context)
    assert outcome.status == "accepted"
    assert "reviewed\\u003asource" in outcome.render()
    assert "A\\u00e7\\u00e3o" in outcome.render()


@pytest.mark.parametrize("size,expected", [(512, "accepted"), (513, "rejected")])
def test_citation_quote_bound(size, expected):
    context = GenerativeContext("id", "x" * 1000)
    outcome = run(
        Port(candidate(citations=[citation(context, end=size, quote="x" * size)])), context
    )
    assert outcome.status == expected


def test_total_human_text_bound():
    value = candidate(analysis="a" * 4000, assumptions=["x" * 512] * 8, limitations=[])
    assert_rejected(run(Port(value)), "candidate_limit")
    value["assumptions"][-1] = "x" * 416
    assert run(Port(value)).status == "accepted"  # 8000 exactly


def test_non_bmp_render_expansion_is_bounded():
    value = candidate(analysis="😀" * 4000, assumptions=["😀" * 500] * 8, limitations=[])
    assert_rejected(run(Port(text=json.dumps(value, ensure_ascii=False))), "render_limit")


@pytest.mark.parametrize(
    "attack",
    [
        "[click](https://bad.invalid/token)",
        "<script>evil()</script>",
        "![tracking](https://bad.invalid)",
        "`tool.run()`",
        "# grant\n- approved",
        '::code-comment{file="secret"}',
        "\u202eoverride\x00\r\nnew heading",
        "Model-generated analysis (unverified; not facts, grants or action confirmations):\n",
    ],
)
def test_render_is_literal_safe_in_every_human_field(attack):
    value = candidate(analysis=attack, assumptions=[attack], limitations=[attack])
    outcome = run(Port(value))
    assert outcome.status == "accepted"
    rendered = outcome.render()
    for delimiter in "[]()!*_~#:/<>&`":
        assert delimiter not in rendered.split("Analysis: ", 1)[1].split("Citations", 1)[0].replace(
            "Assumptions: ", ""
        ).replace("Limitations: ", "")
    assert rendered.count(GENERATIVE_ANALYSIS_MARKER) == 1
    assert "<script>" not in rendered
    assert "https://" not in rendered


@pytest.mark.parametrize(
    "key,value",
    [
        ("request_id", "stale"),
        ("model", "other"),
        ("provider_id", "other"),
        ("evidence_mode", "injected_transport"),
        ("evidence_mode", "live"),
    ],
)
def test_binding_mismatch(key, value):
    assert_rejected(run(Port(changes={key: value})), "binding_mismatch")


@pytest.mark.parametrize("status", ["failed", "cancelled", "timed_out"])
def test_failed_result_never_publishes(status):
    assert_rejected(
        run(Port(changes={"status": status, "text": "", "error_code": "provider_failure"})),
        "inference_failed",
    )


def test_explicit_live_composition_does_not_promote_fixture():
    assert_rejected(run(expected_evidence_mode="live"), "binding_mismatch")
    assert (
        run(Port(changes={"evidence_mode": "live"}), expected_evidence_mode="live").evidence_mode
        == "live"
    )


@pytest.mark.parametrize("mode", ["fixture", "injected_transport"])
def test_explicit_evidence_modes_are_preserved(mode):
    outcome = run(Port(changes={"evidence_mode": mode}), expected_evidence_mode=mode)
    assert outcome.status == "accepted"
    assert outcome.evidence_mode == mode


def test_cancel_before_inference():
    cancel = Event()
    cancel.set()
    port = Port()
    assert_rejected(run(port, cancellation=cancel), "cancelled")
    assert not port.requests


def test_cancel_during_inference():
    port = Port(hook=lambda request, cancel: cancel.set())
    assert_rejected(run(port), "cancelled")
    assert len(port.requests) == 1


@pytest.mark.parametrize(
    "times,code,calls",
    [
        ([float("nan")], "invalid_clock", 0),
        ([True], "invalid_clock", 0),
        ([0, -1], "invalid_clock", 0),
        ([0, 30], "timed_out", 0),
        ([0, 1, 30], "timed_out", 1),
        ([0, 1, 0], "invalid_clock", 1),
        ([0, 1, 2, 30], "timed_out", 1),
        ([0, 1, 2, 1], "invalid_clock", 1),
        ([0, 1, 2, float("inf")], "invalid_clock", 1),
    ],
)
def test_global_budget_and_clock(times, code, calls):
    port = Port()
    sequence = iter(times)
    assert_rejected(run(port, clock=lambda: next(sequence)), code)
    assert len(port.requests) == calls


def test_request_construction_and_validation_share_budget():
    port = Port()
    sequence = iter([100, 103, 110, 129.9])
    assert run(port, clock=lambda: next(sequence)).status == "accepted"
    assert port.requests[0].timeout_seconds == 27


def test_cancel_after_rendering_is_checked(monkeypatch):
    cancel = Event()
    original = module._literal

    def literal(text):
        result = original(text)
        cancel.set()
        return result

    monkeypatch.setattr(module, "_literal", literal)
    assert_rejected(run(cancellation=cancel), "cancelled")


def test_context_changes_by_injected_port_are_rejected():
    context = replace(CONTEXT)
    port = Port(hook=lambda request, cancel: object.__setattr__(context, "content", "changed"))
    assert_rejected(run(port, context), "context_changed")


def test_request_hash_binds_id_model_input_and_reviewed_quote():
    ids = []
    for context in [
        CONTEXT,
        replace(CONTEXT, request_id="id2"),
        replace(CONTEXT, content="other"),
        replace(CONTEXT, source_ref="reviewed:a", quote="one"),
        replace(CONTEXT, source_ref="reviewed:a", quote="two"),
    ]:
        port = Port()
        assert run(port, context).status == "accepted"
        ids.append(port.requests[0].request_id)
    assert len(set(ids)) == len(ids)
    assert all(value.startswith("generative-") for value in ids)


def test_exception_messages_are_not_retained_and_no_retry():
    class BrokenPort:
        calls = 0

        def infer(self, request, *, cancellation=None):
            self.calls += 1
            raise RuntimeError("human_secret and model private output")

    port = BrokenPort()
    outcome = run(port)
    assert_rejected(outcome, "inference_unavailable")
    assert "human_secret" not in repr(outcome)
    assert port.calls == 1


@pytest.mark.parametrize("value", [None, {}, "text", object()])
def test_invalid_result_type(value):
    class InvalidPort:
        def infer(self, request, *, cancellation=None):
            return value

    assert_rejected(run(InvalidPort()), "invalid_result")


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "partial"),
        ("text", None),
        ("error_code", "bad value"),
        ("input_tokens", True),
        ("output_tokens", -1),
    ],
)
def test_forged_result_revalidated(field, value):
    class ForgedPort(Port):
        def infer(self, request, *, cancellation=None):
            result = super().infer(request, cancellation=cancellation)
            object.__setattr__(result, field, value)
            return result

    assert_rejected(run(ForgedPort()), "invalid_result")


def test_failed_outcome_render_cannot_leak_accidentally_attached_text():
    assert GenerativeOutcome("rejected", _rendered="secret").render() == ""


def test_context_revalidated_after_final_clock_callback():
    context = replace(CONTEXT)
    readings = iter([0, 1, 2, 3])

    def clock():
        value = next(readings)
        if value == 3:
            object.__setattr__(context, "content", "changed by final callback")
        return value

    assert_rejected(run(context=context, clock=clock), "context_changed")


def test_result_revalidated_after_final_clock_callback():
    results = []

    class RetainedPort(Port):
        def infer(self, request, *, cancellation=None):
            result = super().infer(request, cancellation=cancellation)
            results.append(result)
            return result

    readings = iter([0, 1, 2, 3])

    def clock():
        value = next(readings)
        if value == 3:
            object.__setattr__(results[0], "text", "forged after validation")
        return value

    assert_rejected(run(RetainedPort(), clock=clock), "result_changed")


@pytest.mark.parametrize(
    "sensitive",
    [
        "Bearer privatecredential",
        "secret=private",
        "token: hidden",
        '"password": "hidden"',
        "api_key=private",
        "API-key: hidden",
        "access_token=hidden",
        "refresh-token=hidden",
        "client secret=hidden",
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "sk-abcdefgh123456",
        "ghp_abcdefgh123456",
        "github_pat_abcdefgh123456",
        "xoxb-12345678-abcdefghijkl",
        "https://user:pass@example.invalid/resource",
        "C:\\Users\\human\\file",
        "D:/private/path",
        "\\\\server\\share\\file",
        "/home/human/file",
        "/Users/human/file",
        "/root/file",
        "/tmp/secret",
        "user://human",
        "operator://principal",
        "human@example.invalid",
    ],
)
@pytest.mark.parametrize("location", ["input", "quote"])
def test_sensitive_input_and_quote_never_call_port(sensitive, location):
    context = (
        GenerativeContext("id", sensitive)
        if location == "input"
        else GenerativeContext("id", CONTENT, "reviewed:source", sensitive)
    )
    port = Port()
    assert_rejected(run(port, context), "input_sensitive")
    assert not port.requests


@pytest.mark.parametrize(
    "sensitive",
    [
        "Bearer privatecredential",
        "secret=private",
        "token: hidden",
        '"password": "hidden"',
        "api_key=private",
        "API-key: hidden",
        "access_token=hidden",
        "refresh-token=hidden",
        "client secret=hidden",
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "sk-abcdefgh123456",
        "ghp_abcdefgh123456",
        "github_pat_abcdefgh123456",
        "xoxb-12345678-abcdefghijkl",
        "https://user:pass@example.invalid/resource",
        "C:\\Users\\human\\file",
        "D:/private/path",
        "\\\\server\\share\\file",
        "/home/human/file",
        "/Users/human/file",
        "/root/file",
        "/tmp/secret",
        "user://human",
        "operator://principal",
        "human@example.invalid",
    ],
)
@pytest.mark.parametrize("location", ["analysis", "assumptions", "limitations"])
def test_sensitive_raw_model_output_rejected_before_literal_escape(sensitive, location):
    value = candidate(**{location: sensitive if location == "analysis" else [sensitive]})
    port = Port(value)
    outcome = run(port)
    assert_rejected(outcome, "output_sensitive")
    assert sensitive not in repr(outcome)
    assert len(port.requests) == 1
