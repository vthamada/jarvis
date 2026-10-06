"""Pure fixture tests of kernel decisions, not POSIX/backend execution evidence."""

from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace

import pytest
from operational_service.adapters.local_text_transaction import (
    LocalTextExecutionAuthorizationContext,
    LocalTextExecutionGrantBinding,
    LocalTextRollbackRequest,
    LocalTextTransactionEngine,
    build_execution_authority_fingerprint,
)

NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)


def _digest(value):
    return sha256(value.encode()).hexdigest()


def _binding():
    return LocalTextExecutionGrantBinding(
        execution_grant_id="grant://mb219/fixture",
        execution_grant_fingerprint=_digest("grant"),
        action_fingerprint=_digest("action"),
        execution_request_fingerprint=_digest("request"),
        intent_fingerprint=_digest("intent"),
        confirmation_receipt_id="confirmation://mb219/fixture",
    )


def _event(phase, *, reservation=None):
    binding = _binding()
    metadata = {
        "action_kind": "execute_external_action",
        "operation": "replace_text",
        "resource_ref": "text:workspace/fixture.txt",
        "subject_ref": "operator://mb219/fixture",
        "preflight_fingerprint": _digest("preflight"),
        "before_content_sha256": _digest("before"),
        "desired_content_sha256": _digest("after"),
        "root_config_fingerprint": _digest("root"),
        "requested_execution_grant_id": binding.execution_grant_id,
        "execution_grant_fingerprint": binding.execution_grant_fingerprint,
        "execution_action_fingerprint": binding.action_fingerprint,
        "execution_request_fingerprint": binding.execution_request_fingerprint,
        "execution_intent_fingerprint": binding.intent_fingerprint,
        "confirmation_receipt_id": binding.confirmation_receipt_id,
    }
    if reservation is not None:
        metadata["journal_reservation_fingerprint"] = reservation
    return SimpleNamespace(phase=phase, metadata=metadata, event_fingerprint=_digest(phase))


def _fixture_engine(*, historical=False, drift=None, verified=True):
    # These callbacks only exercise the mode helper and exact binding verifier.
    # Constructor/backend validation is deliberately not impersonated as passed.
    engine = object.__new__(LocalTextTransactionEngine)
    looked_up = []

    def lookup(request, current):
        looked_up.append((request, current))
        if not historical:
            return None
        fields = asdict(request)
        fields.pop("transaction_policy_version")
        context = LocalTextExecutionAuthorizationContext(
            **fields,
            execution_claim_id="claim://mb219/fixture",
            claimed_at="2026-10-04T11:59:00+00:00",
            expires_at="2026-10-04T12:01:00+00:00",
            authority_fingerprint="",
        )
        if drift:
            context = replace(context, **{drift: _digest("foreign")})
        return replace(
            context, authority_fingerprint=build_execution_authority_fingerprint(context)
        )

    engine._historical_claim_lookup = lookup
    engine._historical_claim_verifier = lambda _context, _current: verified
    return engine, looked_up


@pytest.mark.parametrize("historical", [False, True])
def test_staged_apply_requires_verified_exact_historical_claim_for_historical_mode(historical):
    engine, looked_up = _fixture_engine(historical=historical)
    reserved = _event("reserved")
    staged = _event("staged")
    before_metadata = dict(staged.metadata)
    mode = engine._apply_effect_mode([reserved, staged], "operation://mb219/apply", NOW)
    assert mode == ("historical_recovery" if historical else "new_effect")
    request, observed_time = looked_up[0]
    assert request.purpose == "execute" and request.operation == "replace_text"
    assert request.operation_id == "operation://mb219/apply"
    assert request.journal_reservation_fingerprint == reserved.event_fingerprint
    assert request.mutation_receipt_fingerprint is None
    assert observed_time == NOW and staged.metadata == before_metadata


@pytest.mark.parametrize("phase", ["reserved", "desired_durable", "backup_durable"])
def test_unclaimed_apply_phases_cannot_be_misread_as_historical(phase):
    engine, looked_up = _fixture_engine(historical=True)
    mode = engine._apply_effect_mode([_event(phase)], "operation://mb219/apply", NOW)
    assert mode == "new_effect"
    assert looked_up == []


@pytest.mark.parametrize("historical", [False, True])
def test_rollback_reserved_uses_exact_rollback_request_and_mutation_receipt(historical):
    engine, looked_up = _fixture_engine(historical=historical)
    event = _event("rollback_reserved", reservation=_digest("source-mutation-reservation"))
    receipt = SimpleNamespace(receipt_fingerprint=_digest("mutation-receipt"))
    rollback = LocalTextRollbackRequest("operation://mb219/rollback", receipt, _binding())
    mode = engine._rollback_effect_mode([event], rollback, NOW)
    assert mode == ("historical_recovery" if historical else "new_effect")
    request, observed_time = looked_up[0]
    assert request.purpose == "rollback" and request.operation == "rollback_text"
    assert request.operation_id == rollback.rollback_operation_id
    assert request.mutation_receipt_fingerprint == rollback.receipt.receipt_fingerprint
    assert request.journal_reservation_fingerprint == event.event_fingerprint
    assert request.before_content_sha256 == event.metadata["desired_content_sha256"]
    assert request.desired_content_sha256 == event.metadata["before_content_sha256"]
    assert request.execution_grant_id == rollback.execution_binding.execution_grant_id
    assert observed_time == NOW


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
@pytest.mark.parametrize(
    "drift",
    [
        "purpose",
        "operation_id",
        "journal_reservation_fingerprint",
        "resource_ref",
        "mutation_receipt_fingerprint",
    ],
)
def test_resealed_but_foreign_historical_context_never_selects_historical_mode(purpose, drift):
    engine, _looked_up = _fixture_engine(historical=True, drift=drift)
    with pytest.raises(ValueError, match="historical_claim_binding_invalid"):
        if purpose == "apply":
            engine._apply_effect_mode([_event("staged")], "operation://mb219/apply", NOW)
        else:
            rollback = LocalTextRollbackRequest(
                "operation://mb219/rollback",
                SimpleNamespace(receipt_fingerprint=_digest("mutation-receipt")),
                _binding(),
            )
            engine._rollback_effect_mode([_event("rollback_reserved")], rollback, NOW)


def test_unverified_claim_never_selects_historical_mode():
    engine, _looked_up = _fixture_engine(historical=True, verified=False)
    with pytest.raises(ValueError, match="historical_claim_not_verified"):
        engine._apply_effect_mode([_event("staged")], "operation://mb219/apply", NOW)


def test_canonical_first_effect_requires_scope_provider_before_body():
    engine = object.__new__(LocalTextTransactionEngine)
    engine._canonical_physical_effect_scope_provider = None
    with pytest.raises(ValueError, match="effect_scope_provider_not_configured"):
        with engine._new_effect_scope(object()):
            pytest.fail("missing canonical fence must never enter effect body")


def test_scope_provider_denial_is_normalized_without_entering_effect_body():
    engine = object.__new__(LocalTextTransactionEngine)

    @contextmanager
    def denied(_plan):
        raise RuntimeError("private fixture provider diagnostic")
        yield  # pragma: no cover - marks this as a context manager

    engine._canonical_physical_effect_scope_provider = denied
    with pytest.raises(ValueError, match="first_effect_not_authorized") as error:
        with engine._new_effect_scope(object()):
            pytest.fail("denied canonical fence must never enter effect body")
    assert "private fixture" not in str(error.value)


def test_first_effect_scope_is_released_when_claim_or_effect_body_raises():
    engine = object.__new__(LocalTextTransactionEngine)
    plan = object()
    observations = []

    @contextmanager
    def scope(observed_plan):
        assert observed_plan is plan
        observations.append("entered")
        try:
            yield
        finally:
            observations.append("released")

    engine._canonical_physical_effect_scope_provider = scope
    with pytest.raises(RuntimeError, match="fixture interrupted"):
        with engine._new_effect_scope(plan):
            assert observations == ["entered"]
            raise RuntimeError("fixture interrupted")
    assert observations == ["entered", "released"]
