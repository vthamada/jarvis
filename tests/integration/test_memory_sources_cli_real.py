"""Real canonical Memory/readonly process CLIs; no account or model."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from apps.jarvis_console import memory_retention_cli as retention
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId

ROOT = Path(__file__).resolve().parents[2]
SUBJECT, SESSION = "user://private-retention-fixture", "private-session"


def fingerprint(directory):
    return {item.name: (hashlib.sha256(item.read_bytes()).hexdigest(), item.stat().st_mtime_ns,
                        item.stat().st_size) for item in directory.iterdir() if item.is_file()}


def canonical_source(directory):
    core = _isolated_core(directory)
    result = core.handle_input(InputContract(
        request_id=RequestId("retention-source-1"), session_id=SessionId(SESSION),
        user_id=SUBJECT, canonical_user_ref=SUBJECT, surface_session_id=SESSION,
        channel=ChannelType.CONSOLE, input_type=InputType.TEXT,
        content="Compare the pilot documentation and observability reports.",
        timestamp=datetime.now(UTC).isoformat(), requested_autonomy_level="assist_only",
        max_autonomy_level="assist_only",
    ))
    turns = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(turns) == 1 and turns[0].response_text == result.response_text
    as_of = (datetime.fromisoformat(turns[0].timestamp) + timedelta(days=31)).isoformat()
    return directory / "memory.db", as_of


def invoke_memory(directory, path, as_of, *, extra=(), authorized=True, subject=SUBJECT,
                  session=SESSION):
    command = [sys.executable, "-m", "apps.jarvis_console.memory_retention_cli",
               "--memory-db", str(path), "--subject-id", subject,
               "--session-id", session, "--as-of", as_of, *extra]
    if authorized:
        command.append("--authorized")
    return subprocess.run(command, cwd=directory, capture_output=True, timeout=20,
                          env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
                                   DATABASE_URL="postgresql://must-not-connect.invalid/synthetic"))


def test_canonical_core_to_readonly_cli_two_restarts_with_no_writes(tmp_path):
    path, as_of = canonical_source(tmp_path)
    before = fingerprint(tmp_path)
    products = [invoke_memory(tmp_path, path, as_of) for _ in range(2)]
    assert all(item.returncode == 0 and not item.stderr for item in products)
    assert products[0].stdout == products[1].stdout
    result = json.loads(products[0].stdout)
    assert result["schema_version"] == "jarvis-memory-retention-review-v1"
    assert result["status"] == "review_ready" and result["candidate_count"] == 1
    assert result["items"][0]["reasons"] == ["age_horizon_exceeded"]
    assert result["review_only"] is True and result["mutation_performed"] is False
    assert result["authority"] == "none" and result["operator_authenticated"] is False
    assert b"private" not in products[0].stdout and b"source_ref" not in products[0].stdout
    assert fingerprint(tmp_path) == before
    restarted = _isolated_core(tmp_path)
    assert restarted.memory_service.repository.fetch_recent_turns(SESSION, 10)[0].response_text


@pytest.mark.parametrize("case", ["unauthorized", "foreign_subject", "foreign_session", "missing",
                                    "wal", "mixed_history", "mixed_older_history", "too_many",
                                    "duplicate_scope"])
def test_retention_scope_failures_have_no_partial_output_or_writes(tmp_path, case):
    path, as_of = canonical_source(tmp_path)
    if case == "wal":
        path.with_name(path.name + "-wal").write_bytes(b"synthetic")
    if case in {"mixed_history", "mixed_older_history", "too_many"}:
        with sqlite3.connect(path) as db:
            if case == "mixed_history":
                db.execute("UPDATE interaction_turns SET user_id='foreign-subject'")
            else:
                names = [row[1] for row in db.execute("PRAGMA table_info(interaction_turns)")]
                columns = ",".join(name for name in names if name != "id")
                # Populate 101 fixture rows, retaining canonical scope and source
                # columns; this is test setup, never production retention logic.
                for _ in range(1 if case == "mixed_older_history" else 100):
                    db.execute(f"INSERT INTO interaction_turns ({columns}) "
                               f"SELECT {columns} FROM interaction_turns LIMIT 1")
                if case == "mixed_older_history":
                    db.execute("UPDATE interaction_turns SET user_id='foreign-subject', "
                               "timestamp='2000-01-01T00:00:00Z' "
                               "WHERE id=(SELECT MIN(id) FROM interaction_turns)")
    before = fingerprint(tmp_path)
    result = invoke_memory(
        tmp_path, tmp_path / "missing.db" if case == "missing" else path, as_of,
        authorized=case != "unauthorized",
        subject="foreign" if case == "foreign_subject" else SUBJECT,
        session="foreign-session" if case == "foreign_session" else SESSION,
        extra=("--session-id", SESSION) if case == "duplicate_scope" else (),
    )
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr) == {"error_code": "memory_retention_refused"}
    assert fingerprint(tmp_path) == before


def test_retention_revalidates_file_identity_after_plan(tmp_path, monkeypatch):
    from memory_service import retention_review

    path, as_of = canonical_source(tmp_path)
    original = retention_review.build_retention_review

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        info = path.stat()
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 10_000_000))
        return result

    monkeypatch.setattr(retention_review, "build_retention_review", changed)
    with pytest.raises(ValueError, match="^memory_retention_refused$"):
        retention.build_memory_retention_report(
            authorized=True, database_path=path, subject_id=SUBJECT,
            session_ids=(SESSION,), as_of=as_of,
        )


def document():
    return {
        "schema_version": "jarvis-source-comparison-input-v1", "as_of": "2026-10-13T12:00:00Z",
        "sources": [
            {"source_ref": "private-source-a", "text": "status: enabled", "observed_at":
             "2026-10-12T12:00:00Z", "expires_at": "2026-10-14T12:00:00Z"},
            {"source_ref": "private-source-b", "text": "status: disabled", "observed_at":
             "2026-10-12T12:00:00Z", "expires_at": None},
        ],
        "claims": [
            {"topic_ref": "private-topic", "source_ref": "private-source-a", "start": 8, "end": 15},
            {"topic_ref": "private-topic", "source_ref": "private-source-b", "start": 8, "end": 16},
        ],
    }


def invoke_sources(directory, source, *options):
    return subprocess.run(
        [sys.executable, "-m", "apps.jarvis_console.source_comparison_cli", *options],
        cwd=directory, input=source, capture_output=True, timeout=20,
        env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1"),
    )


def test_source_comparison_cli_real_pipe_metadata_and_content_opt_in(tmp_path):
    raw = json.dumps(document()).encode("utf-8")
    first, replay = (invoke_sources(tmp_path, raw, "--authorized") for _ in range(2))
    assert first.returncode == replay.returncode == 0 and not first.stderr
    assert first.stdout == replay.stdout
    result = json.loads(first.stdout)
    assert result["topics"][0]["state"] == "text_disagreement"
    assert result["facts_verified"] is False and result["authority"] == "none"
    assert b"private" not in first.stdout and b"disabled" not in first.stdout
    display = invoke_sources(tmp_path, raw, "--authorized", "--include-content")
    assert display.returncode == 0 and not display.stderr
    quotes = {item["quote"] for item in json.loads(display.stdout)["review_claims"]}
    assert quotes == {"enabled", "disabled"}
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "raw", [b'{}', b'\xff', b'{"private":"secret"}',
            b'{"schema_version":1,"schema_version":2}', b'x' * 65537],
    ids=["empty_envelope", "invalid_utf8", "extra_fields", "duplicate_keys", "oversized"],
)
def test_source_invalid_pipes_are_bounded_and_refused_without_reflection(tmp_path, raw):
    result = invoke_sources(tmp_path, raw, "--authorized")
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr) == {"error_code": "source_comparison_refused"}
    assert not list(tmp_path.iterdir())
