"""Explicit readonly export of a newly bound canonical conversation.

Only caller-selected quiescent SQLite stores are read. Content-free event
bindings establish consistency, not cryptographic origin/authentication. Old
turns without conversation_readback are refused, never backfilled. Pseudonyms
are not guaranteed anonymity; display filters are not universal PII detection.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import stat
import sys
import time
import unicodedata
from contextlib import ExitStack, closing
from datetime import datetime
from hashlib import sha256
from math import isfinite
from pathlib import Path
from threading import Event

from apps.jarvis_console.bootstrap import ROOT
from apps.jarvis_console.review_input import _requires_redaction
from apps.jarvis_console.runtime import ConsoleRuntime

SCHEMA = "jarvis-conversation-pack-v1"
MAX_PACK_BYTES = 262_144
MAX_EVENT_BYTES = 1_048_576
_EVENT_NAMES = ("input_received", "governance_checked", "response_synthesized", "memory_recorded")
_GENERATIVE_KEYS = {"generative_status", "generative_error_code", "generative_evidence_mode",
                    "generative_analysis_characters"}
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")
_INTENT = re.compile(r"[a-z][a-z_]{0,63}\Z", re.ASCII)
_CODE = re.compile(r"[a-z][a-z0-9_]{0,79}\Z", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


def _refuse():
    raise ValueError("conversation_export_refused")


def _text(value, maximum):
    if (type(value) is not str or not 1 <= len(value) <= maximum
            or not value.strip() or any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                                       and c not in "\r\n\t" for c in value)):
        _refuse()
    value.encode("utf-8", "strict")
    return value


def _identifier(value):
    _text(value, 512)
    if value != value.strip() or any(c.isspace() for c in value):
        _refuse()
    return value


def _stamp(value):
    if type(value) is not str or not _UTC.fullmatch(value):
        _refuse()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _refuse()


def _digest(value):
    return sha256(value.encode("utf-8", "strict")).hexdigest()


def _pseudonym(kind, value):
    return kind + ":sha256:" + _digest(value)


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            _refuse()
        result[key] = value
    return result


def _payload(value):
    if type(value) is not str or len(value.encode("utf-8")) > MAX_EVENT_BYTES:
        _refuse()
    result = json.loads(value, object_pairs_hook=_pairs, parse_constant=lambda _: _refuse())
    if type(result) is not dict:
        _refuse()
    json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8", "strict")
    return result


def _file_state(path):
    path = Path(path)
    if not path.is_absolute():
        _refuse()
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            _refuse()
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or not 100 <= info.st_size <= 268_435_456):
        _refuse()
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        _refuse()
    with path.open("rb") as stream:
        header = stream.read(100)
    if header[:16] != b"SQLite format 3\x00" or header[18:20] != b"\x01\x01":
        _refuse()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _open(path, stack, check, table):
    connection = stack.enter_context(closing(sqlite3.connect(
        path.as_uri() + "?mode=ro", uri=True, timeout=0.1,
    )))
    connection.row_factory = sqlite3.Row
    connection.enable_load_extension(False)
    connection.execute("PRAGMA query_only=ON")

    def authorize(action, argument1, argument2, database, _trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            return (sqlite3.SQLITE_OK if database == "main"
                    and argument1 in {table, "sqlite_master", "sqlite_schema"}
                    else sqlite3.SQLITE_DENY)
        if action == sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_OK if argument2 == "length" else sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_TRANSACTION and argument1 in {"BEGIN", "ROLLBACK"}:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    connection.set_authorizer(authorize)

    def progress():
        try:
            check()
            return 0
        except Exception:
            return 1

    connection.set_progress_handler(progress, 1000)
    connection.execute("BEGIN")
    objects = connection.execute("SELECT type, sql FROM sqlite_master WHERE name = ? LIMIT 2",
                                 (table,)).fetchall()
    if (len(objects) != 1 or objects[0]["type"] != "table"
            or type(objects[0]["sql"]) is not str
            or re.match(r"CREATE\s+TABLE\s", objects[0]["sql"], re.IGNORECASE) is None):
        _refuse()
    check()
    return connection


def _generative(payload, decision):
    present = _GENERATIVE_KEYS.intersection(payload)
    if not present:
        return {"generative_status": "disabled", "generative_error_code": None,
                "generative_evidence_mode": None, "generative_analysis_characters": 0}
    if present != _GENERATIVE_KEYS:
        _refuse()
    result = {key: payload[key] for key in _GENERATIVE_KEYS}
    status, code = result["generative_status"], result["generative_error_code"]
    mode, count = result["generative_evidence_mode"], result["generative_analysis_characters"]
    if (type(status) is not str or status not in {"disabled", "accepted", "withheld", "rejected"}
            or type(count) is not int or not 0 <= count <= 8000
            or (code is not None and (type(code) is not str or not _CODE.fullmatch(code)))):
        _refuse()
    if status == "accepted":
        if (decision != "allow" or type(mode) is not str
                or mode not in {"fixture", "injected_transport", "live"}
                or count == 0 or code is not None):
            _refuse()
    elif (mode is not None or count != 0
          or (status == "disabled" and code is not None)
          or (status in {"withheld", "rejected"} and code is None)):
        _refuse()
    return result


def _read(memory, events, *, session_id, request_id, principal_ref, check):
    # Inspect all matching request/correlation envelopes, including wrong-session
    # rows; don't hide mismatches by selecting only the desired session.
    rows = events.execute(
        "SELECT event_name, timestamp, source_service, request_id, correlation_id, "
        "session_id, mission_id, CASE WHEN length(CAST(payload AS BLOB)) <= ? "
        "THEN payload ELSE NULL END AS payload FROM internal_events "
        "WHERE (request_id = ? OR correlation_id = ?) "
        "AND event_name IN (?, ?, ?, ?) LIMIT 5",
        (MAX_EVENT_BYTES, request_id, request_id, *_EVENT_NAMES),
    ).fetchall()
    check()
    if len(rows) != 4 or {row["event_name"] for row in rows} != set(_EVENT_NAMES):
        _refuse()
    envelopes = {row["event_name"]: row for row in rows}
    if any(row["request_id"] != request_id or row["correlation_id"] != request_id
           or row["session_id"] != session_id or row["source_service"] != "orchestrator-service"
           for row in rows):
        _refuse()
    missions = {row["mission_id"] for row in rows}
    if len(missions) != 1:
        _refuse()
    payloads = {name: _payload(envelopes[name]["payload"]) for name in _EVENT_NAMES}
    memory_payload = payloads["memory_recorded"]
    record = _identifier(memory_payload.get("memory_record_id"))
    if memory_payload.get("record_type") != "interaction_turn":
        _refuse()
    binding = memory_payload.get("conversation_readback")
    keys = {"schema_version", "record_timestamp", "principal_sha256", "request_content_sha256",
            "response_text_sha256"}
    if (type(binding) is not dict or set(binding) != keys
            or binding["schema_version"] != "jarvis-conversation-readback-v1"
            or binding["principal_sha256"] != _digest(principal_ref)):
        _refuse()
    for key in ("principal_sha256", "request_content_sha256", "response_text_sha256"):
        if type(binding[key]) is not str or not _HASH.fullmatch(binding[key]):
            _refuse()
    timestamp = binding["record_timestamp"]
    recorded = _stamp(timestamp)
    timeline = [_stamp(envelopes[name]["timestamp"]) for name in _EVENT_NAMES]
    if not timeline[0] <= timeline[1] <= timeline[2] <= recorded <= timeline[3]:
        _refuse()
    turns = memory.execute(
        "SELECT session_id, user_id, mission_id, intent, timestamp, "
        "CASE WHEN length(request_content) <= 16000 THEN request_content ELSE NULL END AS query, "
        "CASE WHEN length(response_text) <= 131072 THEN response_text ELSE NULL END AS response "
        "FROM interaction_turns WHERE session_id = ? AND timestamp = ? LIMIT 2",
        (session_id, timestamp),
    ).fetchall()
    check()
    if len(turns) != 1:
        _refuse()
    turn = turns[0]
    if (turn["user_id"] != principal_ref or turn["mission_id"] not in missions
            or turn["session_id"] != session_id or turn["timestamp"] != timestamp):
        _refuse()
    query, response = _text(turn["query"], 16000), _text(turn["response"], 131072)
    received = payloads["input_received"]
    if (received.get("content") != query
            or (received.get("canonical_user_ref") is not None
                and received["canonical_user_ref"] != principal_ref)
            or binding["request_content_sha256"] != _digest(query)
            or binding["response_text_sha256"] != _digest(response)):
        _refuse()
    intent = turn["intent"]
    if (type(intent) is not str or not _INTENT.fullmatch(intent)
            or payloads["response_synthesized"].get("intent") != intent):
        _refuse()
    decision = payloads["governance_checked"].get("decision")
    if type(decision) is not str or decision not in {"allow", "block", "defer_for_validation"}:
        _refuse()
    generation = _generative(payloads["response_synthesized"], decision)
    if generation["generative_analysis_characters"] > len(response):
        _refuse()
    # A second request cannot legitimately point at this one-shot record ID.
    reuse = events.execute(
        "SELECT CASE WHEN length(CAST(payload AS BLOB)) <= ? THEN payload ELSE NULL END AS payload "
        "FROM internal_events WHERE event_name = 'memory_recorded' AND session_id = ? LIMIT 1001",
        (MAX_EVENT_BYTES, session_id),
    ).fetchall()
    check()
    if len(reuse) > 1000 or sum(_payload(row["payload"]).get("memory_record_id") == record
                               for row in reuse) != 1:
        _refuse()
    return query, response, timestamp, intent, decision, generation, record


def export_conversation(*, memory_db: Path, events_db: Path, session_id, request_id, principal_ref,
                        authorized=False, include_content=False, cancellation=None) -> dict:
    try:
        if (authorized is not True or type(include_content) is not bool
                or (cancellation is not None and not isinstance(cancellation, Event))):
            _refuse()
        for value in (session_id, request_id, principal_ref):
            _identifier(value)
        token = cancellation if cancellation is not None else Event()
        last = time.monotonic()
        if type(last) not in {int, float} or not isfinite(last):
            _refuse()
        deadline = last + 10.0

        def check():
            nonlocal last
            cancelled, now = token.is_set(), time.monotonic()
            if (type(cancelled) is not bool or cancelled or type(now) not in {int, float}
                    or not isfinite(now) or now < last or now >= deadline):
                _refuse()
            last = now

        check()
        paths = (Path(memory_db), Path(events_db))
        before = tuple(_file_state(path) for path in paths)
        if paths[0].resolve() == paths[1].resolve():
            _refuse()
        check()
        with ExitStack() as stack:
            memory, events = (_open(path, stack, check, table) for path, table in zip(
                paths, ("interaction_turns", "internal_events"), strict=True,
            ))
            query, response, stamp, intent, decision, generation, record = _read(
                memory, events, session_id=session_id, request_id=request_id,
                principal_ref=principal_ref, check=check,
            )
            check()
        if tuple(_file_state(path) for path in paths) != before:
            _refuse()
        redactor = ConsoleRuntime(output_format="json",
                                  sensitive_paths=(str(ROOT), str(Path.home())))
        withheld = include_content and _requires_redaction([query, response], redactor)
        included = include_content and not withheld
        result = {
            "schema_version": SCHEMA, "authority": "none", "operator_authenticated": False,
            "runtime_capability_promoted": False, "origin": "canonical_core_export",
            "content_included": included, "content_withheld": withheld,
            "principal_ref": _pseudonym("principal", principal_ref),
            "session_ref": _pseudonym("session", session_id),
            "request_ref": _pseudonym("request", request_id),
            "memory_record_ref": _pseudonym("memory-record", record),
            "timestamp": stamp, "intent": intent, "governance_decision": decision,
            **generation, "request_character_count": len(query),
            "response_character_count": len(response), "content_sha256": None,
        }
        if included:
            result.update(query=query, response_text=response,
                          content_sha256=_digest(SCHEMA + "\0" + query + "\0" + response))
        encoded = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_PACK_BYTES or redactor.redact(encoded.decode("utf-8"))[1]:
            _refuse()
        check()
        return result
    except Exception:
        raise ValueError("conversation_export_refused") from None


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        # argparse's default diagnostic can echo private argv values/paths.
        _refuse()


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--memory-db", required=True, type=Path)
    parser.add_argument("--events-db", required=True, type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--principal-ref", required=True,
                        help="Exact canonical Memory user_id, not provider/operator identity.")
    parser.add_argument("--include-content", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = export_conversation(**vars(args))
    except Exception:
        print(json.dumps({"error_code": "conversation_export_refused"}))
        return 2
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="strict")
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
