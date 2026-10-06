from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import connect

from memory_service.readonly_repository import ReadOnlySqliteMemoryRepository
from memory_service.recall import RecallScope, select_readonly_recall, turn_source_ref
from memory_service.repository import (
    SqliteMemoryRepository,
    StoredTurn,
    StoredUserScopeSnapshot,
)


def test_sqlite_canonical_rows_mixed_owner_session_readonly_evidence(tmp_path: Path):
    database = (tmp_path / "canonical.sqlite3").resolve()
    writer = SqliteMemoryRepository(database)
    allowed = StoredTurn("shared-session", "mission-a", "subject-a",
                         "Orçamento café aprovado 50", "report", "Registrado como evidência",
                         "2026-10-03T12:00:00Z")
    denied = StoredTurn("shared-session", "mission-b", "subject-b",
                        "Orçamento café secreto 999", "report", "private response",
                        "2026-10-03T13:00:00Z")
    unbound = StoredTurn("shared-session", None, None, "Orçamento café anônimo", "report", "",
                         "2026-10-03T14:00:00Z")
    outside = StoredTurn("outside-session", "mission-a2", "subject-a",
                         "Orçamento café 100", "report", "",
                         "2026-10-03T15:00:00Z")
    for row in (allowed, denied, unbound, outside):
        writer.record_turn(row)
    writer.upsert_user_scope_snapshot(StoredUserScopeSnapshot(
        user_id="subject-a", context_status="active", interaction_count=2,
        updated_at="2026-10-03T15:00:00Z", recent_session_ids=["shared-session"],
    ))
    # Existing exporter supports quiescent DELETE mode; no schema init/write on reader.
    with connect(database) as connection:
        connection.execute("PRAGMA journal_mode=DELETE")
    before = database.read_bytes()
    before_names = sorted(path.name for path in tmp_path.iterdir())
    reader = ReadOnlySqliteMemoryRepository(database)
    canonical_scope = reader.fetch_user_scope_snapshot("subject-a")
    assert canonical_scope is not None
    scope = RecallScope(canonical_scope.user_id, tuple(canonical_scope.recent_session_ids),
                        datetime(2026, 10, 4, tzinfo=timezone.utc))
    rows = [row for session in scope.session_ids
            for row in reader.fetch_recent_turns(session, limit=20)]
    assert {row.user_id for row in rows} == {"subject-a", "subject-b", None}
    selected = select_readonly_recall(rows, scope=scope, query="orçamento café")
    assert selected.status == "selected"
    assert [item.source_ref for item in selected.items] == [turn_source_ref(allowed)]
    assert "999" not in repr(selected)
    assert "anônimo" not in repr(selected)
    assert selected.authority == "none"
    assert database.read_bytes() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == before_names


def test_real_repository_missing_subject_has_no_fallback_scope(tmp_path: Path):
    database = (tmp_path / "canonical.sqlite3").resolve()
    writer = SqliteMemoryRepository(database)
    writer.record_turn(StoredTurn("guessed-subject-a", None, "subject-b",
                                 "secret orçamento", "report", "", "2026-10-03T12:00:00Z"))
    assert writer.fetch_user_scope_snapshot("subject-a") is None
    scope = RecallScope("subject-a", (), datetime(2026, 10, 4, tzinfo=timezone.utc))
    result = select_readonly_recall(writer.fetch_recent_turns("guessed-subject-a", 10),
                                  scope=scope, query="orçamento")
    assert result.status == "invalid_scope"
    assert not result.items
