import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import connect

import pytest
from memory_service.repository import SqliteMemoryRepository, StoredTurn, StoredUserScopeSnapshot

from apps.jarvis_console import cli


def seed(tmp_path, *, mixed=False, orphan=False):
    path = (tmp_path / "private-memory.sqlite3").resolve()
    repository = SqliteMemoryRepository(path)
    source = StoredTurn("private-session", "mission-a", "private-subject",
                        "UniqueQuery café aprovado 50\x1b[31m\u202e", "report",
                        "source response\nnext line", datetime.now(timezone.utc).isoformat())
    if not orphan:
        repository.record_turn(source)
    if mixed:
        # The newest row is scoped, but an older row still belongs to another subject.
        repository.record_turn(replace(source, user_id="other-subject", request_content="secret",
                                       timestamp="2020-01-01T00:00:00Z"))
    repository.upsert_user_scope_snapshot(StoredUserScopeSnapshot(
        user_id="private-subject", context_status="active", interaction_count=1,
        updated_at=datetime.now(timezone.utc).isoformat(), recent_session_ids=["private-session"],
    ))
    if orphan:
        with connect(path) as connection:
            connection.execute(
                "INSERT INTO session_context(session_id,recent_summary,updated_at) VALUES(?,?,?)",
                ("private-session", "orphan", "2026-10-04T00:00:00Z"),
            )
    with connect(path) as connection:
        connection.execute("PRAGMA journal_mode=DELETE")
    return path


def args(path, *extras):
    return ["memory-recall", "--memory-db", str(path), "--subject-id", "private-subject",
            "--session-id", "private-session", "--query", "UniqueQuery", *extras]


def test_cli_standalone_defaults_redact_data_without_writes(tmp_path, capsys, monkeypatch):
    path = seed(tmp_path)
    before = path.read_bytes()
    before_inventory = sorted(p.name for p in tmp_path.iterdir())
    monkeypatch.setattr(cli.JarvisConsole, "build", lambda **_: pytest.fail("Core built"))
    assert cli.main(args(path, "--format", "json")) == 0
    text = capsys.readouterr().out
    projection = json.loads(json.loads(text)["outputs"][0])
    assert projection["status"] == "selected"
    assert projection["selected_count"] == 1
    assert projection["contains_content"] is False
    assert projection["authority"] == "none"
    for private in ("UniqueQuery", "café", "response", "private-subject", "private-session",
                    str(path), "matching_tokens", "request_content", "response_text"):
        assert private not in text
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == before_inventory


@pytest.mark.parametrize("format", ["json", "text"])
def test_content_optin_escapes_controls_and_bidi(tmp_path, capsys, format):
    path = seed(tmp_path)
    assert cli.main(args(path, "--include-content", "--format", format)) == 0
    text = capsys.readouterr().out
    assert "\x1b" not in text and "\u202e" not in text
    assert "private-subject" not in text and "private-session" not in text
    if format == "json":
        assert text.isascii()
        payload = json.loads(json.loads(text)["outputs"][0])
        assert "café" in payload["items"][0]["request_content"]
        assert "\x1b" in payload["items"][0]["request_content"]
    else:
        assert "\\u001b" in text and "\\u202e" in text
        assert "\\u000a" in text


@pytest.mark.parametrize("case", ["mixed", "orphan", "subject", "session", "duplicate"])
def test_scope_failclosed_no_partial_or_private_error(tmp_path, capsys, case):
    path = seed(tmp_path, mixed=case == "mixed", orphan=case == "orphan")
    invocation = args(path, "--format", "json")
    if case == "subject":
        invocation[invocation.index("private-subject")] = "missing-subject"
    if case == "session":
        invocation[invocation.index("private-session")] = "outside-session"
    if case == "duplicate":
        invocation += ["--session-id", "private-session"]
    before = path.read_bytes()
    assert cli.main(invocation) == 3
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)["error_code"] == "memory_recall_refused"
    for private in (str(path), "private-subject", "private-session", "UniqueQuery", "secret"):
        assert private not in captured.err
    assert path.read_bytes() == before


@pytest.mark.parametrize("case", ["missing", "relative", "directory", "invalid", "oversized"])
def test_invalid_database_never_creates_or_initializes(tmp_path, capsys, case):
    path = (tmp_path / "private.sqlite3").resolve()
    if case == "relative":
        path = Path("private-relative-nonexistent.sqlite3")
    elif case == "directory":
        path.mkdir()
    elif case == "invalid":
        path.write_bytes(b"not a SQLite database" * 20)
    elif case == "oversized":
        with path.open("wb") as handle:
            handle.truncate(128 * 1024 * 1024 + 1)
    before = sorted(p.name for p in tmp_path.iterdir())
    assert cli.main(args(path, "--format", "json")) == 3
    captured = capsys.readouterr()
    assert json.loads(captured.err)["error_code"] == "memory_recall_refused"
    assert str(path) not in captured.err
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    if case in {"missing", "relative"}:
        assert not path.exists()


def test_redirected_ancestor_is_refused(tmp_path, capsys):
    real = tmp_path / "real"
    real.mkdir()
    path = seed(real)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlink permission unavailable; reparse preflight covered by unit")
    assert cli.main(args(alias / path.name, "--format", "json")) == 3
    assert json.loads(capsys.readouterr().err)["error_code"] == "memory_recall_refused"


def test_parser_error_never_echoes_control_argv_or_query(tmp_path, capsys):
    path = seed(tmp_path)
    invocation = args(path, "--format", "json", "--limit", "private\x1b[31m\u202e")
    assert cli.main(invocation) == 2
    output = capsys.readouterr().err
    assert "private" not in output
    assert "UniqueQuery" not in output
    assert "\x1b" not in output and "\u202e" not in output


def test_selector_budget_and_output_limit_are_not_silent_partial_success(tmp_path, capsys):
    path = seed(tmp_path)
    writer = SqliteMemoryRepository(path)
    for number in range(101):
        writer.record_turn(StoredTurn("private-session", None, "private-subject",
                                     f"UniqueQuery {number}", "report", "",
                                     datetime.now(timezone.utc).isoformat()))
    assert cli.main(args(path, "--format", "json")) == 3
    assert json.loads(capsys.readouterr().err)["error_code"] == "memory_recall_refused"


def test_limit_refuses_out_of_bounds(tmp_path, capsys):
    path = seed(tmp_path)
    assert cli.main(args(path, "--limit", "33", "--format", "json")) == 3
    assert json.loads(capsys.readouterr().err)["error_code"] == "memory_recall_refused"
