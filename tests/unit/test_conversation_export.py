"""New canonical readback export over owned quiescent synthetic SQLite fixtures."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from threading import Event

import pytest

from apps.jarvis_console import conversation_export as export

PRINCIPAL = "user://synthetic-canonical"
SESSION = "synthetic-session"
REQUEST = "synthetic-request"
RECORD = "synthetic-record"
QUERY = "Compare documentation and observability pilot reports."
FINAL = "Final canônica: evidência disponível, limitações preservadas."
STAMP = "2026-10-06T10:00:04+00:00"


def digest(value):
    return sha256(value.encode("utf-8")).hexdigest()


def binding(query=QUERY, final=FINAL):
    return {"schema_version": "jarvis-conversation-readback-v1", "record_timestamp": STAMP,
            "principal_sha256": digest(PRINCIPAL), "request_content_sha256": digest(query),
            "response_text_sha256": digest(final)}


@pytest.fixture
def stores(tmp_path):
    memory, events = tmp_path / "memory.db", tmp_path / "events.db"
    with sqlite3.connect(memory) as connection:
        connection.execute("CREATE TABLE interaction_turns (session_id TEXT, user_id TEXT, "
                           "mission_id TEXT, request_content TEXT, intent TEXT, "
                           "response_text TEXT, timestamp TEXT)")
        connection.execute("INSERT INTO interaction_turns VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (SESSION, PRINCIPAL, None, QUERY, "analysis", FINAL, STAMP))
    with sqlite3.connect(events) as connection:
        connection.execute("CREATE TABLE internal_events (event_name TEXT, timestamp TEXT, "
                           "source_service TEXT, request_id TEXT, correlation_id TEXT, "
                           "session_id TEXT, mission_id TEXT, payload TEXT)")
        payloads = {
            "input_received": {"content": QUERY, "canonical_user_ref": PRINCIPAL},
            "governance_checked": {"decision": "allow"},
            "response_synthesized": {"intent": "analysis"},
            "memory_recorded": {"memory_record_id": RECORD, "record_type": "interaction_turn",
                                "conversation_readback": binding()},
        }
        for index, (name, payload) in enumerate(payloads.items(), start=1):
            timestamp = f"2026-10-06T10:00:0{index if index < 4 else 5}+00:00"
            connection.execute("INSERT INTO internal_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (name, timestamp, "orchestrator-service", REQUEST, REQUEST,
                                SESSION, None, json.dumps(payload, ensure_ascii=False)))
    return {"memory_db": memory, "events_db": events, "session_id": SESSION,
            "request_id": REQUEST, "principal_ref": PRINCIPAL, "authorized": True}


def change_payload(stores, name, mutate):
    with sqlite3.connect(stores["events_db"]) as connection:
        value = json.loads(connection.execute("SELECT payload FROM internal_events "
                                             "WHERE event_name = ?", (name,)).fetchone()[0])
        mutate(value)
        connection.execute("UPDATE internal_events SET payload = ? WHERE event_name = ?",
                           (json.dumps(value, ensure_ascii=False), name))


def replace_content(stores, query=QUERY, final=FINAL):
    with sqlite3.connect(stores["memory_db"]) as connection:
        connection.execute("UPDATE interaction_turns SET request_content = ?, response_text = ?",
                           (query, final))
    change_payload(stores, "input_received", lambda value: value.update(content=query))
    change_payload(stores, "memory_recorded",
                   lambda value: value.update(conversation_readback=binding(query, final)))


def refused(stores, **kwargs):
    with pytest.raises(ValueError, match="^conversation_export_refused$"):
        export.export_conversation(**{**stores, **kwargs})


def test_default_only_fixed_metadata_and_pseudonyms(stores):
    result = export.export_conversation(**stores)
    assert set(result) == {
        "schema_version", "authority", "operator_authenticated", "runtime_capability_promoted",
        "origin", "content_included", "content_withheld", "principal_ref", "session_ref",
        "request_ref", "memory_record_ref", "timestamp", "intent", "governance_decision",
        "generative_status", "generative_error_code", "generative_evidence_mode",
        "generative_analysis_characters", "request_character_count", "response_character_count",
        "content_sha256",
    }
    assert result["schema_version"] == export.SCHEMA
    assert result["authority"] == "none" and result["origin"] == "canonical_core_export"
    assert result["operator_authenticated"] is False
    assert result["runtime_capability_promoted"] is False
    assert result["content_included"] is False and result["content_withheld"] is False
    assert result["content_sha256"] is None and result["generative_status"] == "disabled"
    for kind, raw in [("principal", PRINCIPAL), ("session", SESSION), ("request", REQUEST)]:
        assert result[kind + "_ref"] == kind + ":sha256:" + digest(raw)
    assert result["memory_record_ref"] == "memory-record:sha256:" + digest(RECORD)
    serialized = json.dumps(result)
    assert all(value not in serialized
               for value in (PRINCIPAL, SESSION, REQUEST, RECORD, QUERY, FINAL))


def test_included_exact_unicode_and_domain_separated_hash(stores):
    query, final = "Compare relatórios 🧪.", "Final exata\r\nCafé; sem normalização. 🧪"
    replace_content(stores, query, final)
    result = export.export_conversation(**stores, include_content=True)
    assert result["query"] == query and result["response_text"] == final
    assert result["request_character_count"] == len(query)
    assert result["response_character_count"] == len(final)
    assert result["content_sha256"] == digest(export.SCHEMA + "\0" + query + "\0" + final)
    assert result["content_included"] is True and result["content_withheld"] is False


@pytest.mark.parametrize("side", ["query", "final"])
@pytest.mark.parametrize("sensitive", ["password=synthetic-value", "Bearer synthetic-access",
                                      "C:\\Users\\Fixture\\private.txt",
                                      "https://user:secret@example.test/path",
                                      "ghp_SYNTHETIC_EXAMPLE_TOKEN01234567890"])
def test_known_sensitive_content_whole_withheld(stores, side, sensitive):
    replace_content(stores, sensitive if side == "query" else QUERY,
                    sensitive if side == "final" else FINAL)
    result = export.export_conversation(**stores, include_content=True)
    assert result["content_withheld"] is True and result["content_included"] is False
    assert "query" not in result and "response_text" not in result
    assert result["content_sha256"] is None and sensitive not in json.dumps(result)


def test_sqlite_bytes_and_directory_exactly_unchanged(stores):
    directory = stores["memory_db"].parent
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    export.export_conversation(**stores, include_content=True)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before


@pytest.mark.parametrize("changes", [{"authorized": False}, {"authorized": 1},
                                     {"include_content": 1}, {"cancellation": object()},
                                     {"session_id": ""}, {"principal_ref": None},
                                     {"request_id": "bad\nvalue"}])
def test_invalid_options_before_file_read(stores, changes, monkeypatch):
    monkeypatch.setattr(export, "_file_state", lambda _: pytest.fail("invalid options read file"))
    refused(stores, **changes)


@pytest.mark.parametrize("field,value", [("session_id", "foreign"), ("request_id", "foreign"),
                                        ("principal_ref", "operator://not-memory-user")])
def test_selected_scope_exact_no_fallback(stores, field, value):
    refused(stores, **{field: value})


@pytest.mark.parametrize("event", export._EVENT_NAMES)
@pytest.mark.parametrize("operation", ["duplicate", "missing", "wrong_session", "wrong_request",
                                      "wrong_correlation", "wrong_source", "wrong_mission"])
def test_event_ambiguity_or_scope_mismatch(stores, event, operation):
    with sqlite3.connect(stores["events_db"]) as connection:
        if operation == "duplicate":
            connection.execute("INSERT INTO internal_events SELECT * FROM internal_events "
                               "WHERE event_name = ?", (event,))
        elif operation == "missing":
            connection.execute("DELETE FROM internal_events WHERE event_name = ?", (event,))
        else:
            column = {"wrong_session": "session_id", "wrong_request": "request_id",
                      "wrong_correlation": "correlation_id", "wrong_source": "source_service",
                      "wrong_mission": "mission_id"}[operation]
            connection.execute(f"UPDATE internal_events SET {column} = 'foreign' "
                               "WHERE event_name = ?", (event,))
    refused(stores)


@pytest.mark.parametrize("mutation", [
    {"schema_version": "wrong"}, {"record_timestamp": "2026-10-06T10:00:03+00:00"},
    {"principal_sha256": digest("foreign")}, {"principal_sha256": None},
    {"request_content_sha256": "0" * 64}, {"response_text_sha256": "0" * 64},
    {"extra": "field"},
])
def test_new_memory_record_binding_strict(stores, mutation):
    change_payload(stores, "memory_recorded",
                   lambda value: value["conversation_readback"].update(mutation))
    refused(stores)


def test_legacy_event_refused_no_historical_hash_backfill(stores):
    change_payload(stores, "memory_recorded", lambda value: value.pop("conversation_readback"))
    refused(stores)


@pytest.mark.parametrize("field,value", [("user_id", "foreign"), ("mission_id", "foreign"),
                                        ("request_content", "forged"), ("response_text", "forged"),
                                        ("intent", "planning"), ("timestamp", "foreign")])
def test_turn_mismatches_refused(stores, field, value):
    with sqlite3.connect(stores["memory_db"]) as connection:
        connection.execute(f"UPDATE interaction_turns SET {field} = ?", (value,))
    refused(stores)


def test_duplicate_turn_cannot_pick_latest(stores):
    with sqlite3.connect(stores["memory_db"]) as connection:
        connection.execute("INSERT INTO interaction_turns SELECT * FROM interaction_turns")
    refused(stores)


@pytest.mark.parametrize("canonical", ["foreign", 123])
def test_input_canonical_user_does_not_override_memory_user(stores, canonical):
    change_payload(stores, "input_received",
                   lambda value: value.update(canonical_user_ref=canonical))
    refused(stores)


def test_null_input_canonical_ref_keeps_actual_memory_user_binding(stores):
    change_payload(stores, "input_received", lambda value: value.update(canonical_user_ref=None))
    expected = "principal:sha256:" + digest(PRINCIPAL)
    assert export.export_conversation(**stores)["principal_ref"] == expected


@pytest.mark.parametrize("decision", ["allow", "block", "defer_for_validation"])
def test_native_governance_retained(stores, decision):
    change_payload(stores, "governance_checked", lambda value: value.update(decision=decision))
    assert export.export_conversation(**stores)["governance_decision"] == decision


def generative(status="accepted", **changes):
    return {"generative_status": status, "generative_error_code": None,
            "generative_evidence_mode": "fixture", "generative_analysis_characters": 42,
            **changes}


@pytest.mark.parametrize("mode", ["fixture", "injected_transport", "live"])
def test_accepted_generative_metadata_exact(stores, mode):
    change_payload(stores, "response_synthesized",
                   lambda value: value.update(generative(generative_evidence_mode=mode)))
    result = export.export_conversation(**stores)
    assert result["generative_status"] == "accepted" and result["generative_evidence_mode"] == mode
    assert result["generative_analysis_characters"] == 42


@pytest.mark.parametrize("changes", [
    {"generative_status": "partial"}, {"generative_status": None},
    {"generative_error_code": "unexpected_error"}, {"generative_evidence_mode": None},
    {"generative_evidence_mode": "promoted"}, {"generative_analysis_characters": 0},
    {"generative_analysis_characters": True}, {"generative_analysis_characters": 8001},
])
def test_incoherent_generative_metadata_refused(stores, changes):
    change_payload(stores, "response_synthesized",
                   lambda value: value.update(generative(**changes)))
    refused(stores)


@pytest.mark.parametrize("key", tuple(export._GENERATIVE_KEYS))
def test_partial_new_fields_cannot_default_to_disabled(stores, key):
    change_payload(stores, "response_synthesized",
                   lambda value: value.update({key: generative()[key]}))
    refused(stores)


@pytest.mark.parametrize("decision", ["block", "defer_for_validation"])
def test_accepted_generative_for_nonallow_refused(stores, decision):
    change_payload(stores, "governance_checked", lambda value: value.update(decision=decision))
    change_payload(stores, "response_synthesized", lambda value: value.update(generative()))
    refused(stores)


@pytest.mark.parametrize("status", ["withheld", "rejected"])
def test_nonaccepted_metadata_retained_without_candidate(stores, status):
    fields = generative(status, generative_evidence_mode=None, generative_analysis_characters=0,
                        generative_error_code="bounded_refusal")
    change_payload(stores, "response_synthesized", lambda value: value.update(fields))
    assert export.export_conversation(**stores)["generative_status"] == status


@pytest.mark.parametrize("stamp", ["2026-10-06T10:00:04", "2026-10-06T10:00:04-03:00",
                                   "2026-10-06T10:00:04.1234567Z", "2026-02-30T10:00:04Z"])
def test_timestamp_bounds_and_actual_utc(stores, stamp):
    change_payload(stores, "memory_recorded",
                   lambda value: value["conversation_readback"].update(record_timestamp=stamp))
    refused(stores)


@pytest.mark.parametrize("unsafe", ["null\0byte", "bad\u202econtrol", "bad\x1bterminal"])
def test_source_controls_rejected_even_metadata_only(stores, unsafe):
    replace_content(stores, final=unsafe)
    refused(stores)


@pytest.mark.parametrize("side", ["query", "response"])
def test_content_bounds_no_truncation(stores, side):
    replace_content(stores, query="x" * 16001 if side == "query" else QUERY,
                    final="x" * 131073 if side == "response" else FINAL)
    refused(stores)


def test_pack_encoded_bytes_limit(stores):
    replace_content(stores, final="🧪" * 100000)
    assert export.export_conversation(**stores)["response_character_count"] == 100000
    refused(stores, include_content=True)


@pytest.mark.parametrize("name", ["input_received", "memory_recorded"])
def test_duplicate_json_field_refused(stores, name):
    with sqlite3.connect(stores["events_db"]) as connection:
        connection.execute("UPDATE internal_events SET payload = ? WHERE event_name = ?",
                           ('{"content":"a","content":"b"}', name))
    refused(stores)


def test_large_event_payload_refused_before_projection(stores):
    with sqlite3.connect(stores["events_db"]) as connection:
        connection.execute("UPDATE internal_events SET payload = ? "
                           "WHERE event_name = 'memory_recorded'",
                           ("x" * (export.MAX_EVENT_BYTES + 1),))
    refused(stores)


def test_cancel_before_or_after_reads(stores, monkeypatch):
    token = Event()
    token.set()
    refused(stores, cancellation=token)
    token.clear()
    read = export._read

    def cancelling(*args, **kwargs):
        result = read(*args, **kwargs)
        token.set()
        return result

    monkeypatch.setattr(export, "_read", cancelling)
    refused(stores, cancellation=token)


@pytest.mark.parametrize("sidecar", ["-wal", "-shm", "-journal"])
def test_sidecar_presence_refused_without_delete(stores, sidecar):
    target = Path(str(stores["memory_db"]) + sidecar)
    target.write_bytes(b"synthetic private sidecar")
    refused(stores)
    assert target.read_bytes() == b"synthetic private sidecar"


def test_wal_database_not_opened_as_immutable(stores):
    with sqlite3.connect(stores["memory_db"]) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    refused(stores)


def test_nonexistent_database_never_created(stores, tmp_path):
    target = tmp_path / "not-created.db"
    refused(stores, memory_db=target)
    assert not target.exists()


def test_relative_database_refused(stores):
    refused(stores, memory_db=Path("memory.db"))


def test_changed_file_after_readback_refused(stores, monkeypatch):
    state = export._file_state
    calls = []

    def changed(path):
        original = state(path)
        calls.append(path)
        return original if len(calls) <= 2 else (*original[:-1], original[-1] + 1)

    monkeypatch.setattr(export, "_file_state", changed)
    refused(stores)


@pytest.mark.parametrize("database,table", [("memory_db", "interaction_turns"),
                                          ("events_db", "internal_events")])
def test_views_not_evaluated_as_canonical_tables(stores, database, table):
    with sqlite3.connect(stores[database]) as connection:
        connection.execute(f"ALTER TABLE {table} RENAME TO disguised_rows")
        connection.execute(f"CREATE VIEW {table} AS SELECT * FROM disguised_rows")
    refused(stores)


def test_reused_record_id_ambiguous_even_different_request(stores):
    with sqlite3.connect(stores["events_db"]) as connection:
        row = list(connection.execute("SELECT * FROM internal_events "
                                      "WHERE event_name = 'memory_recorded'").fetchone())
        row[3] = row[4] = "foreign-request"
        connection.execute("INSERT INTO internal_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row)
    refused(stores)


def test_read_scope_bounds_fail_not_silently_truncate(stores):
    with sqlite3.connect(stores["events_db"]) as connection:
        row = list(connection.execute("SELECT * FROM internal_events "
                                      "WHERE event_name = 'memory_recorded'").fetchone())
        for index in range(1000):
            row[3] = row[4] = f"unrelated-request-{index}"
            row[7] = json.dumps({"memory_record_id": f"unrelated-record-{index}"})
            connection.execute("INSERT INTO internal_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row)
    refused(stores)


def test_connection_is_ro_and_sql_denies_effects(stores, monkeypatch):
    connect = export.sqlite3.connect
    seen = []

    def observed(*args, **kwargs):
        assert args[0].endswith("?mode=ro") and kwargs["uri"] is True
        seen.append(args[0])
        return connect(*args, **kwargs)

    monkeypatch.setattr(export.sqlite3, "connect", observed)
    assert export.export_conversation(**stores)["content_included"] is False
    assert len(seen) == 2


def test_redirected_database_refused_before_open(stores, monkeypatch):
    original = Path.lstat

    def redirected(path):
        if path == stores["memory_db"]:
            value = original(path)
            return type("Info", (), {"st_mode": value.st_mode,
                                      "st_file_attributes": 0x400})()
        return original(path)

    monkeypatch.setattr(Path, "lstat", redirected)
    refused(stores)


def test_analysis_count_cannot_exceed_entire_final(stores):
    change_payload(stores, "response_synthesized",
                   lambda value: value.update(generative(generative_analysis_characters=8000)))
    refused(stores)


def test_cli_stdout_only_and_exact_pack(stores):
    command = [sys.executable, "-m", "apps.jarvis_console.conversation_export", "--authorized",
               "--memory-db", str(stores["memory_db"]), "--events-db", str(stores["events_db"]),
               "--session-id", SESSION, "--request-id", REQUEST, "--principal-ref", PRINCIPAL,
               "--include-content"]
    result = subprocess.run(command, cwd=export.ROOT, capture_output=True, encoding="utf-8",
                            env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=60, check=False)
    assert result.returncode == 0 and result.stderr == ""
    assert json.loads(result.stdout) == export.export_conversation(**stores, include_content=True)


def test_cli_error_only_fixed_diagnostic(stores):
    command = [sys.executable, "-m", "apps.jarvis_console.conversation_export",
               "--memory-db", str(stores["memory_db"]), "--events-db", str(stores["events_db"]),
               "--session-id", SESSION, "--request-id", REQUEST, "--principal-ref", PRINCIPAL]
    result = subprocess.run(command, cwd=export.ROOT, capture_output=True, encoding="utf-8",
                            timeout=60, check=False)
    assert result.returncode == 2 and result.stderr == ""
    assert json.loads(result.stdout) == {"error_code": "conversation_export_refused"}
    assert str(stores["memory_db"]) not in result.stdout


def test_cli_parser_failure_never_echoes_private_argv():
    secret = "Bearer synthetic-secret C:/Users/Fixture/private.db"
    command = [sys.executable, "-m", "apps.jarvis_console.conversation_export", "--output", secret]
    result = subprocess.run(command, cwd=export.ROOT, capture_output=True, encoding="utf-8",
                            timeout=60, check=False)
    assert result.returncode == 2 and result.stderr == ""
    assert json.loads(result.stdout) == {"error_code": "conversation_export_refused"}
    assert secret not in result.stdout
