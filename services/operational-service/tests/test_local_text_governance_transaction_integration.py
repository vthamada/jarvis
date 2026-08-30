from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest
from governance_service.service import GovernanceService
from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)
from operational_service.adapters.local_text_governance import (
    LocalTextGovernanceAuthorityAdapter,
)
from operational_service.adapters.local_text_transaction import (
    LocalTextExecutionGrantBinding,
    LocalTextMutationRequest,
    LocalTextRollbackRequest,
)
from operational_service.service import OperationalService

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.adapter_execution_permissions import SEEDED_ADAPTER_EXECUTION_REGISTRY
from shared.adapter_permissions import SEEDED_ADAPTER_REGISTRY
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import (
    AdapterActionRequestContract,
    AutonomyActionPolicyDecisionContract,
    LocalTextFilePreflightRequestContract,
)
from shared.local_text_rollback_permissions import (
    LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR,
    SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY,
)
from shared.types import RiskLevel


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
    resource_ref: str,
    content_digest: str,
    precondition_digest: str,
    issued_at: datetime,
    ttl: timedelta = timedelta(minutes=10),
):
    expires_at = issued_at + ttl
    return build_action_intent(
        intent_id=f"intent://mb216/{prefix}",
        origin_request_id=f"request://mb216/{prefix}",
        session_id="session://mb216/e2e",
        mission_id="mission://mb216/e2e",
        operator_identity_ref=subject_ref,
        handler_id=handler_id,
        handler_version=handler_version,
        operation=operation,
        target_ref=resource_ref,
        content_digest=content_digest,
        precondition_digest=precondition_digest,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce=f"mb216{prefix.title()}Nonce123456789",
        issued_at=_z(issued_at),
        expires_at=_z(expires_at),
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


@pytest.mark.skipif(os.name != "posix", reason="physical backend is Linux-only")
def test_real_governance_bridge_applies_and_rolls_back_exact_bytes(
    tmp_path: Path,
) -> None:
    base = datetime(2026, 8, 30, 12, tzinfo=UTC)
    clock = _StepClock(base + timedelta(seconds=2))
    database_path = tmp_path / "governance.sqlite3"
    root = tmp_path / "text-root"
    root.mkdir(mode=0o755)
    transaction_root = root / ".jarvis-transactions"
    transaction_root.mkdir(mode=0o700)
    target = root / "note.txt"
    original = "conteúdo original exato\n"
    desired = "conteúdo governado MB-216\n"
    target.write_text(original, encoding="utf-8", newline="")

    governance = GovernanceService(
        database_path,
        trusted_execution_clock=clock.governance_now,
    )
    governance.activate_adapter_registry(
        SEEDED_ADAPTER_REGISTRY,
        activated_at=_z(base),
    )
    governance.activate_adapter_execution_registry(
        SEEDED_ADAPTER_EXECUTION_REGISTRY,
        activated_at=_z(base),
    )
    governance.activate_local_text_file_rollback_registry(SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY)

    preparer = OperationalService(
        artifact_dir=str(tmp_path / "artifacts"),
        adapter_preflight_verifier=governance.verify_adapter_grant_for_preflight_exact,
        local_text_file_roots={"notes": root},
        local_text_file_preflight_attestor=governance.attest_local_text_file_preflight,
    )
    action_request = AdapterActionRequestContract(
        adapter_id="local_text_file",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        operation="replace_text",
        resource_scope="configured_text_root",
        resource_ref="text:notes/note.txt",
    )
    root_fingerprint = preparer.local_text_file_root_config_fingerprint()
    prepare_intent = _intent(
        prefix="prepare",
        subject_ref="operator://local/e2e",
        handler_id="adapter://local_text_file",
        handler_version="1.0.0",
        operation=action_request.operation,
        resource_ref=action_request.resource_ref,
        content_digest=sha256(desired.encode()).hexdigest(),
        precondition_digest=root_fingerprint,
        issued_at=base,
    )
    prepare_registry, prepare_descriptor = governance.resolve_active_adapter_descriptor(
        action_request
    )
    prepare_grant = governance.issue_adapter_grant(
        prepare_intent,
        action_request,
        _decision(confirmation_required=False),
        expected_registry_fingerprint=prepare_registry.registry_fingerprint,
        expected_descriptor_fingerprint=prepare_descriptor.descriptor_fingerprint,
        issued_at=_z(base),
        expires_at=_z(base + timedelta(minutes=10)),
    )
    prepared_at = base + timedelta(seconds=1)
    preflight_request = LocalTextFilePreflightRequestContract(
        grant_id=prepare_grant.grant_id,
        grant_fingerprint=prepare_grant.grant_fingerprint,
        action_fingerprint=prepare_intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(prepare_intent),
        descriptor_fingerprint=prepare_grant.descriptor_fingerprint,
        registry_fingerprint=prepare_grant.registry_fingerprint,
        subject_ref=prepare_intent.operator_identity_ref,
        adapter_request=action_request,
        desired_text=desired,
        expected_root_config_fingerprint=root_fingerprint,
        preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
        diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
        diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
        prepared_at=_z(prepared_at),
        expires_at=_z(base + timedelta(minutes=4)),
        authorization_expires_at=prepare_grant.expires_at,
        expected_current_sha256=sha256(original.encode()).hexdigest(),
    )
    preflight, _attestation, execution_request = preparer.preflight_and_attest_local_text_file(
        preflight_request,
        now=prepared_at,
    )

    execution_intent = _intent(
        prefix="execute",
        subject_ref=execution_request.subject_ref,
        handler_id="adapter-executor://local_text_file",
        handler_version="2.0.0",
        operation=execution_request.operation,
        resource_ref=execution_request.resource_ref,
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
    execution_confirmation = _confirm(governance, execution_intent, clock.peek())
    clock.current += timedelta(seconds=1)

    authority = LocalTextGovernanceAuthorityAdapter(governance)
    operational = OperationalService(
        artifact_dir=str(tmp_path / "artifacts"),
        adapter_preflight_verifier=governance.verify_adapter_grant_for_preflight_exact,
        local_text_file_roots={"notes": root},
        local_text_file_transaction_roots={"notes": transaction_root},
        local_text_file_staging_authorization_verifier=authority.verify_staging,
        local_text_file_effect_start_claim_verifier=authority.verify_effect_start,
        local_text_file_historical_claim_lookup=authority.lookup_historical,
        local_text_file_historical_claim_verifier=authority.verify_historical,
        local_text_file_authorization_lease_provider=authority.claim,
        local_text_file_trusted_transaction_clock=clock.transaction_now,
        local_text_file_mutation_receipt_recorder=authority.record_mutation_receipt,
        local_text_file_rollback_receipt_recorder=authority.record_rollback_receipt,
    )
    execution_binding = LocalTextExecutionGrantBinding(
        execution_grant_id=execution_grant.grant_id,
        execution_grant_fingerprint=execution_grant.grant_fingerprint,
        action_fingerprint=execution_grant.action_fingerprint,
        execution_request_fingerprint=execution_request.execution_request_fingerprint,
        intent_fingerprint=execution_grant.intent_fingerprint,
        confirmation_receipt_id=execution_confirmation.receipt_id,
    )
    mutation_receipt = operational.execute_local_text_file(
        LocalTextMutationRequest(
            operation_id="operation://mb216/e2e-apply",
            preflight=preflight,
            desired_text=desired,
            execution_binding=execution_binding,
        )
    )
    assert target.read_bytes() == desired.encode()
    execution_claim = governance.load_adapter_execution_claim_for_recovery_exact(
        mutation_receipt.operation_id
    )
    assert datetime.fromisoformat(str(execution_claim.claimed_at).replace("Z", "+00:00")) <= (
        datetime.fromisoformat(mutation_receipt.committed_at.replace("Z", "+00:00"))
    )

    rollback_request = governance.prepare_local_text_file_rollback(
        mutation_receipt,
        rollback_operation_id="operation://mb216/e2e-rollback",
    )
    rollback_intent = _intent(
        prefix="rollback",
        subject_ref=rollback_request.subject_ref,
        handler_id=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.executor_ref,
        handler_version=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.adapter_version,
        operation=rollback_request.operation,
        resource_ref=rollback_request.resource_ref,
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
    clock.current += timedelta(seconds=1)
    rollback_binding = LocalTextExecutionGrantBinding(
        execution_grant_id=rollback_grant.grant_id,
        execution_grant_fingerprint=rollback_grant.grant_fingerprint,
        action_fingerprint=rollback_grant.action_fingerprint,
        execution_request_fingerprint=rollback_request.rollback_request_fingerprint,
        intent_fingerprint=rollback_grant.intent_fingerprint,
        confirmation_receipt_id=rollback_confirmation.receipt_id,
    )
    rollback_receipt = operational.rollback_local_text_file(
        LocalTextRollbackRequest(
            rollback_operation_id=str(rollback_request.rollback_operation_id),
            receipt=mutation_receipt,
            execution_binding=rollback_binding,
        )
    )
    assert target.read_bytes() == original.encode()
    assert rollback_receipt.mutation_operation_id == mutation_receipt.operation_id
    rollback_claim = governance.load_local_text_file_rollback_claim_for_recovery_exact(
        str(rollback_request.rollback_operation_id)
    )
    assert datetime.fromisoformat(str(rollback_claim.claimed_at).replace("Z", "+00:00")) <= (
        datetime.fromisoformat(rollback_receipt.rolled_back_at.replace("Z", "+00:00"))
    )
    assert governance.record_local_text_rollback_receipt(rollback_receipt) == rollback_receipt
