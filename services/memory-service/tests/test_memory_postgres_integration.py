import importlib.util
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from os import getenv
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from governance_service.service import GovernanceService
from memory_service.service import MemoryService

from shared.artifact_physical_saga import (
    seal_artifact_physical_apply_plan,
    seal_artifact_physical_rollback_plan,
    seal_local_text_physical_state_attestation,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalRollbackPlanContract,
    DecisionOutcomeAttributionRecordContract,
    ExperienceRecordContract,
    InputContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
    LocalTextRollbackReceipt,
    MissionStateContract,
    WorkItemStateContract,
)
from shared.decision_attribution import canonicalize_decision_attribution_record
from shared.local_text_rollback_permissions import (
    build_mutation_receipt_fingerprint,
    build_rollback_receipt_fingerprint,
)
from shared.types import ChannelType, InputType, MissionId, MissionStatus, RequestId, SessionId
from shared.workflow_lifecycle import workflow_lifecycle_transition_fingerprint
from tests.unit.test_workflow_lifecycle import _activation, _rollback
from tools.benchmarks.harness import ADOPT_IN_V1, BenchmarkHarness


def postgres_url() -> str:
    database_url = getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL não configurada para a integração PostgreSQL.")
    if importlib.util.find_spec("psycopg") is None:
        pytest.skip("psycopg não instalado na .venv local.")
    return database_url


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_memory_service_persists_session_history_in_postgres() -> None:
    service = MemoryService(database_url=postgres_url())
    contract = InputContract(
        request_id=RequestId("postgres-req-1"),
        session_id=SessionId("postgres-sess-1"),
        mission_id=MissionId("postgres-mission-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan the PostgreSQL validation flow.",
        timestamp="2026-03-19T00:00:00Z",
    )

    service.record_turn(contract, intent="planning", response_text="PostgreSQL validated.")
    recovered = MemoryService(database_url=postgres_url()).recover_for_input(contract)
    mission_state = MemoryService(database_url=postgres_url()).get_mission_state(
        "postgres-mission-1"
    )
    checkpoint = MemoryService(database_url=postgres_url()).get_session_continuity_checkpoint(
        "postgres-sess-1"
    )
    replay = MemoryService(database_url=postgres_url()).get_session_continuity_replay(
        "postgres-sess-1"
    )

    assert any("PostgreSQL validated." in item for item in recovered.recovered_items)
    assert any(
        ("intent=planning" in item) or ("PostgreSQL validated." in item)
        for item in recovered.recovered_items
    )
    assert mission_state is not None
    assert checkpoint is not None
    assert replay is not None
    assert checkpoint.checkpoint_status in {"ready", "closed", "awaiting_validation", "contained"}
    assert replay.replay_status in {"resumable", "closed", "awaiting_validation", "contained"}
    assert "planning" in mission_state.active_tasks
    assert mission_state.semantic_brief is not None
    assert "Plan the PostgreSQL validation flow." in mission_state.semantic_brief


def test_decision_outcome_attribution_is_immutable_across_postgres_instances() -> None:
    import psycopg

    suffix = uuid4().hex
    database_url = postgres_url()
    request_id = f"postgres-attribution-request-{suffix}"
    mission_id = f"postgres-attribution-mission-{suffix}"
    experience_id = f"experience://{mission_id}/{request_id}"
    record = canonicalize_decision_attribution_record(
        DecisionOutcomeAttributionRecordContract(
            attribution_record_id=f"decision-attribution://postgres/{suffix}",
            request_id=RequestId(request_id),
            session_id=SessionId(f"postgres-attribution-session-{suffix}"),
            mission_id=MissionId(mission_id),
            observed_at="2026-08-11T12:00:00Z",
            governance_decision_ref=f"governance-decision://postgres/{suffix}",
            governance_decision_status="allow_with_conditions",
            workflow_profile="software_change_workflow",
            route="software_engineering",
            outcome_ref=experience_id,
            outcome_status="completed",
            experience_id=experience_id,
            workflow_policy_ref=f"workflow-policy://postgres/{suffix}",
            workflow_policy_version="1.0.0",
            workflow_policy_source_registry_ref="registry://domains/v1",
            workflow_policy_source_registry_fingerprint="sha256:registry-v1",
            workflow_policy_application_status="applied",
            workflow_policy_effects=["bounded_patch"],
            evidence_refs=[f"trace://postgres/{suffix}"],
        )
    )

    service = MemoryService(database_url=database_url)
    assert (
        service.claim_runtime_request(
            request_id=request_id,
            session_id=str(record.session_id),
            claimed_at=record.observed_at,
        )
        is True
    )
    service.record_experience(
        experience=ExperienceRecordContract(
            experience_id=experience_id,
            mission_id=MissionId(mission_id),
            workflow_profile=str(record.workflow_profile),
            outcome_status=str(record.outcome_status),
            timestamp=record.observed_at,
            route=record.route,
            evidence_refs=[f"experience-evidence://postgres/{suffix}"],
        )
    )
    assert service.record_decision_outcome_attribution(record) == record
    assert service.record_decision_outcome_attribution(record) == record

    reloaded = MemoryService(database_url=database_url)
    assert reloaded.get_decision_outcome_attribution(request_id=str(record.request_id)) == record
    assert reloaded.list_decision_outcome_attributions(
        mission_id=str(record.mission_id),
        workflow_profile=record.workflow_profile,
        limit=1,
    ) == [record]

    with pytest.raises(ValueError, match="identity is immutable"):
        reloaded.record_decision_outcome_attribution(
            DecisionOutcomeAttributionRecordContract(
                **{
                    **record.__dict__,
                    "outcome_status": "failed",
                }
            )
        )

    repository = reloaded.repository
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        with repository._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM decision_outcome_attributions
                WHERE attribution_record_id = %s
                """,
                (record.attribution_record_id,),
            )


def test_workflow_lifecycle_is_cas_safe_and_append_only_in_postgres() -> None:
    import psycopg

    database_url = postgres_url()
    suffix = uuid4().hex[:10]
    service = MemoryService(
        database_url=database_url,
        workflow_lifecycle_transition_verifier=lambda _transition: True,
    )
    seed = _activation()
    current = service.get_active_workflow_lifecycle(
        workflow_profile=seed.workflow_profile,
        route=seed.route,
    )
    transition_time = datetime.now(UTC)
    if current is not None:
        current_time = datetime.fromisoformat(current.timestamp.replace("Z", "+00:00"))
        transition_time = max(transition_time, current_time + timedelta(microseconds=1))
    transition_at = transition_time.isoformat().replace("+00:00", "Z")
    if current is None:
        transition = replace(
            seed,
            transition_id=f"workflow-lifecycle-transition://postgres/{suffix}/1",
            human_authorization_ref=f"human-authorization://postgres/{suffix}/1",
            operator_ref=f"operator://postgres/{suffix}",
            timestamp=transition_at,
        )
    elif current.transition_status == "active_promoted":
        transition = replace(
            _rollback(current),
            transition_id=(f"workflow-lifecycle-transition://postgres/{suffix}/rollback"),
            revision=current.revision + 1,
            previous_transition_id=current.transition_id,
            previous_transition_fingerprint=(workflow_lifecycle_transition_fingerprint(current)),
            human_authorization_ref=(f"human-authorization://postgres/{suffix}/rollback"),
            operator_ref=f"operator://postgres/{suffix}",
            timestamp=transition_at,
        )
    else:
        transition = replace(
            seed,
            transition_id=(f"workflow-lifecycle-transition://postgres/{suffix}/activate"),
            revision=current.revision + 1,
            previous_transition_id=current.transition_id,
            previous_transition_fingerprint=(workflow_lifecycle_transition_fingerprint(current)),
            human_authorization_ref=(f"human-authorization://postgres/{suffix}/activate"),
            operator_ref=f"operator://postgres/{suffix}",
            timestamp=transition_at,
        )
    assessment = GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        current_transition=current,
        release_bundle_verifier=lambda candidate: candidate == transition,
        assessed_at=transition_at,
    )
    assert (
        service.record_workflow_lifecycle_transition(
            transition,
            assessment,
        )
        == transition
    )
    reloaded = MemoryService(database_url=database_url)
    assert (
        reloaded.get_active_workflow_lifecycle(
            workflow_profile=transition.workflow_profile,
            route=transition.route,
        )
        == transition
    )

    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        with reloaded.repository._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM workflow_lifecycle_transitions
                WHERE transition_id = %s
                """,
                (transition.transition_id,),
            )


def test_memory_benchmark_track_adopts_postgres_when_environment_is_ready() -> None:
    harness = BenchmarkHarness(
        output_dir=str(runtime_dir("memory-benchmark") / "benchmarks"),
        postgres_url=postgres_url(),
    )

    report = harness.run_memory_track()

    assert report.decision == ADOPT_IN_V1
    candidate = report.metrics["candidate"]
    assert candidate["backend"] == "postgresql"
    assert candidate["executed"] is True
    assert candidate["functional_parity"] is True
    assert candidate["persistence_across_instances"] is True
    assert candidate["mission_state_persisted"] is True
    assert candidate["failure_rate"] == 0.0


def test_artifact_physical_saga_schema_is_complete_in_postgres() -> None:
    service = MemoryService(database_url=postgres_url())
    expected_tables = {
        "artifact_physical_saga_plans",
        "artifact_physical_saga_events",
        "artifact_physical_attestations",
        "physical_artifact_versions",
        "artifact_physical_version_statuses",
        "artifact_physical_lineages",
        "artifact_physical_outbox",
        "artifact_physical_canonical_commits",
        "artifact_physical_outbox_deliveries",
    }
    with service.repository._connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            """,
            (sorted(expected_tables),),
        )
        observed = {str(row["table_name"]) for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'artifact_physical_saga_plans'
            """
        )
        plan_columns = {str(row["column_name"]) for row in cursor.fetchall()}
    assert observed == expected_tables
    assert {"resource_ref", "plan_fingerprint", "plan_payload_json"} <= plan_columns


def test_artifact_physical_apply_round_trips_and_commits_outbox_in_postgres() -> None:
    suffix = uuid4().hex[:12]
    database_url = postgres_url()
    now = datetime.now(UTC).isoformat()
    mission_id = MissionId(f"mission:pg-physical:{suffix}")
    work_item_ref = f"work-item:pg-physical:{suffix}"
    service = MemoryService(
        database_url=database_url,
        artifact_physical_mutation_verifier=lambda _receipt, _attestation: True,
        artifact_physical_rollback_verifier=lambda _receipt, _attestation: True,
    )
    service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=mission_id,
            mission_goal="validate PostgreSQL physical saga parity",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at=now,
            objective_ref=f"objective:pg-physical:{suffix}",
            work_item_refs=[work_item_ref],
            work_items=[
                WorkItemStateContract(
                    work_item_ref=work_item_ref,
                    work_item_status="active",
                    mission_id=mission_id,
                    blocking_state="ready",
                )
            ],
        )
    )
    desired_sha256 = sha256(f"postgres-{suffix}\n".encode()).hexdigest()
    plan = seal_artifact_physical_apply_plan(
        ArtifactPhysicalApplyPlanContract(
            saga_id=f"saga:pg-physical:{suffix}",
            mission_id=mission_id,
            artifact_ref=f"artifact:pg-physical:{suffix}",
            artifact_version=1,
            owner_mission_id=mission_id,
            objective_ref=f"objective:pg-physical:{suffix}",
            work_item_ref=work_item_ref,
            lineage_root_ref=f"artifact:pg-physical:{suffix}",
            supersedes_artifact_ref=None,
            transition="register",
            physical_operation_id=f"operation:pg-physical:{suffix}",
            resource_ref=f"text:workspace/docs/pg-{suffix}.md",
            root_alias="workspace",
            preflight_fingerprint=sha256(f"preflight-{suffix}".encode()).hexdigest(),
            root_config_fingerprint=sha256(b"pg-root").hexdigest(),
            preflight_policy_version="1.0.0",
            transaction_policy_version="1.0.0",
            transaction_backend_version="posix-openat-v1",
            adapter_backend_version="local-text-v1",
            before_content_sha256=sha256(b"").hexdigest(),
            desired_content_sha256=desired_sha256,
            rollback_plan_ref=sha256(f"rollback-{suffix}".encode()).hexdigest(),
            expected_lineage_revision=0,
            created_at=now,
            plan_fingerprint="",
        )
    )
    receipt = LocalTextMutationReceipt(
        operation_id=plan.physical_operation_id,
        execution_grant_id=f"grant:pg-physical:{suffix}",
        execution_claim_id=f"claim:pg-physical:{suffix}",
        operation="create_text",
        resource_ref=plan.resource_ref,
        subject_ref=f"subject:pg-physical:{suffix}",
        preflight_fingerprint=plan.preflight_fingerprint,
        before_content_sha256=plan.before_content_sha256,
        desired_content_sha256=plan.desired_content_sha256,
        root_config_fingerprint=plan.root_config_fingerprint,
        applied_event_fingerprint=sha256(f"applied-{suffix}".encode()).hexdigest(),
        committed_at=now,
        mutation_status="applied",
        receipt_fingerprint="",
    )
    receipt = replace(
        receipt,
        receipt_fingerprint=build_mutation_receipt_fingerprint(receipt),
    )
    attestation = seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id=f"attestation:pg-physical:{suffix}",
            purpose="mutation_current",
            receipt_fingerprint=receipt.receipt_fingerprint,
            mutation_operation_id=receipt.operation_id,
            rollback_operation_id=None,
            resource_ref=plan.resource_ref,
            root_alias=plan.root_alias,
            root_config_fingerprint=plan.root_config_fingerprint,
            physical_state="applied",
            observed_content_sha256=plan.desired_content_sha256,
            observed_identity_fingerprint=sha256(f"identity-{suffix}".encode()).hexdigest(),
            journal_event_fingerprint=receipt.applied_event_fingerprint,
            transaction_policy_version=plan.transaction_policy_version,
            transaction_backend_version=plan.transaction_backend_version,
            verified_at=now,
            attestation_fingerprint="",
        )
    )

    service.reserve_artifact_physical_apply(plan)
    service.advance_artifact_physical_apply(
        plan.saga_id,
        phase="effect_dispatched",
        occurred_at=now,
    )
    commit = service.commit_artifact_physical_apply(
        plan.saga_id,
        receipt=receipt,
        attestation=attestation,
    )

    reloaded = MemoryService(database_url=database_url)
    assert reloaded.get_artifact_physical_apply_plan(plan.saga_id) == plan
    assert reloaded.get_artifact_physical_canonical_commit_receipt(plan.saga_id) == commit
    outbox = reloaded.get_artifact_physical_outbox_for_saga(plan.saga_id)
    assert outbox is not None
    assert outbox.event_name == "artifact_lifecycle_state_changed"
    service.mark_artifact_physical_outbox_published(
        outbox.outbox_id,
        publisher_ref=f"publisher:pg-physical:{suffix}",
        published_at=now,
    )

    replacement = seal_artifact_physical_apply_plan(
        replace(
            plan,
            saga_id=f"saga:pg-physical:{suffix}:replacement",
            artifact_ref=f"artifact:pg-physical:{suffix}:replacement",
            artifact_version=2,
            supersedes_artifact_ref=plan.artifact_ref,
            transition="replace",
            physical_operation_id=f"operation:pg-physical:{suffix}:replacement",
            preflight_fingerprint=sha256(f"preflight-{suffix}-replacement".encode()).hexdigest(),
            before_content_sha256=plan.desired_content_sha256,
            desired_content_sha256=sha256(f"postgres-{suffix}-replacement\n".encode()).hexdigest(),
            rollback_plan_ref=sha256(f"rollback-{suffix}-replacement".encode()).hexdigest(),
            expected_lineage_revision=1,
            plan_fingerprint="",
        )
    )
    replacement_receipt = LocalTextMutationReceipt(
        operation_id=replacement.physical_operation_id,
        execution_grant_id=f"grant:pg-physical:{suffix}:replacement",
        execution_claim_id=f"claim:pg-physical:{suffix}:replacement",
        operation="replace_text",
        resource_ref=replacement.resource_ref,
        subject_ref=f"subject:pg-physical:{suffix}",
        preflight_fingerprint=replacement.preflight_fingerprint,
        before_content_sha256=replacement.before_content_sha256,
        desired_content_sha256=replacement.desired_content_sha256,
        root_config_fingerprint=replacement.root_config_fingerprint,
        applied_event_fingerprint=sha256(f"applied-{suffix}-replacement".encode()).hexdigest(),
        committed_at=now,
        mutation_status="applied",
        receipt_fingerprint="",
    )
    replacement_receipt = replace(
        replacement_receipt,
        receipt_fingerprint=build_mutation_receipt_fingerprint(replacement_receipt),
    )
    service.reserve_artifact_physical_apply(replacement)
    service.advance_artifact_physical_apply(
        replacement.saga_id,
        phase="effect_dispatched",
        occurred_at=now,
    )
    rollback = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id=f"saga:pg-physical:{suffix}:compensation",
            mission_id=mission_id,
            active_artifact_ref=replacement.artifact_ref,
            active_artifact_version=replacement.artifact_version,
            restored_artifact_ref=plan.artifact_ref,
            restored_artifact_version=plan.artifact_version,
            owner_mission_id=mission_id,
            objective_ref=plan.objective_ref,
            work_item_ref=work_item_ref,
            lineage_root_ref=plan.lineage_root_ref,
            physical_operation_id=f"operation:pg-physical:{suffix}:compensation",
            mutation_operation_id=replacement.physical_operation_id,
            source_apply_saga_id=replacement.saga_id,
            rollback_mode="precanonical_compensation",
            canonical_effect_expected=False,
            mutation_receipt_fingerprint=replacement_receipt.receipt_fingerprint,
            resource_ref=plan.resource_ref,
            root_alias=plan.root_alias,
            expected_current_sha256=replacement.desired_content_sha256,
            restored_content_sha256=plan.desired_content_sha256,
            expected_lineage_revision=1,
            created_at=now,
            plan_fingerprint="",
        )
    )
    service.reserve_artifact_physical_rollback(rollback)
    service.advance_artifact_physical_rollback(
        rollback.saga_id,
        phase="rollback_effect_dispatched",
        occurred_at=now,
    )
    rollback_receipt = LocalTextRollbackReceipt(
        operation_id=rollback.physical_operation_id,
        mutation_operation_id=rollback.mutation_operation_id,
        rollback_grant_id=f"grant:pg-physical:{suffix}:compensation",
        rollback_claim_id=f"claim:pg-physical:{suffix}:compensation",
        mutation_receipt_fingerprint=rollback.mutation_receipt_fingerprint,
        resource_ref=rollback.resource_ref,
        restored_content_sha256=rollback.restored_content_sha256,
        rolled_back_at=now,
        rolled_back_event_fingerprint=sha256(
            f"rolled-back-{suffix}-compensation".encode()
        ).hexdigest(),
        rollback_receipt_fingerprint="",
    )
    rollback_receipt = replace(
        rollback_receipt,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(rollback_receipt),
    )
    rollback_attestation = seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id=f"attestation:pg-physical:{suffix}:compensation",
            purpose="rollback_current",
            receipt_fingerprint=rollback_receipt.rollback_receipt_fingerprint,
            mutation_operation_id=rollback.mutation_operation_id,
            rollback_operation_id=rollback.physical_operation_id,
            resource_ref=rollback.resource_ref,
            root_alias=rollback.root_alias,
            root_config_fingerprint=replacement.root_config_fingerprint,
            physical_state="restored",
            observed_content_sha256=rollback.restored_content_sha256,
            observed_identity_fingerprint=sha256(
                f"identity-{suffix}-restored".encode()
            ).hexdigest(),
            journal_event_fingerprint=rollback_receipt.rolled_back_event_fingerprint,
            transaction_policy_version=replacement.transaction_policy_version,
            transaction_backend_version=replacement.transaction_backend_version,
            verified_at=now,
            attestation_fingerprint="",
        )
    )
    rollback_commit = service.commit_artifact_physical_rollback(
        rollback.saga_id,
        receipt=rollback_receipt,
        attestation=rollback_attestation,
    )

    reloaded_after_rollback = MemoryService(database_url=database_url)
    assert reloaded_after_rollback.get_artifact_physical_rollback_plan(rollback.saga_id) == rollback
    assert (
        reloaded_after_rollback.get_artifact_physical_canonical_commit_receipt(rollback.saga_id)
        == rollback_commit
    )
    assert reloaded_after_rollback.get_artifact_physical_saga(replacement.saga_id).phase == (
        "compensated"
    )
    rollback_outbox = reloaded_after_rollback.get_artifact_physical_outbox_for_saga(
        rollback.saga_id
    )
    assert rollback_outbox is not None
    assert rollback_outbox.event_name == "artifact_physical_apply_compensated"
    reloaded_after_rollback.mark_artifact_physical_outbox_published(
        rollback_outbox.outbox_id,
        publisher_ref=f"publisher:pg-physical:{suffix}:compensation",
        published_at=now,
    )
    lineage = reloaded_after_rollback.get_artifact_physical_lineage(
        str(mission_id), plan.lineage_root_ref
    )
    assert lineage is not None
    assert lineage.revision == 1
    assert lineage.active_artifact_ref == plan.artifact_ref
    canonical_replacement = seal_artifact_physical_apply_plan(
        replace(
            replacement,
            saga_id=f"saga:pg-physical:{suffix}:canonical-replacement",
            artifact_ref=f"artifact:pg-physical:{suffix}:canonical-replacement",
            physical_operation_id=(f"operation:pg-physical:{suffix}:canonical-replacement"),
            preflight_fingerprint=sha256(
                f"preflight-{suffix}-canonical-replacement".encode()
            ).hexdigest(),
            rollback_plan_ref=sha256(
                f"rollback-{suffix}-canonical-replacement".encode()
            ).hexdigest(),
            plan_fingerprint="",
        )
    )
    canonical_mutation = replace(
        replacement_receipt,
        operation_id=canonical_replacement.physical_operation_id,
        execution_grant_id=f"grant:pg-physical:{suffix}:canonical-replacement",
        execution_claim_id=f"claim:pg-physical:{suffix}:canonical-replacement",
        preflight_fingerprint=canonical_replacement.preflight_fingerprint,
        applied_event_fingerprint=sha256(
            f"applied-{suffix}-canonical-replacement".encode()
        ).hexdigest(),
        receipt_fingerprint="",
    )
    canonical_mutation = replace(
        canonical_mutation,
        receipt_fingerprint=build_mutation_receipt_fingerprint(canonical_mutation),
    )
    canonical_attestation = seal_local_text_physical_state_attestation(
        replace(
            attestation,
            attestation_id=f"attestation:pg-physical:{suffix}:canonical-replacement",
            receipt_fingerprint=canonical_mutation.receipt_fingerprint,
            mutation_operation_id=canonical_mutation.operation_id,
            observed_content_sha256=canonical_replacement.desired_content_sha256,
            observed_identity_fingerprint=sha256(
                f"identity-{suffix}-canonical-replacement".encode()
            ).hexdigest(),
            journal_event_fingerprint=canonical_mutation.applied_event_fingerprint,
            attestation_fingerprint="",
        )
    )
    service.reserve_artifact_physical_apply(canonical_replacement)
    service.advance_artifact_physical_apply(
        canonical_replacement.saga_id,
        phase="effect_dispatched",
        occurred_at=now,
    )
    service.commit_artifact_physical_apply(
        canonical_replacement.saga_id,
        receipt=canonical_mutation,
        attestation=canonical_attestation,
    )
    canonical_apply_outbox = service.get_artifact_physical_outbox_for_saga(
        canonical_replacement.saga_id
    )
    assert canonical_apply_outbox is not None
    service.mark_artifact_physical_outbox_published(
        canonical_apply_outbox.outbox_id,
        publisher_ref=f"publisher:pg-physical:{suffix}:canonical-replacement",
        published_at=now,
    )
    canonical_rollback = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id=f"saga:pg-physical:{suffix}:canonical-rollback",
            mission_id=mission_id,
            active_artifact_ref=canonical_replacement.artifact_ref,
            active_artifact_version=canonical_replacement.artifact_version,
            restored_artifact_ref=plan.artifact_ref,
            restored_artifact_version=plan.artifact_version,
            owner_mission_id=mission_id,
            objective_ref=plan.objective_ref,
            work_item_ref=work_item_ref,
            lineage_root_ref=plan.lineage_root_ref,
            physical_operation_id=f"operation:pg-physical:{suffix}:canonical-rollback",
            mutation_operation_id=canonical_replacement.physical_operation_id,
            source_apply_saga_id=canonical_replacement.saga_id,
            rollback_mode="canonical_rollback",
            canonical_effect_expected=True,
            mutation_receipt_fingerprint=canonical_mutation.receipt_fingerprint,
            resource_ref=plan.resource_ref,
            root_alias=plan.root_alias,
            expected_current_sha256=canonical_replacement.desired_content_sha256,
            restored_content_sha256=plan.desired_content_sha256,
            expected_lineage_revision=2,
            created_at=now,
            plan_fingerprint="",
        )
    )
    service.reserve_artifact_physical_rollback(canonical_rollback)
    service.advance_artifact_physical_rollback(
        canonical_rollback.saga_id,
        phase="rollback_effect_dispatched",
        occurred_at=now,
    )
    canonical_rollback_receipt = LocalTextRollbackReceipt(
        operation_id=canonical_rollback.physical_operation_id,
        mutation_operation_id=canonical_rollback.mutation_operation_id,
        rollback_grant_id=f"grant:pg-physical:{suffix}:canonical-rollback",
        rollback_claim_id=f"claim:pg-physical:{suffix}:canonical-rollback",
        mutation_receipt_fingerprint=canonical_mutation.receipt_fingerprint,
        resource_ref=canonical_rollback.resource_ref,
        restored_content_sha256=canonical_rollback.restored_content_sha256,
        rolled_back_at=now,
        rolled_back_event_fingerprint=sha256(
            f"rolled-back-{suffix}-canonical".encode()
        ).hexdigest(),
        rollback_receipt_fingerprint="",
    )
    canonical_rollback_receipt = replace(
        canonical_rollback_receipt,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(canonical_rollback_receipt),
    )
    canonical_rollback_attestation = seal_local_text_physical_state_attestation(
        replace(
            rollback_attestation,
            attestation_id=f"attestation:pg-physical:{suffix}:canonical-rollback",
            receipt_fingerprint=canonical_rollback_receipt.rollback_receipt_fingerprint,
            mutation_operation_id=canonical_rollback.mutation_operation_id,
            rollback_operation_id=canonical_rollback.physical_operation_id,
            observed_content_sha256=canonical_rollback.restored_content_sha256,
            observed_identity_fingerprint=sha256(
                f"identity-{suffix}-canonical-restored".encode()
            ).hexdigest(),
            journal_event_fingerprint=(canonical_rollback_receipt.rolled_back_event_fingerprint),
            attestation_fingerprint="",
        )
    )
    canonical_rollback_commit = service.commit_artifact_physical_rollback(
        canonical_rollback.saga_id,
        receipt=canonical_rollback_receipt,
        attestation=canonical_rollback_attestation,
    )
    final_reloaded = MemoryService(database_url=database_url)
    assert (
        final_reloaded.get_artifact_physical_canonical_commit_receipt(canonical_rollback.saga_id)
        == canonical_rollback_commit
    )
    final_lineage = final_reloaded.get_artifact_physical_lineage(
        str(mission_id), plan.lineage_root_ref
    )
    assert final_lineage is not None
    assert final_lineage.revision == 3
    assert final_lineage.active_artifact_ref == plan.artifact_ref
    canonical_rollback_outbox = final_reloaded.get_artifact_physical_outbox_for_saga(
        canonical_rollback.saga_id
    )
    assert canonical_rollback_outbox is not None
    final_reloaded.mark_artifact_physical_outbox_published(
        canonical_rollback_outbox.outbox_id,
        publisher_ref=f"publisher:pg-physical:{suffix}:canonical-rollback",
        published_at=now,
    )
    stale = seal_artifact_physical_apply_plan(
        replace(
            canonical_replacement,
            saga_id=f"saga:pg-physical:{suffix}:stale",
            artifact_ref=f"artifact:pg-physical:{suffix}:stale",
            artifact_version=3,
            supersedes_artifact_ref=plan.artifact_ref,
            physical_operation_id=f"operation:pg-physical:{suffix}:stale",
            expected_lineage_revision=99,
            plan_fingerprint="",
        )
    )
    with pytest.raises(ValueError, match="replace_requires_normalized_head"):
        reloaded_after_rollback.reserve_artifact_physical_apply(stale)

    import psycopg

    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        with reloaded_after_rollback.repository._connect() as connection:
            connection.execute(
                "UPDATE artifact_physical_saga_events SET phase = %s WHERE saga_id = %s",
                ("failed", rollback.saga_id),
            )
