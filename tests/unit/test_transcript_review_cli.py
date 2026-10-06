"""Fail-closed stdin envelope boundaries and fresh local review/Core handoff."""

from __future__ import annotations

import base64
import builtins
import hashlib
import io
import json
import sys
from argparse import Namespace
from dataclasses import replace

import pytest

from apps.jarvis_console.runtime import ConsoleCommandError
from apps.jarvis_console.transcript_review_cli import (
    MAX_DOCUMENT_BYTES,
    MAX_ENVELOPE_BYTES,
    run_transcript_review,
)


def document(text="Explain what an agent is."):
    return {"review_required": True, "language": "Portuguese", "audio_duration_seconds": 5.0,
            "segments": [{"start_seconds": 0.0, "end_seconds": 5.0,
                          "timestamps_estimated": False, "text": text}]}


def envelope(source=None, text=None):
    source = document() if source is None else source
    raw = json.dumps(source, ensure_ascii=False).encode("utf-8")
    return envelope_bytes(raw, document()["segments"][0]["text"] if text is None else text)


def envelope_bytes(raw, text="Explain what an agent is."):
    return {"schema_version": "jarvis-transcript-handoff-v1", "authority": "none",
            "source_origin": "unverified", "document_utf8_b64": base64.b64encode(raw).decode(),
            "source_sha256": hashlib.sha256(raw).hexdigest(), "reviewed_text": text,
            "reviewed_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "review_revision": 1}


def args(**changes):
    values = {"authorized": True, "include_content": False, "session_id": "review-test"}
    values.update(changes)
    return Namespace(**values)


def stdin(monkeypatch, value):
    monkeypatch.setattr(sys, "stdin", io.StringIO(
        json.dumps(value, ensure_ascii=True) if isinstance(value, dict) else value,
    ))


def never_core():
    pytest.fail("invalid input bootstrapped Core")


def refused(monkeypatch, value, supplied=None):
    stdin(monkeypatch, value)
    with pytest.raises(ConsoleCommandError) as error:
        run_transcript_review(supplied or args(), never_core)
    assert error.value.error_code == "transcript_handoff_refused"
    assert "private-marker" not in str(error.value)


@pytest.mark.parametrize("authorized", [False, None, 0, 1, "true", [], {}])
def test_no_authorization_does_not_read_import_or_bootstrap(monkeypatch, authorized):
    class NoRead:
        def isatty(self):
            pytest.fail("unauthorized stdin queried")

        def read(self, *arguments):
            pytest.fail("unauthorized stdin read")

    monkeypatch.setattr(sys, "stdin", NoRead())
    original = builtins.__import__

    def guarded(name, *arguments, **kwargs):
        if name.startswith(("apps.jarvis_voice", "apps.jarvis_console.voice_pilot",
                            "orchestrator_service")):
            pytest.fail("unauthorized Core/review import")
        return original(name, *arguments, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(ConsoleCommandError) as error:
        run_transcript_review(args(authorized=authorized), never_core)
    assert error.value.error_code == "transcript_handoff_not_authorized"


@pytest.mark.parametrize("change", [
    {"include_content": 1}, {"include_content": "true"}, {"include_content": None},
    {"session_id": ""}, {"session_id": "a" * 81}, {"session_id": "session/with/slash"},
    {"session_id": "á"}, {"session_id": "private-marker\n"}, {"session_id": True},
    {"session_id": None}, {"session_id": "session name"},
])
def test_bad_arguments_before_stdin(monkeypatch, change):
    class NoRead:
        def isatty(self):
            pytest.fail("invalid argv read stdin")

    monkeypatch.setattr(sys, "stdin", NoRead())
    with pytest.raises(ConsoleCommandError, match="Transcript handoff refused"):
        run_transcript_review(args(**change), never_core)


@pytest.mark.parametrize("field,value", [
    ("schema_version", "unknown"), ("authority", "operator"), ("source_origin", "verified"),
    ("document_utf8_b64", None), ("document_utf8_b64", 123), ("document_utf8_b64", ""),
    ("source_sha256", "A" * 64), ("source_sha256", "b" * 64),
    ("source_sha256", None), ("reviewed_sha256", "c" * 64),
    ("reviewed_sha256", []), ("review_revision", True), ("review_revision", 0),
    ("review_revision", -1), ("review_revision", 2**31), ("review_revision", 1.0),
    ("review_revision", "1"), ("reviewed_text", " "), ("reviewed_text", "x" * 4001),
    ("reviewed_text", "private-marker\x00"), ("reviewed_text", "private-marker\u200b"),
    ("reviewed_text", "\ud800"), ("reviewed_text", {}),
])
def test_bad_envelope_fields_before_core(monkeypatch, field, value):
    value_envelope = envelope()
    value_envelope[field] = value
    refused(monkeypatch, value_envelope)


@pytest.mark.parametrize("field", sorted(envelope()))
def test_missing_envelope_field_before_core(monkeypatch, field):
    value = envelope()
    del value[field]
    refused(monkeypatch, value)


def test_extra_identity_field_never_trusted(monkeypatch):
    value = envelope()
    value["operator_identity_ref"] = "operator://private-marker"
    refused(monkeypatch, value)


@pytest.mark.parametrize("raw", [
    "", "[]", "null", "private-marker", "{", "\ufeff{}", "{\"x\":NaN}",
    "{\"x\":Infinity}", "{\"x\":1e999}", "{\"x\":\"\\ud800\"}",
    "{\"x\":0,\"x\":1}", "{\"x\":" + "[" * 14 + "0" + "]" * 14 + "}",
    " " * (MAX_ENVELOPE_BYTES + 1),
], ids=["empty", "array", "null", "text", "syntax", "bom", "nan", "infinity",
        "overflow", "surrogate", "duplicate", "deep", "large"])
def test_bad_envelope_json_before_core(monkeypatch, raw):
    refused(monkeypatch, raw)


@pytest.mark.parametrize("mutate", [
    lambda raw: raw[:-1] + b",\"review_required\":true}",
    lambda raw: b"\xef\xbb\xbf" + raw,
    lambda raw: raw.replace(b"5.0", b"NaN", 1),
    lambda raw: b'{"private-marker":"\\ud800"}',
    lambda raw: b"\xffprivate-marker",
    lambda raw: b"{}" + b" " * MAX_DOCUMENT_BYTES,
    lambda raw: b"",
    lambda raw: b"[]",
])
def test_bad_source_bytes_even_with_matching_digest(monkeypatch, mutate):
    raw = json.dumps(document()).encode()
    refused(monkeypatch, envelope_bytes(mutate(raw)))


@pytest.mark.parametrize("change", [
    {"review_required": False}, {"language": "English"}, {"audio_duration_seconds": True},
    {"audio_duration_seconds": 901}, {"segments": []}, {"private-marker": True},
])
def test_bad_asr_contract(monkeypatch, change):
    source = document()
    source.update(change)
    refused(monkeypatch, envelope(source))


@pytest.mark.parametrize("encoded", ["e30", "e30===", "e30=\n", "e3/=" , "e3_="])
def test_base64_must_be_canonical_standard(monkeypatch, encoded):
    value = envelope_bytes(b"{}")
    value["document_utf8_b64"] = encoded
    refused(monkeypatch, value)


def test_terminal_stdin_refused(monkeypatch):
    class Terminal(io.StringIO):
        def isatty(self):
            return True

        def read(self, *arguments):
            pytest.fail("interactive read")

    monkeypatch.setattr(sys, "stdin", Terminal())
    with pytest.raises(ConsoleCommandError):
        run_transcript_review(args(), never_core)


def test_binary_stdin_utf8_refused(monkeypatch):
    class Binary:
        buffer = io.BytesIO(b"\xffprivate-marker")

        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", Binary())
    with pytest.raises(ConsoleCommandError):
        run_transcript_review(args(), never_core)


@pytest.mark.parametrize("changed,revision", [(False, 1), (True, 2), (True, 2**31 - 1)])
def test_actual_core_exact_text_fresh_revision_and_private_metadata(
    monkeypatch, tmp_path, changed, revision,
):
    from apps.jarvis_console.voice_pilot import _isolated_core

    core = _isolated_core(tmp_path / "runtime")
    text = "  Explain what a harness is.\n" if changed else "Explain what an agent is."
    value = envelope(text=text)
    value["review_revision"] = revision
    stdin(monkeypatch, value)
    calls = []
    original = core.handle_input

    def tracked(contract):
        calls.append(contract)
        return original(contract)

    monkeypatch.setattr(core, "handle_input", tracked)
    factory_calls = []

    def factory():
        factory_calls.append(True)
        return core

    payload = json.loads(run_transcript_review(args(), factory).outputs[0])
    assert len(factory_calls) == len(calls) == 1
    contract = calls[0]
    assert contract.content == text
    assert contract.surface_id == "surface://local-transcript-review"
    assert contract.surface_kind == "voice"
    assert contract.operator_identity_ref == "operator://local_console"
    assert contract.canonical_user_ref == "user://local_operator"
    assert contract.surface_session_id == "review-test"
    assert contract.channel.value == "voice"
    assert contract.surface_capability_scope == []
    assert contract.action_confirmation_receipt_id is None
    assert contract.adapter_action_request is None
    assert contract.max_autonomy_level == contract.requested_autonomy_level == "assist_only"
    turns = core.memory_service.repository.fetch_recent_turns("review-test", 10)
    assert len(turns) == 1 and turns[0].request_content == text
    assert payload["state"] == "handed_off"
    assert payload["declared_review_revision"] == revision
    assert payload["local_review_revision"] == (2 if changed else 1)
    assert payload["canonical_turn_recorded"] and payload["core_event_count"] > 0
    assert not payload["operation_dispatched"]
    assert payload["operator_authenticated"] is False
    encoded = json.dumps(payload)
    for forbidden in (text, value["source_sha256"], value["reviewed_sha256"],
                      "surface://", "operator://", "user://", str(contract.request_id)):
        assert forbidden not in encoded


def test_explicit_content_matches_exact_canonical_final(monkeypatch, tmp_path):
    from apps.jarvis_console.voice_pilot import _isolated_core

    core = _isolated_core(tmp_path / "runtime")
    text = " Explique o agente.\n"
    stdin(monkeypatch, envelope(text=text))
    payload = json.loads(run_transcript_review(args(include_content=True), lambda: core).outputs[0])
    turns = core.memory_service.repository.fetch_recent_turns("review-test", 10)
    assert payload["reviewed_text"] == text == turns[0].request_content
    assert payload["final_text"] == turns[0].response_text
    assert payload["content_included"] and not payload["content_withheld"]


@pytest.mark.parametrize("secret", ["Bearer private-marker-secret-token", "sk-" + "a" * 40])
def test_sensitive_output_withheld_whole_not_mutated(monkeypatch, tmp_path, secret):
    from apps.jarvis_console.voice_pilot import _isolated_core

    core = _isolated_core(tmp_path / "runtime")
    text = "Explain this value: " + secret
    stdin(monkeypatch, envelope(text=text))
    payload = json.loads(run_transcript_review(args(include_content=True), lambda: core).outputs[0])
    turns = core.memory_service.repository.fetch_recent_turns("review-test", 10)
    assert turns[0].request_content == text
    assert payload["content_withheld"] and not payload["content_included"]
    assert "reviewed_text" not in payload and "final_text" not in payload
    assert secret not in json.dumps(payload)


def test_reusing_bundle_is_another_explicit_turn_not_hidden_dedup(monkeypatch, tmp_path):
    from apps.jarvis_console.voice_pilot import _isolated_core

    core = _isolated_core(tmp_path / "runtime")
    original = core.handle_input
    request_ids = []

    def tracked(contract):
        request_ids.append(contract.request_id)
        return original(contract)

    monkeypatch.setattr(core, "handle_input", tracked)
    for _ in range(2):
        stdin(monkeypatch, envelope())
        run_transcript_review(args(), lambda: core)
    turns = core.memory_service.repository.fetch_recent_turns("review-test", 10)
    assert len(turns) == 2 and len(request_ids) == 2 and request_ids[0] != request_ids[1]


def test_core_failure_fixed_no_retry_no_success_downgrade(monkeypatch):
    class BrokenCore:
        calls = 0

        def handle_input(self, contract):
            self.calls += 1
            raise RuntimeError("private-marker secret-file /private/path")

    core = BrokenCore()
    stdin(monkeypatch, envelope())
    with pytest.raises(ConsoleCommandError) as error:
        run_transcript_review(args(), lambda: core)
    assert core.calls == 1
    assert error.value.error_code == "transcript_handoff_refused"
    assert "private-marker" not in str(error.value)


def test_invalid_core_final_is_not_displayed_or_retried(monkeypatch, tmp_path):
    from apps.jarvis_console.voice_pilot import _isolated_core

    core = _isolated_core(tmp_path / "runtime")
    original = core.handle_input
    calls = []

    def wrong(contract):
        calls.append(contract)
        return replace(original(contract), request_id="private-marker")

    monkeypatch.setattr(core, "handle_input", wrong)
    stdin(monkeypatch, envelope())
    with pytest.raises(ConsoleCommandError) as error:
        run_transcript_review(args(include_content=True), lambda: core)
    assert len(calls) == 1 and "private-marker" not in str(error.value)
