"""New-turn correspondence fingerprints are data, never authenticated receipts."""

import hashlib
import json
from dataclasses import replace

import pytest
from orchestrator_service.service import OrchestratorService

from shared.contracts import MemoryRecordContract
from shared.types import MemoryRecordId, SessionId

TIMESTAMP = "2026-10-06T12:34:56.123456+00:00"
PRINCIPAL = "synthetic-private-principal-sentinel"
QUERY = "Compare synthetic-private-query-sentinel."
FINAL = "Canonical synthetic-private-final-sentinel."
FIELDS = {
    "schema_version",
    "record_timestamp",
    "principal_sha256",
    "request_content_sha256",
    "response_text_sha256",
}


def record(**changes):
    values = {
        "memory_record_id": MemoryRecordId("synthetic-readback-record"),
        "record_type": "interaction_turn",
        "source_service": "memory-service",
        "payload": {"request_content": QUERY, "response_text": FINAL},
        "timestamp": TIMESTAMP,
        "session_id": SessionId("synthetic-readback-session"),
        "user_id": PRINCIPAL,
    }
    values.update(changes)
    return MemoryRecordContract(**values)


def readback(value):
    return OrchestratorService._conversation_readback_payload(value)


def digest(text):
    return hashlib.sha256(text.encode("utf-8", errors="strict")).hexdigest()


def test_exact_five_field_schema_and_content_free_correspondence():
    value = record()
    payload = readback(value)
    assert set(payload) == FIELDS
    assert payload == {
        "schema_version": "jarvis-conversation-readback-v1",
        "record_timestamp": TIMESTAMP,
        "principal_sha256": digest(PRINCIPAL),
        "request_content_sha256": digest(QUERY),
        "response_text_sha256": digest(FINAL),
    }
    serialized = json.dumps(payload, ensure_ascii=False)
    for raw in (PRINCIPAL, QUERY, FINAL, str(value.memory_record_id), str(value.session_id)):
        assert raw not in serialized
    assert "authority" not in payload and "authenticated" not in payload


@pytest.mark.parametrize(
    "query,final",
    [
        ("Plain query", "Plain final"),
        ("Análise: documentação e observabilidade.", "Conclusão: revisão necessária."),
        ("Análise: ação 😀", "Final: áudio 🎧"),
        ("line one\r\nline two\r\n", "first\r\nsecond\r\n"),
        ("line one\nline two\n", "first\nsecond\n"),
        (" leading and trailing ", "  preserved  "),
        ("ação", "revisão"),
        ("ação", "revisão"),
        ("\tquery\t", "\tfinal\t"),
        ("", ""),
    ],
)
def test_hashes_match_exact_utf8_without_trim_unicode_or_newline_normalization(query, final):
    value = record(payload={"request_content": query, "response_text": final})
    payload = readback(value)
    assert payload["request_content_sha256"] == digest(query)
    assert payload["response_text_sha256"] == digest(final)
    assert value.payload == {"request_content": query, "response_text": final}
    assert payload["record_timestamp"] == value.timestamp


@pytest.mark.parametrize(
    "first,second",
    [
        ("ação", "ação"),
        ("a\r\nb", "a\nb"),
        ("text", " text"),
        ("text", "text "),
        ("😀", "🙂"),
    ],
)
def test_visually_related_but_byte_distinct_inputs_have_distinct_bindings(first, second):
    one = readback(record(payload={"request_content": first, "response_text": first}))
    two = readback(record(payload={"request_content": second, "response_text": second}))
    assert one["request_content_sha256"] != two["request_content_sha256"]
    assert one["response_text_sha256"] != two["response_text_sha256"]


@pytest.mark.parametrize("principal", ["user://synthetic", "identidade-ação", "subject😀", ""])
def test_principal_hash_is_exact_utf8_and_not_identity_metadata(principal):
    payload = readback(record(user_id=principal))
    assert payload["principal_sha256"] == digest(principal)
    if principal:
        assert principal not in json.dumps(payload)


def test_absent_principal_is_explicitly_unbound_not_manufactured_identity():
    payload = readback(record(user_id=None))
    assert set(payload) == FIELDS
    assert payload["principal_sha256"] is None
    assert payload["request_content_sha256"] == digest(QUERY)
    assert payload["response_text_sha256"] == digest(FINAL)
    # This helper deliberately preserves legacy/native compatibility. An offline
    # exporter must reject this unbound record, not select an ambient principal.


@pytest.mark.parametrize("key", ["request_content", "response_text"])
@pytest.mark.parametrize("invalid", [None, True, 123, 1.5, [], {}, b"bytes"])
def test_invalid_text_types_return_none_without_breaking_native_record(key, invalid):
    payload = {"request_content": QUERY, "response_text": FINAL}
    payload[key] = invalid
    value = record(payload=payload)
    assert readback(value) is None
    assert value.payload[key] is invalid


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"request_content": QUERY},
        {"response_text": FINAL},
        None,
        [],
        "text",
        12,
        True,
    ],
)
def test_missing_or_malformed_payload_returns_none(payload):
    assert readback(record(payload=payload)) is None


@pytest.mark.parametrize("timestamp", [None, "", True, 123, [], {}, b"timestamp"])
def test_invalid_timestamp_types_or_empty_return_none(timestamp):
    assert readback(record(timestamp=timestamp)) is None


@pytest.mark.parametrize("principal", [True, 123, [], {}, b"identity"])
def test_invalid_principal_types_return_none(principal):
    assert readback(record(user_id=principal)) is None


@pytest.mark.parametrize("key", ["query", "final", "principal", "timestamp"])
@pytest.mark.parametrize("surrogate", ["\ud800", "\udfff"])
def test_lone_surrogate_is_unexportable_but_original_native_record_remains(key, surrogate):
    value = record()
    if key == "query":
        value.payload["request_content"] = surrogate
    elif key == "final":
        value.payload["response_text"] = surrogate
    elif key == "principal":
        value.user_id = surrogate
    else:
        value.timestamp = surrogate
    assert readback(value) is None
    assert surrogate in (
        value.payload["request_content"],
        value.payload["response_text"],
        value.user_id,
        value.timestamp,
    )


@pytest.mark.parametrize(
    "record_type", ["mission_state", "semantic_memory", "checkpoint", "", None, True, 123]
)
def test_other_record_types_never_receive_conversation_bindings(record_type):
    assert readback(record(record_type=record_type)) is None


@pytest.mark.parametrize("value", [None, {}, [], "record", object()])
def test_unrecognized_records_return_none(value):
    assert readback(value) is None


@pytest.mark.parametrize("attribute", ["payload", "timestamp", "record_type"])
def test_forged_missing_required_attributes_remain_native_compatible(attribute):
    value = record()
    delattr(value, attribute)
    assert readback(value) is None


def test_dict_subclass_payload_cannot_run_custom_binding_lookup():
    class CustomPayload(dict):
        def __getitem__(self, key):
            pytest.fail("Custom lookup should not be invoked")

    value = record(payload=CustomPayload(request_content=QUERY, response_text=FINAL))
    assert readback(value) is None


def test_extra_native_payload_data_is_not_copied_into_readback():
    value = record(
        payload={
            "request_content": QUERY,
            "response_text": FINAL,
            "history": "PRIVATE_HISTORY_SENTINEL",
            "token": "PRIVATE_TOKEN_SENTINEL",
            "principal": "FORGED_PRINCIPAL_SENTINEL",
            "raw_source": "PRIVATE_SOURCE_SENTINEL",
        }
    )
    payload = readback(value)
    assert set(payload) == FIELDS
    encoded = json.dumps(payload)
    for private in (
        "PRIVATE_HISTORY_SENTINEL",
        "PRIVATE_TOKEN_SENTINEL",
        "FORGED_PRINCIPAL_SENTINEL",
        "PRIVATE_SOURCE_SENTINEL",
    ):
        assert private not in encoded
    assert payload["principal_sha256"] == digest(PRINCIPAL)


def test_existing_binding_does_not_mutate_when_native_record_payload_changes():
    value = record()
    before = readback(value)
    value.payload["response_text"] = "Different canonical final"
    after = readback(value)
    assert before["response_text_sha256"] == digest(FINAL)
    assert after["response_text_sha256"] == digest("Different canonical final")
    assert before["request_content_sha256"] == after["request_content_sha256"]


def test_session_and_record_identifiers_are_not_misrepresented_as_authenticated_binding():
    value = record()
    one = readback(value)
    two = readback(
        replace(
            value,
            memory_record_id=MemoryRecordId("other-record"),
            session_id=SessionId("other-session"),
        )
    )
    assert one == two
    # Event envelope correlation owns these IDs. Hash equality alone is not a
    # receipt, source authenticity check, session authorization or trusted grant.
