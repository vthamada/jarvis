"""Exact, metadata-only adapter registry and permission grants."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from json import dumps
from re import fullmatch
from unicodedata import is_normalized

from shared.action_confirmation import action_intent_fingerprint, validate_action_intent
from shared.autonomy_ladder import AUTONOMY_ACTION_POLICY_VERSION
from shared.contracts import (
    ActionIntentContract,
    AdapterActionRequestContract,
    AdapterDescriptorContract,
    AdapterGrantClaimContract,
    AdapterGrantContract,
    AdapterRegistrySnapshotContract,
    AutonomyActionPolicyDecisionContract,
)
from shared.types import OperationId, Timestamp

_ID = r"[a-z][a-z0-9_.-]{0,127}"
_REF = r"[^\x00-\x1f\x7f*?]{1,512}"
_RESOURCE_REF = r"[a-z][a-z0-9+.-]{1,31}:[^\x00-\x20\x7f\\*?]{1,479}"
_SHA256 = r"[0-9a-f]{64}"
_NONCE = r"[A-Za-z0-9_-]{16,128}"
_SEMVER = (
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
_AUTHORITY_FIELDS = (
    "execution_allowed",
    "tool_dispatch_allowed",
    "runtime_activation_allowed",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
)
_EXTERNAL_CAPABILITIES = {"core_with_supervised_external_operation"}


def _canonical(value: object) -> str:
    return dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _without(value: object, field: str) -> dict[str, object]:
    payload = asdict(value)  # type: ignore[arg-type]
    payload.pop(field, None)
    return payload


def _parse_time(value: Timestamp | datetime) -> datetime:
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    )
    if parsed.tzinfo is None:
        raise ValueError("timestamp_not_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _now(value: Timestamp | datetime | None) -> datetime:
    return _parse_time(value) if value is not None else datetime.now(timezone.utc)


def _errors(check) -> list[str]:  # type: ignore[no-untyped-def]
    try:
        check()
    except (AttributeError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []


def _require_match(value: str, pattern: str, error: str) -> None:
    if not isinstance(value, str) or fullmatch(pattern, value) is None:
        raise ValueError(error)


def _require_canonical_ref(value: str, *, resource: bool, error: str) -> None:
    pattern = _RESOURCE_REF if resource else _REF
    _require_match(value, pattern, error)
    if value != value.strip() or not is_normalized("NFC", value) or "\\" in value:
        raise ValueError(error)
    payload = value.split(":", 1)[1] if resource else value
    if any(segment in {".", ".."} for segment in payload.split("/")):
        raise ValueError(error)


def _require_metadata_only(value: object) -> None:
    if not getattr(value, "read_only", False) or not getattr(value, "immutable", False):
        raise ValueError("adapter_artifact_not_immutable_metadata")
    if any(getattr(value, field, True) for field in _AUTHORITY_FIELDS):
        raise ValueError("adapter_artifact_authority_flag_true")


def build_adapter_descriptor_fingerprint(descriptor: AdapterDescriptorContract) -> str:
    return _digest(_without(descriptor, "descriptor_fingerprint"))


def build_adapter_registry_fingerprint(registry: AdapterRegistrySnapshotContract) -> str:
    return _digest(_without(registry, "registry_fingerprint"))


def build_adapter_grant_fingerprint(grant: AdapterGrantContract) -> str:
    return _digest(_without(grant, "grant_fingerprint"))


def build_adapter_grant_claim_fingerprint(claim: AdapterGrantClaimContract) -> str:
    return _digest(_without(claim, "claim_fingerprint"))


def build_adapter_descriptor(
    *,
    adapter_id: str,
    adapter_version: str,
    action_kind: str,
    allowed_operations: tuple[str, ...],
    allowed_resource_scopes: tuple[str, ...],
) -> AdapterDescriptorContract:
    descriptor = AdapterDescriptorContract(
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        action_kind=action_kind,
        allowed_operations=tuple(sorted(allowed_operations)),
        allowed_resource_scopes=tuple(sorted(allowed_resource_scopes)),
        descriptor_fingerprint="0" * 64,
    )
    descriptor = replace(
        descriptor,
        descriptor_fingerprint=build_adapter_descriptor_fingerprint(descriptor),
    )
    require_valid_adapter_descriptor(descriptor)
    return descriptor


def validate_adapter_descriptor_fingerprint(descriptor: AdapterDescriptorContract) -> bool:
    return bool(fullmatch(_SHA256, descriptor.descriptor_fingerprint)) and compare_digest(
        descriptor.descriptor_fingerprint,
        build_adapter_descriptor_fingerprint(descriptor),
    )


def validate_adapter_descriptor(descriptor: AdapterDescriptorContract) -> list[str]:
    return _errors(lambda: require_valid_adapter_descriptor(descriptor))


def require_valid_adapter_descriptor(descriptor: AdapterDescriptorContract) -> None:
    _require_match(descriptor.adapter_id, _ID, "adapter_id_invalid")
    _require_match(descriptor.adapter_version, _SEMVER, "adapter_version_invalid")
    _require_match(descriptor.action_kind, _ID, "adapter_action_kind_invalid")
    if descriptor.action_kind != "prepare_external_action":
        raise ValueError("adapter_action_kind_not_prepare_only")
    if not descriptor.allowed_operations or len(set(descriptor.allowed_operations)) != len(
        descriptor.allowed_operations
    ):
        raise ValueError("adapter_operations_empty_or_duplicate")
    if not descriptor.allowed_resource_scopes or len(
        set(descriptor.allowed_resource_scopes)
    ) != len(descriptor.allowed_resource_scopes):
        raise ValueError("adapter_scopes_empty_or_duplicate")
    for value in (*descriptor.allowed_operations, *descriptor.allowed_resource_scopes):
        _require_match(value, _ID, "adapter_allowlist_value_invalid")
    if any(
        "*" in value
        for value in (*descriptor.allowed_operations, *descriptor.allowed_resource_scopes)
    ):
        raise ValueError("adapter_wildcard_forbidden")
    if not descriptor.prepare_only or descriptor.executor_ref is not None:
        raise ValueError("adapter_executor_forbidden")
    _require_metadata_only(descriptor)
    if not validate_adapter_descriptor_fingerprint(descriptor):
        raise ValueError("descriptor_fingerprint_invalid")


def build_adapter_registry_snapshot(
    *, registry_id: str, registry_version: str, descriptors: tuple[AdapterDescriptorContract, ...]
) -> AdapterRegistrySnapshotContract:
    ordered = tuple(sorted(descriptors, key=lambda item: (item.adapter_id, item.adapter_version)))
    registry = AdapterRegistrySnapshotContract(
        registry_id=registry_id,
        registry_version=registry_version,
        descriptors=ordered,
        registry_fingerprint="0" * 64,
    )
    registry = replace(registry, registry_fingerprint=build_adapter_registry_fingerprint(registry))
    require_valid_adapter_registry_snapshot(registry)
    return registry


def validate_adapter_registry_fingerprint(registry: AdapterRegistrySnapshotContract) -> bool:
    return bool(fullmatch(_SHA256, registry.registry_fingerprint)) and compare_digest(
        registry.registry_fingerprint,
        build_adapter_registry_fingerprint(registry),
    )


def validate_adapter_registry_snapshot(registry: AdapterRegistrySnapshotContract) -> list[str]:
    return _errors(lambda: require_valid_adapter_registry_snapshot(registry))


def require_valid_adapter_registry_snapshot(registry: AdapterRegistrySnapshotContract) -> None:
    _require_match(registry.registry_id, _ID, "adapter_registry_id_invalid")
    _require_match(registry.registry_version, _SEMVER, "adapter_registry_version_invalid")
    keys = [(item.adapter_id, item.adapter_version) for item in registry.descriptors]
    if len(keys) != len(set(keys)):
        raise ValueError("adapter_registry_duplicate_key")
    if keys != sorted(keys):
        raise ValueError("adapter_registry_order_not_canonical")
    for descriptor in registry.descriptors:
        require_valid_adapter_descriptor(descriptor)
    _require_metadata_only(registry)
    if not validate_adapter_registry_fingerprint(registry):
        raise ValueError("registry_fingerprint_invalid")


def resolve_adapter_descriptor(
    registry: AdapterRegistrySnapshotContract, *, adapter_id: str, adapter_version: str
) -> AdapterDescriptorContract | None:
    if validate_adapter_registry_snapshot(registry):
        return None
    return next(
        (
            item
            for item in registry.descriptors
            if item.adapter_id == adapter_id and item.adapter_version == adapter_version
        ),
        None,
    )


def _require_request(
    descriptor: AdapterDescriptorContract, request: AdapterActionRequestContract
) -> None:
    for value, error in (
        (request.adapter_id, "adapter_id_invalid"),
        (request.action_kind, "adapter_action_kind_invalid"),
        (request.operation, "adapter_operation_invalid"),
        (request.resource_scope, "adapter_resource_scope_invalid"),
    ):
        _require_match(value, _ID, error)
    _require_match(request.adapter_version, _SEMVER, "adapter_version_invalid")
    _require_canonical_ref(
        request.resource_ref, resource=True, error="adapter_resource_ref_invalid"
    )
    if (request.adapter_id, request.adapter_version, request.action_kind) != (
        descriptor.adapter_id,
        descriptor.adapter_version,
        descriptor.action_kind,
    ):
        raise ValueError("adapter_descriptor_request_mismatch")
    if request.operation not in descriptor.allowed_operations:
        raise ValueError("adapter_operation_not_allowlisted")
    if request.resource_scope not in descriptor.allowed_resource_scopes:
        raise ValueError("adapter_scope_not_allowlisted")


def validate_adapter_action_request(
    request: AdapterActionRequestContract, *, descriptor: AdapterDescriptorContract
) -> list[str]:
    return _errors(lambda: require_valid_adapter_action_request(request, descriptor=descriptor))


def require_valid_adapter_action_request(
    request: AdapterActionRequestContract, *, descriptor: AdapterDescriptorContract
) -> None:
    require_valid_adapter_descriptor(descriptor)
    _require_request(descriptor, request)


def autonomy_policy_decision_fingerprint(decision: AutonomyActionPolicyDecisionContract) -> str:
    return _digest(asdict(decision))


def build_adapter_grant(
    *,
    grant_id: str,
    subject_ref: str,
    request: AdapterActionRequestContract,
    descriptor: AdapterDescriptorContract,
    registry: AdapterRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    policy_version: str,
    nonce: str,
    issued_at: Timestamp,
    expires_at: Timestamp,
    now: Timestamp | datetime | None = None,
) -> AdapterGrantContract:
    grant = AdapterGrantContract(
        grant_id=grant_id,
        subject_ref=subject_ref,
        adapter_request=request,
        descriptor_fingerprint=descriptor.descriptor_fingerprint,
        registry_fingerprint=registry.registry_fingerprint,
        intent_id=intent.intent_id,
        intent_fingerprint=intent_fingerprint,
        action_fingerprint=intent.action_fingerprint,
        autonomy_policy_decision_fingerprint=autonomy_policy_decision_fingerprint(
            autonomy_decision
        ),
        policy_version=policy_version,
        nonce=nonce,
        confirmation_required=autonomy_decision.confirmation_required,
        issued_at=issued_at,
        expires_at=expires_at,
        grant_fingerprint="0" * 64,
    )
    grant = replace(grant, grant_fingerprint=build_adapter_grant_fingerprint(grant))
    require_valid_adapter_grant(
        grant,
        descriptor=descriptor,
        registry=registry,
        intent=intent,
        intent_fingerprint=intent_fingerprint,
        autonomy_decision=autonomy_decision,
        now=now,
    )
    return grant


def validate_adapter_grant_fingerprint(grant: AdapterGrantContract) -> bool:
    return bool(fullmatch(_SHA256, grant.grant_fingerprint)) and compare_digest(
        grant.grant_fingerprint, build_adapter_grant_fingerprint(grant)
    )


def validate_adapter_grant(
    grant: AdapterGrantContract,
    *,
    descriptor: AdapterDescriptorContract,
    registry: AdapterRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    now: Timestamp | datetime | None = None,
) -> list[str]:
    return _errors(
        lambda: require_valid_adapter_grant(
            grant,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            now=now,
        )
    )


def require_valid_adapter_grant(
    grant: AdapterGrantContract,
    *,
    descriptor: AdapterDescriptorContract,
    registry: AdapterRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    now: Timestamp | datetime | None = None,
) -> None:
    _require_canonical_ref(grant.grant_id, resource=False, error="adapter_grant_id_invalid")
    _require_canonical_ref(grant.subject_ref, resource=False, error="adapter_subject_ref_invalid")
    require_valid_adapter_registry_snapshot(registry)
    resolved = resolve_adapter_descriptor(
        registry,
        adapter_id=grant.adapter_request.adapter_id,
        adapter_version=grant.adapter_request.adapter_version,
    )
    if resolved is None or resolved != descriptor:
        raise ValueError("adapter_descriptor_not_in_registry")
    _require_request(descriptor, grant.adapter_request)
    if grant.descriptor_fingerprint != descriptor.descriptor_fingerprint:
        raise ValueError("adapter_descriptor_fingerprint_drift")
    if grant.registry_fingerprint != registry.registry_fingerprint:
        raise ValueError("adapter_registry_fingerprint_drift")
    if validate_action_intent(intent, now=now):
        raise ValueError("adapter_intent_invalid")
    if not compare_digest(action_intent_fingerprint(intent), intent_fingerprint):
        raise ValueError("adapter_intent_fingerprint_invalid")
    if (grant.intent_id, grant.intent_fingerprint, grant.action_fingerprint) != (
        intent.intent_id,
        intent_fingerprint,
        intent.action_fingerprint,
    ):
        raise ValueError("adapter_intent_binding_drift")
    if intent.operation != grant.adapter_request.operation:
        raise ValueError("adapter_operation_intent_mismatch")
    if grant.subject_ref != intent.operator_identity_ref:
        raise ValueError("adapter_subject_intent_mismatch")
    if grant.adapter_request.resource_ref != intent.target_ref:
        raise ValueError("adapter_resource_intent_mismatch")
    if intent.handler_id != f"adapter://{grant.adapter_request.adapter_id}":
        raise ValueError("adapter_handler_intent_mismatch")
    if intent.handler_version != grant.adapter_request.adapter_version:
        raise ValueError("adapter_handler_version_intent_mismatch")
    if grant.autonomy_policy_decision_fingerprint != autonomy_policy_decision_fingerprint(
        autonomy_decision
    ):
        raise ValueError("adapter_autonomy_decision_drift")
    if not (
        intent.policy_version
        == grant.policy_version
        == autonomy_decision.policy_version
        == AUTONOMY_ACTION_POLICY_VERSION
    ):
        raise ValueError("adapter_policy_version_invalid")
    _require_match(grant.nonce, _NONCE, "adapter_grant_nonce_invalid")
    if autonomy_decision.action_kind != grant.adapter_request.action_kind:
        raise ValueError("adapter_autonomy_action_mismatch")
    _require_metadata_only(autonomy_decision)
    if autonomy_decision.autonomy_ladder_status not in {"within_limit", "downgraded_to_max"}:
        raise ValueError("adapter_autonomy_ladder_invalid")
    expected_decision_projection = {
        "allow": (False, "not_required", ("autonomy_action_policy_satisfied",)),
        "require_confirmation": (
            True,
            "explicit_confirmation_required",
            ("exact_confirmation_required",),
        ),
    }
    if autonomy_decision.decision not in expected_decision_projection:
        raise ValueError("adapter_autonomy_decision_blocked")
    expected_confirmation, expected_requirement, expected_reasons = expected_decision_projection[
        autonomy_decision.decision
    ]
    if (
        autonomy_decision.confirmation_required != expected_confirmation
        or autonomy_decision.confirmation_requirement != expected_requirement
        or autonomy_decision.reason_codes != expected_reasons
    ):
        raise ValueError("adapter_autonomy_decision_inconsistent")
    if (
        autonomy_decision.side_effect_allowed
        or autonomy_decision.confirmation_evidence_state != "absent"
    ):
        raise ValueError("adapter_autonomy_decision_forged_authority")
    if (
        autonomy_decision.selected_capability_mode not in _EXTERNAL_CAPABILITIES
        or autonomy_decision.max_capability_mode not in _EXTERNAL_CAPABILITIES
    ):
        raise ValueError("adapter_autonomy_capability_insufficient")
    if grant.confirmation_required != autonomy_decision.confirmation_required:
        raise ValueError("adapter_confirmation_requirement_drift")
    issued, expires, intent_expires, current = (
        _parse_time(grant.issued_at),
        _parse_time(grant.expires_at),
        _parse_time(intent.expires_at),
        _now(now),
    )
    if issued >= expires:
        raise ValueError("adapter_grant_window_invalid")
    if expires > intent_expires:
        raise ValueError("adapter_grant_exceeds_intent_expiry")
    if current < issued:
        raise ValueError("adapter_grant_not_yet_valid")
    if current >= expires:
        raise ValueError("adapter_grant_expired")
    if not grant.single_use:
        raise ValueError("adapter_grant_not_single_use")
    _require_metadata_only(grant)
    if not validate_adapter_grant_fingerprint(grant):
        raise ValueError("adapter_grant_fingerprint_invalid")


def build_adapter_grant_claim(
    *,
    claim_id: str,
    operation_id: OperationId | str,
    grant: AdapterGrantContract,
    claimed_at: Timestamp,
    confirmation_receipt_id: str | None = None,
    confirmation_claim_id: str | None = None,
    confirmation_claim_fingerprint: str | None = None,
) -> AdapterGrantClaimContract:
    claim = AdapterGrantClaimContract(
        claim_id=claim_id,
        grant_id=grant.grant_id,
        grant_fingerprint=grant.grant_fingerprint,
        operation_id=OperationId(str(operation_id)),
        subject_ref=grant.subject_ref,
        adapter_request=grant.adapter_request,
        intent_id=grant.intent_id,
        intent_fingerprint=grant.intent_fingerprint,
        action_fingerprint=grant.action_fingerprint,
        claimed_at=claimed_at,
        expires_at=grant.expires_at,
        confirmation_receipt_id=confirmation_receipt_id,
        confirmation_claim_id=confirmation_claim_id,
        confirmation_claim_fingerprint=confirmation_claim_fingerprint,
        claim_fingerprint="0" * 64,
    )
    claim = replace(claim, claim_fingerprint=build_adapter_grant_claim_fingerprint(claim))
    require_valid_adapter_grant_claim(claim, grant=grant, now=claimed_at)
    return claim


def validate_adapter_grant_claim_fingerprint(claim: AdapterGrantClaimContract) -> bool:
    return bool(fullmatch(_SHA256, claim.claim_fingerprint)) and compare_digest(
        claim.claim_fingerprint, build_adapter_grant_claim_fingerprint(claim)
    )


def validate_adapter_grant_claim(
    claim: AdapterGrantClaimContract,
    *,
    grant: AdapterGrantContract,
    now: Timestamp | datetime | None = None,
) -> list[str]:
    return _errors(lambda: require_valid_adapter_grant_claim(claim, grant=grant, now=now))


def require_valid_adapter_grant_claim(
    claim: AdapterGrantClaimContract,
    *,
    grant: AdapterGrantContract,
    now: Timestamp | datetime | None = None,
) -> None:
    _require_canonical_ref(
        str(claim.operation_id), resource=False, error="adapter_claim_operation_id_invalid"
    )
    expected = (
        grant.grant_id,
        grant.grant_fingerprint,
        grant.subject_ref,
        grant.adapter_request,
        grant.intent_id,
        grant.intent_fingerprint,
        grant.action_fingerprint,
        grant.expires_at,
    )
    observed = (
        claim.grant_id,
        claim.grant_fingerprint,
        claim.subject_ref,
        claim.adapter_request,
        claim.intent_id,
        claim.intent_fingerprint,
        claim.action_fingerprint,
        claim.expires_at,
    )
    if observed != expected:
        raise ValueError("adapter_claim_binding_drift")
    claimed, expires, current = (
        _parse_time(claim.claimed_at),
        _parse_time(claim.expires_at),
        _now(now),
    )
    if claimed < _parse_time(grant.issued_at) or claimed >= expires:
        raise ValueError("adapter_claim_time_invalid")
    if current < claimed:
        raise ValueError("adapter_claim_not_yet_valid")
    if current >= expires:
        raise ValueError("adapter_claim_expired")
    evidence = (
        claim.confirmation_receipt_id,
        claim.confirmation_claim_id,
        claim.confirmation_claim_fingerprint,
    )
    if grant.confirmation_required and any(value is None for value in evidence):
        raise ValueError("adapter_confirmation_evidence_missing")
    if not grant.confirmation_required and any(value is not None for value in evidence):
        raise ValueError("adapter_confirmation_evidence_unexpected")
    if claim.confirmation_claim_fingerprint is not None:
        _require_match(
            claim.confirmation_claim_fingerprint,
            _SHA256,
            "adapter_confirmation_claim_fingerprint_invalid",
        )
    if not claim.single_use:
        raise ValueError("adapter_claim_not_single_use")
    _require_metadata_only(claim)
    if not validate_adapter_grant_claim_fingerprint(claim):
        raise ValueError("adapter_claim_fingerprint_invalid")


LOCAL_TEXT_FILE_DESCRIPTOR = build_adapter_descriptor(
    adapter_id="local_text_file",
    adapter_version="1.0.0",
    action_kind="prepare_external_action",
    allowed_operations=("create_text", "replace_text"),
    allowed_resource_scopes=("configured_text_root",),
)

SEEDED_ADAPTER_REGISTRY = build_adapter_registry_snapshot(
    registry_id="jarvis.adapter_registry",
    registry_version="1.0.0",
    descriptors=(LOCAL_TEXT_FILE_DESCRIPTOR,),
)
