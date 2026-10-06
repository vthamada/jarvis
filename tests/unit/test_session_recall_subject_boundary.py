"""Explicit subject session isolation, using disposable real SQLite only.

Repository injections below represent corrupt/imported canonical state, not a
new external memory-write API. Legacy unbound sessions remain compatible.
"""

import re
from dataclasses import replace

import pytest
from memory_service.repository import (
    PostgresMemoryRepository,
    SessionContinuitySnapshot,
    StoredContinuityCheckpoint,
    StoredContinuityPauseResolution,
    StoredTurn,
)
from memory_service.service import MemoryService

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract, MissionStateContract
from shared.types import ChannelType, InputType, MissionId, MissionStatus, RequestId, SessionId

SUBJECT = "public-subject-alpha"
FOREIGN = "public-subject-beta"
SECRET = "foreign-synthetic-sentinel-481"
SESSION = "subject-boundary-session"
STAMP = "2026-10-04T12:00:00Z"


def _input(subject=SUBJECT, *, session=SESSION, mission=None):
    return InputContract(
        request_id=RequestId("subject-boundary-request"),
        session_id=SessionId(session),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Review the existing synthetic evidence only.",
        timestamp=STAMP,
        user_id=subject,
        mission_id=MissionId(mission) if mission else None,
        surface_id="surface://subject-boundary-test",
        surface_kind="console",
        surface_session_id=session,
        canonical_user_ref=f"user://{subject}" if subject else None,
        operator_identity_ref=f"operator://{subject}" if subject else None,
        requested_autonomy_level="assist_only",
        max_autonomy_level="assist_only",
    )


def _memory(tmp_path):
    return MemoryService(database_url=f"sqlite:///{(tmp_path / 'memory.db').as_posix()}")


def _seed(memory, subject, *, session=SESSION, text=SECRET):
    memory.record_turn(
        replace(_input(subject, session=session), content=text),
        "analysis",
        f"Canonical final: {text}",
    )


@pytest.mark.parametrize("stored_subject", [FOREIGN, None])
def test_explicit_subject_cannot_recover_foreign_or_legacy_session(tmp_path, stored_subject):
    memory = _memory(tmp_path)
    _seed(memory, stored_subject)
    before = memory.repository.fetch_recent_turns(SESSION, 100)
    with pytest.raises(ValueError, match="subject|owner|scope"):
        memory.recover_for_input(_input())
    assert memory.repository.fetch_recent_turns(SESSION, 100) == before
    assert memory.repository.fetch_user_scope_snapshot(SUBJECT) is None


@pytest.mark.parametrize("foreign_age", [0, 30])
def test_session_owner_check_is_not_limited_to_recent_turn_window(tmp_path, foreign_age):
    memory = _memory(tmp_path)
    # A foreign historical row must not disappear from the ownership proof just
    # because the normal context payload only returns the latest few turns.
    memory.repository.record_turn(StoredTurn(
        session_id=SESSION,
        mission_id=None,
        user_id=FOREIGN,
        request_content=SECRET,
        intent="analysis",
        response_text=SECRET,
        timestamp="2020-01-01T00:00:00Z",
    ))
    for index in range(max(1, foreign_age)):
        _seed(memory, SUBJECT, text=f"Public own observation {index}")
    before = memory.repository.fetch_recent_turns(SESSION, 100)
    with pytest.raises(ValueError, match="subject|owner|scope"):
        memory.recover_for_input(_input())
    assert memory.repository.fetch_recent_turns(SESSION, 100) == before


@pytest.mark.parametrize("artifact", ["continuity", "checkpoint", "summary", "pause"])
def test_orphan_session_context_cannot_prove_explicit_subject_ownership(tmp_path, artifact):
    memory = _memory(tmp_path)
    if artifact == "continuity":
        memory.repository.upsert_session_continuity(SessionContinuitySnapshot(
            session_id=SESSION,
            continuity_brief=SECRET,
            continuity_mode="continue",
            anchor_mission_id=None,
            anchor_goal=SECRET,
            related_mission_id=None,
            related_goal=None,
            updated_at=STAMP,
        ))
    elif artifact == "checkpoint":
        memory.repository.upsert_continuity_checkpoint(StoredContinuityCheckpoint(
            checkpoint_id="foreign-checkpoint",
            session_id=SESSION,
            continuity_action="continue",
            checkpoint_status="awaiting_validation",
            checkpoint_summary=SECRET,
            updated_at=STAMP,
        ))
    elif artifact == "pause":
        memory.repository.upsert_continuity_pause_resolution(StoredContinuityPauseResolution(
            session_id=SESSION,
            checkpoint_id="foreign-checkpoint",
            resolution_status="approved",
            resolved_at=STAMP,
            resolved_by=FOREIGN,
            resolution_note=SECRET,
        ))
    else:
        # Simulate an imported summary with no corresponding canonical owner row.
        with memory.repository._connect() as connection:
            connection.execute(
                "INSERT INTO session_context (session_id, recent_summary, updated_at) "
                "VALUES (?, ?, ?)", (SESSION, SECRET, STAMP),
            )
    with pytest.raises(ValueError, match="subject|owner|scope"):
        memory.recover_for_input(_input())
    assert memory.repository.fetch_recent_turns(SESSION, 100) == []
    assert memory.repository.fetch_user_scope_snapshot(SUBJECT) is None


def test_explicit_foreign_mission_cannot_enter_recovery_in_a_new_session(tmp_path):
    memory = _memory(tmp_path)
    memory.record_turn(
        replace(_input(FOREIGN, session="foreign-session", mission="foreign-mission"),
                content=SECRET),
        "analysis",
        SECRET,
    )
    memory.repository.upsert_mission_state(MissionStateContract(
        mission_id=MissionId("foreign-mission"),
        mission_goal=SECRET,
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at=STAMP,
        owner_context=FOREIGN,
        semantic_brief=SECRET,
    ))
    with pytest.raises(ValueError, match="subject|owner|scope"):
        memory.recover_for_input(_input(mission="foreign-mission"))
    assert memory.repository.fetch_recent_turns(SESSION, 100) == []


def test_related_mission_candidates_require_subject_proof_not_matching_session_origin(tmp_path):
    memory = _memory(tmp_path)
    _seed(memory, SUBJECT, text="Own synthetic rollout evidence")
    memory.record_turn(
        replace(_input(FOREIGN, session="foreign-session", mission="foreign-related"),
                content=SECRET),
        "analysis",
        SECRET,
    )
    memory.repository.upsert_mission_state(MissionStateContract(
        mission_id=MissionId("foreign-related"),
        mission_goal=f"Review synthetic rollout evidence {SECRET}",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at=STAMP,
        # Imported legacy state can contain a matching session_origin despite
        # canonical owner evidence belonging to another subject/session.
        session_origin=SESSION,
        semantic_brief=SECRET,
        semantic_focus=[SECRET],
        open_loops=[SECRET],
    ))
    recovered = memory.recover_for_input(replace(
        _input(mission="new-own-mission"), content="Review synthetic rollout evidence",
    ))
    assert not any(SECRET in item for item in recovered.recovered_items)
    assert not any(
        item.mission_id == "foreign-related"
        for item in (recovered.continuity_context.related_candidates
                     if recovered.continuity_context else [])
    )
    assert not any(
        "foreign-related" in item.anchor_ref for item in recovered.semantic_memory_candidates
    )


@pytest.mark.parametrize("owners", [(), (None,), (SUBJECT, FOREIGN), (SUBJECT, None)])
def test_direct_mission_requires_whole_canonical_subject_history(tmp_path, owners):
    memory = _memory(tmp_path)
    for index, owner in enumerate(owners):
        memory.record_turn(
            _input(owner, session=f"mission-source-{index}", mission="imported-mission"),
            "analysis", f"Synthetic owner row {index}",
        )
    memory.repository.upsert_mission_state(MissionStateContract(
        mission_id=MissionId("imported-mission"),
        mission_goal=SECRET,
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at=STAMP,
        # A caller-populated owner_context cannot replace canonical owner proof.
        owner_context=SUBJECT,
    ))
    with pytest.raises(ValueError, match="mission_subject_scope_mismatch"):
        memory.recover_for_input(_input(mission="imported-mission"))


def test_owned_mission_recovery_does_not_require_nonpersisted_owner_context(tmp_path):
    memory = _memory(tmp_path)
    memory.record_turn(
        _input(SUBJECT, session="owned-prior-session", mission="owned-mission"),
        "analysis", "Owned canonical final",
    )
    memory.repository.upsert_mission_state(MissionStateContract(
        mission_id=MissionId("owned-mission"),
        mission_goal="Owned synthetic mission",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at=STAMP,
        owner_context=None,
    ))
    recovered = memory.recover_for_input(_input(mission="owned-mission"))
    assert any("Owned synthetic mission" in item for item in recovered.mission_hints)


def test_specialist_memory_cannot_load_or_write_foreign_session_context(tmp_path, monkeypatch):
    memory = _memory(tmp_path)
    _seed(memory, FOREIGN)
    writes = []
    monkeypatch.setattr(memory.repository, "upsert_specialist_shared_memory", writes.append)
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        memory.prepare_specialist_shared_memory(
            session_id=SESSION,
            specialist_hints=["structured_analysis_specialist"],
            user_id=SUBJECT,
        )
    assert writes == []


@pytest.mark.parametrize("source_contaminated", [False, True])
def test_recurrent_specialist_revalidates_source_session_before_reusing_domains(
    tmp_path, source_contaminated
):
    memory = _memory(tmp_path)
    source_session = "specialist-source-session"
    target_session = "specialist-target-session"
    specialist = "software_change_specialist"
    _seed(memory, SUBJECT, session=source_session, text="Public source turn")
    initial = memory.prepare_specialist_shared_memory(
        session_id=source_session,
        specialist_hints=[specialist],
        active_domains=["software_development", "analysis"],
        user_id=SUBJECT,
    )[specialist]
    assert initial.recurrent_interaction_count == 1
    if source_contaminated:
        # The existing exact-user specialist row stays unchanged; a later
        # canonical foreign turn makes its source session incompatible.
        _seed(memory, FOREIGN, session=source_session, text="Foreign synthetic turn")
    previous = memory.repository.fetch_latest_specialist_shared_memory_for_user(
        user_id=SUBJECT, specialist_type=specialist, exclude_session_id=target_session,
    )
    assert (previous is None) is source_contaminated
    if previous is not None:
        assert previous.recurrent_domain_focus == initial.recurrent_domain_focus
    _seed(memory, SUBJECT, session=target_session, text="Public target turn")
    target = memory.prepare_specialist_shared_memory(
        session_id=target_session,
        specialist_hints=[specialist],
        active_domains=["software_development"],
        user_id=SUBJECT,
    )[specialist]
    assert target.recurrent_interaction_count == (1 if source_contaminated else 2)
    if source_contaminated:
        assert "analysis" not in target.recurrent_domain_focus
    # An eligible historical row preserves recurrence, not a grant to reuse all
    # its domains. Independent native lifecycle policy can still contain reuse.


@pytest.mark.parametrize("stored_subject,seed_own_turn", [
    (SUBJECT, False), (FOREIGN, True), (None, True),
])
def test_orphan_foreign_or_unbound_specialist_packet_cannot_prove_session_scope(
    tmp_path, stored_subject, seed_own_turn
):
    core = _isolated_core(tmp_path)
    memory = core.memory_service
    memory.prepare_specialist_shared_memory(
        session_id=SESSION,
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development"],
        user_id=stored_subject,
    )
    if seed_own_turn:
        _seed(memory, SUBJECT, text="Public own canonical turn")
    before = memory.repository.fetch_recent_turns(SESSION, 100)
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        memory.recover_for_input(_input())
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        core.handle_input(_input())
    assert memory.repository.fetch_recent_turns(SESSION, 100) == before
    assert memory.repository.fetch_runtime_request_claim("subject-boundary-request") is None


@pytest.mark.parametrize("reference_kind", [
    "continuity_anchor", "continuity_related", "checkpoint_mission", "checkpoint_target",
    "specialist_source",
])
def test_own_session_structured_mission_refs_cannot_link_foreign_context(tmp_path, reference_kind):
    core = _isolated_core(tmp_path)
    memory = core.memory_service
    _seed(memory, SUBJECT, text="Public own evidence")
    memory.record_turn(
        _input(FOREIGN, session="foreign-linked-session", mission="foreign-linked-mission"),
        "analysis", SECRET,
    )
    memory.repository.upsert_mission_state(MissionStateContract(
        mission_id=MissionId("foreign-linked-mission"),
        mission_goal=SECRET,
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at=STAMP,
        open_loops=[SECRET],
        active_work_items=[SECRET],
    ))
    if reference_kind.startswith("continuity_"):
        memory.repository.upsert_session_continuity(SessionContinuitySnapshot(
            session_id=SESSION,
            continuity_brief="Public own continuity",
            continuity_mode="continue",
            anchor_mission_id=("foreign-linked-mission"
                               if reference_kind == "continuity_anchor" else None),
            anchor_goal=None,
            related_mission_id=("foreign-linked-mission"
                                if reference_kind == "continuity_related" else None),
            related_goal=None,
            updated_at=STAMP,
        ))
    elif reference_kind.startswith("checkpoint_"):
        memory.repository.upsert_continuity_checkpoint(StoredContinuityCheckpoint(
            checkpoint_id="own-checkpoint-with-foreign-link",
            session_id=SESSION,
            continuity_action="continue",
            checkpoint_status="recoverable",
            checkpoint_summary="Public own checkpoint",
            updated_at=STAMP,
            mission_id=("foreign-linked-mission"
                        if reference_kind == "checkpoint_mission" else None),
            target_mission_id=("foreign-linked-mission"
                               if reference_kind == "checkpoint_target" else None),
        ))
    else:
        memory.prepare_specialist_shared_memory(
            session_id=SESSION,
            specialist_hints=["software_change_specialist"],
            active_domains=["software_development"],
            user_id=SUBJECT,
        )
        # Structured imported link, not authority or arbitrary forged prose.
        with memory.repository._connect() as connection:
            connection.execute(
                "UPDATE specialist_shared_memory SET source_mission_id = ? "
                "WHERE session_id = ?",
                ("foreign-linked-mission", SESSION),
            )
    before = memory.repository.fetch_recent_turns(SESSION, 100)
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        memory.recover_for_input(_input())
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        core.handle_input(_input())
    assert memory.repository.fetch_recent_turns(SESSION, 100) == before
    assert memory.repository.fetch_runtime_request_claim("subject-boundary-request") is None


def test_postgres_schema_and_scope_query_fixture_preserve_relation_and_parameter_binding(
    monkeypatch,
):
    """Structural SQL fixture, deliberately not controlled PostgreSQL evidence."""
    statements = []

    class RecordingConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def cursor(self):
            return self

        def execute(self, query, params=None):
            statements.append((query, params))

        def fetchone(self):
            return {"compatible": 1}

        def commit(self):
            pass

    repository = object.__new__(PostgresMemoryRepository)
    monkeypatch.setattr(repository, "_connect", RecordingConnection)
    repository._init_schema()
    schema = "\n".join(query for query, _params in statements)
    definition = re.search(
        r"CREATE TABLE IF NOT EXISTS continuity_pause_resolutions\s*\((.*?)\)",
        schema, re.DOTALL,
    )
    assert definition is not None
    for column in ("session_id", "checkpoint_id", "resolution_status", "resolved_by",
                   "resolution_note", "resolved_at"):
        assert column in definition.group(1)
    statements.clear()
    unsafe_session = "'; DROP TABLE interaction_turns; --"
    assert repository.session_subject_is_compatible(unsafe_session, SUBJECT)
    query, params = statements[-1]
    assert unsafe_session not in query
    assert "LIMIT" not in query.upper()
    assert params == (unsafe_session, SUBJECT)
    assert query.count("%s") == 2
    assert repository.mission_subject_is_compatible("mission-for-fixture", SUBJECT)
    query, params = statements[-1]
    assert query.count("%s") == 4
    assert params == ("mission-for-fixture", SUBJECT, "mission-for-fixture", "mission-for-fixture")


@pytest.mark.parametrize("subject", [SUBJECT, None])
def test_own_and_legacy_session_recovery_remain_compatible(tmp_path, subject):
    memory = _memory(tmp_path)
    _seed(memory, subject, text="Own synthetic material")
    recovered = memory.recover_for_input(_input(subject))
    assert any("Own synthetic material" in item for item in recovered.session_context)


def test_brand_new_explicit_subject_session_is_allowed_without_existing_payload(tmp_path):
    memory = _memory(tmp_path)
    recovered = memory.recover_for_input(_input())
    assert not any(item.startswith("user=") for item in recovered.session_context)
    assert not any(SECRET in item for item in recovered.recovered_items)


@pytest.mark.parametrize("entrypoint", ["handle_input", "handle_input_langgraph_flow"])
def test_core_refuses_foreign_session_before_continuity_resolution_and_recording(
    tmp_path, monkeypatch, entrypoint
):
    core = _isolated_core(tmp_path)
    _seed(core.memory_service, FOREIGN)
    before = core.memory_service.repository.fetch_recent_turns(SESSION, 100)
    resolution_calls = []
    original = core._maybe_resolve_continuity_pause

    def observe_resolution(contract):
        resolution_calls.append(contract.request_id)
        return original(contract)

    monkeypatch.setattr(core, "_maybe_resolve_continuity_pause", observe_resolution)
    with pytest.raises(ValueError, match="subject|owner|scope"):
        getattr(core, entrypoint)(_input())
    assert resolution_calls == []
    assert core.memory_service.repository.fetch_recent_turns(SESSION, 100) == before
    assert core.memory_service.repository.fetch_user_scope_snapshot(SUBJECT) is None
    assert core.memory_service.repository.fetch_runtime_request_claim(
        "subject-boundary-request"
    ) is None


@pytest.mark.parametrize("runner_kind", ["full", "continuity"])
def test_direct_optional_runner_refuses_foreign_scope_before_optional_library_load(
    tmp_path, monkeypatch, runner_kind
):
    from orchestrator_service import langgraph_flow

    core = _isolated_core(tmp_path)
    _seed(core.memory_service, FOREIGN)
    library_loads = []

    def forbidden_optional_load():
        library_loads.append(True)
        pytest.fail("foreign subject reached optional graph runtime")

    monkeypatch.setattr(langgraph_flow, "_load_langgraph", forbidden_optional_load)
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        if runner_kind == "full":
            langgraph_flow.LangGraphFlowRunner(core).run(_input())
        else:
            langgraph_flow.LangGraphContinuityFlowRunner(core).run(contract=_input(), events=[])
    assert library_loads == []
    assert core.memory_service.repository.fetch_runtime_request_claim(
        "subject-boundary-request"
    ) is None
