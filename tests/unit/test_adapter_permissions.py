from dataclasses import replace

import pytest

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.adapter_permissions import (
    LOCAL_TEXT_FILE_DESCRIPTOR,
    SEEDED_ADAPTER_REGISTRY,
    build_adapter_descriptor,
    build_adapter_grant,
    build_adapter_grant_claim,
    build_adapter_grant_claim_fingerprint,
    build_adapter_registry_snapshot,
    resolve_adapter_descriptor,
    validate_adapter_descriptor,
    validate_adapter_descriptor_fingerprint,
    validate_adapter_grant,
    validate_adapter_grant_claim,
    validate_adapter_grant_claim_fingerprint,
    validate_adapter_grant_fingerprint,
)
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import AdapterActionRequestContract
from shared.types import RiskLevel, Timestamp

NOW = Timestamp("2026-08-29T12:00:00Z")
LATER = Timestamp("2026-08-29T12:10:00Z")
INTENT_EXPIRY = Timestamp("2026-08-29T12:20:00Z")


def _request(**changes: str) -> AdapterActionRequestContract:
    values = {
        "adapter_id": "local_text_file",
        "adapter_version": "1.0.0",
        "action_kind": "prepare_external_action",
        "operation": "create_text",
        "resource_scope": "configured_text_root",
        "resource_ref": "text:notes/example.txt",
    }
    values.update(changes)
    return AdapterActionRequestContract(**values)


def _intent(**overrides):  # type: ignore[no-untyped-def]
    values = {
        "intent_id": "intent-adapter-1",
        "origin_request_id": "req-adapter-1",
        "session_id": "session-adapter-1",
        "mission_id": None,
        "operator_identity_ref": "operator-local",
        "handler_id": "adapter://local_text_file",
        "handler_version": "1.0.0",
        "operation": "create_text",
        "target_ref": "text:notes/example.txt",
        "content_digest": "a" * 64,
        "precondition_digest": "b" * 64,
        "risk_level": RiskLevel.MODERATE,
        "policy_version": AUTONOMY_ACTION_POLICY_VERSION,
        "nonce": "adapterIntentNonce123",
        "issued_at": NOW,
        "expires_at": INTENT_EXPIRY,
        "now": NOW,
    }
    values.update(overrides)
    return build_action_intent(**values)


def _decision():  # type: ignore[no-untyped-def]
    policy = AUTONOMY_LEVEL_POLICIES["supervised_external_action"]
    return evaluate_autonomy_action(
        requested_autonomy_level="supervised_external_action",
        max_autonomy_level="supervised_external_action",
        effective_autonomy_level="supervised_external_action",
        autonomy_ladder_status="within_limit",
        action_kind="prepare_external_action",
        selected_capability_mode="core_with_supervised_external_operation",
        max_capability_mode="core_with_supervised_external_operation",
        allowed_runtime_actions=policy["allowed_runtime_actions"],
        blocked_runtime_actions=policy["blocked_runtime_actions"],
        human_confirmation_required=True,
        human_confirmation_mode="explicit_confirmation_required",
        confirmation_evidence_state="absent",
    )


def _grant(**overrides):  # type: ignore[no-untyped-def]
    intent = _intent()
    values = {
        "grant_id": "grant-adapter-1",
        "subject_ref": "operator-local",
        "request": _request(),
        "descriptor": LOCAL_TEXT_FILE_DESCRIPTOR,
        "registry": SEEDED_ADAPTER_REGISTRY,
        "intent": intent,
        "intent_fingerprint": action_intent_fingerprint(intent),
        "autonomy_decision": _decision(),
        "policy_version": AUTONOMY_ACTION_POLICY_VERSION,
        "nonce": "adapterGrantNonce123",
        "issued_at": NOW,
        "expires_at": LATER,
        "now": NOW,
    }
    values.update(overrides)
    return build_adapter_grant(**values)


def test_seed_is_exact_prepare_only_metadata() -> None:
    descriptor = LOCAL_TEXT_FILE_DESCRIPTOR
    assert descriptor.allowed_operations == ("create_text", "replace_text")
    assert descriptor.allowed_resource_scopes == ("configured_text_root",)
    assert descriptor.action_kind == "prepare_external_action"
    assert descriptor.prepare_only is True and descriptor.executor_ref is None
    assert validate_adapter_descriptor(descriptor) == []
    assert validate_adapter_descriptor_fingerprint(descriptor)
    assert not any(
        (
            descriptor.execution_allowed,
            descriptor.tool_dispatch_allowed,
            descriptor.runtime_activation_allowed,
            descriptor.promotion_authorized,
            descriptor.automatic_promotion_allowed,
            descriptor.core_mutation_allowed,
        )
    )


def test_resolution_is_exact_without_wildcard_prefix_or_fallback() -> None:
    assert (
        resolve_adapter_descriptor(
            SEEDED_ADAPTER_REGISTRY,
            adapter_id="local_text_file",
            adapter_version="1.0.0",
        )
        == LOCAL_TEXT_FILE_DESCRIPTOR
    )
    for adapter_id, version in (
        ("local_text", "1.0.0"),
        ("local_text_file.extra", "1.0.0"),
        ("local_text_file", "1.0"),
        ("*", "1.0.0"),
    ):
        assert (
            resolve_adapter_descriptor(
                SEEDED_ADAPTER_REGISTRY,
                adapter_id=adapter_id,
                adapter_version=version,
            )
            is None
        )


@pytest.mark.parametrize("version", ["1", "1.0", "01.0.0", "1.00.0", "v1.0.0", "1.0.0-"])
def test_noncanonical_semver_is_rejected(version: str) -> None:
    descriptor = replace(LOCAL_TEXT_FILE_DESCRIPTOR, adapter_version=version)
    assert validate_adapter_descriptor(descriptor) == ["adapter_version_invalid"]


def test_registry_rejects_duplicate_key_and_is_order_stable() -> None:
    duplicate = replace(LOCAL_TEXT_FILE_DESCRIPTOR, descriptor_fingerprint="0" * 64)
    with pytest.raises(ValueError, match="adapter_registry_duplicate_key"):
        build_adapter_registry_snapshot(
            registry_id="registry.test",
            registry_version="1.0.0",
            descriptors=(LOCAL_TEXT_FILE_DESCRIPTOR, duplicate),
        )
    second = build_adapter_descriptor(
        adapter_id="z_adapter",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        allowed_operations=("create_text",),
        allowed_resource_scopes=("configured_text_root",),
    )
    left = build_adapter_registry_snapshot(
        registry_id="registry.test",
        registry_version="1.0.0",
        descriptors=(second, LOCAL_TEXT_FILE_DESCRIPTOR),
    )
    right = build_adapter_registry_snapshot(
        registry_id="registry.test",
        registry_version="1.0.0",
        descriptors=(LOCAL_TEXT_FILE_DESCRIPTOR, second),
    )
    assert left == right
    assert left.registry_fingerprint == right.registry_fingerprint


@pytest.mark.parametrize(
    "resource_ref",
    [
        " text:notes/a.txt",
        "text:notes/a.txt ",
        "text:notes/../a.txt",
        "text:notes\\a.txt",
        "text:notes/*.txt",
        "notes/a.txt",
        "text:note\N{COMBINING ACUTE ACCENT}.txt",
    ],
)
def test_resource_refs_must_be_canonical(resource_ref: str) -> None:
    with pytest.raises(ValueError, match="adapter_resource_ref_invalid"):
        _grant(request=_request(resource_ref=resource_ref))


def test_real_autonomy_decision_builds_exact_expiring_grant() -> None:
    grant = _grant()
    intent = _intent()
    assert grant.confirmation_required is True
    assert grant.policy_version == AUTONOMY_ACTION_POLICY_VERSION
    assert validate_adapter_grant_fingerprint(grant)
    assert (
        validate_adapter_grant(
            grant,
            descriptor=LOCAL_TEXT_FILE_DESCRIPTOR,
            registry=SEEDED_ADAPTER_REGISTRY,
            intent=intent,
            intent_fingerprint=action_intent_fingerprint(intent),
            autonomy_decision=_decision(),
            now=NOW,
        )
        == []
    )


def test_canonical_allow_without_confirmation_is_also_metadata_only() -> None:
    decision = replace(
        _decision(),
        decision="allow",
        confirmation_required=False,
        confirmation_requirement="not_required",
        reason_codes=("autonomy_action_policy_satisfied",),
    )
    grant = _grant(autonomy_decision=decision)
    claim = build_adapter_grant_claim(
        claim_id="claim-adapter-allow",
        operation_id="operation-adapter-allow",
        grant=grant,
        claimed_at=NOW,
    )
    assert grant.confirmation_required is False
    assert validate_adapter_grant_claim(claim, grant=grant, now=NOW) == []
    assert claim.execution_allowed is False


@pytest.mark.parametrize(
    ("intent_change", "error"),
    [
        ({"operator_identity_ref": "other-operator"}, "adapter_subject_intent_mismatch"),
        ({"target_ref": "text:notes/other.txt"}, "adapter_resource_intent_mismatch"),
        ({"handler_id": "adapter://other_adapter"}, "adapter_handler_intent_mismatch"),
        ({"handler_version": "1.0.1"}, "adapter_handler_version_intent_mismatch"),
        ({"policy_version": "autonomy-action-policy/v2"}, "adapter_policy_version_invalid"),
    ],
)
def test_intent_identity_drift_is_rejected_individually(
    intent_change: dict[str, object], error: str
) -> None:
    intent = _intent(**intent_change)
    with pytest.raises(ValueError, match=error):
        _grant(
            intent=intent,
            intent_fingerprint=action_intent_fingerprint(intent),
        )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("subject_ref", "other-subject", "adapter_subject_intent_mismatch"),
        ("descriptor_fingerprint", "c" * 64, "adapter_descriptor_fingerprint_drift"),
        ("registry_fingerprint", "c" * 64, "adapter_registry_fingerprint_drift"),
        ("intent_id", "other-intent", "adapter_intent_binding_drift"),
        ("action_fingerprint", "c" * 64, "adapter_intent_binding_drift"),
        ("nonce", "otherNonceValue123", "adapter_grant_fingerprint_invalid"),
        ("execution_allowed", True, "adapter_artifact_authority_flag_true"),
    ],
)
def test_grant_field_drift_and_authority_flags_fail_closed(
    field: str, value: object, error: str
) -> None:
    grant = replace(_grant(), **{field: value})
    intent = _intent()
    assert validate_adapter_grant(
        grant,
        descriptor=LOCAL_TEXT_FILE_DESCRIPTOR,
        registry=SEEDED_ADAPTER_REGISTRY,
        intent=intent,
        intent_fingerprint=action_intent_fingerprint(intent),
        autonomy_decision=_decision(),
        now=NOW,
    ) == [error]


def test_expired_not_yet_valid_and_intent_exceeding_grants_are_rejected() -> None:
    with pytest.raises(ValueError, match="adapter_grant_not_yet_valid"):
        _grant(issued_at="2026-08-29T12:01:00Z")
    with pytest.raises(ValueError, match="adapter_grant_expired"):
        _grant(
            issued_at="2026-08-29T11:50:00Z",
            expires_at="2026-08-29T11:59:00Z",
        )
    with pytest.raises(ValueError, match="adapter_grant_exceeds_intent_expiry"):
        _grant(expires_at="2026-08-29T12:21:00Z")


def test_forged_or_under_capable_autonomy_decision_is_blocked() -> None:
    decision = _decision()
    with pytest.raises(ValueError, match="adapter_autonomy_capability_insufficient"):
        _grant(
            autonomy_decision=replace(
                decision,
                selected_capability_mode="core_with_local_operation",
            )
        )
    with pytest.raises(ValueError, match="adapter_autonomy_decision_forged_authority"):
        _grant(autonomy_decision=replace(decision, side_effect_allowed=True))
    with pytest.raises(ValueError, match="adapter_artifact_authority_flag_true"):
        _grant(autonomy_decision=replace(decision, execution_allowed=True))


def test_claim_is_exact_single_use_and_confirmation_is_evidence_only() -> None:
    grant = _grant()
    claim = build_adapter_grant_claim(
        claim_id="claim-adapter-1",
        operation_id="operation-adapter-1",
        grant=grant,
        claimed_at=NOW,
        confirmation_receipt_id="receipt-1",
        confirmation_claim_id="confirmation-claim-1",
        confirmation_claim_fingerprint="d" * 64,
    )
    assert validate_adapter_grant_claim(claim, grant=grant, now=NOW) == []
    assert validate_adapter_grant_claim_fingerprint(claim)
    assert claim.execution_allowed is False and claim.tool_dispatch_allowed is False
    tampered = replace(claim, operation_id="operation-adapter-2")
    assert build_adapter_grant_claim_fingerprint(tampered) != claim.claim_fingerprint
    assert validate_adapter_grant_claim(tampered, grant=grant, now=NOW) == [
        "adapter_claim_fingerprint_invalid"
    ]
    assert validate_adapter_grant_claim(replace(claim, single_use=False), grant=grant, now=NOW) == [
        "adapter_claim_not_single_use"
    ]


def test_confirmation_evidence_is_required_but_never_expands_authority() -> None:
    grant = _grant()
    with pytest.raises(ValueError, match="adapter_confirmation_evidence_missing"):
        build_adapter_grant_claim(
            claim_id="claim-adapter-1",
            operation_id="operation-adapter-1",
            grant=grant,
            claimed_at=NOW,
        )
