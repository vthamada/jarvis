"""Real Core persistence -> readonly review -> restart, without retention writes."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlite3 import connect

from memory_service.readonly_repository import ReadOnlySqliteMemoryRepository
from memory_service.recall import RecallScope, RecallSourceState, turn_source_ref
from memory_service.retention_review import build_retention_review

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId


def _input(subject, session, request, content):
    return InputContract(
        request_id=RequestId(request), session_id=SessionId(session),
        channel=ChannelType.CHAT, input_type=InputType.TEXT, content=content,
        timestamp=datetime.now(timezone.utc).isoformat(), user_id=subject,
        canonical_user_ref=subject, surface_id="surface://retention-review-fixture",
        surface_kind="console", surface_session_id=session, surface_capability_scope=[],
        requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
    )


def test_core_canonical_turn_review_and_reader_restart_preserve_bytes(tmp_path: Path):
    runtime = tmp_path / "runtime"
    core = _isolated_core(runtime)
    subject, session = "user://retention-review-fixture", "retention-review-session"
    contract = _input(subject, session, "retention-review-request",
                      "Explain a reversible internal pilot checkpoint without taking actions.")
    response = core.handle_input(contract)
    assert response.operation_dispatch is None and response.operation_result is None
    assert response.memory_record.memory_record_id
    canonical = core.memory_service.repository.fetch_recent_turns(session, 10)
    assert len(canonical) == 1
    assert canonical[0].response_text == response.response_text
    foreign_contract = _input("user://foreign-review-fixture", "foreign-review-session",
                              "foreign-review-request", "Explain this private foreign pilot.")
    core.handle_input(foreign_contract)
    database = (runtime / "memory.db").resolve()
    with connect(database) as connection:
        connection.execute("PRAGMA journal_mode=DELETE")
    before = database.read_bytes()
    before_names = sorted(path.relative_to(runtime).as_posix() for path in runtime.rglob("*"))
    reader = ReadOnlySqliteMemoryRepository(database)
    snapshot = reader.fetch_user_scope_snapshot(subject)
    assert snapshot is not None and session in snapshot.recent_session_ids
    now = datetime.fromisoformat(canonical[0].timestamp.replace("Z", "+00:00")) + timedelta(days=60)
    scope = RecallScope(subject, tuple(snapshot.recent_session_ids), now)
    rows = reader.fetch_recent_turns(session, 10)
    rows += reader.fetch_recent_turns("foreign-review-session", 10)
    review = build_retention_review(rows, scope=scope, max_age_seconds=30 * 86400)
    assert review.status == "review_ready"
    assert len(review.items) == 1 and review.items[0].source_ref == turn_source_ref(canonical[0])
    assert review.items[0].reasons == ("age_horizon_exceeded",)
    assert review.metadata()["authority"] == "none"
    for private in (subject, session, contract.content, response.response_text,
                    foreign_contract.content):
        assert private not in json.dumps(review.metadata())
    restarted_reader = ReadOnlySqliteMemoryRepository(database)
    restarted_rows = restarted_reader.fetch_recent_turns(session, 10)
    assert restarted_rows == canonical
    repeated = build_retention_review(restarted_rows, scope=scope,
                                      max_age_seconds=30 * 86400)
    assert repeated.plan_hash == review.plan_hash
    assert database.read_bytes() == before
    after_names = sorted(path.relative_to(runtime).as_posix() for path in runtime.rglob("*"))
    assert after_names == before_names


def test_real_canonical_rows_declared_revocation_is_advisory_not_applied(tmp_path: Path):
    core = _isolated_core(tmp_path / "runtime")
    subject, session = "user://retention-revocation-fixture", "revocation-review-session"
    core.handle_input(_input(subject, session, "revocation-review-request",
                             "Explain how an operator can review memory safely."))
    repository = core.memory_service.repository
    canonical = repository.fetch_recent_turns(session, 10)
    scope = RecallScope(subject, (session,), datetime.now(timezone.utc) + timedelta(seconds=1))
    plan = build_retention_review(canonical, scope=scope, source_states={
        turn_source_ref(canonical[0]): RecallSourceState(status="revoked"),
    })
    assert plan.status == "review_ready"
    assert plan.items[0].reasons == ("declared_revoked",)
    assert plan.metadata()["mutation_performed"] is False
    assert repository.fetch_recent_turns(session, 10) == canonical
    assert build_retention_review(canonical, scope=scope).status == "empty"
