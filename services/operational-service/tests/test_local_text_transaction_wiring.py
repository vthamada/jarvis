from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import operational_service.service as service_module
import pytest
from operational_service.adapters.local_text_transaction import LocalTextTransactionEngine
from operational_service.service import OperationalService

from shared.artifact_physical_attestation_authority import (
    ArtifactPhysicalAttestationLeaseAuthority,
)
from shared.contracts import ArtifactPhysicalRollbackPlanContract


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    return root


def test_transaction_engine_receives_historical_claim_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    mutation_receipt = object()
    rollback_receipt = object()
    mutation_attestation = object()
    rollback_attestation = object()
    apply_plan = object()
    rollback_plan = object()
    canonical_commit_receipt = object()
    recorded_mutations: list[object] = []
    recorded_rollbacks: list[object] = []

    class Engine:
        def execute(self, _request: object) -> object:
            return mutation_receipt

        def recover(self, **_kwargs: object) -> object:
            return mutation_receipt

        def rollback(self, _request: object) -> object:
            return rollback_receipt

        def recover_rollback(self, **_kwargs: object) -> object:
            return rollback_receipt

        def verify_mutation_receipt_current(self, **_kwargs: object) -> object:
            return mutation_receipt

        def verify_rollback_receipt_current(self, **_kwargs: object) -> object:
            return rollback_receipt

        def commit_mutation_if_current(self, **kwargs: object) -> object:
            callback = kwargs["canonical_commit"]
            assert callable(callback)
            return callback(kwargs["plan"], mutation_receipt, mutation_attestation)

        def commit_rollback_if_current(self, **kwargs: object) -> object:
            callback = kwargs["canonical_commit"]
            assert callable(callback)
            return callback(kwargs["plan"], rollback_receipt, rollback_attestation)

        def execute_and_commit_apply(self, plan: object, _request: object, **kwargs: object):
            assert plan is apply_plan
            recorded = kwargs["receipt_recorder"](mutation_receipt)
            return kwargs["canonical_commit"](plan, recorded, mutation_attestation)

        def recover_and_commit_apply(self, **kwargs: object) -> object:
            recorded = kwargs["receipt_recorder"](mutation_receipt)
            return kwargs["canonical_commit"](kwargs["plan"], recorded, mutation_attestation)

        def rollback_and_commit(self, plan: object, _request: object, **kwargs: object):
            assert plan is rollback_plan
            recorded = kwargs["receipt_recorder"](rollback_receipt)
            return kwargs["canonical_commit"](plan, recorded, rollback_attestation)

        def recover_rollback_and_commit(self, **kwargs: object) -> object:
            recorded = kwargs["receipt_recorder"](rollback_receipt)
            return kwargs["canonical_commit"](kwargs["plan"], recorded, rollback_attestation)

    engine = Engine()

    def build_engine(**kwargs: object) -> object:
        captured.update(kwargs)
        return engine

    monkeypatch.setattr(service_module, "LocalTextTransactionEngine", build_engine)
    root = _root(tmp_path)

    def lookup(_request: object, _current: object) -> None:
        return None

    def record_mutation(receipt: object) -> object:
        recorded_mutations.append(receipt)
        return receipt

    def record_rollback(receipt: object) -> object:
        recorded_rollbacks.append(receipt)
        return receipt

    def transaction_clock() -> datetime:
        return datetime(2026, 8, 30, 12, tzinfo=UTC)

    def verify_mutation(receipt: object) -> bool:
        return receipt is mutation_receipt

    def verify_rollback(receipt: object) -> bool:
        return receipt is rollback_receipt

    def authorize_effect(
        _plan: object,
        *,
        resource_ref: str,
        mutation_receipt_fingerprint: str | None = None,
    ) -> bool:
        return bool(resource_ref) and mutation_receipt_fingerprint is None

    def resource_bound(_resource_ref: str) -> bool:
        return False

    def verify_canonical_commit(receipt: object) -> bool:
        return receipt is canonical_commit_receipt

    lease_authority = ArtifactPhysicalAttestationLeaseAuthority()

    service = OperationalService(
        artifact_dir=str(tmp_path / "artifacts"),
        local_text_file_roots={"workspace": root},
        local_text_file_transaction_roots={"workspace": root / ".transactions"},
        local_text_file_staging_authorization_verifier=lambda _request, _current: True,
        local_text_file_effect_start_claim_verifier=lambda _context, _current: True,
        local_text_file_historical_claim_lookup=lookup,
        local_text_file_historical_claim_verifier=lambda _context, _current: True,
        local_text_file_authorization_lease_provider=lambda _request, _current: object(),
        local_text_file_trusted_transaction_clock=transaction_clock,
        local_text_file_mutation_receipt_recorder=record_mutation,
        local_text_file_rollback_receipt_recorder=record_rollback,
        local_text_file_mutation_receipt_verifier=verify_mutation,
        local_text_file_rollback_receipt_verifier=verify_rollback,
        local_text_file_canonical_physical_effect_authorizer=authorize_effect,
        local_text_file_resource_physical_binding_lookup=resource_bound,
        local_text_file_canonical_commit_receipt_verifier=verify_canonical_commit,
        local_text_file_physical_attestation_lease_provider=lease_authority.issue,
    )

    assert captured["historical_claim_lookup"] is lookup
    assert captured["trusted_transaction_clock"] is transaction_clock
    assert captured["mutation_receipt_verifier"] is verify_mutation
    assert captured["rollback_receipt_verifier"] is verify_rollback
    assert callable(captured["canonical_physical_effect_authorizer"])
    assert captured["resource_physical_binding_lookup"] is resource_bound
    assert captured["canonical_commit_receipt_verifier"] is verify_canonical_commit
    assert callable(captured["physical_attestation_lease_provider"])
    assert callable(captured["effect_start_claim_verifier"])
    assert service._local_text_file_transaction_engine is engine
    assert service.execute_local_text_file(object()) is mutation_receipt
    assert (
        service.recover_local_text_file(root_alias="workspace", operation_id="operation-1")
        is mutation_receipt
    )
    assert service.rollback_local_text_file(object()) is rollback_receipt
    assert (
        service.recover_local_text_file_rollback(
            root_alias="workspace",
            operation_id="operation-1",
        )
        is rollback_receipt
    )
    assert recorded_mutations == [mutation_receipt, mutation_receipt]
    assert recorded_rollbacks == [rollback_receipt, rollback_receipt]
    assert (
        service.verify_local_text_file_mutation_receipt_current(
            root_alias="workspace",
            receipt=mutation_receipt,
        )
        is mutation_receipt
    )
    assert (
        service.verify_local_text_file_rollback_receipt_current(
            root_alias="workspace",
            receipt=rollback_receipt,
        )
        is rollback_receipt
    )
    assert service.commit_local_text_file_mutation_if_current(
        plan=apply_plan,
        root_alias="workspace",
        receipt=mutation_receipt,
        canonical_commit=lambda plan, exact, proof: (plan, exact, proof),
    ) == (apply_plan, mutation_receipt, mutation_attestation)
    assert service.commit_local_text_file_rollback_if_current(
        plan=rollback_plan,
        root_alias="workspace",
        receipt=rollback_receipt,
        canonical_commit=lambda plan, exact, proof: (plan, exact, proof),
    ) == (rollback_plan, rollback_receipt, rollback_attestation)

    def commit(_plan: object, _receipt: object, _proof: object) -> object:
        return canonical_commit_receipt

    assert (
        service.execute_and_commit_local_text_file_apply(
            apply_plan,
            object(),
            canonical_commit=commit,
        )
        is canonical_commit_receipt
    )
    assert (
        service.recover_and_commit_local_text_file_apply(
            plan=apply_plan,
            root_alias="workspace",
            operation_id="operation-1",
            canonical_commit=commit,
        )
        is canonical_commit_receipt
    )
    assert (
        service.rollback_and_commit_local_text_file(
            rollback_plan,
            object(),
            canonical_commit=commit,
        )
        is canonical_commit_receipt
    )
    assert (
        service.recover_and_commit_local_text_file_rollback(
            plan=rollback_plan,
            root_alias="workspace",
            operation_id="operation-1",
            canonical_commit=commit,
        )
        is canonical_commit_receipt
    )


def test_transaction_configuration_requires_historical_claim_lookup(tmp_path: Path) -> None:
    root = _root(tmp_path)

    with pytest.raises(
        ValueError,
        match="local_text_file_transaction_governance_ports_required",
    ):
        OperationalService(
            artifact_dir=str(tmp_path / "artifacts"),
            local_text_file_roots={"workspace": root},
            local_text_file_transaction_roots={"workspace": root / ".transactions"},
            local_text_file_staging_authorization_verifier=lambda _request, _current: True,
            local_text_file_effect_start_claim_verifier=lambda _context, _current: True,
            local_text_file_historical_claim_verifier=lambda _context, _current: True,
            local_text_file_authorization_lease_provider=lambda _request, _current: object(),
            local_text_file_trusted_transaction_clock=lambda: datetime(2026, 8, 30, 12, tzinfo=UTC),
            local_text_file_mutation_receipt_recorder=lambda receipt: receipt,
            local_text_file_rollback_receipt_recorder=lambda receipt: receipt,
        )


def test_canonical_effect_authorizer_bridge_passes_exact_memory_keywords() -> None:
    calls = []

    def authorize(
        plan: object,
        *,
        resource_ref: str,
        mutation_receipt_fingerprint: str | None = None,
    ) -> bool:
        calls.append((plan, resource_ref, mutation_receipt_fingerprint))
        return True

    service = object.__new__(OperationalService)
    service._local_text_file_canonical_physical_effect_authorizer = authorize

    class ApplyPlan:
        resource_ref = "text:workspace/docs/apply.txt"

    apply_plan = ApplyPlan()
    rollback_plan = object.__new__(ArtifactPhysicalRollbackPlanContract)
    object.__setattr__(rollback_plan, "resource_ref", "text:workspace/docs/rollback.txt")
    object.__setattr__(rollback_plan, "mutation_receipt_fingerprint", "a" * 64)

    assert service._authorize_local_text_file_canonical_physical_effect(apply_plan)
    assert service._authorize_local_text_file_canonical_physical_effect(rollback_plan)
    assert calls == [
        (apply_plan, "text:workspace/docs/apply.txt", None),
        (rollback_plan, "text:workspace/docs/rollback.txt", "a" * 64),
    ]


def test_engine_runs_canonical_callback_only_inside_injected_attestation_lease() -> None:
    engine = object.__new__(LocalTextTransactionEngine)
    active = False
    values = (object(), object(), object())
    expected = object()

    @contextmanager
    def lease_provider(plan: object, receipt: object, attestation: object):
        nonlocal active
        assert (plan, receipt, attestation) == values
        active = True
        try:
            yield
        finally:
            active = False

    engine._physical_attestation_lease_provider = lease_provider

    def canonical_commit(plan: object, receipt: object, attestation: object) -> object:
        assert active
        assert (plan, receipt, attestation) == values
        return expected

    assert (
        engine._run_canonical_commit_under_attestation_lease(
            plan=values[0],
            receipt=values[1],
            attestation=values[2],
            canonical_commit=canonical_commit,
        )
        is expected
    )
    assert not active
