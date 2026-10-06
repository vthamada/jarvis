from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)
from operational_service.adapters.local_text_governance import (
    LocalTextGovernanceAuthorityAdapter,
)
from operational_service.adapters.local_text_transaction import (
    LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
    LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
    LocalTextExecutionGrantBinding,
    LocalTextMutationRequest,
    LocalTextRollbackRequest,
)
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.adapter_execution_permissions import SEEDED_ADAPTER_EXECUTION_REGISTRY
from shared.adapter_permissions import SEEDED_ADAPTER_REGISTRY
from shared.artifact_physical_attestation_authority import (
    ArtifactPhysicalAttestationLeaseAuthority,
)
from shared.artifact_physical_saga import (
    seal_artifact_physical_apply_plan,
    seal_artifact_physical_rollback_plan,
)
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import (
    AdapterActionRequestContract,
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalRollbackPlanContract,
    AutonomyActionPolicyDecisionContract,
    LocalTextFilePreflightRequestContract,
    MissionStateContract,
    WorkItemStateContract,
)
from shared.local_text_rollback_permissions import (
    LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR,
    SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY,
)
from shared.types import MissionId, MissionStatus, RiskLevel

MISSION_ID = MissionId("mission://mb217/e2e")
OBJECTIVE_REF = "objective://mb217/e2e"
WORK_ITEM_REF = "work-item://mb217/e2e"
RESOURCE_REF = "text:notes/note.txt"
ROOT_ALIAS = "notes"


@dataclass
class _StepClock:
    current: datetime
    step: timedelta = timedelta(seconds=1)

    def _take(self) -> datetime:
        observed = self.current
        self.current += self.step
        return observed

    def governance_now(self) -> str:
        return self._take().isoformat()

    def transaction_now(self) -> datetime:
        return self._take()

    def peek(self) -> datetime:
        return self.current


def _z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _decision(*, confirmation_required: bool) -> AutonomyActionPolicyDecisionContract:
    policy = AUTONOMY_LEVEL_POLICIES["supervised_external_action"]
    return evaluate_autonomy_action(
        requested_autonomy_level="supervised_external_action",
        max_autonomy_level="supervised_external_action",
        effective_autonomy_level="supervised_external_action",
        autonomy_ladder_status="within_limit",
        action_kind=(
            "execute_external_action" if confirmation_required else "prepare_external_action"
        ),
        selected_capability_mode="core_with_supervised_external_operation",
        max_capability_mode="core_with_supervised_external_operation",
        allowed_runtime_actions=policy["allowed_runtime_actions"],
        blocked_runtime_actions=policy["blocked_runtime_actions"],
        human_confirmation_required=confirmation_required,
        human_confirmation_mode=(
            "explicit_confirmation_required" if confirmation_required else "not_required"
        ),
        confirmation_evidence_state="absent",
    )


def _intent(
    *,
    prefix: str,
    subject_ref: str,
    handler_id: str,
    handler_version: str,
    operation: str,
    content_digest: str,
    precondition_digest: str,
    issued_at: datetime,
    ttl: timedelta = timedelta(minutes=10),
):
    return build_action_intent(
        intent_id=f"intent://mb217/{prefix}",
        origin_request_id=f"request://mb217/{prefix}",
        session_id="session://mb217/e2e",
        mission_id=str(MISSION_ID),
        operator_identity_ref=subject_ref,
        handler_id=handler_id,
        handler_version=handler_version,
        operation=operation,
        target_ref=RESOURCE_REF,
        content_digest=content_digest,
        precondition_digest=precondition_digest,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce=f"mb217{prefix.title()}Nonce123456789",
        issued_at=_z(issued_at),
        expires_at=_z(issued_at + ttl),
        now=issued_at,
    )


def _confirm(governance: GovernanceService, intent, confirmed_at: datetime):
    challenge = governance.issue_action_confirmation_challenge(intent)
    return governance.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
        confirmed_at=_z(confirmed_at),
    )


def _compose(
    *,
    governance: GovernanceService,
    memory_path: Path,
    observability_path: Path,
    root: Path,
    transaction_root: Path,
    clock: _StepClock,
    failure_injector=None,
) -> tuple[OrchestratorService, MemoryService, OperationalService]:
    attestation_authority = ArtifactPhysicalAttestationLeaseAuthority()
    memory = MemoryService(
        f"sqlite:///{memory_path.as_posix()}",
        artifact_physical_mutation_verifier=(
            lambda receipt, attestation: (
                governance.verify_local_text_mutation_receipt_exact(receipt)
                and attestation_authority.verify_and_consume(receipt, attestation)
            )
        ),
        artifact_physical_rollback_verifier=(
            lambda receipt, attestation: (
                governance.verify_local_text_rollback_receipt_exact(receipt)
                and attestation_authority.verify_and_consume(receipt, attestation)
            )
        ),
    )
    authority = LocalTextGovernanceAuthorityAdapter(governance)
    operational = OperationalService(
        artifact_dir=str(root / ".artifacts"),
        adapter_preflight_verifier=governance.verify_adapter_grant_for_preflight_exact,
        local_text_file_roots={ROOT_ALIAS: root},
        local_text_file_preflight_attestor=governance.attest_local_text_file_preflight,
        local_text_file_transaction_roots={ROOT_ALIAS: transaction_root},
        local_text_file_staging_authorization_verifier=authority.verify_staging,
        local_text_file_effect_start_claim_verifier=authority.verify_effect_start,
        local_text_file_historical_claim_lookup=authority.lookup_historical,
        local_text_file_historical_claim_verifier=authority.verify_historical,
        local_text_file_authorization_lease_provider=authority.claim,
        local_text_file_trusted_transaction_clock=clock.transaction_now,
        local_text_file_mutation_receipt_recorder=authority.record_mutation_receipt,
        local_text_file_rollback_receipt_recorder=authority.record_rollback_receipt,
        local_text_file_mutation_receipt_verifier=(
            governance.verify_local_text_mutation_receipt_exact
        ),
        local_text_file_rollback_receipt_verifier=(
            governance.verify_local_text_rollback_receipt_exact
        ),
        local_text_file_canonical_physical_effect_authorizer=(
            memory.authorize_artifact_physical_effect
        ),
        local_text_file_canonical_physical_effect_scope_provider=(
            memory.artifact_physical_effect_scope
        ),
        local_text_file_resource_physical_binding_lookup=(
            memory.is_local_text_resource_physically_bound
        ),
        local_text_file_canonical_commit_receipt_verifier=(
            memory.verify_artifact_physical_canonical_commit_receipt
        ),
        local_text_file_physical_attestation_lease_provider=(attestation_authority.issue),
    )
    orchestrator = OrchestratorService(
        governance_service=governance,
        memory_service=memory,
        operational_service=operational,
        observability_service=ObservabilityService(str(observability_path)),
        artifact_physical_failure_injector=failure_injector,
        artifact_physical_clock=clock.governance_now,
        artifact_physical_attestation_authority=attestation_authority,
    )
    transaction_engine = operational._local_text_file_transaction_engine
    assert transaction_engine is not None
    lease_provider = transaction_engine._physical_attestation_lease_provider
    assert getattr(lease_provider, "__self__", None) is attestation_authority
    return orchestrator, memory, operational


def _prepare_mutation(
    *,
    governance: GovernanceService,
    operational: OperationalService,
    clock: _StepClock,
    prefix: str,
    operation_id: str,
    operation: str,
    desired: str,
    expected_current_sha256: str | None,
) -> LocalTextMutationRequest:
    action_request = AdapterActionRequestContract(
        adapter_id="local_text_file",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        operation=operation,
        resource_scope="configured_text_root",
        resource_ref=RESOURCE_REF,
    )
    root_fingerprint = operational.local_text_file_root_config_fingerprint()
    prepare_intent = _intent(
        prefix=f"{prefix}-prepare",
        subject_ref="operator://mb217/e2e",
        handler_id="adapter://local_text_file",
        handler_version="1.0.0",
        operation=operation,
        content_digest=sha256(desired.encode()).hexdigest(),
        precondition_digest=root_fingerprint,
        issued_at=clock.peek(),
    )
    registry, descriptor = governance.resolve_active_adapter_descriptor(action_request)
    grant = governance.issue_adapter_grant(
        prepare_intent,
        action_request,
        _decision(confirmation_required=False),
        expected_registry_fingerprint=registry.registry_fingerprint,
        expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        issued_at=_z(clock.peek()),
        expires_at=_z(clock.peek() + timedelta(minutes=10)),
    )
    prepared_at = clock.peek()
    preflight, _attestation, execution_request = operational.preflight_and_attest_local_text_file(
        LocalTextFilePreflightRequestContract(
            grant_id=grant.grant_id,
            grant_fingerprint=grant.grant_fingerprint,
            action_fingerprint=prepare_intent.action_fingerprint,
            intent_fingerprint=action_intent_fingerprint(prepare_intent),
            descriptor_fingerprint=grant.descriptor_fingerprint,
            registry_fingerprint=grant.registry_fingerprint,
            subject_ref=prepare_intent.operator_identity_ref,
            adapter_request=action_request,
            desired_text=desired,
            expected_root_config_fingerprint=root_fingerprint,
            preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
            diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
            diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
            prepared_at=_z(prepared_at),
            expires_at=_z(prepared_at + timedelta(minutes=5)),
            authorization_expires_at=grant.expires_at,
            expected_current_sha256=expected_current_sha256,
        ),
        now=prepared_at,
    )
    execution_intent = _intent(
        prefix=f"{prefix}-execute",
        subject_ref=execution_request.subject_ref,
        handler_id="adapter-executor://local_text_file",
        handler_version="2.0.0",
        operation=execution_request.operation,
        content_digest=execution_request.desired_content_sha256,
        precondition_digest=execution_request.execution_request_fingerprint,
        issued_at=clock.peek(),
        ttl=timedelta(seconds=90),
    )
    execution_registry, execution_descriptor = (
        governance.resolve_active_adapter_execution_descriptor(execution_request)
    )
    execution_grant = governance.issue_adapter_execution_grant(
        execution_intent,
        execution_request,
        _decision(confirmation_required=True),
        expected_registry_fingerprint=execution_registry.registry_fingerprint,
        expected_descriptor_fingerprint=execution_descriptor.descriptor_fingerprint,
    )
    confirmation = _confirm(governance, execution_intent, clock.peek())
    # Keep the trusted execution instant strictly after confirmation issuance.
    clock.current += timedelta(seconds=1)
    return LocalTextMutationRequest(
        operation_id=operation_id,
        preflight=preflight,
        desired_text=desired,
        execution_binding=LocalTextExecutionGrantBinding(
            execution_grant_id=execution_grant.grant_id,
            execution_grant_fingerprint=execution_grant.grant_fingerprint,
            action_fingerprint=execution_grant.action_fingerprint,
            execution_request_fingerprint=(execution_request.execution_request_fingerprint),
            intent_fingerprint=execution_grant.intent_fingerprint,
            confirmation_receipt_id=confirmation.receipt_id,
        ),
    )


def _apply_plan(
    *,
    saga_id: str,
    artifact_ref: str,
    version: int,
    supersedes: str | None,
    request: LocalTextMutationRequest,
    expected_revision: int,
    created_at: str,
) -> ArtifactPhysicalApplyPlanContract:
    preflight = request.preflight
    return seal_artifact_physical_apply_plan(
        ArtifactPhysicalApplyPlanContract(
            saga_id=saga_id,
            mission_id=MISSION_ID,
            artifact_ref=artifact_ref,
            artifact_version=version,
            owner_mission_id=MISSION_ID,
            objective_ref=OBJECTIVE_REF,
            work_item_ref=WORK_ITEM_REF,
            lineage_root_ref="artifact://mb217/e2e/v1",
            supersedes_artifact_ref=supersedes,
            transition="register" if supersedes is None else "replace",
            physical_operation_id=request.operation_id,
            resource_ref=preflight.resource_ref,
            root_alias=preflight.root_alias,
            preflight_fingerprint=preflight.preflight_fingerprint,
            root_config_fingerprint=preflight.root_config_fingerprint,
            preflight_policy_version=preflight.preflight_policy_version,
            transaction_policy_version=LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
            transaction_backend_version=LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
            adapter_backend_version=preflight.adapter_backend_version,
            before_content_sha256=preflight.before_content_sha256,
            desired_content_sha256=preflight.desired_content_sha256,
            rollback_plan_ref=preflight.rollback_plan.rollback_fingerprint,
            expected_lineage_revision=expected_revision,
            created_at=created_at,
            plan_fingerprint="0" * 64,
        )
    )


@pytest.mark.skipif(os.name != "posix", reason="physical backend is Linux-only")
def test_real_services_recover_apply_then_replace_and_canonical_rollback(
    tmp_path: Path,
) -> None:
    base = datetime(2026, 8, 30, 12, tzinfo=UTC)
    clock = _StepClock(base + timedelta(seconds=2))
    governance_path = tmp_path / "governance.sqlite3"
    memory_path = tmp_path / "memory.sqlite3"
    observability_path = tmp_path / "observability.sqlite3"
    root = tmp_path / "text-root"
    root.mkdir(mode=0o755)
    transaction_root = root / ".jarvis-transactions"
    transaction_root.mkdir(mode=0o700)
    target = root / "note.txt"
    desired_v1 = "conteúdo canônico MB-217 v1\n"
    desired_v2 = "conteúdo canônico MB-217 v2\n"

    governance = GovernanceService(
        governance_path,
        trusted_execution_clock=clock.governance_now,
    )
    governance.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=_z(base))
    governance.activate_adapter_execution_registry(
        SEEDED_ADAPTER_EXECUTION_REGISTRY,
        activated_at=_z(base),
    )
    governance.activate_local_text_file_rollback_registry(SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY)

    def fail_before_first_commit(boundary: str) -> None:
        if boundary == "before_apply_canonical_commit":
            raise RuntimeError("simulated crash before canonical commit")

    orchestrator, memory, operational = _compose(
        governance=governance,
        memory_path=memory_path,
        observability_path=observability_path,
        root=root,
        transaction_root=transaction_root,
        clock=clock,
        failure_injector=fail_before_first_commit,
    )
    memory.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MISSION_ID,
            mission_goal="Validate physical/canonical artifact consistency",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at=_z(base),
            objective_ref=OBJECTIVE_REF,
            objective_status="active",
            active_work_items=[WORK_ITEM_REF],
            work_item_refs=[WORK_ITEM_REF],
            work_items=[
                WorkItemStateContract(
                    work_item_ref=WORK_ITEM_REF,
                    work_item_status="active",
                    mission_id=MISSION_ID,
                    priority_level="p0",
                    blocking_state="ready",
                )
            ],
        )
    )
    request_v1 = _prepare_mutation(
        governance=governance,
        operational=operational,
        clock=clock,
        prefix="v1",
        operation_id="operation://mb217/e2e/apply-v1",
        operation="create_text",
        desired=desired_v1,
        expected_current_sha256=None,
    )
    binding_v1 = request_v1.execution_binding
    assert governance.verify_adapter_execution_grant_for_staging_exact(
        binding_v1.execution_grant_id,
        subject_ref=request_v1.preflight.subject_ref,
        expected_grant_fingerprint=binding_v1.execution_grant_fingerprint,
        expected_action_fingerprint=binding_v1.action_fingerprint,
        expected_execution_request_fingerprint=(binding_v1.execution_request_fingerprint),
        intent_fingerprint=binding_v1.intent_fingerprint,
        confirmation_receipt_id=binding_v1.confirmation_receipt_id,
    )
    plan_v1 = _apply_plan(
        saga_id="saga://mb217/e2e/apply-v1",
        artifact_ref="artifact://mb217/e2e/v1",
        version=1,
        supersedes=None,
        request=request_v1,
        expected_revision=0,
        created_at=clock.peek().isoformat(),
    )
    with pytest.raises(RuntimeError, match="crash before canonical commit"):
        orchestrator.execute_artifact_physical_apply(plan_v1, request_v1)
    assert target.read_bytes() == desired_v1.encode()
    assert memory.get_artifact_physical_saga(plan_v1.saga_id).phase == "effect_dispatched"
    assert memory.get_artifact_physical_version(plan_v1.artifact_ref) is None

    # New service instances prove recovery from durable Governance, Memory and
    # transaction journals rather than from in-process objects or a stale lease.
    governance = GovernanceService(
        governance_path,
        trusted_execution_clock=clock.governance_now,
    )
    orchestrator, memory, operational = _compose(
        governance=governance,
        memory_path=memory_path,
        observability_path=observability_path,
        root=root,
        transaction_root=transaction_root,
        clock=clock,
    )
    recovered_v1 = orchestrator.recover_artifact_physical_apply(plan_v1.saga_id)
    assert recovered_v1.state.phase == "completed"
    assert memory.get_artifact_physical_version(plan_v1.artifact_ref) is not None

    request_v2 = _prepare_mutation(
        governance=governance,
        operational=operational,
        clock=clock,
        prefix="v2",
        operation_id="operation://mb217/e2e/apply-v2",
        operation="replace_text",
        desired=desired_v2,
        expected_current_sha256=sha256(desired_v1.encode()).hexdigest(),
    )
    plan_v2 = _apply_plan(
        saga_id="saga://mb217/e2e/apply-v2",
        artifact_ref="artifact://mb217/e2e/v2",
        version=2,
        supersedes=plan_v1.artifact_ref,
        request=request_v2,
        expected_revision=1,
        created_at=clock.peek().isoformat(),
    )
    applied_v2 = orchestrator.execute_artifact_physical_apply(plan_v2, request_v2)
    assert applied_v2.state.phase == "completed"
    assert target.read_bytes() == desired_v2.encode()

    version_v2 = memory.get_artifact_physical_version(plan_v2.artifact_ref)
    assert version_v2 is not None
    mutation_receipt = governance.load_local_text_mutation_receipt_exact(
        plan_v2.physical_operation_id,
        expected_receipt_fingerprint=version_v2.mutation_receipt_fingerprint,
    )
    rollback_operation_id = "operation://mb217/e2e/rollback-v2"
    rollback_request = governance.prepare_local_text_file_rollback(
        mutation_receipt,
        rollback_operation_id=rollback_operation_id,
    )
    rollback_intent = _intent(
        prefix="v2-rollback",
        subject_ref=rollback_request.subject_ref,
        handler_id=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.executor_ref,
        handler_version=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.adapter_version,
        operation=rollback_request.operation,
        content_digest=rollback_request.restored_content_sha256,
        precondition_digest=rollback_request.rollback_request_fingerprint,
        issued_at=clock.peek(),
        ttl=timedelta(seconds=90),
    )
    rollback_registry, rollback_descriptor = (
        governance.resolve_active_local_text_file_rollback_descriptor(rollback_request)
    )
    rollback_grant = governance.issue_local_text_file_rollback_grant(
        rollback_intent,
        rollback_request,
        _decision(confirmation_required=True),
        expected_registry_fingerprint=rollback_registry.registry_fingerprint,
        expected_descriptor_fingerprint=rollback_descriptor.descriptor_fingerprint,
    )
    rollback_confirmation = _confirm(governance, rollback_intent, clock.peek())
    physical_rollback_request = LocalTextRollbackRequest(
        rollback_operation_id=rollback_operation_id,
        receipt=mutation_receipt,
        execution_binding=LocalTextExecutionGrantBinding(
            execution_grant_id=rollback_grant.grant_id,
            execution_grant_fingerprint=rollback_grant.grant_fingerprint,
            action_fingerprint=rollback_grant.action_fingerprint,
            execution_request_fingerprint=rollback_request.rollback_request_fingerprint,
            intent_fingerprint=rollback_grant.intent_fingerprint,
            confirmation_receipt_id=rollback_confirmation.receipt_id,
        ),
    )
    rollback_plan = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id="saga://mb217/e2e/rollback-v2",
            mission_id=MISSION_ID,
            active_artifact_ref=plan_v2.artifact_ref,
            active_artifact_version=2,
            restored_artifact_ref=plan_v1.artifact_ref,
            restored_artifact_version=1,
            owner_mission_id=MISSION_ID,
            objective_ref=OBJECTIVE_REF,
            work_item_ref=WORK_ITEM_REF,
            lineage_root_ref=plan_v1.lineage_root_ref,
            physical_operation_id=rollback_operation_id,
            mutation_operation_id=plan_v2.physical_operation_id,
            source_apply_saga_id=plan_v2.saga_id,
            rollback_mode="canonical_rollback",
            canonical_effect_expected=True,
            mutation_receipt_fingerprint=mutation_receipt.receipt_fingerprint,
            resource_ref=RESOURCE_REF,
            root_alias=ROOT_ALIAS,
            expected_current_sha256=sha256(desired_v2.encode()).hexdigest(),
            restored_content_sha256=sha256(desired_v1.encode()).hexdigest(),
            expected_lineage_revision=2,
            created_at=clock.peek().isoformat(),
            plan_fingerprint="0" * 64,
        )
    )
    rolled_back = orchestrator.execute_artifact_physical_rollback(
        rollback_plan,
        physical_rollback_request,
    )
    assert rolled_back.state.phase == "completed"
    assert target.read_bytes() == desired_v1.encode()
    lineage = memory.get_artifact_physical_lineage(
        str(MISSION_ID),
        plan_v1.lineage_root_ref,
    )
    assert lineage is not None
    assert lineage.revision == 3
    assert lineage.active_artifact_ref == plan_v1.artifact_ref
    mission = memory.get_mission_state(str(MISSION_ID))
    assert mission is not None
    statuses = {item.artifact_ref: item.artifact_status for item in mission.artifact_states}
    assert statuses[plan_v1.artifact_ref] == "active"
    assert statuses[plan_v2.artifact_ref] == "rolled_back"
    events = orchestrator.observability_service.list_recent_events(
        ObservabilityQuery(
            event_names=["artifact_lifecycle_state_changed"],
            mission_id=str(MISSION_ID),
            limit=10,
        )
    )
    assert len(events) == 3
    assert all(str(root) not in str(event.payload) for event in events)
