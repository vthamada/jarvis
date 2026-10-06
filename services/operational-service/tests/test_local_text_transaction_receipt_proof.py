from __future__ import annotations

import os
import threading
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path

import pytest
from operational_service.adapters import (
    LocalTextFilePreflightAdapter,
    LocalTextMutationRequest,
    LocalTextRollbackRequest,
    LocalTextTransactionEngine,
)
from operational_service.adapters.local_text_transaction import (
    LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
    LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
)
from test_local_text_transaction import (
    _binding,
    _digest,
    _harness,
    _preflight,
    _state_tree_snapshot,
)

from shared.artifact_physical_attestation_authority import (
    ArtifactPhysicalAttestationLeaseAuthority,
)
from shared.artifact_physical_saga import (
    require_valid_local_text_physical_state_attestation,
    seal_artifact_physical_apply_plan,
    seal_artifact_physical_canonical_commit_receipt,
    seal_artifact_physical_rollback_plan,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalCanonicalCommitReceiptContract,
    ArtifactPhysicalRollbackPlanContract,
    LocalTextFilePreflightContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
    LocalTextRollbackReceipt,
)
from shared.local_text_rollback_permissions import build_mutation_receipt_fingerprint


class _ReceiptProofLedger:
    def __init__(self) -> None:
        self.mutation = None
        self.rollback = None
        self.canonical_commits = []
        self.attestation_authority = ArtifactPhysicalAttestationLeaseAuthority()

    def verify_mutation(self, receipt: object) -> bool:
        return self.mutation == receipt

    def verify_rollback(self, receipt: object) -> bool:
        return self.rollback == receipt

    def record_mutation(self, receipt: LocalTextMutationReceipt) -> LocalTextMutationReceipt:
        self.mutation = receipt
        return receipt

    def record_rollback(self, receipt: LocalTextRollbackReceipt) -> LocalTextRollbackReceipt:
        self.rollback = receipt
        return receipt

    def record_canonical_commit(
        self,
        receipt: ArtifactPhysicalCanonicalCommitReceiptContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        self.canonical_commits.append(receipt)
        return receipt

    def verify_canonical_commit(self, receipt: object) -> bool:
        return receipt in self.canonical_commits


def _apply_plan(
    preflight: LocalTextFilePreflightContract,
    receipt: LocalTextMutationReceipt,
) -> ArtifactPhysicalApplyPlanContract:
    return _apply_plan_for_preflight(preflight, receipt.operation_id)


def _apply_plan_for_preflight(
    preflight: LocalTextFilePreflightContract,
    operation_id: str,
) -> ArtifactPhysicalApplyPlanContract:
    register = preflight.operation == "create_text"
    lineage_root_ref = f"artifact://lineage/{operation_id}"
    artifact_ref = lineage_root_ref if register else f"{lineage_root_ref}/version/2"
    plan = ArtifactPhysicalApplyPlanContract(
        saga_id=f"artifact-physical-saga://apply/{operation_id}",
        mission_id="mission://receipt-proof",
        artifact_ref=artifact_ref,
        artifact_version=1 if register else 2,
        owner_mission_id="mission://receipt-proof",
        objective_ref=None,
        work_item_ref="work-item://receipt-proof",
        lineage_root_ref=lineage_root_ref,
        supersedes_artifact_ref=None if register else f"{lineage_root_ref}/version/1",
        transition="register" if register else "replace",
        physical_operation_id=operation_id,
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
        expected_lineage_revision=0 if register else 1,
        created_at=preflight.prepared_at,
        plan_fingerprint="0" * 64,
    )
    return seal_artifact_physical_apply_plan(plan)


def _rollback_plan(
    mutation: LocalTextMutationReceipt,
    rollback: LocalTextRollbackReceipt,
) -> ArtifactPhysicalRollbackPlanContract:
    compensation = mutation.operation == "create_text"
    lineage_root_ref = f"artifact://lineage/{mutation.operation_id}"
    plan = ArtifactPhysicalRollbackPlanContract(
        saga_id=f"artifact-physical-saga://rollback/{rollback.operation_id}",
        mission_id="mission://receipt-proof",
        active_artifact_ref=(lineage_root_ref if compensation else f"{lineage_root_ref}/version/2"),
        active_artifact_version=1 if compensation else 2,
        restored_artifact_ref=None if compensation else f"{lineage_root_ref}/version/1",
        restored_artifact_version=None if compensation else 1,
        owner_mission_id="mission://receipt-proof",
        objective_ref=None,
        work_item_ref="work-item://receipt-proof",
        lineage_root_ref=lineage_root_ref,
        physical_operation_id=rollback.operation_id,
        mutation_operation_id=mutation.operation_id,
        source_apply_saga_id=f"artifact-physical-saga://apply/{mutation.operation_id}",
        rollback_mode=("precanonical_compensation" if compensation else "canonical_rollback"),
        canonical_effect_expected=not compensation,
        mutation_receipt_fingerprint=mutation.receipt_fingerprint,
        resource_ref=mutation.resource_ref,
        root_alias="workspace",
        expected_current_sha256=mutation.desired_content_sha256,
        restored_content_sha256=rollback.restored_content_sha256,
        expected_lineage_revision=0 if compensation else 2,
        created_at=rollback.rolled_back_at,
        plan_fingerprint="0" * 64,
    )
    return seal_artifact_physical_rollback_plan(plan)


def _canonical_commit(
    ledger: _ReceiptProofLedger,
    plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
    receipt: LocalTextMutationReceipt | LocalTextRollbackReceipt,
    attestation: LocalTextPhysicalStateAttestationContract,
    *,
    persist: bool = True,
) -> ArtifactPhysicalCanonicalCommitReceiptContract:
    apply = isinstance(plan, ArtifactPhysicalApplyPlanContract)
    verified = ledger.attestation_authority.verify_and_consume(receipt, attestation)
    if verified is not True:
        raise ValueError("test_memory_attestation_lease_not_verified")
    artifact_ref = (
        plan.artifact_ref
        if apply
        else plan.restored_artifact_ref
        if plan.canonical_effect_expected
        else None
    )
    artifact_version = (
        plan.artifact_version
        if apply
        else plan.restored_artifact_version
        if plan.canonical_effect_expected
        else None
    )
    commit = ArtifactPhysicalCanonicalCommitReceiptContract(
        commit_id=f"artifact-physical-commit://{plan.saga_id}",
        purpose="apply" if apply else "rollback",
        saga_id=plan.saga_id,
        plan_fingerprint=plan.plan_fingerprint,
        mission_id=plan.mission_id,
        artifact_ref=artifact_ref,
        artifact_version=artifact_version,
        lineage_root_ref=plan.lineage_root_ref,
        lineage_revision=(
            plan.expected_lineage_revision + (1 if apply else int(plan.canonical_effect_expected))
        ),
        physical_operation_id=plan.physical_operation_id,
        resource_ref=plan.resource_ref,
        root_alias=plan.root_alias,
        mutation_receipt_fingerprint=(
            receipt.receipt_fingerprint
            if isinstance(receipt, LocalTextMutationReceipt)
            else receipt.mutation_receipt_fingerprint
        ),
        rollback_receipt_fingerprint=(
            None
            if isinstance(receipt, LocalTextMutationReceipt)
            else receipt.rollback_receipt_fingerprint
        ),
        physical_state_attestation_fingerprint=attestation.attestation_fingerprint,
        canonical_event_fingerprint="c" * 64,
        committed_at=attestation.verified_at,
        commit_fingerprint="0" * 64,
    )
    sealed = seal_artifact_physical_canonical_commit_receipt(commit)
    return ledger.record_canonical_commit(sealed) if persist else sealed


def _enable_receipt_proof(engine: LocalTextTransactionEngine) -> _ReceiptProofLedger:
    ledger = _ReceiptProofLedger()
    engine._mutation_receipt_verifier = ledger.verify_mutation
    engine._rollback_receipt_verifier = ledger.verify_rollback
    engine._canonical_physical_effect_authorizer = lambda _plan, *, effect_mode="new_effect": True
    # Explicit fixture authority doubles; these are not live Memory fences.
    engine._canonical_physical_effect_scope_provider = lambda _plan: nullcontext()
    engine._resource_physical_binding_lookup = lambda _resource_ref: False
    engine._canonical_commit_receipt_verifier = ledger.verify_canonical_commit
    engine._physical_attestation_lease_provider = ledger.attestation_authority.issue
    return ledger


def _restart(
    *,
    adapter: LocalTextFilePreflightAdapter,
    state: Path,
    authority: object,
    ledger: _ReceiptProofLedger,
) -> LocalTextTransactionEngine:
    return LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots={"workspace": state},
        staging_authorization_verifier=lambda _request, _current: True,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=authority.claim,
        trusted_transaction_clock=authority.clock,
        mutation_receipt_verifier=ledger.verify_mutation,
        rollback_receipt_verifier=ledger.verify_rollback,
        canonical_physical_effect_authorizer=lambda _plan, *, effect_mode="new_effect": True,
        canonical_physical_effect_scope_provider=lambda _plan: nullcontext(),
        resource_physical_binding_lookup=lambda _resource_ref: False,
        canonical_commit_receipt_verifier=ledger.verify_canonical_commit,
        physical_attestation_lease_provider=ledger.attestation_authority.issue,
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_mutation_receipt_proof_is_fresh_exact_and_restart_safe(tmp_path: Path) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    ledger = _enable_receipt_proof(engine)
    target = root / "docs" / "note.txt"
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="canonical\n",
        expected_current_sha256=None,
    )
    receipt = engine.execute(
        LocalTextMutationRequest(
            "operation-proof-create",
            preflight,
            "canonical\n",
            _binding("proof-create"),
        )
    )
    ledger.mutation = receipt
    plan = _apply_plan(preflight, receipt)

    assert (
        engine.verify_mutation_receipt_current(
            root_alias="workspace",
            receipt=receipt,
        )
        == receipt
    )
    captured = []

    def commit(bound_plan, exact, attestation):
        captured.append((bound_plan, exact, attestation))
        return _canonical_commit(ledger, bound_plan, exact, attestation)

    committed = engine.commit_mutation_if_current(
        plan=plan,
        root_alias="workspace",
        receipt=receipt,
        canonical_commit=commit,
    )
    assert committed in ledger.canonical_commits
    bound_plan, exact, attestation = captured[-1]
    assert bound_plan == plan
    assert exact == receipt
    require_valid_local_text_physical_state_attestation(attestation)
    assert attestation.purpose == "mutation_current"
    assert attestation.receipt_fingerprint == receipt.receipt_fingerprint
    assert attestation.mutation_operation_id == receipt.operation_id
    assert attestation.rollback_operation_id is None
    assert attestation.physical_state == "applied"
    assert attestation.observed_content_sha256 == receipt.desired_content_sha256
    assert attestation.journal_event_fingerprint == receipt.applied_event_fingerprint
    assert not attestation.contains_content

    with pytest.raises(ValueError, match="canonical_commit_receipt_not_verified"):
        engine.commit_mutation_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=receipt,
            canonical_commit=lambda bound_plan, exact_receipt, proof: _canonical_commit(
                ledger,
                bound_plan,
                exact_receipt,
                proof,
                persist=False,
            ),
        )

    restarted = _restart(
        adapter=adapter,
        state=state,
        authority=authority,
        ledger=ledger,
    )
    assert (
        restarted.verify_mutation_receipt_current(
            root_alias="workspace",
            receipt=receipt,
        )
        == receipt
    )
    with pytest.raises(ValueError, match="root_alias_mismatch"):
        restarted.verify_mutation_receipt_current(
            root_alias="wrong",
            receipt=receipt,
        )
    forged = replace(
        receipt,
        resource_ref="text:workspace/docs/other.txt",
        receipt_fingerprint="0" * 64,
    )
    forged = replace(
        forged,
        receipt_fingerprint=build_mutation_receipt_fingerprint(forged),
    )
    with pytest.raises(ValueError, match="mutation_receipt_not_verified"):
        restarted.verify_mutation_receipt_current(
            root_alias="workspace",
            receipt=forged,
        )
    with pytest.raises(ValueError, match="mutation_receipt_fingerprint_invalid"):
        restarted.verify_mutation_receipt_current(
            root_alias="workspace",
            receipt=replace(receipt, receipt_fingerprint="f" * 64),
        )

    callback_called = False

    def must_not_commit(_plan, _exact, _attestation):
        nonlocal callback_called
        callback_called = True

    restarted._mutation_receipt_verifier = lambda _receipt: False
    with pytest.raises(ValueError, match="mutation_receipt_not_verified"):
        restarted.commit_mutation_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=receipt,
            canonical_commit=must_not_commit,
        )
    restarted._mutation_receipt_verifier = lambda _receipt: 1 / 0
    with pytest.raises(ValueError, match="mutation_receipt_verification_failed"):
        restarted.commit_mutation_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=receipt,
            canonical_commit=must_not_commit,
        )
    restarted._mutation_receipt_verifier = ledger.verify_mutation
    restarted._canonical_commit_receipt_verifier = None
    with pytest.raises(ValueError, match="commit_receipt_verifier_not_configured"):
        restarted.commit_mutation_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=receipt,
            canonical_commit=must_not_commit,
        )
    restarted._canonical_commit_receipt_verifier = ledger.verify_canonical_commit
    restarted._physical_attestation_lease_provider = None
    with pytest.raises(ValueError, match="attestation_lease_provider_not_configured"):
        restarted.commit_mutation_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=receipt,
            canonical_commit=must_not_commit,
        )
    restarted._physical_attestation_lease_provider = ledger.attestation_authority.issue
    target.write_bytes(b"later external edit\n")
    with pytest.raises(ValueError, match="physical_state_mismatch"):
        restarted.commit_mutation_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=receipt,
            canonical_commit=must_not_commit,
        )
    assert not callback_called


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_create_rollback_receipt_proves_absent_target_after_restart(tmp_path: Path) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    ledger = _enable_receipt_proof(engine)
    target = root / "docs" / "created.txt"
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/created.txt",
        desired_text="temporary\n",
        expected_current_sha256=None,
    )
    mutation = engine.execute(
        LocalTextMutationRequest(
            "operation-proof-create-rollback",
            preflight,
            "temporary\n",
            _binding("create-rollback"),
        )
    )
    ledger.mutation = mutation
    rollback = engine.rollback(
        LocalTextRollbackRequest(
            "operation-proof-create-rollback-undo",
            mutation,
            _binding("create-rollback-undo"),
        )
    )
    ledger.rollback = rollback
    plan = _rollback_plan(mutation, rollback)
    assert not target.exists()

    restarted = _restart(
        adapter=adapter,
        state=state,
        authority=authority,
        ledger=ledger,
    )
    captured = []
    with pytest.raises(ValueError, match="rollback_recovery_binding_invalid"):
        restarted.recover_rollback_and_commit(
            plan=plan,
            root_alias="workspace",
            operation_id=mutation.operation_id,
            receipt_recorder=ledger.record_rollback,
            canonical_commit=lambda *_values: (_ for _ in ()).throw(
                AssertionError("callback must not run")
            ),
        )
    result = restarted.recover_rollback_and_commit(
        plan=plan,
        root_alias="workspace",
        operation_id=rollback.operation_id,
        receipt_recorder=ledger.record_rollback,
        canonical_commit=lambda bound_plan, exact, proof: (
            captured.append((bound_plan, exact, proof))
            or _canonical_commit(ledger, bound_plan, exact, proof)
        ),
    )
    assert result in ledger.canonical_commits
    bound_plan, exact, attestation = captured[0]
    assert bound_plan == plan
    assert exact == rollback
    require_valid_local_text_physical_state_attestation(attestation)
    assert attestation.purpose == "rollback_current"
    assert attestation.physical_state == "absent"
    assert attestation.rollback_operation_id == rollback.operation_id
    assert attestation.mutation_operation_id == mutation.operation_id
    assert attestation.observed_content_sha256 == rollback.restored_content_sha256
    assert attestation.journal_event_fingerprint == rollback.rolled_back_event_fingerprint

    target.write_bytes(b"later recreation\n")
    callback_called = False

    def must_not_commit(_plan, _exact, _proof):
        nonlocal callback_called
        callback_called = True

    with pytest.raises(ValueError, match="physical_state"):
        restarted.commit_rollback_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=rollback,
            canonical_commit=must_not_commit,
        )
    assert not callback_called


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_replace_rollback_receipt_proves_restored_identity_and_detects_edit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    ledger = _enable_receipt_proof(engine)
    target = root / "docs" / "replace.txt"
    target.write_bytes(b"before\n")
    preflight = _preflight(
        adapter,
        operation="replace_text",
        relative_path="docs/replace.txt",
        desired_text="after\n",
        expected_current_sha256=_digest(b"before\n"),
    )
    mutation = engine.execute(
        LocalTextMutationRequest(
            "operation-proof-replace",
            preflight,
            "after\n",
            _binding("replace"),
        )
    )
    ledger.mutation = mutation
    rollback = engine.rollback(
        LocalTextRollbackRequest(
            "operation-proof-replace-rollback",
            mutation,
            _binding("replace-rollback"),
        )
    )
    ledger.rollback = rollback
    plan = _rollback_plan(mutation, rollback)
    assert target.read_bytes() == b"before\n"

    with pytest.raises(ValueError, match="physical_state_mismatch"):
        engine.verify_mutation_receipt_current(
            root_alias="workspace",
            receipt=mutation,
        )
    captured = []
    engine.commit_rollback_if_current(
        plan=plan,
        root_alias="workspace",
        receipt=rollback,
        canonical_commit=lambda bound_plan, exact, proof: (
            captured.append((bound_plan, exact, proof))
            or _canonical_commit(ledger, bound_plan, exact, proof)
        ),
    )
    attestation = captured[0][2]
    require_valid_local_text_physical_state_attestation(attestation)
    assert attestation.physical_state == "restored"
    assert attestation.observed_content_sha256 == _digest(b"before\n")

    restarted = _restart(
        adapter=adapter,
        state=state,
        authority=authority,
        ledger=ledger,
    )
    assert (
        restarted.verify_rollback_receipt_current(
            root_alias="workspace",
            receipt=rollback,
        )
        == rollback
    )
    target.write_bytes(b"external\n")
    with pytest.raises(ValueError, match="physical_state"):
        restarted.verify_rollback_receipt_current(
            root_alias="workspace",
            receipt=rollback,
        )

    before_state = _state_tree_snapshot(state)
    callback_calls = []

    def forbidden_io(*_args, **_kwargs):
        raise AssertionError("receipt rejection must precede transaction filesystem I/O")

    monkeypatch.setattr(restarted, "_resource_lock", forbidden_io)
    monkeypatch.setattr(restarted, "_load_events", forbidden_io)
    monkeypatch.setattr(restarted, "_open_pinned_posix", forbidden_io)
    restarted._mutation_receipt_verifier = lambda _receipt: False
    with pytest.raises(ValueError, match="mutation_receipt_not_verified"):
        restarted.commit_mutation_if_current(
            plan=_apply_plan(preflight, mutation),
            root_alias="workspace",
            receipt=mutation,
            canonical_commit=lambda *_values: callback_calls.append(_values),
        )

    def rollback_verifier_error(_receipt):
        raise RuntimeError("ledger unavailable")

    restarted._rollback_receipt_verifier = rollback_verifier_error
    with pytest.raises(ValueError, match="rollback_receipt_verification_failed"):
        restarted.commit_rollback_if_current(
            plan=plan,
            root_alias="workspace",
            receipt=rollback,
            canonical_commit=lambda *_values: callback_calls.append(_values),
        )
    assert callback_calls == []
    assert _state_tree_snapshot(state) == before_state


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_atomic_apply_records_exact_proof_and_blocks_bound_raw_retry(tmp_path: Path) -> None:
    root, _state, adapter, engine, _authority, _calls = _harness(tmp_path)
    ledger = _enable_receipt_proof(engine)
    target = root / "docs" / "atomic.txt"
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/atomic.txt",
        desired_text="atomic\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest(
        "operation-proof-atomic",
        preflight,
        "atomic\n",
        _binding("atomic"),
    )
    plan = _apply_plan_for_preflight(preflight, request.operation_id)
    authorized_plans = []
    binding_lookups = []
    resource_bound = False

    def authorize(bound_plan: object, *, effect_mode: str = "new_effect") -> bool:
        authorized_plans.append((bound_plan, effect_mode))
        return bound_plan == plan and effect_mode in {"new_effect", "historical_recovery"}

    engine._canonical_physical_effect_authorizer = authorize

    def lookup_binding(resource_ref: str) -> bool:
        binding_lookups.append(resource_ref)
        return resource_bound

    engine._resource_physical_binding_lookup = lookup_binding
    callback_observations = []

    def commit(bound_plan, receipt, attestation):
        callback_observations.append((ledger.mutation, receipt, attestation))
        return _canonical_commit(ledger, bound_plan, receipt, attestation)

    result = engine.execute_and_commit_apply(
        plan,
        request,
        receipt_recorder=ledger.record_mutation,
        canonical_commit=commit,
    )
    assert result in ledger.canonical_commits
    assert callback_observations[0][0] == callback_observations[0][1]
    require_valid_local_text_physical_state_attestation(callback_observations[0][2])
    assert authorized_plans == [(plan, "new_effect"), (plan, "historical_recovery")]
    assert target.read_bytes() == b"atomic\n"

    with pytest.raises(ValueError, match="resource_scope_mismatch"):
        engine._require_canonical_physical_binding(
            purpose="apply",
            operation_id="operation-proof-noncanonical",
            mutation_operation_id=None,
            mutation_receipt_fingerprint=None,
            resource_ref="text:workspace/docs/%2e%2e/escape.txt",
            root_alias="workspace",
            plan=None,
        )
    assert binding_lookups == []

    resource_bound = True
    with pytest.raises(ValueError, match="resource_physically_bound"):
        engine.execute(
            replace(
                request,
                operation_id="operation-proof-atomic-raw-retry",
                execution_binding=_binding("atomic-raw-retry"),
            )
        )
    assert target.read_bytes() == b"atomic\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_restart_recovers_apply_into_canonical_commit_under_one_lock(tmp_path: Path) -> None:
    _root_path, state, adapter, engine, authority, _calls = _harness(tmp_path)
    ledger = _enable_receipt_proof(engine)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/recovered.txt",
        desired_text="recovered\n",
        expected_current_sha256=None,
    )
    mutation = engine.execute(
        LocalTextMutationRequest(
            "operation-proof-recover-apply",
            preflight,
            "recovered\n",
            _binding("recover-apply"),
        )
    )
    ledger.mutation = mutation
    plan = _apply_plan(preflight, mutation)
    restarted = _restart(
        adapter=adapter,
        state=state,
        authority=authority,
        ledger=ledger,
    )

    result = restarted.recover_and_commit_apply(
        plan=plan,
        root_alias="workspace",
        operation_id=mutation.operation_id,
        receipt_recorder=ledger.record_mutation,
        canonical_commit=lambda bound_plan, receipt, proof: _canonical_commit(
            ledger,
            bound_plan,
            receipt,
            proof,
        ),
    )
    assert result in ledger.canonical_commits


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_canonical_commit_holds_lock_and_bound_guard_rejects_concurrent_raw_rollback(
    tmp_path: Path,
) -> None:
    root, _state, adapter, engine, _authority, _calls = _harness(tmp_path)
    ledger = _enable_receipt_proof(engine)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/locked.txt",
        desired_text="locked\n",
        expected_current_sha256=None,
    )
    mutation = engine.execute(
        LocalTextMutationRequest(
            "operation-proof-lock",
            preflight,
            "locked\n",
            _binding("locked"),
        )
    )
    ledger.mutation = mutation
    plan = _apply_plan(preflight, mutation)
    callback_entered = threading.Event()
    release_callback = threading.Event()
    rollback_started = threading.Event()
    rollback_finished = threading.Event()
    resource_bound = threading.Event()
    errors = []
    engine._resource_physical_binding_lookup = lambda _resource_ref: resource_bound.is_set()

    def canonical_commit(bound_plan, exact, proof):
        callback_entered.set()
        assert release_callback.wait(timeout=5)
        result = _canonical_commit(ledger, bound_plan, exact, proof)
        resource_bound.set()
        return result

    def run_commit() -> None:
        try:
            engine.commit_mutation_if_current(
                plan=plan,
                root_alias="workspace",
                receipt=mutation,
                canonical_commit=canonical_commit,
            )
        except Exception as exc:  # pragma: no cover - assertion reports value
            errors.append(exc)

    def run_rollback() -> None:
        rollback_started.set()
        try:
            engine.rollback(
                LocalTextRollbackRequest(
                    "operation-proof-lock-rollback",
                    mutation,
                    _binding("locked-rollback"),
                )
            )
        except Exception as exc:  # pragma: no cover - assertion reports value
            errors.append(exc)
        finally:
            rollback_finished.set()

    commit_thread = threading.Thread(target=run_commit)
    rollback_thread = threading.Thread(target=run_rollback)
    commit_thread.start()
    assert callback_entered.wait(timeout=5)
    rollback_thread.start()
    assert rollback_started.wait(timeout=5)
    assert not rollback_finished.wait(timeout=0.2)
    release_callback.set()
    commit_thread.join(timeout=5)
    rollback_thread.join(timeout=5)

    assert not commit_thread.is_alive()
    assert not rollback_thread.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)
    assert "local_text_resource_physically_bound" in str(errors[0])
    assert rollback_finished.is_set()
    assert (root / "docs" / "locked.txt").read_bytes() == b"locked\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows fail-closed backend")
def test_windows_receipt_proof_backend_fails_closed_before_verifier(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    state = root / ".jarvis-transactions"
    state.mkdir()
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
    )
    verifier_calls = []

    def verifier(receipt: object) -> bool:
        verifier_calls.append(receipt)
        return True

    with pytest.raises(ValueError, match="canonical_physical_ports_incomplete"):
        LocalTextTransactionEngine(
            preflight_adapter=adapter,
            transaction_roots={"workspace": state},
            staging_authorization_verifier=lambda _request, _current: True,
            effect_start_claim_verifier=lambda _context, _current: True,
            historical_claim_lookup=lambda _request, _current: None,
            historical_claim_verifier=lambda _context, _current: True,
            authorization_lease_provider=lambda _request, _current: object(),
            trusted_transaction_clock=lambda: None,
            canonical_commit_receipt_verifier=verifier,
        )

    with pytest.raises(ValueError, match="backend_not_handle_safe"):
        LocalTextTransactionEngine(
            preflight_adapter=adapter,
            transaction_roots={"workspace": state},
            staging_authorization_verifier=lambda _request, _current: True,
            effect_start_claim_verifier=lambda _context, _current: True,
            historical_claim_lookup=lambda _request, _current: None,
            historical_claim_verifier=lambda _context, _current: True,
            authorization_lease_provider=lambda _request, _current: object(),
            trusted_transaction_clock=lambda: None,
            mutation_receipt_verifier=verifier,
            rollback_receipt_verifier=verifier,
        )
    assert verifier_calls == []
