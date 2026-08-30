from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from sqlite3 import IntegrityError
from tempfile import gettempdir
from threading import Barrier
from uuid import uuid4

import memory_service.repository as memory_repository
import pytest
from governance_service.service import GovernanceService
from memory_service.repository import (
    PostgresMemoryRepository,
    SqliteMemoryRepository,
    StoredReviewedProceduralPlaybook,
    StoredSpecialistSharedMemory,
    StoredWorkflowLifecycleTransition,
    build_memory_repository,
    normalize_database_url,
    parse_sqlite_database_path,
)
from memory_service.service import (
    MemoryRecordResult,
    MemoryRecoveryResult,
    MemoryService,
    WorkflowLifecycleIntegrityError,
)

from shared.contracts import (
    DecisionOutcomeAttributionRecordContract,
    DeliberativePlanContract,
    ExperienceRecordContract,
    InputContract,
    MemoryLifecycleGovernanceAssessmentContract,
    MissionStateContract,
    OperationDispatchContract,
    OperationResultContract,
    OperatorFeedbackContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    ReviewedLearningGuidanceContract,
    ReviewedProceduralPlaybookContract,
    SkillCandidateContract,
    SpecialistContributionContract,
    SpecialistSharedMemoryContextContract,
    WorkflowLifecycleGovernanceAssessmentContract,
    WorkflowLifecycleTransitionContract,
)
from shared.decision_attribution import (
    canonical_decision_attribution_payload,
    canonicalize_decision_attribution_record,
    decision_attribution_fingerprint,
)
from shared.memory_registry import DEFAULT_MEMORY_SCOPES, memory_lifecycle_decision
from shared.types import (
    ChannelType,
    EvolutionProposalId,
    InputType,
    MissionId,
    MissionStatus,
    OperationId,
    OperationStatus,
    PermissionDecision,
    RequestId,
    RiskLevel,
    SessionId,
)
from shared.workflow_lifecycle import (
    canonical_workflow_lifecycle_payload,
    workflow_lifecycle_artifact_fingerprint,
    workflow_lifecycle_transition_fingerprint,
)
from tests.unit.test_workflow_lifecycle import _activation, _rollback


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def sample_plan() -> DeliberativePlanContract:
    return DeliberativePlanContract(
        plan_summary="decompor objetivo em etapas reversiveis",
        goal="Please plan the sprint.",
        steps=["continuar a missao", "listar etapas", "recomendar proxima acao"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=nenhum; apoio=baseline local",
        tensions_considered=["equilibrar ambicao estrategica com a menor proxima acao segura"],
        specialist_hints=["operational_planning_specialist"],
        success_criteria=["plano deve indicar a menor proxima acao segura"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="continuar a missao",
        continuity_action="continuar",
        open_loops=["fechar checkpoint principal"],
    )


def sample_specialist_contributions() -> list[SpecialistContributionContract]:
    return [
        SpecialistContributionContract(
            specialist_type="operational_planning_specialist",
            role="planejamento_operacional_subordinado",
            focus="sequenciamento reversivel e checkpoints claros",
            findings=["open_loop: fechar checkpoint principal"],
            recommendation="encadear o plano em etapas pequenas e verificaveis",
            confidence=0.78,
        )
    ]


def sample_reviewed_procedural_playbook(
    *,
    playbook_id: str = "reviewed-playbook://software-change/bounded-review",
    version: str = "1.0.0",
    route: str = "software_engineering",
    workflow_profile: str = "software_change_workflow",
    domain: str = "software_engineering",
    timestamp: str = "2026-07-18T12:00:00Z",
) -> ReviewedProceduralPlaybookContract:
    source_suffix = playbook_id.removeprefix("reviewed-playbook://")
    return ReviewedProceduralPlaybookContract(
        playbook_id=playbook_id,
        version=version,
        source_candidate_id=f"playbook-candidate://{source_suffix}",
        source_review_decision_id=(f"evolution-review-decision://{source_suffix}/{version}"),
        evolution_proposal_id=EvolutionProposalId(f"evolution-proposal://{source_suffix}"),
        review_status="approved",
        procedure_name=f"bounded review for {source_suffix}",
        route=route,
        workflow_profile=workflow_profile,
        domain=domain,
        bounded_steps=[
            "collect reviewed evidence",
            "apply bounded planning guidance",
            "preserve the rollback path",
        ],
        allowed_usage=["planning_context"],
        evidence_refs=[f"evidence://{source_suffix}/{version}"],
        rollback_plan_ref=f"rollback://{source_suffix}/{version}",
        timestamp=timestamp,
    )


def reviewed_playbook_memory_service(database_url: str) -> MemoryService:
    return MemoryService(
        database_url=database_url,
        reviewed_procedural_playbook_verifier=lambda _playbook: True,
    )


def sample_decision_outcome_attribution(
    *,
    suffix: str = "001",
    request_id: str | None = None,
    mission_id: str | None = "mission-attribution",
    workflow_profile: str | None = "software_change_workflow",
    observed_at: str = "2026-08-11T12:00:00Z",
) -> DecisionOutcomeAttributionRecordContract:
    resolved_request_id = request_id or f"req-attribution-{suffix}"
    resolved_mission_id = mission_id or "mission-attribution"
    experience_id = f"experience://{resolved_mission_id}/{resolved_request_id}"
    record = DecisionOutcomeAttributionRecordContract(
        attribution_record_id=f"decision-attribution://{suffix}",
        request_id=RequestId(resolved_request_id),
        session_id=SessionId(f"sess-attribution-{suffix}"),
        mission_id=MissionId(resolved_mission_id),
        observed_at=observed_at,
        governance_decision_ref=f"governance-decision://{suffix}",
        governance_decision_status="allow_with_conditions",
        workflow_profile=workflow_profile,
        route="software_engineering",
        outcome_ref=experience_id,
        outcome_status="completed",
        experience_id=experience_id,
        workflow_policy_ref="workflow-policy://software-change",
        workflow_policy_version="1.0.0",
        workflow_policy_source_registry_ref="registry://domains/v1",
        workflow_policy_source_registry_fingerprint="sha256:registry-v1",
        workflow_policy_application_status="applied",
        workflow_policy_effects=["bounded_patch"],
        memory_policy_decision_ref=f"memory-policy-decision://{suffix}",
        memory_policy_status="applied",
        memory_policy_refs=[f"memory://reviewed/{suffix}"],
        memory_selected_refs=[f"memory://reviewed/{suffix}"],
        memory_use_reasons={f"memory://reviewed/{suffix}": "declared_planning_context"},
        memory_signal_kinds={f"memory://reviewed/{suffix}": "semantic"},
        memory_causal_use_allowed=True,
        declared_effects_by_ref={f"memory://reviewed/{suffix}": ["bounded_patch"]},
        participating_refs=[f"memory://reviewed/{suffix}"],
        declared_causal_refs=[f"memory://reviewed/{suffix}"],
        attribution_status="declared_causality",
        attribution_reasons=["runtime_declared_causal_use"],
        evidence_refs=[f"trace://{suffix}"],
    )
    return canonicalize_decision_attribution_record(record)


def persist_attribution_experience(
    service: MemoryService,
    record: DecisionOutcomeAttributionRecordContract,
) -> None:
    service.claim_runtime_request(
        request_id=str(record.request_id),
        session_id=str(record.session_id),
        claimed_at=record.observed_at,
    )
    service.record_experience(
        experience=ExperienceRecordContract(
            experience_id=str(record.experience_id),
            mission_id=MissionId(str(record.mission_id)),
            workflow_profile=str(record.workflow_profile),
            outcome_status=str(record.outcome_status),
            timestamp=record.observed_at,
            route=record.route,
            evidence_refs=[f"experience-evidence://{record.request_id}"],
        )
    )


def test_memory_service_name() -> None:
    assert MemoryService.name == "memory-service"


def test_memory_service_transitions_work_item_in_canonical_mission_state() -> None:
    temp_dir = runtime_dir("memory-work-item-transition")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-work-item-memory"),
        session_id=SessionId("sess-work-item-memory"),
        mission_id=MissionId("mission-work-item-memory"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan the controlled rollout.",
        timestamp="2026-05-18T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan ready.",
        deliberative_plan=sample_plan(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    created = service.transition_work_item_state(
        mission_id="mission-work-item-memory",
        work_item_ref="work-item://mission-work-item-memory/validate-plan",
        work_item_status="active",
        transition_ref=(
            "work_item_transition:create:"
            "work-item://mission-work-item-memory/validate-plan:abc12345"
        ),
        next_action_ref="next_action:validate-plan",
    )
    paused = service.transition_work_item_state(
        mission_id="mission-work-item-memory",
        work_item_ref="work-item://mission-work-item-memory/validate-plan",
        work_item_status="paused",
        transition_ref=(
            "work_item_transition:pause:work-item://mission-work-item-memory/validate-plan:def67890"
        ),
    )

    assert created is not None
    assert created.next_action_ref == "next_action:validate-plan"
    assert "work-item://mission-work-item-memory/validate-plan" in created.work_item_refs
    assert "work-item://mission-work-item-memory/validate-plan" in created.active_work_items
    assert paused is not None
    assert "work-item://mission-work-item-memory/validate-plan" in paused.work_item_refs
    assert "work-item://mission-work-item-memory/validate-plan" not in paused.active_work_items
    assert any(ref.startswith("work_item_transition:pause:") for ref in paused.checkpoint_refs)


def test_memory_service_persists_work_item_graph_and_refreshes_readiness() -> None:
    temp_dir = runtime_dir("memory-work-item-graph")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = MemoryService(database_url=database_url)
    mission_id = "mission-memory-work-item-graph"
    foundation_ref = f"work-item://{mission_id}/foundation"
    release_ref = f"work-item://{mission_id}/release"
    service.record_turn(
        InputContract(
            request_id=RequestId("req-memory-work-item-graph"),
            session_id=SessionId("sess-memory-work-item-graph"),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CONSOLE,
            input_type=InputType.TEXT,
            content="Plan the governed graph.",
            timestamp="2026-07-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Graph planned.",
        deliberative_plan=sample_plan(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref=foundation_ref,
        work_item_status="active",
        transition="create",
        transition_ref=f"work_item_transition:create:{foundation_ref}:one",
        priority_level="p2",
    )
    created = service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref=release_ref,
        work_item_status="active",
        transition="create",
        transition_ref=f"work_item_transition:create:{release_ref}:two",
        dependency_refs=[foundation_ref],
        priority_level="p0",
    )

    reloaded = MemoryService(database_url=database_url).get_mission_state(mission_id)

    assert created is not None
    assert reloaded is not None
    assert len(reloaded.work_items) == 2
    release = next(item for item in reloaded.work_items if item.work_item_ref == release_ref)
    assert release.dependency_refs == [foundation_ref]
    assert release.priority_level == "p0"
    assert release.blocking_state == "dependency_blocked"

    completed = service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref=foundation_ref,
        work_item_status="completed",
        transition="complete",
        transition_ref=f"work_item_transition:complete:{foundation_ref}:three",
    )

    assert completed is not None
    release = next(item for item in completed.work_items if item.work_item_ref == release_ref)
    assert release.blocking_state == "ready"
    assert release_ref in completed.active_work_items


def test_memory_service_transitions_artifact_lifecycle_in_mission_state() -> None:
    temp_dir = runtime_dir("memory-artifact-lifecycle")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-artifact-memory"),
        session_id=SessionId("sess-artifact-memory"),
        mission_id=MissionId("mission-artifact-memory"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan the controlled rollout.",
        timestamp="2026-05-18T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan ready.",
        deliberative_plan=sample_plan(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    work_item_ref = "work-item://mission-artifact-memory/plan"
    service.transition_work_item_state(
        mission_id="mission-artifact-memory",
        work_item_ref=work_item_ref,
        work_item_status="active",
        transition="create",
        transition_ref=f"work_item_transition:create:{work_item_ref}:source",
    )

    registered = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="active",
        transition_ref=(
            "artifact_lifecycle_transition:register:"
            "artifact://mission-artifact-memory/plan/v1:abc12345"
        ),
        artifact_version=1,
        work_item_ref=work_item_ref,
        rollback_plan_ref="rollback://mission-artifact-memory/plan/v1",
    )
    replaced = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="active",
        transition_ref=(
            "artifact_lifecycle_transition:replace:"
            "artifact://mission-artifact-memory/plan/v1:def67890"
        ),
        replacement_artifact_ref="artifact://mission-artifact-memory/plan/v2",
        artifact_version=2,
        rollback_plan_ref="rollback://mission-artifact-memory/plan/v1",
    )
    rolled_back = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="active",
        transition="rollback",
        transition_ref=(
            "artifact_lifecycle_transition:rollback:"
            "artifact://mission-artifact-memory/plan/v1:rollback1"
        ),
        rollback_plan_ref="rollback://mission-artifact-memory/plan/v1",
    )
    reloaded = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    ).get_mission_state("mission-artifact-memory")
    archived = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="archived",
        transition_ref=(
            "artifact_lifecycle_transition:archive:"
            "artifact://mission-artifact-memory/plan/v1:fedcba98"
        ),
    )

    assert registered is not None
    assert "artifact://mission-artifact-memory/plan/v1" in registered.artifact_refs
    assert "artifact://mission-artifact-memory/plan/v1" in registered.active_artifact_refs
    assert replaced is not None
    assert "artifact://mission-artifact-memory/plan/v2" in replaced.artifact_refs
    assert "artifact://mission-artifact-memory/plan/v2" in replaced.active_artifact_refs
    assert "artifact://mission-artifact-memory/plan/v1" not in replaced.active_artifact_refs
    assert len(replaced.artifact_states) == 2
    version_one = next(
        item
        for item in replaced.artifact_states
        if item.artifact_ref == "artifact://mission-artifact-memory/plan/v1"
    )
    version_two = next(
        item
        for item in replaced.artifact_states
        if item.artifact_ref == "artifact://mission-artifact-memory/plan/v2"
    )
    assert version_one.artifact_status == "superseded"
    assert version_one.replacement_artifact_ref == version_two.artifact_ref
    assert version_two.supersedes_artifact_ref == version_one.artifact_ref
    assert version_two.artifact_version == 2
    assert version_two.work_item_ref == work_item_ref
    assert rolled_back is not None
    assert reloaded is not None
    reloaded_v1 = next(
        item for item in reloaded.artifact_states if item.artifact_ref == version_one.artifact_ref
    )
    reloaded_v2 = next(
        item for item in reloaded.artifact_states if item.artifact_ref == version_two.artifact_ref
    )
    assert reloaded_v1.artifact_status == "active"
    assert reloaded_v2.artifact_status == "rolled_back"
    assert reloaded_v1.artifact_version == 1
    assert reloaded_v1.created_at == version_one.created_at
    assert archived is not None
    assert "artifact://mission-artifact-memory/plan/v1" not in archived.active_artifact_refs
    assert any(
        ref.startswith("artifact_lifecycle_transition:archive:") for ref in archived.checkpoint_refs
    )


def test_postgres_mission_upsert_keeps_columns_and_placeholders_in_sync() -> None:
    captured: dict[str, object] = {}

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            captured["query"] = query
            captured["params"] = params

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            captured["committed"] = True

    repository = PostgresMemoryRepository.__new__(PostgresMemoryRepository)
    repository._connect = lambda: FakeConnection()
    mission = MissionStateContract(
        mission_id=MissionId("mission-postgres-artifact-state"),
        mission_goal="Persist artifact lineage",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T00:00:00Z",
    )

    repository.upsert_mission_state(mission)

    query = str(captured["query"])
    params = captured["params"]
    assert isinstance(params, tuple)
    assert query.count("%s") == len(params) == 36
    assert "artifact_states" in query
    assert "open_loop_states" in query
    assert captured["committed"] is True


def test_postgres_reviewed_playbook_uses_atomic_insert_and_revoke_sql() -> None:
    captured_queries: list[str] = []

    class FakeCursor:
        rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query: str, _params: tuple[object, ...]) -> None:
            captured_queries.append(query)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

    repository = PostgresMemoryRepository.__new__(PostgresMemoryRepository)
    repository._connect = lambda: FakeConnection()
    playbook = sample_reviewed_procedural_playbook()
    created = repository._insert_reviewed_procedural_playbook(
        StoredReviewedProceduralPlaybook(playbook=playbook)
    )
    revoked = repository._transition_reviewed_procedural_playbook_to_revoked(
        StoredReviewedProceduralPlaybook(
            playbook=replace(
                playbook,
                review_status="revoked",
                evidence_refs=[*playbook.evidence_refs, "human-review://revoke/pg"],
                revoked_at="2026-07-18T13:00:00Z",
                revocation_ref="human-review://revoke/pg",
            )
        )
    )

    assert created is True
    assert revoked is True
    assert "ON CONFLICT (playbook_id, version) DO NOTHING" in captured_queries[0]
    assert "AND review_status = 'approved'" in captured_queries[1]


def test_postgres_decision_attribution_uses_atomic_append_and_scoped_paging() -> None:
    captured: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            captured.append((query, params))

        def fetchall(self) -> list[dict[str, object]]:
            return []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

    repository = PostgresMemoryRepository.__new__(PostgresMemoryRepository)
    repository._connect = lambda: FakeConnection()
    record = sample_decision_outcome_attribution(suffix="postgres-sql")

    assert repository._insert_decision_outcome_attribution(record) is True
    assert (
        repository._claim_runtime_request(
            request_id=str(record.request_id),
            session_id=str(record.session_id),
            claimed_at=record.observed_at,
        )
        is True
    )
    assert (
        repository.list_decision_outcome_attributions(
            request_id=str(record.request_id),
            mission_id=str(record.mission_id),
            workflow_profile=record.workflow_profile,
            limit=3,
            offset=2,
        )
        == []
    )

    insert_query, insert_params = captured[0]
    claim_query, claim_params = captured[1]
    list_query, list_params = captured[2]
    assert "ON CONFLICT DO NOTHING" in insert_query
    assert "UPDATE" not in insert_query.upper()
    assert "DELETE" not in insert_query.upper()
    assert len(insert_params) == insert_query.count("%s") == 16
    assert "FROM runtime_request_claims" in insert_query
    assert "request_id = %s AND session_id = %s" in insert_query
    assert "FROM experience_reflections" in insert_query
    assert "outcome_status IS NOT DISTINCT FROM %s" in insert_query
    assert "INSERT INTO runtime_request_claims" in claim_query
    assert "ON CONFLICT DO NOTHING" in claim_query
    assert claim_params == (
        str(record.request_id),
        str(record.session_id),
        record.observed_at,
    )
    assert list_query.index("WHERE") < list_query.index("LIMIT")
    assert "request_id = %s" in list_query
    assert "mission_id = %s" in list_query
    assert "workflow_profile = %s" in list_query
    assert list_params == (
        str(record.request_id),
        str(record.mission_id),
        record.workflow_profile,
        3,
        2,
    )


def workflow_lifecycle_assessment(
    transition: WorkflowLifecycleTransitionContract,
    *,
    assessed_at: str | None = None,
) -> WorkflowLifecycleGovernanceAssessmentContract:
    return GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        current_transition=None if transition.revision == 1 else _activation(),
        release_bundle_verifier=lambda candidate: candidate == transition,
        assessed_at=assessed_at
        or ("2026-08-12T10:31:00Z" if transition.revision == 1 else "2026-08-12T11:01:00Z"),
    )


def workflow_lifecycle_memory_service(database_url: str) -> MemoryService:
    return MemoryService(
        database_url=database_url,
        workflow_lifecycle_transition_verifier=lambda _transition: True,
    )


def test_workflow_lifecycle_transition_is_idempotent_and_survives_restart() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-restart")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    activation = _activation()
    assessment = workflow_lifecycle_assessment(activation)
    service = workflow_lifecycle_memory_service(database_url)

    assert service.record_workflow_lifecycle_transition(activation, assessment) == activation
    assert service.record_workflow_lifecycle_transition(activation, assessment) == activation
    reloaded = workflow_lifecycle_memory_service(database_url)

    assert (
        reloaded.get_active_workflow_lifecycle(
            workflow_profile=activation.workflow_profile,
            route=activation.route,
        )
        == activation
    )
    assert reloaded.list_workflow_lifecycle_transitions(
        workflow_profile=activation.workflow_profile,
        route=activation.route,
    ) == [activation]

    changed = replace(
        activation,
        evidence_refs=[*activation.evidence_refs, "evidence://forged/collision"],
    )
    changed_assessment = workflow_lifecycle_assessment(changed)
    with pytest.raises(ValueError, match="identity is immutable"):
        reloaded.record_workflow_lifecycle_transition(changed, changed_assessment)


def test_workflow_lifecycle_storage_requires_independent_release_bundle_verification() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-release-verifier")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    activation = _activation()
    assessment = workflow_lifecycle_assessment(activation)

    for service in (
        MemoryService(database_url=database_url),
        MemoryService(
            database_url=database_url,
            workflow_lifecycle_transition_verifier=lambda _transition: False,
        ),
    ):
        with pytest.raises(ValueError, match="verified persisted release bundle"):
            service.record_workflow_lifecycle_transition(activation, assessment)


def test_workflow_lifecycle_rollback_restores_baseline_without_registry_write() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-rollback")
    service = workflow_lifecycle_memory_service(
        f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    activation = _activation()
    rollback = _rollback(activation)
    service.record_workflow_lifecycle_transition(
        activation,
        workflow_lifecycle_assessment(activation),
    )
    rollback_assessment = GovernanceService().assess_workflow_lifecycle_transition(
        rollback,
        current_transition=activation,
        release_bundle_verifier=lambda candidate: candidate == rollback,
        assessed_at="2026-08-12T11:01:00Z",
    )

    assert (
        service.record_workflow_lifecycle_transition(
            rollback,
            rollback_assessment,
        )
        == rollback
    )
    assert (
        service.get_active_workflow_lifecycle(
            workflow_profile=activation.workflow_profile,
            route=activation.route,
        )
        == rollback
    )
    assert service.list_workflow_lifecycle_transitions(
        workflow_profile=activation.workflow_profile,
        route=activation.route,
    ) == [rollback, activation]
    assert service.list_workflow_lifecycle_transitions(
        workflow_profile=activation.workflow_profile,
        route=activation.route,
        limit=1,
        offset=1,
    ) == [activation]
    assert rollback.active_version_ref == rollback.baseline_version_ref
    assert rollback.active_definition_hash == rollback.baseline_definition_hash


def test_workflow_lifecycle_concurrent_cas_allows_one_revision_winner() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-concurrent-cas")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    activation = _activation()
    workflow_lifecycle_memory_service(database_url).record_workflow_lifecycle_transition(
        activation,
        workflow_lifecycle_assessment(activation),
    )
    first = _rollback(activation)
    second = replace(
        first,
        transition_id="workflow-lifecycle-transition://software-change/competing-2",
        human_authorization_ref="human-authorization://workflow/software-change/rollback/2",
        operator_ref="operator://secondary",
    )
    barrier = Barrier(2)

    def record(candidate: WorkflowLifecycleTransitionContract) -> str:
        service = workflow_lifecycle_memory_service(database_url)
        assessment = GovernanceService().assess_workflow_lifecycle_transition(
            candidate,
            current_transition=activation,
            release_bundle_verifier=lambda transition: transition == candidate,
            assessed_at="2026-08-12T11:01:00Z",
        )
        barrier.wait()
        try:
            service.record_workflow_lifecycle_transition(candidate, assessment)
        except ValueError:
            return "lost"
        return candidate.transition_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(record, (first, second)))

    assert outcomes.count("lost") == 1
    winner = workflow_lifecycle_memory_service(
        database_url
    ).get_active_workflow_lifecycle(
        workflow_profile=activation.workflow_profile,
        route=activation.route,
    )
    assert winner is not None
    assert winner.transition_id in {first.transition_id, second.transition_id}
    assert winner.revision == 2


def test_workflow_lifecycle_fails_closed_on_tail_or_lineage_tamper() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-tamper")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = workflow_lifecycle_memory_service(database_url)
    activation = _activation()
    rollback = _rollback(activation)
    service.record_workflow_lifecycle_transition(
        activation,
        workflow_lifecycle_assessment(activation),
    )
    service.record_workflow_lifecycle_transition(
        rollback,
        GovernanceService().assess_workflow_lifecycle_transition(
            rollback,
            current_transition=activation,
            release_bundle_verifier=lambda candidate: candidate == rollback,
            assessed_at="2026-08-12T11:01:00Z",
        ),
    )
    with service.repository._connect() as connection:
        connection.execute("DROP TRIGGER workflow_lifecycle_transitions_no_update")
        connection.execute(
            """
            UPDATE workflow_lifecycle_transitions
            SET transition_payload_json = ?
            WHERE revision = 1
            """,
            (canonical_workflow_lifecycle_payload(replace(activation, operator_ref="forged")),),
        )
        connection.commit()

    reader = workflow_lifecycle_memory_service(database_url)
    with pytest.raises(
        WorkflowLifecycleIntegrityError,
        match="workflow_lifecycle_persisted_chain_rejected",
    ):
        reader.get_active_workflow_lifecycle(
            workflow_profile=activation.workflow_profile,
            route=activation.route,
        )
    assert (
        reader.list_workflow_lifecycle_transitions(
            workflow_profile=activation.workflow_profile,
            route=activation.route,
        )
        == []
    )


def test_workflow_lifecycle_repository_paging_skips_invalid_rows_without_starvation() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-starvation")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    activation = _activation()
    assessment = workflow_lifecycle_assessment(activation)
    stored = StoredWorkflowLifecycleTransition(
        transition=activation,
        governance_assessment=assessment,
        transition_fingerprint=workflow_lifecycle_transition_fingerprint(activation),
        governance_assessment_fingerprint=workflow_lifecycle_artifact_fingerprint(assessment),
    )
    assert service.repository._insert_workflow_lifecycle_transition(stored) is True
    with service.repository._connect() as connection:
        connection.execute("DROP TRIGGER workflow_lifecycle_transitions_no_update")
        connection.execute(
            """
            UPDATE workflow_lifecycle_transitions
            SET transition_fingerprint = ?
            WHERE transition_id = ?
            """,
            ("0" * 64, activation.transition_id),
        )
        connection.commit()

    assert service.repository.list_workflow_lifecycle_transitions(limit=1) == []


def test_workflow_lifecycle_storage_rejects_blocked_or_mismatched_assessment() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-governance")
    service = workflow_lifecycle_memory_service(
        f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    activation = _activation()
    approved = workflow_lifecycle_assessment(activation)
    blocked = replace(
        approved,
        status="blocked",
        blockers=["human_authorization_missing"],
        human_authorization_verified=False,
        transition_recording_authorized=False,
    )

    with pytest.raises(ValueError, match="approved governance authorization"):
        service.record_workflow_lifecycle_transition(activation, blocked)
    with pytest.raises(ValueError, match="governance assessment is invalid"):
        service.record_workflow_lifecycle_transition(
            activation,
            replace(approved, transition_id="forged-transition"),
        )


def test_workflow_lifecycle_sqlite_triggers_block_update_and_delete() -> None:
    temp_dir = runtime_dir("workflow-lifecycle-append-only")
    service = workflow_lifecycle_memory_service(
        f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    activation = _activation()
    service.record_workflow_lifecycle_transition(
        activation,
        workflow_lifecycle_assessment(activation),
    )

    with pytest.raises(IntegrityError, match="append-only"):
        with service.repository._connect() as connection:
            connection.execute("UPDATE workflow_lifecycle_transitions SET route = 'forged'")
    with pytest.raises(IntegrityError, match="append-only"):
        with service.repository._connect() as connection:
            connection.execute("DELETE FROM workflow_lifecycle_transitions")


def test_postgres_workflow_lifecycle_uses_atomic_cas_and_scoped_paging() -> None:
    captured: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            captured.append((query, params))

        def fetchall(self) -> list[dict[str, object]]:
            return []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

    repository = PostgresMemoryRepository.__new__(PostgresMemoryRepository)
    repository._connect = lambda: FakeConnection()
    transition = _activation()
    assessment = workflow_lifecycle_assessment(transition)
    stored = StoredWorkflowLifecycleTransition(
        transition=transition,
        governance_assessment=assessment,
        transition_fingerprint=workflow_lifecycle_transition_fingerprint(transition),
        governance_assessment_fingerprint=workflow_lifecycle_artifact_fingerprint(assessment),
    )

    assert repository._insert_workflow_lifecycle_transition(stored) is True
    assert (
        repository.list_workflow_lifecycle_transitions(
            workflow_profile=transition.workflow_profile,
            route=transition.route,
            limit=3,
            offset=2,
        )
        == []
    )
    insert_query, insert_params = captured[0]
    list_query, list_params = captured[1]
    assert "ON CONFLICT DO NOTHING" in insert_query
    assert "predecessor.transition_fingerprint = %s" in insert_query
    assert "NOT EXISTS" in insert_query
    assert insert_query.count("%s") == len(insert_params)
    assert "workflow_profile = %s" in list_query
    assert "route = %s" in list_query
    assert list_params == (
        transition.workflow_profile,
        transition.route,
        50,
        0,
    )


def test_postgres_schema_creates_guarded_experience_storage() -> None:
    captured_queries: list[str] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(
            self,
            query: str,
            _params: tuple[object, ...] | None = None,
        ) -> None:
            captured_queries.append(query)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

    repository = PostgresMemoryRepository.__new__(PostgresMemoryRepository)
    repository._connect = lambda: FakeConnection()

    repository._init_schema()

    schema = "\n".join(captured_queries)
    assert "CREATE TABLE IF NOT EXISTS experience_reflections" in schema
    assert "experience_id TEXT PRIMARY KEY" in schema
    assert "outcome_status TEXT NOT NULL" in schema
    assert "reflection_core_mutation_allowed BOOLEAN" in schema
    assert "enforce_experience_reflection_immutability" in schema
    assert "experience_reflections is append-only" in schema
    assert "experience identity and outcome are immutable" in schema
    assert "CREATE TABLE IF NOT EXISTS workflow_lifecycle_transitions" in schema
    assert "UNIQUE (workflow_profile, route, revision)" in schema
    assert "reject_workflow_lifecycle_transition_mutation" in schema
    assert "workflow_lifecycle_transitions is append-only" in schema


def test_decision_outcome_attribution_is_idempotent_and_survives_reload() -> None:
    temp_dir = runtime_dir("decision-attribution-reload")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = MemoryService(database_url=database_url)
    record = sample_decision_outcome_attribution()
    persist_attribution_experience(service, record)

    assert service.record_decision_outcome_attribution(record) == record
    assert service.record_decision_outcome_attribution(record) == record

    reloaded = MemoryService(database_url=database_url)
    assert (
        reloaded.get_decision_outcome_attribution(
            attribution_record_id=record.attribution_record_id
        )
        == record
    )
    assert reloaded.get_decision_outcome_attribution(request_id=str(record.request_id)) == record
    assert reloaded.list_decision_outcome_attributions() == [record]
    assert reloaded.list_decision_outcome_attributions(
        request_id=str(record.request_id),
        limit=1,
    ) == [record]

    with pytest.raises(ValueError, match="identity is immutable"):
        reloaded.record_decision_outcome_attribution(replace(record, outcome_status="failed"))
    with pytest.raises(ValueError, match="identity is immutable"):
        reloaded.record_decision_outcome_attribution(
            replace(record, attribution_record_id="decision-attribution://other")
        )
    with pytest.raises(ValueError, match="does not match request and mission identity"):
        reloaded.record_decision_outcome_attribution(
            replace(record, request_id=RequestId("req-attribution-other"))
        )


def test_decision_outcome_attribution_binds_claim_and_persisted_experience() -> None:
    temp_dir = runtime_dir("decision-attribution-bound-identities")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    record = sample_decision_outcome_attribution(suffix="bound-identities")

    with pytest.raises(ValueError, match="requires a runtime request claim"):
        service.record_decision_outcome_attribution(record)

    service.claim_runtime_request(
        request_id=str(record.request_id),
        session_id="sess-different",
        claimed_at=record.observed_at,
    )
    with pytest.raises(ValueError, match="session does not match"):
        service.record_decision_outcome_attribution(record)

    matching = replace(record, session_id=SessionId("sess-different"))
    with pytest.raises(ValueError, match="requires a persisted experience"):
        service.record_decision_outcome_attribution(matching)


def test_repository_attribution_insert_requires_exact_claim_and_experience() -> None:
    temp_dir = runtime_dir("decision-attribution-repository-links")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    record = sample_decision_outcome_attribution(suffix="repository-links")

    assert service.repository._insert_decision_outcome_attribution(record) is False
    service.record_experience(
        experience=ExperienceRecordContract(
            experience_id=str(record.experience_id),
            mission_id=MissionId(str(record.mission_id)),
            workflow_profile=str(record.workflow_profile),
            outcome_status=str(record.outcome_status),
            timestamp=record.observed_at,
            route=record.route,
            evidence_refs=["experience-evidence://repository-links"],
        )
    )
    assert service.repository._insert_decision_outcome_attribution(record) is False
    service.claim_runtime_request(
        request_id=str(record.request_id),
        session_id="sess-wrong",
        claimed_at=record.observed_at,
    )
    assert service.repository._insert_decision_outcome_attribution(record) is False

    mismatch_dir = runtime_dir("decision-attribution-repository-experience-mismatch")
    mismatch_service = MemoryService(
        database_url=f"sqlite:///{(mismatch_dir / 'memory.db').as_posix()}"
    )
    mismatch_service.claim_runtime_request(
        request_id=str(record.request_id),
        session_id=str(record.session_id),
        claimed_at=record.observed_at,
    )
    mismatch_service.record_experience(
        experience=ExperienceRecordContract(
            experience_id=str(record.experience_id),
            mission_id=MissionId(str(record.mission_id)),
            workflow_profile=str(record.workflow_profile),
            outcome_status=str(record.outcome_status),
            timestamp=record.observed_at,
            route="different_route",
            evidence_refs=["experience-evidence://repository-links-mismatch"],
        )
    )
    assert mismatch_service.repository._insert_decision_outcome_attribution(record) is False


def test_attributed_experience_outcome_is_immutable_at_repository_boundary() -> None:
    temp_dir = runtime_dir("attributed-experience-immutable")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    record = sample_decision_outcome_attribution(suffix="experience-immutable")
    persist_attribution_experience(service, record)
    service.record_decision_outcome_attribution(record)
    stored = service.get_experience_reflection(str(record.experience_id))
    assert stored is not None
    changed_outcome = replace(stored.experience, outcome_status="failed")

    with pytest.raises(ValueError, match="experience identity is immutable"):
        service.record_experience(experience=changed_outcome)

    service.repository.record_experience(changed_outcome)
    after_direct_repository_call = service.get_experience_reflection(str(record.experience_id))
    assert after_direct_repository_call is not None
    assert after_direct_repository_call.experience == stored.experience

    repository = service.repository
    assert isinstance(repository, SqliteMemoryRepository)
    with pytest.raises(IntegrityError, match="identity and outcome are immutable"):
        with repository._connect() as connection:
            connection.execute(
                """
                UPDATE experience_reflections
                SET outcome_status = 'failed'
                WHERE experience_id = ?
                """,
                (record.experience_id,),
            )
    with repository._connect() as connection:
        connection.execute(
            """
            UPDATE experience_reflections
            SET user_feedback = ?, reflection_id = ?, reflection_status = 'candidate',
                learning_candidate = 'retain bounded operator evidence',
                recommendation = 'review the bounded feedback',
                reflection_human_review_required = 1,
                reflection_automatic_promotion_allowed = 0,
                reflection_core_mutation_allowed = 0
            WHERE experience_id = ?
            """,
            (
                "feedback_id=operator-feedback://storage/allowed",
                "reflection://storage/allowed",
                record.experience_id,
            ),
        )
        connection.commit()
    enriched = service.get_experience_reflection(str(record.experience_id))
    assert enriched is not None
    assert enriched.experience.outcome_status == "completed"
    assert "operator-feedback://storage/allowed" in (enriched.experience.user_feedback or "")
    assert enriched.reflection is not None
    assert enriched.reflection.reflection_id == "reflection://storage/allowed"

    with pytest.raises(IntegrityError, match="enrichment must remain bounded"):
        with repository._connect() as connection:
            connection.execute(
                """
                UPDATE experience_reflections
                SET user_feedback = ?
                WHERE experience_id = ?
                """,
                ("x" * 2001, record.experience_id),
            )
    with pytest.raises(IntegrityError, match="append-only"):
        with repository._connect() as connection:
            connection.execute(
                """
                DELETE FROM experience_reflections
                WHERE experience_id = ?
                """,
                (record.experience_id,),
            )


def test_operator_feedback_compare_and_swap_preserves_concurrent_feedback() -> None:
    temp_dir = runtime_dir("operator-feedback-concurrency")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    experience_id = "experience://mission-feedback-race/request-feedback-race"
    mission_id = MissionId("mission-feedback-race")
    seed = MemoryService(database_url=database_url)
    seed.record_experience_reflection(
        experience=ExperienceRecordContract(
            experience_id=experience_id,
            mission_id=mission_id,
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            evidence_refs=["trace://feedback-race"],
            timestamp="2026-08-11T18:00:00Z",
        ),
        reflection=PostTaskReflectionContract(
            reflection_id="reflection://mission-feedback-race/request-feedback-race",
            experience_id=experience_id,
            reflection_status="candidate",
            learning_candidate="preserve concurrent operator feedback",
            recommendation="merge feedback through canonical memory",
            evidence_refs=["trace://feedback-race"],
            timestamp="2026-08-11T18:00:01Z",
        ),
    )
    services = [
        MemoryService(database_url=database_url),
        MemoryService(database_url=database_url),
    ]
    first_read_barrier = Barrier(2)

    def synchronized_first_read(service: MemoryService):
        original = service.get_experience_reflection
        state = {"first": True}

        def read(experience_ref: str):
            current = original(experience_ref)
            if state["first"]:
                state["first"] = False
                first_read_barrier.wait()
            return current

        return read

    for service in services:
        service.get_experience_reflection = synchronized_first_read(service)

    feedback = [
        OperatorFeedbackContract(
            feedback_id=f"operator-feedback://feedback-race/{index}",
            mission_id=mission_id,
            experience_id=experience_id,
            assessment="helpful",
            operator_ref=f"operator://feedback-race/{index}",
            evidence_refs=[f"evidence://feedback-race/{index}"],
            timestamp=f"2026-08-11T18:00:0{index + 1}Z",
        )
        for index in (1, 2)
    ]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(service.record_operator_feedback, item)
            for service, item in zip(services, feedback, strict=True)
        ]
        results = [future.result() for future in futures]

    assert len(results) == 2
    stored = seed.get_experience_reflection(experience_id)
    assert stored is not None
    for index in (1, 2):
        feedback_id = f"operator-feedback://feedback-race/{index}"
        assert feedback_id in (stored.experience.user_feedback or "")
        assert feedback_id in stored.experience.evidence_refs
        assert feedback_id in stored.experience.signal_refs
    assert stored.reflection is not None
    assert stored.reflection.evidence_refs == stored.experience.evidence_refs


def test_decision_outcome_attribution_append_is_concurrency_idempotent() -> None:
    temp_dir = runtime_dir("decision-attribution-concurrency")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    record = sample_decision_outcome_attribution(suffix="concurrent")
    services = [
        MemoryService(database_url=database_url),
        MemoryService(database_url=database_url),
    ]
    persist_attribution_experience(services[0], record)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda service: service.record_decision_outcome_attribution(record),
                services,
            )
        )

    assert results == [record, record]
    assert services[0].list_decision_outcome_attributions() == [record]

    competing = (
        sample_decision_outcome_attribution(suffix="race-left", request_id="req-attribution-race"),
        sample_decision_outcome_attribution(suffix="race-right", request_id="req-attribution-race"),
    )
    persist_attribution_experience(services[0], competing[0])
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                service.record_decision_outcome_attribution,
                candidate,
            )
            for service, candidate in zip(services, competing, strict=True)
        ]
    successes = [future.result() for future in futures if future.exception() is None]
    failures = [future.exception() for future in futures if future.exception() is not None]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], ValueError)
    assert (
        services[0].get_decision_outcome_attribution(request_id="req-attribution-race") in competing
    )


def test_runtime_request_claim_is_atomic_across_memory_service_instances() -> None:
    temp_dir = runtime_dir("runtime-request-claim-concurrency")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    services = [
        MemoryService(database_url=database_url),
        MemoryService(database_url=database_url),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda service: service.claim_runtime_request(
                    request_id="req-atomic-claim",
                    session_id="sess-atomic-claim",
                    claimed_at="2026-08-11T16:00:00+00:00",
                ),
                services,
            )
        )

    assert sorted(results) == [False, True]
    assert (
        services[0].claim_runtime_request(
            request_id="req-atomic-claim",
            session_id="sess-atomic-claim",
            claimed_at="2026-08-11T16:00:01+00:00",
        )
        is False
    )


def test_decision_outcome_attribution_table_rejects_mutation_and_tamper() -> None:
    temp_dir = runtime_dir("decision-attribution-immutable")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = MemoryService(database_url=database_url)
    record = sample_decision_outcome_attribution(suffix="immutable")
    persist_attribution_experience(service, record)
    service.record_decision_outcome_attribution(record)
    repository = service.repository
    assert isinstance(repository, SqliteMemoryRepository)

    with pytest.raises(IntegrityError, match="append-only"):
        with repository._connect() as connection:
            connection.execute(
                """
                UPDATE decision_outcome_attributions
                SET observed_at = '2026-08-11T13:00:00Z'
                WHERE attribution_record_id = ?
                """,
                (record.attribution_record_id,),
            )
    with pytest.raises(IntegrityError, match="append-only"):
        with repository._connect() as connection:
            connection.execute(
                """
                DELETE FROM decision_outcome_attributions
                WHERE attribution_record_id = ?
                """,
                (record.attribution_record_id,),
            )

    tampered = sample_decision_outcome_attribution(suffix="tampered")
    with repository._connect() as connection:
        connection.execute(
            """
            INSERT INTO decision_outcome_attributions (
                attribution_record_id, request_id, session_id, mission_id,
                workflow_profile, observed_at, payload_json, payload_sha256
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tampered.attribution_record_id,
                str(tampered.request_id),
                str(tampered.session_id),
                str(tampered.mission_id),
                tampered.workflow_profile,
                tampered.observed_at,
                canonical_decision_attribution_payload(tampered),
                "0" * 64,
            ),
        )
    with pytest.raises(ValueError, match="integrity check failed"):
        service.get_decision_outcome_attribution(
            attribution_record_id=tampered.attribution_record_id
        )


def test_decision_outcome_attribution_scope_precedes_limit_and_offset() -> None:
    temp_dir = runtime_dir("decision-attribution-scope")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    target_old = sample_decision_outcome_attribution(
        suffix="target-old",
        mission_id="mission-target",
        observed_at="2026-08-11T10:00:00Z",
    )
    target_new = sample_decision_outcome_attribution(
        suffix="target-new",
        mission_id="mission-target",
        observed_at="2026-08-11T11:00:00Z",
    )
    global_newest = sample_decision_outcome_attribution(
        suffix="other-newest",
        mission_id="mission-other",
        workflow_profile="other_workflow",
        observed_at="2026-08-11T12:00:00Z",
    )
    for record in (target_old, target_new, global_newest):
        persist_attribution_experience(service, record)
        service.record_decision_outcome_attribution(record)

    forged = canonicalize_decision_attribution_record(
        replace(
            target_new,
            attribution_record_id="decision-attribution://target-forged",
            request_id=RequestId("req-attribution-target-forged"),
            observed_at="2026-08-11T13:00:00Z",
            execution_allowed=True,
        )
    )
    repository = service.repository
    assert isinstance(repository, SqliteMemoryRepository)
    with repository._connect() as connection:
        connection.execute(
            """
            INSERT INTO decision_outcome_attributions (
                attribution_record_id, request_id, session_id, mission_id,
                workflow_profile, observed_at, payload_json, payload_sha256
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                forged.attribution_record_id,
                str(forged.request_id),
                str(forged.session_id),
                str(forged.mission_id),
                forged.workflow_profile,
                forged.observed_at,
                canonical_decision_attribution_payload(forged),
                decision_attribution_fingerprint(forged),
            ),
        )

    with pytest.raises(ValueError):
        service.get_decision_outcome_attribution(attribution_record_id=forged.attribution_record_id)

    assert service.list_decision_outcome_attributions(mission_id="mission-target", limit=1) == [
        target_new
    ]
    assert service.list_decision_outcome_attributions(
        mission_id="mission-target",
        workflow_profile="software_change_workflow",
        limit=1,
        offset=1,
    ) == [target_old]


def test_decision_outcome_attribution_never_enters_input_recovery() -> None:
    temp_dir = runtime_dir("decision-attribution-recovery-isolation")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    record = sample_decision_outcome_attribution(suffix="recovery-isolation")
    persist_attribution_experience(service, record)
    service.record_decision_outcome_attribution(record)

    recovered = service.recover_for_input(
        InputContract(
            request_id=record.request_id,
            session_id=record.session_id,
            mission_id=record.mission_id,
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue without consuming attribution telemetry.",
            timestamp="2026-08-11T12:01:00Z",
        )
    )

    assert all(record.attribution_record_id not in item for item in recovered.recovered_items)


def test_memory_service_recovers_empty_context_for_new_session() -> None:
    temp_dir = runtime_dir("memory-empty")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    result = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Hello",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    assert isinstance(result, MemoryRecoveryResult)
    assert result.recovered_items == []
    assert result.recovery_contract.requested_scopes == DEFAULT_MEMORY_SCOPES
    assert result.recovery_contract.priority_rules[0].startswith("default_recovery_order=")


def test_memory_service_recovers_evidence_grounded_semantic_candidates() -> None:
    temp_dir = runtime_dir("memory-semantic-candidates")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MissionId("mission-semantic-current"),
            mission_goal="Define the governed strategic direction.",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-07-18T11:00:00Z",
            semantic_brief="objective=Define the governed strategic direction.",
            semantic_focus=[
                "strategy",
                "estrategia_e_pensamento_sistemico",
            ],
        )
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-semantic-current"),
            session_id=SessionId("sess-semantic-current"),
            mission_id=MissionId("mission-semantic-current"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the governed strategic direction.",
            timestamp="2026-07-18T12:00:00Z",
        )
    )

    assert len(recovered.semantic_memory_candidates) == 1
    candidate = recovered.semantic_memory_candidates[0]
    assert candidate.anchor_ref == ("memory://mission/mission-semantic-current/semantic")
    assert candidate.source_kind == "active_mission"
    assert candidate.observed_at == "2026-07-18T11:00:00Z"
    assert candidate.freshness_status == "current"
    assert candidate.relevance_score >= 0.5
    assert candidate.relevance_reason == "active_mission_id_match"
    assert candidate.evidence_refs[0].startswith(
        "mission-state://mission-semantic-current/semantic/"
    )
    assert candidate.read_only is True
    assert candidate.memory_write_allowed is False
    assert candidate.automatic_promotion_allowed is False
    assert candidate.core_mutation_allowed is False


def test_memory_service_marks_stale_semantic_candidate_without_using_it() -> None:
    temp_dir = runtime_dir("memory-semantic-stale")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MissionId("mission-semantic-stale"),
            mission_goal="Old strategic direction.",
            mission_status=MissionStatus.PAUSED,
            checkpoints=[],
            updated_at="2026-05-01T12:00:00Z",
            semantic_brief="objective=Old strategic direction.",
            semantic_focus=["strategy"],
        )
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-semantic-stale"),
            session_id=SessionId("sess-semantic-stale"),
            mission_id=MissionId("mission-semantic-stale"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Review the old direction.",
            timestamp="2026-07-18T12:00:00Z",
        )
    )

    assert len(recovered.semantic_memory_candidates) == 1
    candidate = recovered.semantic_memory_candidates[0]
    assert candidate.freshness_status == "stale"
    assert candidate.lifecycle_status == "expired"
    assert candidate.read_only is True


def test_memory_service_records_and_recovers_session_history_across_instances() -> None:
    temp_dir = runtime_dir("memory-history")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-2"),
        session_id=SessionId("sess-2"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    writer = reviewed_playbook_memory_service(database_url)
    record = writer.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    reader = MemoryService(database_url=database_url)
    recovered = reader.recover_for_input(contract)
    assert isinstance(record, MemoryRecordResult)
    assert record.record_contract.record_type == "interaction_turn"
    assert record.record_contract.payload["decision_frame"] == "planning"
    assert record.record_contract.payload["dominant_goal"] == "Please plan the sprint."
    assert record.record_contract.payload["open_loops"] == ["fechar checkpoint principal"]
    assert any("planning" in item for item in recovered.recovered_items)
    assert any("context_summary=" in item for item in recovered.session_context)
    assert any("session_continuity_brief=" in item for item in recovered.session_context)
    assert any("session_continuity_mode=continuar" in item for item in recovered.session_context)
    assert any("continuity_checkpoint_id=" in item for item in recovered.session_context)
    assert any("continuity_checkpoint_status=ready" in item for item in recovered.session_context)
    assert any("continuity_replay_status=resumable" in item for item in recovered.session_context)
    assert any("continuity_resume_point=continuar:" in item for item in recovered.session_context)
    assert recovered.mission_hints == []
    assert any("prior_plan=" in item for item in recovered.plan_hints)


def test_memory_service_exposes_recoverable_continuity_checkpoint() -> None:
    temp_dir = runtime_dir("memory-checkpoint")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-checkpoint"),
        session_id=SessionId("sess-checkpoint"),
        mission_id=MissionId("mission-checkpoint"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service = MemoryService(database_url=database_url)
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    checkpoint = MemoryService(database_url=database_url).get_session_continuity_checkpoint(
        "sess-checkpoint"
    )

    assert checkpoint is not None
    assert checkpoint.session_id == SessionId("sess-checkpoint")
    assert checkpoint.continuity_action == "continuar"
    assert checkpoint.checkpoint_status == "ready"
    assert "sessao segue ancorada" in checkpoint.checkpoint_summary
    assert checkpoint.replay_summary is not None


def test_memory_service_builds_resumable_continuity_replay_state() -> None:
    temp_dir = runtime_dir("memory-replay")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-replay"),
        session_id=SessionId("sess-replay"),
        mission_id=MissionId("mission-replay"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service = MemoryService(database_url=database_url)
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    replay = MemoryService(database_url=database_url).get_session_continuity_replay("sess-replay")

    assert replay is not None
    assert replay.session_id == SessionId("sess-replay")
    assert replay.replay_status == "resumable"
    assert replay.recovery_mode == "resume_active_mission"
    assert replay.resume_point.startswith("continuar:")
    assert replay.requires_manual_resume is False


def test_memory_service_recovers_bounded_ecosystem_state_for_continuity() -> None:
    temp_dir = runtime_dir("memory-ecosystem-state")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-eco-1"),
        session_id=SessionId("sess-eco"),
        mission_id=MissionId("mission-eco"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-04-23T00:00:00Z",
    )
    service = MemoryService(database_url=database_url)
    dispatch = sample_operation_dispatch(
        request_id="req-eco-1",
        session_id="sess-eco",
        mission_id="mission-eco",
    )
    result = sample_operation_result(
        operation_id="op-sample",
        artifact_ref="runtime://artifact/milestone-plan.md",
    )

    service.record_turn(
        contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
        operation_dispatch=dispatch,
        operation_result=result,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-eco-2"),
            session_id=SessionId("sess-eco"),
            mission_id=MissionId("mission-eco"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue milestone coordination.",
            timestamp="2026-04-23T00:01:00Z",
        )
    )
    replay = service.get_session_continuity_replay("sess-eco")
    checkpoint = service.get_session_continuity_checkpoint("sess-eco")
    mission_state = service.get_mission_state("mission-eco")

    assert replay is not None
    assert replay.ecosystem_state_status == "operational_state_attached"
    assert replay.recovery_mode == "resume_operational_checkpoint"
    assert replay.resume_point.startswith("ecosystem_checkpoint:")
    assert replay.linked_surface_ids == ["surface://jarvis_console"]
    assert replay.active_surface_id == "surface://jarvis_console"
    assert replay.surface_continuity_status == "single_surface"
    assert replay.surface_identity_conflict_flags == []
    assert checkpoint is not None
    assert checkpoint.ecosystem_state_status == "operational_state_attached"
    assert checkpoint.open_checkpoint_refs == [
        "workflow_checkpoint:close_readiness_checkpoint:pending"
    ]
    assert checkpoint.active_surface_id == "surface://jarvis_console"
    assert mission_state is not None
    assert mission_state.ecosystem_state_status == "operational_state_attached"
    assert mission_state.active_work_items == ["mission_task:Plan milestone M3"]
    assert "runtime://artifact/milestone-plan.md" in mission_state.active_artifact_refs
    assert mission_state.project_ref == "project://mission-eco"
    assert mission_state.objective_ref == "objective://mission-eco"
    assert mission_state.objective_status == "completed"
    assert mission_state.next_action_ref == "next_action:close_readiness_checkpoint"
    assert mission_state.linked_surface_ids == ["surface://jarvis_console"]
    assert mission_state.active_surface_id == "surface://jarvis_console"
    assert any(
        item == "mission_ecosystem_state_status=operational_state_attached"
        for item in recovered.recovered_items
    )
    assert any(
        item.startswith("mission_active_work_items=mission_task:Plan milestone M3")
        for item in recovered.recovered_items
    )
    assert any(
        item.startswith("mission_active_artifact_refs=")
        and "runtime://artifact/milestone-plan.md" in item
        for item in recovered.recovered_items
    )
    assert any(
        item.startswith("mission_open_checkpoint_refs=") for item in recovered.recovered_items
    )
    assert any(item == "mission_objective_status=completed" for item in recovered.recovered_items)
    assert any(
        item == "mission_project_ref=project://mission-eco" for item in recovered.recovered_items
    )
    assert any(item.startswith("mission_work_item_refs=") for item in recovered.recovered_items)
    assert any(
        item == "mission_active_surface_id=surface://jarvis_console"
        for item in recovered.recovered_items
    )


def test_memory_service_resolves_governed_continuity_pause() -> None:
    temp_dir = runtime_dir("memory-pause")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = MemoryService(database_url=database_url)
    contract = InputContract(
        request_id=RequestId("req-pause-1"),
        session_id=SessionId("sess-pause"),
        mission_id=MissionId("mission-pause"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Need explicit validation before changing mission.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="reformular objetivo com impacto operacional",
            goal="Please plan the sprint.",
            steps=["explicitar conflito", "pedir validacao"],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            constraints=["revisao humana"],
            risks=["pedido contem sinais de risco operacional"],
            recommended_task_type="general_response",
            requires_human_validation=True,
            rationale="contexto=missao ativa; apoio=baseline local",
            continuity_action="reformular",
            continuity_reason="pedido atual desloca o foco da missao ativa",
            open_loops=["fechar checkpoint principal"],
        ),
        governance_decision=PermissionDecision.DEFER_FOR_VALIDATION,
    )

    pause = service.get_session_continuity_pause("sess-pause")

    assert pause is not None
    assert pause.pause_status == "awaiting_validation"
    assert pause.requires_human_input is True

    resolved_pause = service.resolve_session_continuity_pause(
        "sess-pause",
        approved=True,
        resolved_by="operator",
        resolution_note="validado manualmente para retomar",
    )
    replay = service.get_session_continuity_replay("sess-pause")

    assert resolved_pause is not None
    assert resolved_pause.pause_status == "approved"
    assert resolved_pause.resolution_status == "approved"
    assert replay is not None
    assert replay.replay_status == "resumable"
    assert replay.requires_manual_resume is False


def test_memory_service_persists_mission_state_with_identity_continuity_and_open_loops() -> None:
    temp_dir = runtime_dir("memory-mission")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-3"),
        session_id=SessionId("sess-3"),
        mission_id=MissionId("mission-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    mission_state = service.get_mission_state("mission-1")
    assert mission_state is not None
    assert mission_state.mission_goal == "Coordinate milestone M3."
    assert mission_state.checkpoints
    assert "planning" in mission_state.active_tasks
    assert mission_state.last_recommendation == "decompor objetivo em etapas reversiveis"
    assert mission_state.semantic_brief is not None
    assert mission_state.identity_continuity_brief is not None
    assert "prioridade=fechar checkpoint principal" in mission_state.identity_continuity_brief
    assert mission_state.open_loops == ["fechar checkpoint principal"]
    assert mission_state.last_decision_frame == "planning"


def test_memory_service_lists_open_missions_by_latest_canonical_update() -> None:
    temp_dir = runtime_dir("memory-daily-workspace-list")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    for mission_id, status, updated_at in (
        ("mission-older", MissionStatus.PAUSED, "2026-07-16T09:00:00+00:00"),
        ("mission-closed", MissionStatus.COMPLETED, "2026-07-17T10:00:00+00:00"),
        ("mission-newer", MissionStatus.ACTIVE, "2026-07-17T09:00:00+00:00"),
    ):
        service.repository.upsert_mission_state(
            MissionStateContract(
                mission_id=MissionId(mission_id),
                mission_goal=f"Goal for {mission_id}",
                mission_status=status,
                checkpoints=[],
                updated_at=updated_at,
            )
        )

    open_states = service.list_mission_states(limit=20)
    all_states = service.list_mission_states(limit=20, include_closed=True)

    assert [str(state.mission_id) for state in open_states] == [
        "mission-newer",
        "mission-older",
    ]
    assert [str(state.mission_id) for state in all_states] == [
        "mission-closed",
        "mission-newer",
        "mission-older",
    ]


def test_memory_service_recovers_mission_hints_in_continuity_priority_order() -> None:
    temp_dir = runtime_dir("memory-order")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-4"),
        session_id=SessionId("sess-4"),
        mission_id=MissionId("mission-2"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    recovered = service.recover_for_input(contract)
    assert recovered.mission_hints[0].startswith("identity_continuity_brief=")
    assert recovered.mission_hints[1].startswith("open_loops=")
    assert any(item.startswith("mission_goal=") for item in recovered.mission_hints)
    assert any(item.startswith("mission_recommendation=") for item in recovered.mission_hints)


def test_memory_service_derives_long_horizon_goal_strategy_read_only() -> None:
    temp_dir = runtime_dir("memory-long-horizon")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    mission_id = "mission-long-horizon"
    service.record_turn(
        InputContract(
            request_id=RequestId("req-long-horizon"),
            session_id=SessionId("sess-long-horizon"),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the long horizon rollout.",
            timestamp="2026-05-20T00:00:00Z",
        ),
        intent="planning",
        response_text="Long horizon rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref="work-item://mission-long-horizon/validate-plan",
        work_item_status="active",
        transition_ref="work_item_transition:create:long-horizon",
        next_action_ref="next_action:operator-review",
    )
    service.transition_artifact_lifecycle_state(
        mission_id=mission_id,
        artifact_ref="artifact://mission-long-horizon/plan/v1",
        artifact_status="active",
        transition_ref="artifact_lifecycle_transition:register:long-horizon",
        artifact_version=1,
        work_item_ref="work-item://mission-long-horizon/validate-plan",
    )

    strategy = service.build_long_horizon_goal_strategy(mission_id)

    assert strategy is not None
    assert strategy.strategy_status == "ready"
    assert "mode=read_only_no_scheduler" in strategy.strategy_summary
    assert "work-item://mission-long-horizon/validate-plan" in strategy.milestone_refs
    assert "artifact://mission-long-horizon/plan/v1" in strategy.evidence_refs
    assert strategy.next_action_ref == "next_action:operator-review"
    assert strategy.memory_write_mode == "read_only"
    assert strategy.autonomous_scheduling_allowed is False


def test_memory_service_detects_related_mission_continuity_within_same_session() -> None:
    temp_dir = runtime_dir("memory-related")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.record_turn(
        InputContract(
            request_id=RequestId("req-related-1"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-related-2"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout risks.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="analysis",
        response_text="Risk analysis drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-related-3"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the risk analysis.",
            timestamp="2026-03-17T00:02:00Z",
        )
    )

    assert recovered.continuity_context is not None
    assert recovered.continuity_context.related_candidates
    candidate = recovered.continuity_context.related_candidates[0]
    assert candidate.mission_id == MissionId("mission-a")
    assert candidate.relation_type == "same_session_related_mission"
    assert candidate.priority_score >= 0.6
    assert recovered.continuity_context.recommended_action == "priorizar_loop_ativo"


def test_memory_service_prepares_core_mediated_shared_memory_for_specialists() -> None:
    temp_dir = runtime_dir("memory-specialist-shared")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.record_turn(
        InputContract(
            request_id=RequestId("req-specialist-a"),
            session_id=SessionId("sess-specialist"),
            mission_id=MissionId("mission-specialist-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    continuity = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-specialist-b"),
            session_id=SessionId("sess-specialist"),
            mission_id=MissionId("mission-specialist-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout risks.",
            timestamp="2026-03-17T00:01:00Z",
        )
    ).continuity_context

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-specialist",
        specialist_hints=["operational_planning_specialist"],
        active_domains=["strategy", "productivity"],
        mission_id="mission-specialist-b",
        continuity_context=continuity,
    )

    shared_memory = contexts["operational_planning_specialist"]
    persisted = service.get_specialist_shared_memory(
        session_id="sess-specialist",
        specialist_type="operational_planning_specialist",
    )

    assert shared_memory.sharing_mode == "core_mediated_read_only"
    assert shared_memory.write_policy == "through_core_only"
    assert shared_memory.related_mission_ids
    assert shared_memory.shared_memory_brief.startswith(
        "specialist=operational_planning_specialist"
    )
    assert persisted is not None
    assert persisted.shared_memory_brief == shared_memory.shared_memory_brief
    assert persisted.write_policy == "through_core_only"
    assert "memory://relational" in persisted.memory_refs
    assert "memory://domain/strategy" in persisted.memory_refs
    assert persisted.memory_class_policies["mission"]["sharing_mode"] == "core_mediated_read_only"
    assert persisted.memory_class_policies["domain"]["domain_linked"] is True
    assert "semantic" not in persisted.consumed_memory_classes
    assert "procedural" not in persisted.consumed_memory_classes
    assert persisted.consumer_mode == "baseline_shared_context"
    assert persisted.mission_context_brief is not None
    assert persisted.domain_context_brief is not None
    assert persisted.continuity_context_brief is not None


def test_memory_service_builds_guided_domain_memory_packet_for_promoted_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-domain")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-memory-1"),
        session_id=SessionId("sess-guided-memory"),
        mission_id=MissionId("mission-guided-memory"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Analyze Python service rollout.",
        timestamp="2026-03-27T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial software analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="avaliar rollout do servico Python com contratos estaveis",
            goal="Review Python service rollout",
            steps=["mapear contratos", "comparar mudanca", "recomendar"],
            active_domains=["software_development", "analysis"],
            active_minds=["mente_analitica"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=False,
            rationale="contexto=software",
            specialist_hints=["software_change_specialist"],
            continuity_action="continuar",
            open_loops=["comparar mudanca no servico"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-memory",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development", "analysis"],
        mission_id="mission-guided-memory",
        continuity_context=None,
    )

    guided = contexts["software_change_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert guided.mission_context_brief is not None
    assert "goal=Analyze Python service rollout." in guided.mission_context_brief
    assert guided.domain_context_brief is not None
    assert "active_domains=software_development,analysis" in guided.domain_context_brief
    assert "workflow_profile=software_change_workflow" in guided.domain_context_brief
    assert guided.continuity_context_brief is not None
    assert "continuity_mode=continuar" in guided.continuity_context_brief
    assert guided.consumer_profile == "software_change_review"
    assert guided.consumer_objective is not None
    assert "direção de patch recomendada" in guided.consumer_objective
    assert guided.expected_deliverables == [
        "implementation_findings",
        "change_risk_summary",
        "recommended_patch_direction",
    ]
    assert guided.telemetry_focus == [
        "contract_impact",
        "change_safety",
        "implementation_trace",
    ]

    persisted = service.get_specialist_shared_memory(
        session_id="sess-guided-memory",
        specialist_type="software_change_specialist",
    )
    assert persisted is not None
    assert persisted.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in persisted.consumed_memory_classes
    assert "procedural" in persisted.consumed_memory_classes
    assert guided.semantic_memory_state == "operational"
    assert guided.procedural_memory_state == "operational"
    assert guided.memory_consolidation_status == "in_progress"
    assert guided.memory_fixation_status == "not_fixed"
    assert guided.memory_archive_status == "active_memory"
    assert guided.procedural_artifact_status == "candidate"
    assert guided.procedural_artifact_refs
    assert guided.procedural_artifact_version == 1
    assert guided.procedural_artifact_summary is not None
    assert persisted.consumer_profile == guided.consumer_profile
    assert persisted.consumer_objective == guided.consumer_objective
    assert persisted.expected_deliverables == guided.expected_deliverables
    assert persisted.telemetry_focus == guided.telemetry_focus
    assert persisted.mission_context_brief == guided.mission_context_brief
    assert persisted.domain_context_brief == guided.domain_context_brief
    assert persisted.continuity_context_brief == guided.continuity_context_brief
    assert persisted.semantic_memory_state == "operational"
    assert persisted.procedural_memory_state == "operational"
    assert persisted.memory_consolidation_status == "in_progress"
    assert persisted.memory_fixation_status == "not_fixed"
    assert persisted.memory_archive_status == "active_memory"
    assert persisted.procedural_artifact_status == "candidate"
    assert persisted.procedural_artifact_refs == guided.procedural_artifact_refs
    assert persisted.procedural_artifact_version == guided.procedural_artifact_version
    assert persisted.procedural_artifact_summary == guided.procedural_artifact_summary


def test_memory_service_records_bounded_procedural_playbook_candidate() -> None:
    temp_dir = runtime_dir("memory-procedural-playbook")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    record = service.record_procedural_playbook_candidate(
        ProceduralPlaybookCandidateContract(
            playbook_candidate_id="playbook-candidate://software-change/001",
            procedure_name="bounded patch review",
            workflow_profile="software_change_workflow",
            route="software_engineering",
            domain="engenharia_de_software",
            bounded_steps=[
                "collect evidence",
                "run targeted tests",
                "prepare rollback",
            ],
            evidence_refs=["trace://req-playbook"],
            source_artifact_refs=["artifact://procedural/software/v1"],
            source_reflection_refs=["reflection://mission/001"],
            proposed_tests=["pytest services/memory-service/tests"],
            rollback_plan_ref="rollback://playbook/001",
            timestamp="2026-07-04T00:00:00Z",
        )
    )
    blocked = service.record_procedural_playbook_candidate(
        ProceduralPlaybookCandidateContract(
            playbook_candidate_id="playbook-candidate://software-change/blocked",
            procedure_name="unsafe patch review",
            workflow_profile="software_change_workflow",
            bounded_steps=["skip evidence"],
            evidence_refs=[],
            timestamp="2026-07-04T00:01:00Z",
            automatic_promotion_allowed=True,
        )
    )

    assert record.candidate.review_status == "candidate"
    assert record.candidate.automatic_promotion_allowed is False
    assert record.candidate.core_mutation_allowed is False
    assert blocked.candidate.review_status == "needs_review"
    assert "evidence_required" in blocked.candidate.blockers
    assert "rollback_plan_required" in blocked.candidate.blockers
    assert "automatic_promotion_not_allowed" in blocked.candidate.blockers

    records = service.list_procedural_playbook_candidates(
        workflow_profile="software_change_workflow",
        limit=5,
    )
    assert [item.candidate.playbook_candidate_id for item in records] == [
        "playbook-candidate://software-change/blocked",
        "playbook-candidate://software-change/001",
    ]
    assert records[1].candidate.memory_write_mode == "through_core_only"


def test_memory_service_persists_reviewed_procedural_playbook_idempotently() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-persistence")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    playbook = sample_reviewed_procedural_playbook()
    writer = reviewed_playbook_memory_service(database_url)

    stored = writer.record_reviewed_procedural_playbook(playbook)
    idempotent = writer.record_reviewed_procedural_playbook(playbook)
    unverified_reload = MemoryService(database_url=database_url).list_reviewed_procedural_playbooks(
        workflow_profile=playbook.workflow_profile,
        route=playbook.route,
        domain=playbook.domain,
        review_status="approved",
    )
    reloaded = reviewed_playbook_memory_service(database_url).list_reviewed_procedural_playbooks(
        workflow_profile=playbook.workflow_profile,
        route=playbook.route,
        domain=playbook.domain,
        review_status="approved",
    )

    assert idempotent == stored
    assert unverified_reload == []
    assert reloaded == [stored]
    assert reloaded[0].playbook == playbook


@pytest.mark.parametrize(
    ("case_id", "version"),
    [
        ("leading-major-zero", "01.0.0"),
        ("leading-minor-zero", "1.01.0"),
        ("leading-patch-zero", "1.0.01"),
        ("arabic-indic-digit", "١.2.3"),
        ("fullwidth-digit", "１.2.3"),
    ],
)
def test_memory_service_rejects_noncanonical_reviewed_playbook_semver(
    case_id: str,
    version: str,
) -> None:
    temp_dir = runtime_dir(f"memory-reviewed-playbook-semver-{case_id}")
    service = reviewed_playbook_memory_service(f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    with pytest.raises(ValueError, match="numeric semver"):
        service.record_reviewed_procedural_playbook(
            replace(sample_reviewed_procedural_playbook(), version=version)
        )

    assert service.list_reviewed_procedural_playbooks() == []


def test_memory_service_fails_closed_without_persisted_evolution_verifier() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-verifier")
    playbook = sample_reviewed_procedural_playbook()
    unverified = MemoryService(database_url=f"sqlite:///{(temp_dir / 'unverified.db').as_posix()}")
    rejected = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'rejected.db').as_posix()}",
        reviewed_procedural_playbook_verifier=lambda _playbook: False,
    )

    for service in (unverified, rejected):
        with pytest.raises(ValueError, match="persisted evolution verification"):
            service.record_reviewed_procedural_playbook(playbook)
        assert service.list_reviewed_procedural_playbooks() == []


def test_memory_service_filters_repository_rows_that_fail_evolution_verification() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-read-verification")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    reviewed = sample_reviewed_procedural_playbook()
    service = MemoryService(
        database_url=database_url,
        reviewed_procedural_playbook_verifier=lambda playbook: playbook == reviewed,
    )
    stored = service.record_reviewed_procedural_playbook(reviewed)
    forged_rows = [
        replace(
            reviewed,
            playbook_id=(f"reviewed-playbook://software-change/forged-{index:02d}"),
            bounded_steps=["unreviewed runtime guidance"],
            timestamp=f"9999-12-31T23:{index:02d}:00Z",
        )
        for index in range(25)
    ]
    for forged in forged_rows:
        assert (
            service.repository._insert_reviewed_procedural_playbook(
                StoredReviewedProceduralPlaybook(playbook=forged)
            )
            is True
        )

    assert service.list_reviewed_procedural_playbooks(limit=20) == [stored]
    with pytest.raises(ValueError, match="persisted evolution verification"):
        service.revoke_reviewed_procedural_playbook(
            playbook_id=forged_rows[0].playbook_id,
            version=forged_rows[0].version,
            revocation_ref="human-review://forged/revoke",
            revoked_at="2026-07-19T00:00:00Z",
        )


def test_reviewed_playbook_repository_create_and_revoke_are_atomic() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-atomic")
    service = reviewed_playbook_memory_service(f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    original = sample_reviewed_procedural_playbook()
    changed = replace(original, bounded_steps=["overwrite immutable guidance"])

    assert (
        service.repository._insert_reviewed_procedural_playbook(
            StoredReviewedProceduralPlaybook(playbook=original)
        )
        is True
    )
    assert (
        service.repository._insert_reviewed_procedural_playbook(
            StoredReviewedProceduralPlaybook(playbook=changed)
        )
        is False
    )
    assert service.repository.fetch_reviewed_procedural_playbook(
        original.playbook_id,
        original.version,
    ) == StoredReviewedProceduralPlaybook(playbook=original)

    first_revocation = replace(
        original,
        review_status="revoked",
        evidence_refs=[*original.evidence_refs, "human-review://revoke/first"],
        revoked_at="2026-07-18T13:00:00Z",
        revocation_ref="human-review://revoke/first",
    )
    competing_revocation = replace(
        first_revocation,
        evidence_refs=[*original.evidence_refs, "human-review://revoke/second"],
        revocation_ref="human-review://revoke/second",
    )
    assert (
        service.repository._transition_reviewed_procedural_playbook_to_revoked(
            StoredReviewedProceduralPlaybook(playbook=first_revocation)
        )
        is True
    )
    assert (
        service.repository._transition_reviewed_procedural_playbook_to_revoked(
            StoredReviewedProceduralPlaybook(playbook=competing_revocation)
        )
        is False
    )
    assert service.repository.fetch_reviewed_procedural_playbook(
        original.playbook_id,
        original.version,
    ) == StoredReviewedProceduralPlaybook(playbook=first_revocation)


def test_memory_service_keeps_reviewed_playbook_version_immutable() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-immutable")
    service = reviewed_playbook_memory_service(f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    playbook = sample_reviewed_procedural_playbook()
    service.record_reviewed_procedural_playbook(playbook)

    with pytest.raises(ValueError, match="version is immutable"):
        service.record_reviewed_procedural_playbook(
            replace(
                playbook,
                bounded_steps=["replace approved guidance in place"],
            )
        )

    persisted = service.list_reviewed_procedural_playbooks(
        workflow_profile=playbook.workflow_profile,
        route=playbook.route,
        domain=playbook.domain,
    )
    assert [record.playbook for record in persisted] == [playbook]


def test_memory_service_filters_reviewed_playbooks_by_scope_and_status() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-filters")
    service = reviewed_playbook_memory_service(f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    relevant = sample_reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://software-change/relevant",
        timestamp="2026-07-18T12:00:00Z",
    )
    other_route = sample_reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://software-change/other-route",
        route="strategic_reasoning",
        timestamp="2026-07-18T12:01:00Z",
    )
    other_workflow = sample_reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://software-change/other-workflow",
        workflow_profile="strategic_reasoning_workflow",
        timestamp="2026-07-18T12:02:00Z",
    )
    other_domain = sample_reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://software-change/other-domain",
        domain="strategy",
        timestamp="2026-07-18T12:03:00Z",
    )
    revoked = sample_reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://software-change/revoked",
        timestamp="2026-07-18T12:04:00Z",
    )
    for playbook in (
        relevant,
        other_route,
        other_workflow,
        other_domain,
        revoked,
    ):
        service.record_reviewed_procedural_playbook(playbook)
    service.revoke_reviewed_procedural_playbook(
        playbook_id=revoked.playbook_id,
        version=revoked.version,
        revocation_ref="human-review://software-change/revoke-filtered",
        revoked_at="2026-07-18T13:00:00Z",
    )

    approved_for_scope = service.list_reviewed_procedural_playbooks(
        workflow_profile=relevant.workflow_profile,
        route=relevant.route,
        domain=relevant.domain,
        review_status="approved",
    )
    revoked_for_scope = service.list_reviewed_procedural_playbooks(
        workflow_profile=relevant.workflow_profile,
        route=relevant.route,
        domain=relevant.domain,
        review_status="revoked",
    )

    assert [record.playbook.playbook_id for record in approved_for_scope] == [relevant.playbook_id]
    assert [record.playbook.playbook_id for record in revoked_for_scope] == [revoked.playbook_id]


def test_memory_service_revocation_preserves_artifact_and_blocks_reactivation() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-revocation")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = reviewed_playbook_memory_service(database_url)
    playbook = sample_reviewed_procedural_playbook()
    service.record_reviewed_procedural_playbook(playbook)
    revocation_ref = "human-review://software-change/revoke-bounded-review"

    revoked = service.revoke_reviewed_procedural_playbook(
        playbook_id=playbook.playbook_id,
        version=playbook.version,
        revocation_ref=revocation_ref,
        revoked_at="2026-07-18T13:00:00Z",
    )
    reader = reviewed_playbook_memory_service(database_url)
    reloaded = reader.list_reviewed_procedural_playbooks(
        workflow_profile=playbook.workflow_profile,
        route=playbook.route,
        domain=playbook.domain,
        review_status="revoked",
    )

    assert reloaded == [revoked]
    assert revoked.playbook.playbook_id == playbook.playbook_id
    assert revoked.playbook.version == playbook.version
    assert revoked.playbook.source_candidate_id == playbook.source_candidate_id
    assert revoked.playbook.bounded_steps == playbook.bounded_steps
    assert revoked.playbook.review_status == "revoked"
    assert revoked.playbook.revoked_at == "2026-07-18T13:00:00Z"
    assert revoked.playbook.revocation_ref == revocation_ref
    assert revocation_ref in revoked.playbook.evidence_refs

    with pytest.raises(ValueError, match="version is immutable"):
        reader.record_reviewed_procedural_playbook(playbook)

    assert (
        reader.list_reviewed_procedural_playbooks(
            workflow_profile=playbook.workflow_profile,
            route=playbook.route,
            domain=playbook.domain,
            review_status="approved",
        )
        == []
    )


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("read_only", False),
        ("execution_allowed", True),
        ("tool_dispatch_allowed", True),
        ("memory_write_mode", "through_core_only"),
        ("automatic_promotion_allowed", True),
        ("core_mutation_allowed", True),
    ],
)
def test_memory_service_rejects_reviewed_playbook_authority_flags(
    field_name: str,
    unsafe_value: object,
) -> None:
    temp_dir = runtime_dir(f"memory-reviewed-playbook-authority-{field_name}")
    service = reviewed_playbook_memory_service(f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    unsafe_playbook = replace(
        sample_reviewed_procedural_playbook(),
        **{field_name: unsafe_value},
    )

    with pytest.raises(ValueError, match="cannot claim authority"):
        service.record_reviewed_procedural_playbook(unsafe_playbook)

    assert service.list_reviewed_procedural_playbooks() == []


def test_memory_service_scoped_playbook_query_avoids_global_limit_starvation() -> None:
    temp_dir = runtime_dir("memory-reviewed-playbook-scoped-limit")
    service = reviewed_playbook_memory_service(f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    relevant = sample_reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://software-change/old-but-relevant",
        timestamp="2026-07-18T00:00:00Z",
    )
    service.record_reviewed_procedural_playbook(relevant)
    for index in range(12):
        service.record_reviewed_procedural_playbook(
            sample_reviewed_procedural_playbook(
                playbook_id=f"reviewed-playbook://strategy/unrelated-{index:02d}",
                route="strategic_reasoning",
                workflow_profile="strategic_reasoning_workflow",
                domain="strategy",
                timestamp=f"2026-07-18T12:{index:02d}:00Z",
            )
        )

    globally_limited = service.list_reviewed_procedural_playbooks(limit=8)
    assert relevant.playbook_id not in {record.playbook.playbook_id for record in globally_limited}

    # Route-aware recovery consumes this seam after routing; scope filters must
    # therefore be applied before LIMIT instead of slicing a global snapshot.
    scoped = service.list_reviewed_procedural_playbooks(
        workflow_profile=relevant.workflow_profile,
        route=relevant.route,
        domain=relevant.domain,
        review_status="approved",
        limit=1,
    )
    assert [record.playbook.playbook_id for record in scoped] == [relevant.playbook_id]


def test_memory_service_registers_versioned_inactive_skill_candidate() -> None:
    temp_dir = runtime_dir("memory-skill-candidate")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    candidate = SkillCandidateContract(
        skill_candidate_id="skill-candidate://release-evidence/1.0.0",
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        inputs=["change_scope", "release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify evidence", "report missing gates"],
        risk_level=RiskLevel.MODERATE,
        evidence_refs=["trace://release-evidence/1"],
        source_pattern_refs=["recurring-pattern://release-evidence"],
        failure_modes=["missing_release_evidence"],
        proposed_tests=["run targeted release tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        timestamp="2026-07-16T14:00:00Z",
    )

    stored = service.record_skill_candidate(candidate)
    idempotent = service.record_skill_candidate(candidate)
    reloaded = service.get_skill_candidate(candidate.skill_candidate_id)
    filtered = service.list_skill_candidates(
        skill_id=candidate.skill_id,
        version="1.0.0",
        domain="software_engineering",
        review_status="needs_review",
    )

    assert stored == idempotent
    assert reloaded == stored
    assert filtered == [stored]
    assert stored.candidate.registry_status == "candidate_inactive"
    assert stored.candidate.review_status == "needs_review"
    assert stored.candidate.activation_status == "inactive"
    assert stored.candidate.risk_level == RiskLevel.MODERATE
    assert stored.candidate.automatic_activation_allowed is False
    assert stored.candidate.automatic_promotion_allowed is False
    assert stored.candidate.core_mutation_allowed is False


def test_memory_service_contains_unsafe_skill_candidate_claims() -> None:
    temp_dir = runtime_dir("memory-skill-candidate-contained")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    stored = service.record_skill_candidate(
        SkillCandidateContract(
            skill_candidate_id="skill-candidate://unsafe-release/1.0.0",
            skill_id="skill://unsafe-release",
            skill_name="unsafe release automation",
            version="1.0.0",
            workflow_profile="software_change_workflow",
            domain="software_engineering",
            specialist_type="software_change_specialist",
            inputs=["release_scope"],
            outputs=["release_decision"],
            allowed_tools=["*"],
            bounded_instructions=["release without review"],
            risk_level=RiskLevel.HIGH,
            evidence_refs=["trace://unsafe-release/1"],
            source_pattern_refs=["recurring-pattern://unsafe-release"],
            failure_modes=["unauthorized_release"],
            proposed_tests=["run release gate"],
            rollback_plan_ref="rollback://skill/unsafe-release/1.0.0",
            registry_status="active",
            review_status="approved",
            activation_status="active",
            sandbox_required=False,
            automatic_activation_allowed=True,
            automatic_promotion_allowed=True,
            core_mutation_allowed=True,
            memory_write_mode="direct",
            timestamp="2026-07-16T14:01:00Z",
        )
    )

    assert stored.candidate.registry_status == "candidate_inactive"
    assert stored.candidate.review_status == "needs_review"
    assert stored.candidate.activation_status == "inactive"
    assert stored.candidate.sandbox_required is True
    assert stored.candidate.automatic_activation_allowed is False
    assert stored.candidate.automatic_promotion_allowed is False
    assert stored.candidate.core_mutation_allowed is False
    assert stored.candidate.memory_write_mode == "through_core_only"
    assert "high_risk_candidate_requires_explicit_sandbox_review" in (stored.candidate.blockers)
    assert "activation_status_forced_inactive" in stored.candidate.blockers
    assert "automatic_activation_not_allowed" in stored.candidate.blockers
    assert "allowed_tools_must_be_explicit" in stored.candidate.blockers


def test_memory_service_rejects_skill_candidate_version_collisions_and_mutation() -> None:
    temp_dir = runtime_dir("memory-skill-candidate-immutable")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    def candidate(candidate_id: str, *, name: str) -> SkillCandidateContract:
        return SkillCandidateContract(
            skill_candidate_id=candidate_id,
            skill_id="skill://immutable",
            skill_name=name,
            version="1.0.0",
            workflow_profile="software_change_workflow",
            domain="software_engineering",
            specialist_type="software_change_specialist",
            inputs=["input"],
            outputs=["output"],
            allowed_tools=[],
            bounded_instructions=["bounded step"],
            risk_level=RiskLevel.LOW,
            evidence_refs=["trace://immutable/1"],
            source_pattern_refs=["recurring-pattern://immutable"],
            failure_modes=["invalid_output"],
            proposed_tests=["run immutable skill test"],
            rollback_plan_ref="rollback://skill/immutable/1.0.0",
            timestamp="2026-07-16T14:02:00Z",
        )

    service.record_skill_candidate(
        candidate("skill-candidate://immutable/1.0.0", name="immutable skill")
    )

    with pytest.raises(ValueError, match="versions are immutable"):
        service.record_skill_candidate(
            candidate("skill-candidate://immutable/1.0.0", name="mutated skill")
        )
    with pytest.raises(ValueError, match="already belong"):
        service.record_skill_candidate(
            candidate("skill-candidate://immutable-alias/1.0.0", name="alias skill")
        )
    with pytest.raises(ValueError, match="numeric semver"):
        invalid_version = candidate(
            "skill-candidate://immutable/latest",
            name="invalid version",
        )
        invalid_version.version = "latest"
        service.record_skill_candidate(invalid_version)


def test_memory_service_persists_session_continuity_for_governed_reformulation() -> None:
    temp_dir = runtime_dir("memory-session-continuity")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-session-1"),
        session_id=SessionId("sess-session"),
        mission_id=MissionId("mission-session"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-session-2"),
            session_id=SessionId("sess-session"),
            mission_id=MissionId("mission-session"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="planning",
        response_text="Need explicit validation before changing mission.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="reformular objetivo com impacto operacional",
            goal="Please plan the sprint.",
            steps=["explicitar conflito", "pedir validacao"],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            constraints=["revisao humana"],
            risks=["pedido contem sinais de risco operacional"],
            recommended_task_type="general_response",
            requires_human_validation=True,
            rationale="contexto=missao ativa; apoio=baseline local",
            continuity_action="reformular",
            continuity_reason="pedido atual desloca o foco da missao ativa",
            open_loops=["fechar checkpoint principal"],
        ),
        governance_decision=PermissionDecision.DEFER_FOR_VALIDATION,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-session-3"),
            session_id=SessionId("sess-session"),
            mission_id=MissionId("mission-session"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="How should we proceed?",
            timestamp="2026-03-17T00:02:00Z",
        )
    )

    assert any("session_continuity_mode=reformular" in item for item in recovered.session_context)
    assert any(
        "session_continuity_brief=sessao entrou em reformulacao governada" in item
        for item in recovered.session_context
    )


def test_memory_service_recommends_related_mission_for_new_request_when_score_is_strong() -> None:
    temp_dir = runtime_dir("memory-related-new")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.record_turn(
        InputContract(
            request_id=RequestId("req-related-4"),
            session_id=SessionId("sess-related-new"),
            mission_id=MissionId("mission-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-related-5"),
            session_id=SessionId("sess-related-new"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout risks.",
            timestamp="2026-03-17T00:03:00Z",
        )
    )

    assert recovered.continuity_context is not None
    assert recovered.continuity_context.recommended_action == "retomar_missao_relacionada"
    assert recovered.continuity_context.related_priority_score is not None
    assert recovered.continuity_context.related_priority_score >= 0.7
    assert any(
        item == "continuity_recommendation=retomar_missao_relacionada"
        for item in recovered.mission_hints
    )


def test_memory_service_ranks_related_candidates_deterministically() -> None:
    temp_dir = runtime_dir("memory-ranked")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    first_plan = sample_plan()
    second_plan = sample_plan()
    second_plan.open_loops = []
    service.record_turn(
        InputContract(
            request_id=RequestId("req-rank-a"),
            session_id=SessionId("sess-ranked"),
            mission_id=MissionId("mission-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Plan A.",
        deliberative_plan=first_plan,
        specialist_contributions=sample_specialist_contributions(),
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-rank-b"),
            session_id=SessionId("sess-ranked"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout risk controls.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="planning",
        response_text="Plan B.",
        deliberative_plan=second_plan,
        specialist_contributions=[],
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-rank-c"),
            session_id=SessionId("sess-ranked"),
            mission_id=MissionId("mission-c"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout.",
            timestamp="2026-03-17T00:02:00Z",
        )
    )

    assert recovered.continuity_context is not None
    candidates = recovered.continuity_context.related_candidates
    assert [candidate.mission_id for candidate in candidates] == [
        MissionId("mission-b"),
        MissionId("mission-a"),
    ]


def test_build_memory_repository_defaults_to_runtime_sqlite() -> None:
    repository = build_memory_repository(None)
    assert isinstance(repository, SqliteMemoryRepository)


def test_parse_sqlite_database_path_handles_windows_style_urls() -> None:
    database_path = parse_sqlite_database_path("sqlite:///C:/jarvis/runtime/memory.db")
    assert database_path == Path("C:/jarvis/runtime/memory.db")


def test_normalize_database_url_accepts_postgres_aliases() -> None:
    assert (
        normalize_database_url("postgres://user:pass@localhost:5432/jarvis")
        == "postgresql://user:pass@localhost:5432/jarvis"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@localhost:5432/jarvis")
        == "postgresql://user:pass@localhost:5432/jarvis"
    )


def test_build_memory_repository_uses_postgres_for_operational_urls(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakePostgresRepository:
        def __init__(self, database_url: str) -> None:
            captured["database_url"] = database_url

    monkeypatch.setattr(memory_repository, "PostgresMemoryRepository", FakePostgresRepository)
    repository = build_memory_repository("postgres://postgres:postgres@localhost:5432/jarvis")
    assert isinstance(repository, FakePostgresRepository)
    assert captured["database_url"] == "postgresql://postgres:postgres@localhost:5432/jarvis"


def test_memory_service_preserves_accepted_mission_state_on_defer_and_block() -> None:
    temp_dir = runtime_dir("memory-governed")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    mission_contract = InputContract(
        request_id=RequestId("req-accepted"),
        session_id=SessionId("sess-governed"),
        mission_id=MissionId("mission-governed"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-03-17T00:00:00Z",
    )
    accepted_plan = sample_plan()
    service.record_turn(
        mission_contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=accepted_plan,
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-defer"),
            session_id=SessionId("sess-governed"),
            mission_id=MissionId("mission-governed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="planning",
        response_text="Need explicit validation before changing mission.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="reformular objetivo com impacto operacional",
            goal="Start a new marketing campaign instead.",
            steps=["explicitar conflito", "pedir validacao"],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            constraints=["revisao humana"],
            risks=["pedido contem sinais de risco operacional"],
            recommended_task_type="general_response",
            requires_human_validation=True,
            rationale="contexto=missao ativa; apoio=baseline local",
            continuity_action="reformular",
            open_loops=["fechar checkpoint principal"],
        ),
        governance_decision=PermissionDecision.DEFER_FOR_VALIDATION,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-block"),
            session_id=SessionId("sess-governed"),
            mission_id=MissionId("mission-governed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all mission records now.",
            timestamp="2026-03-17T00:02:00Z",
        ),
        intent="sensitive_action",
        response_text="Blocked by governance.",
        deliberative_plan=accepted_plan,
        governance_decision=PermissionDecision.BLOCK,
    )

    mission_state = service.get_mission_state("mission-governed")

    assert mission_state is not None
    assert mission_state.mission_goal == "Coordinate milestone M3."
    assert mission_state.last_recommendation == accepted_plan.plan_summary
    assert mission_state.open_loops == ["fechar checkpoint principal"]
    assert mission_state.last_decision_frame == "planning"


def test_memory_service_builds_guided_domain_memory_packet_for_analysis_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-analysis")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-analysis-1"),
        session_id=SessionId("sess-guided-analysis"),
        mission_id=MissionId("mission-guided-analysis"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Compare evidence for the rollout decision.",
        timestamp="2026-03-27T00:10:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial structured analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="comparar evidencias e trade-offs do rollout",
            goal="Compare rollout evidence",
            steps=["coletar evidencias", "comparar trade-offs", "recomendar criterio"],
            active_domains=["analysis", "decision_risk"],
            active_minds=["mente_analitica"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=False,
            rationale="contexto=analysis",
            specialist_hints=["structured_analysis_specialist"],
            continuity_action="continuar",
            open_loops=["consolidar criterio dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-analysis",
        specialist_hints=["structured_analysis_specialist"],
        active_domains=["analysis", "decision_risk"],
        mission_id="mission-guided-analysis",
        continuity_context=None,
    )

    guided = contexts["structured_analysis_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert any(ref.startswith("memory://semantic/") for ref in guided.memory_refs)
    assert not any(ref.startswith("memory://procedural/") for ref in guided.memory_refs)
    assert guided.domain_context_brief is not None
    assert "active_domains=analysis,decision_risk" in guided.domain_context_brief
    assert "workflow_profile=structured_analysis_workflow" in guided.domain_context_brief
    persisted = service.get_specialist_shared_memory(
        session_id="sess-guided-analysis",
        specialist_type="structured_analysis_specialist",
    )
    assert persisted is not None
    assert persisted.consumer_mode == "domain_guided_memory_packet"


def test_memory_service_prefers_first_eligible_route_when_specialist_is_shared() -> None:
    temp_dir = runtime_dir("memory-guided-shared-analysis-route")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-shared-analysis-1"),
        session_id=SessionId("sess-guided-shared-analysis"),
        mission_id=MissionId("mission-guided-shared-analysis"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Compare strategic options and clarify the dominant trade-off.",
        timestamp="2026-03-27T00:20:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Initial strategic analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="comparar trade-offs estrategicos e recomendar direcao",
            goal="Plan strategic options",
            steps=["mapear opcoes", "comparar trade-offs", "recomendar direcao"],
            active_domains=["strategy", "analysis"],
            active_minds=["mente_decisoria"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=strategy",
            specialist_hints=["structured_analysis_specialist"],
            continuity_action="continuar",
            open_loops=["fechar criterio estrategico dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-shared-analysis",
        specialist_hints=["structured_analysis_specialist"],
        active_domains=["strategy", "analysis"],
        mission_id="mission-guided-shared-analysis",
        continuity_context=None,
    )

    guided = contexts["structured_analysis_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert guided.consumer_profile == "strategy_tradeoff_review"
    assert guided.consumer_objective is not None
    assert "trade-offs" in guided.consumer_objective
    assert guided.expected_deliverables == [
        "tradeoff_map",
        "decision_criteria",
        "recommended_direction",
    ]
    assert guided.telemetry_focus == [
        "tradeoff_clarity",
        "decision_trace",
        "domain_alignment",
    ]


def sample_operation_dispatch(
    *,
    request_id: str,
    session_id: str,
    mission_id: str,
) -> OperationDispatchContract:
    return OperationDispatchContract(
        operation_id=OperationId("op-sample"),
        request_id=RequestId(request_id),
        task_type="draft_plan",
        task_goal="Coordinate milestone M3.",
        task_plan="Draft milestone plan.",
        constraints=["low-risk"],
        expected_output="markdown plan",
        plan_summary="decompor objetivo em etapas reversiveis",
        session_id=SessionId(session_id),
        mission_id=MissionId(mission_id),
        workflow_profile="operational_readiness_workflow",
        workflow_domain_route="operational_readiness",
        workflow_steps=["map readiness", "close checkpoint"],
        workflow_checkpoints=["capture_scope", "close_readiness_checkpoint"],
        workflow_checkpoint_state={
            "capture_scope": "completed",
            "close_readiness_checkpoint": "pending",
        },
        workflow_resume_point="close_readiness_checkpoint",
        workflow_resume_status="resume_available",
        ecosystem_state_status="operational_state_attached",
        active_work_items=["mission_task:Plan milestone M3"],
        active_artifact_refs=["artifact://procedural/strategy/milestone-plan/v1"],
        open_checkpoint_refs=["workflow_checkpoint:close_readiness_checkpoint:pending"],
        surface_presence=["surface:chat", f"session:{session_id}", f"mission:{mission_id}"],
        ecosystem_state_summary="work_items=1; artifacts=1; open_checkpoints=1; surfaces=3",
        surface_id="surface://jarvis_console",
        surface_kind="console",
        surface_session_id=session_id,
        surface_capability_scope=["text_input"],
        operator_identity_ref="operator://local_console",
        canonical_user_ref="user://local_operator",
        surface_continuity_status="single_surface",
    )


def sample_operation_result(*, operation_id: str, artifact_ref: str) -> OperationResultContract:
    return OperationResultContract(
        operation_id=OperationId(operation_id),
        status=OperationStatus.COMPLETED,
        outputs=["Milestone plan created."],
        timestamp="2026-04-23T00:00:00Z",
        artifacts=[artifact_ref],
        checkpoints=["workflow_state:completed"],
        ecosystem_state_status="operational_state_attached",
        active_work_items=["mission_task:Plan milestone M3"],
        active_artifact_refs=[
            "artifact://procedural/strategy/milestone-plan/v1",
            artifact_ref,
        ],
        open_checkpoint_refs=["workflow_checkpoint:close_readiness_checkpoint:pending"],
        surface_presence=["surface:chat", "session:sess-eco", "mission:mission-eco"],
        ecosystem_state_summary="work_items=1; artifacts=2; open_checkpoints=1; surfaces=3",
        surface_id="surface://jarvis_console",
        surface_kind="console",
        surface_session_id="sess-eco",
        surface_capability_scope=["text_input"],
        operator_identity_ref="operator://local_console",
        canonical_user_ref="user://local_operator",
        surface_continuity_status="single_surface",
    )


def test_memory_service_exposes_archivable_lifecycle_policy_for_stale_guided_memory() -> None:
    decision = memory_lifecycle_decision(
        semantic_sources=["related_mission"],
        procedural_sources=["user_scope"],
        continuity_source="fresh_request",
    )

    assert decision.semantic_lifecycle == "aging"
    assert decision.procedural_lifecycle == "aging"
    assert decision.semantic_memory_state == "archivable"
    assert decision.procedural_memory_state == "archivable"
    assert decision.lifecycle_status == "review_recommended"
    assert decision.review_status == "review_recommended"
    assert decision.consolidation_status == "revisit_before_reuse"
    assert decision.fixation_status == "not_fixed"
    assert decision.archive_status == "archive_candidate"


def test_memory_service_recovery_marks_archivable_procedural_artifact_for_review() -> None:
    temp_dir = runtime_dir("memory-archivable-artifact-recovery")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-archivable-artifact-1"),
        session_id=SessionId("sess-archivable-artifact"),
        mission_id=MissionId("mission-archivable-artifact"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Prepare the rollout procedure update.",
        timestamp="2026-04-09T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Governed rollout procedure stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="estruturar procedimento de rollout com revisao governada",
            goal="Prepare rollout procedure update",
            steps=["preparar patch", "revisar rollback", "publicar checkpoint"],
            active_domains=["software_development"],
            active_minds=["mente_executiva"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=software",
            specialist_hints=["software_change_specialist"],
            continuity_action="continuar",
            open_loops=["revisar checkpoint de rollback"],
            procedural_memory_lifecycle="aging",
            procedural_memory_state="archivable",
            memory_review_status="review_recommended",
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-archivable-artifact-2"),
            session_id=SessionId("sess-archivable-artifact"),
            mission_id=MissionId("mission-archivable-artifact"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the rollout procedure review.",
            timestamp="2026-04-09T00:01:00Z",
        )
    )

    assert "procedural_artifact_status=archivable" in recovered.plan_hints
    assert "memory_recovery_mode=review_before_reuse" in recovered.plan_hints
    assert not any(item.startswith("procedural_artifact_ref=") for item in recovered.plan_hints)
    assert not any(item.startswith("procedural_artifact_summary=") for item in recovered.plan_hints)


def test_memory_service_blocks_auto_reuse_of_archivable_recurrent_specialist_memory(
    monkeypatch,
) -> None:
    temp_dir = runtime_dir("memory-archivable-recurrent-specialist")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    stale_context = SpecialistSharedMemoryContextContract(
        specialist_type="software_change_specialist",
        sharing_mode="core_mediated_read_only",
        continuity_mode="continuar",
        shared_memory_brief="specialist=software_change_specialist continuidade=continuar",
        write_policy="through_core_only",
        consumer_mode="domain_guided_memory_packet",
        semantic_focus=["software_development"],
        semantic_memory_lifecycle="aging",
        procedural_memory_lifecycle="aging",
        semantic_memory_state="archivable",
        procedural_memory_state="archivable",
        memory_lifecycle_status="review_recommended",
        memory_review_status="review_recommended",
        memory_consolidation_status="revisit_before_reuse",
        memory_fixation_status="not_fixed",
        memory_archive_status="archive_candidate",
        recurrent_context_status="recoverable",
        recurrent_interaction_count=2,
        recurrent_context_brief="specialist=software_change_specialist | reuse=enabled",
        recurrent_domain_focus=["software_development"],
        recurrent_memory_refs=["memory://semantic/mission/old"],
        recurrent_continuity_modes=["continuar"],
    )

    monkeypatch.setattr(
        service.repository,
        "fetch_latest_specialist_shared_memory_for_user",
        lambda **_: stale_context,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-archivable-recurrent-specialist",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development"],
        mission_id=None,
        continuity_context=None,
        user_id="user-archivable-recurrent",
    )

    guided = contexts["software_change_specialist"]

    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" not in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.recurrent_context_status == "review_required"
    assert guided.continuity_context_brief is not None
    assert "recurrent_memory_status=review_required" in guided.continuity_context_brief
    assert guided.domain_context_brief is not None
    assert "memory_runtime_mode=review_only" in guided.domain_context_brief


def test_memory_service_builds_guided_domain_memory_packet_for_governance_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-governance")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-governance-1"),
        session_id=SessionId("sess-guided-governance"),
        mission_id=MissionId("mission-guided-governance"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Review governance limits for the rollout.",
        timestamp="2026-03-27T00:30:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial governance analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="avaliar limites de governanca do rollout",
            goal="Review governance limits",
            steps=["mapear riscos", "comparar limites", "recomendar contenção"],
            active_domains=["governance", "decision_risk"],
            active_minds=["mente_etica"],
            constraints=["through_core_only"],
            risks=["governance_risk"],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=True,
            rationale="contexto=governance",
            specialist_hints=["governance_review_specialist"],
            continuity_action="continuar",
            open_loops=["validar limite dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-governance",
        specialist_hints=["governance_review_specialist"],
        active_domains=["governance", "decision_risk"],
        mission_id="mission-guided-governance",
        continuity_context=None,
    )

    guided = contexts["governance_review_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=governance,decision_risk" in guided.domain_context_brief
    assert "workflow_profile=governance_boundary_workflow" in guided.domain_context_brief


def test_memory_service_builds_guided_packet_for_readiness_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-readiness")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-readiness-1"),
        session_id=SessionId("sess-guided-readiness"),
        mission_id=MissionId("mission-guided-readiness"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan readiness checks for the release.",
        timestamp="2026-03-27T00:50:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Initial readiness planning stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="estruturar readiness checks do release",
            goal="Plan readiness checks",
            steps=["mapear readiness", "definir checkpoints", "sugerir rollback"],
            active_domains=["operational_readiness", "observability"],
            active_minds=["mente_executiva"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=readiness",
            specialist_hints=["operational_planning_specialist"],
            continuity_action="continuar",
            open_loops=["fechar checkpoint de readiness"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-readiness",
        specialist_hints=["operational_planning_specialist"],
        active_domains=["operational_readiness", "observability"],
        mission_id="mission-guided-readiness",
        continuity_context=None,
    )

    guided = contexts["operational_planning_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=operational_readiness,observability" in guided.domain_context_brief
    assert "workflow_profile=operational_readiness_workflow" in guided.domain_context_brief


def test_memory_service_builds_guided_packet_for_strategy_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-strategy")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-strategy-1"),
        session_id=SessionId("sess-guided-strategy"),
        mission_id=MissionId("mission-guided-strategy"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan strategic options for the next release.",
        timestamp="2026-03-27T01:10:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Initial strategy planning stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="comparar direcoes estrategicas do release",
            goal="Plan strategic options",
            steps=["mapear opcoes", "comparar trade-offs", "recomendar criterio"],
            active_domains=["strategy", "decision_risk"],
            active_minds=["mente_decisoria"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=strategy",
            specialist_hints=["structured_analysis_specialist"],
            continuity_action="continuar",
            open_loops=["fechar criterio estrategico dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-strategy",
        specialist_hints=["structured_analysis_specialist"],
        active_domains=["strategy", "decision_risk"],
        mission_id="mission-guided-strategy",
        continuity_context=None,
    )

    guided = contexts["structured_analysis_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=strategy,decision_risk" in guided.domain_context_brief
    assert "workflow_profile=strategic_direction_workflow" in guided.domain_context_brief


def test_memory_service_builds_guided_packet_for_decision_risk_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-decision-risk")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-decision-risk-1"),
        session_id=SessionId("sess-guided-decision-risk"),
        mission_id=MissionId("mission-guided-decision-risk"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Review decision risk and containment gates for the release.",
        timestamp="2026-03-27T01:30:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial decision risk analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="avaliar reversibilidade e gate dominante da decisao",
            goal="Review decision risk",
            steps=["mapear risco", "comparar reversibilidade", "recomendar gate dominante"],
            active_domains=["decision_risk", "governance"],
            active_minds=["mente_etica"],
            constraints=["through_core_only"],
            risks=["decision_risk"],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=True,
            rationale="contexto=decision_risk",
            specialist_hints=["governance_review_specialist"],
            continuity_action="continuar",
            open_loops=["fechar gate dominante de decisao"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-decision-risk",
        specialist_hints=["governance_review_specialist"],
        active_domains=["decision_risk", "governance"],
        mission_id="mission-guided-decision-risk",
        continuity_context=None,
    )

    guided = contexts["governance_review_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=decision_risk,governance" in guided.domain_context_brief
    assert "workflow_profile=decision_risk_workflow" in guided.domain_context_brief


def test_memory_service_builds_recoverable_recurrent_specialist_context() -> None:
    temp_dir = runtime_dir("memory-specialist-recurrence")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    first = service.prepare_specialist_shared_memory(
        session_id="sess-recurrent-1",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development"],
        mission_id=None,
        continuity_context=None,
        user_id="user-recurrent-1",
    )["software_change_specialist"]
    second = service.prepare_specialist_shared_memory(
        session_id="sess-recurrent-2",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development", "analysis"],
        mission_id=None,
        continuity_context=None,
        user_id="user-recurrent-1",
    )["software_change_specialist"]

    assert first.recurrent_context_status == "seeded"
    assert first.recurrent_interaction_count == 1
    assert second.recurrent_context_status == "recoverable"
    assert second.recurrent_interaction_count == 2
    assert second.recurrent_context_brief is not None
    assert "software_development" in second.recurrent_domain_focus
    assert second.recurrent_continuity_modes == ["continuar"]
    persisted = service.get_specialist_shared_memory(
        session_id="sess-recurrent-2",
        specialist_type="software_change_specialist",
    )
    assert persisted is not None
    assert persisted.recurrent_context_status == "recoverable"
    assert persisted.recurrent_interaction_count == 2


def test_memory_service_recovers_recoverable_user_scope_context() -> None:
    temp_dir = runtime_dir("memory-user-scope")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    user_id = "user-1"
    service.record_turn(
        InputContract(
            request_id=RequestId("req-user-1"),
            session_id=SessionId("sess-user-1"),
            mission_id=MissionId("mission-user-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the first milestone.",
            timestamp="2026-03-31T00:00:00Z",
            user_id=user_id,
        ),
        intent="planning",
        response_text="Initial milestone plan stored.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-user-2"),
            session_id=SessionId("sess-user-2"),
            mission_id=MissionId("mission-user-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the milestone trade-offs.",
            timestamp="2026-03-31T00:01:00Z",
            user_id=user_id,
        ),
        intent="analysis",
        response_text="Trade-off analysis stored.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-user-3"),
            session_id=SessionId("sess-user-3"),
            mission_id=MissionId("mission-user-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue from the user context.",
            timestamp="2026-03-31T00:02:00Z",
            user_id=user_id,
        )
    )

    assert recovered.organization_scope_status == "no_go_without_canonical_consumer"
    assert recovered.organization_scope_reopen_signal == "canonical_consumer_required_for_reopen"
    assert recovered.user_scope_context is not None
    assert recovered.user_scope_context.context_status == "recoverable"
    assert recovered.user_scope_context.interaction_count == 2
    assert "planning" in recovered.user_scope_context.recent_intents
    assert "analysis" in recovered.user_scope_context.recent_intents
    assert recovered.user_scope_context.recent_domain_focus
    assert any(item == "user_scope_status=recoverable" for item in recovered.user_hints)
    assert any(item.startswith("user_context_brief=") for item in recovered.user_hints)
    assert any(
        item == "context_compaction_status=compressed_live_context"
        for item in recovered.session_context
    )
    assert any(item.startswith("context_live_summary=") for item in recovered.session_context)
    assert any(item == "cross_session_recall_status=active" for item in recovered.recovered_items)
    assert any(
        item.startswith("cross_session_recall_summary=") for item in recovered.recovered_items
    )
    assert any(str(scope.value) == "user" for scope in recovered.recovery_contract.requested_scopes)


def test_memory_lifecycle_queue_requires_human_review_and_never_mutates_sources() -> None:
    temp_dir = runtime_dir("memory-lifecycle-review")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.repository.upsert_specialist_shared_memory(
        StoredSpecialistSharedMemory(
            session_id="sess-memory-consolidating",
            specialist_type="software_change_specialist",
            sharing_mode="shared_read_only",
            continuity_mode="continuar",
            shared_memory_brief="consolidating memory",
            write_policy="through_core_only",
            semantic_memory_lifecycle="consolidating",
            procedural_memory_lifecycle="consolidating",
            memory_lifecycle_status="emerging",
            memory_review_status="monitor",
            updated_at="2026-07-16T00:00:00Z",
        )
    )
    service.repository.upsert_specialist_shared_memory(
        StoredSpecialistSharedMemory(
            session_id="sess-memory-aging",
            specialist_type="structured_analysis_specialist",
            sharing_mode="shared_read_only",
            continuity_mode="continuar",
            shared_memory_brief="aging memory",
            write_policy="through_core_only",
            semantic_memory_lifecycle="aging",
            procedural_memory_lifecycle="aging",
            memory_lifecycle_status="review_recommended",
            memory_review_status="review_recommended",
            updated_at="2026-07-16T00:00:00Z",
        )
    )
    service.record_reviewed_learning_guidance(
        ReviewedLearningGuidanceContract(
            guidance_id="reviewed-learning-guidance://expired/001",
            source_review_decision_id="review-decision://expired/001",
            evolution_proposal_id="proposal-expired-001",
            review_status="approved",
            route="software_change",
            workflow_profile="software_change_workflow",
            domain="software_development",
            guidance_summary="use the bounded rollback checklist",
            allowed_usage=["planning_context"],
            evidence_refs=["trace://expired-guidance/001"],
            rollback_plan_ref="rollback://reviewed-learning/expired/001",
            timestamp="2026-07-14T00:00:00Z",
            expires_at="2026-07-15T00:00:00Z",
        )
    )

    generated_at = "2026-07-16T00:00:00Z"
    queue = service.list_memory_lifecycle_review_queue(
        generated_at=generated_at,
        limit=10,
    )
    assert {candidate.maintenance_action for candidate in queue} == {
        "archive",
        "consolidate",
        "expire",
    }
    assert all(candidate.review_status == "needs_review" for candidate in queue)
    assert all(candidate.execution_status == "not_executed" for candidate in queue)
    assert all(not candidate.automatic_execution_allowed for candidate in queue)

    archive_candidate = next(
        candidate for candidate in queue if candidate.maintenance_action == "archive"
    )
    source_summary_before = service.repository.summarize_memory_corpus()
    guidance_before = service.list_reviewed_learning_guidance(limit=10)
    governance = GovernanceService()
    assessment = governance.assess_memory_lifecycle_review(
        archive_candidate,
        decision_action="approve",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/archive/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        assessed_at="2026-07-16T00:00:01Z",
    )
    approved = service.record_memory_lifecycle_review_decision(
        candidate_id=archive_candidate.candidate_id,
        decision_action="approve",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/archive/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        review_notes=["evidence checked; manual execution remains separate"],
        governance_assessment=assessment,
    )

    assert approved.review_status == "approved"
    assert approved.execution_authorized is False
    approved_queue = service.list_memory_lifecycle_review_queue(
        generated_at=generated_at,
        limit=10,
    )
    approved_candidate = next(
        candidate
        for candidate in approved_queue
        if candidate.candidate_id == archive_candidate.candidate_id
    )
    assert approved_candidate.review_status == "approved"
    assert approved_candidate.execution_status == "not_executed"

    rollback_assessment = governance.assess_memory_lifecycle_review(
        approved_candidate,
        decision_action="rollback",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/rollback/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        previous_review_status=approved.review_status,
        assessed_at="2026-07-16T00:00:02Z",
    )
    rolled_back = service.record_memory_lifecycle_review_decision(
        candidate_id=archive_candidate.candidate_id,
        decision_action="rollback",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/rollback/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        review_notes=["reverted review disposition only"],
        governance_assessment=rollback_assessment,
    )

    assert rolled_back.review_status == "rolled_back"
    assert rolled_back.execution_authorized is False
    assert service.repository.summarize_memory_corpus() == source_summary_before
    assert service.list_reviewed_learning_guidance(limit=10) == guidance_before

    expire_candidate = next(
        candidate for candidate in queue if candidate.maintenance_action == "expire"
    )
    forged_assessment = MemoryLifecycleGovernanceAssessmentContract(
        assessment_id="memory-lifecycle-assessment://forged",
        candidate_id=expire_candidate.candidate_id,
        maintenance_action="expire",
        decision_action="reject",
        status="governed",
        timestamp="2026-07-16T00:00:03Z",
    )
    with pytest.raises(ValueError, match="policy trace required"):
        service.record_memory_lifecycle_review_decision(
            candidate_id=expire_candidate.candidate_id,
            decision_action="reject",
            operator_ref="operator://memory-reviewer",
            evidence_refs=[],
            rollback_plan_ref=None,
            review_notes=[],
            governance_assessment=forged_assessment,
        )
