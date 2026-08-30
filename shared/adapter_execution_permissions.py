"""Exact execution-only adapter registry, grants, and claim evidence."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from json import dumps
from re import fullmatch
from unicodedata import is_normalized

from shared.action_confirmation import action_intent_fingerprint, validate_action_intent
from shared.adapter_permissions import (
    LOCAL_TEXT_FILE_DESCRIPTOR,
    autonomy_policy_decision_fingerprint,
    require_valid_adapter_action_request,
)
from shared.autonomy_ladder import AUTONOMY_ACTION_POLICY_VERSION
from shared.contracts import (
    ActionIntentContract,
    AdapterExecutionDescriptorContract,
    AdapterExecutionGrantClaimContract,
    AdapterExecutionGrantContract,
    AdapterExecutionRegistrySnapshotContract,
    AdapterExecutionRequestContract,
    AutonomyActionPolicyDecisionContract,
    LocalTextFilePreflightAttestationContract,
    LocalTextFilePreflightContract,
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
_EMPTY_SHA256 = sha256(b"").hexdigest()

LOCAL_TEXT_FILE_EXECUTION_POLICY_VERSION = "local-text-file-execution-policy/v1"
LOCAL_TEXT_FILE_EXECUTION_BACKEND_VERSION = "local-text-transactional-writer/v1"
LOCAL_TEXT_FILE_EXECUTION_ADAPTER_VERSION = "2.0.0"
LOCAL_TEXT_FILE_EXECUTION_MAX_TTL_SECONDS = 120
LOCAL_TEXT_FILE_PREFLIGHT_POLICY_VERSION = "1.0.0"
LOCAL_TEXT_FILE_PREFLIGHT_BACKEND_VERSION = "1.0.0"
LOCAL_TEXT_FILE_PREFLIGHT_TRUSTED_BOUNDARY_REF = (
    "operational-service://local-text-file-preflight/v1"
)


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


def _require_sha256(value: str, error: str) -> None:
    _require_match(value, _SHA256, error)


def _require_canonical_ref(value: str, *, resource: bool, error: str) -> None:
    _require_match(value, _RESOURCE_REF if resource else _REF, error)
    if value != value.strip() or not is_normalized("NFC", value) or "\\" in value:
        raise ValueError(error)
    payload = value.split(":", 1)[1] if resource else value
    if any(segment in {".", ".."} for segment in payload.split("/")):
        raise ValueError(error)


def _require_metadata_only(value: object) -> None:
    if not getattr(value, "read_only", False) or not getattr(value, "immutable", False):
        raise ValueError("adapter_execution_artifact_not_immutable_metadata")
    if any(getattr(value, field, True) for field in _AUTHORITY_FIELDS):
        raise ValueError("adapter_execution_artifact_authority_flag_true")


def build_adapter_execution_descriptor_fingerprint(
    descriptor: AdapterExecutionDescriptorContract,
) -> str:
    return _digest(_without(descriptor, "descriptor_fingerprint"))


def build_adapter_execution_registry_fingerprint(
    registry: AdapterExecutionRegistrySnapshotContract,
) -> str:
    return _digest(_without(registry, "registry_fingerprint"))


def build_adapter_execution_request_fingerprint(
    request: AdapterExecutionRequestContract,
) -> str:
    return _digest(_without(request, "execution_request_fingerprint"))


def build_adapter_execution_grant_fingerprint(grant: AdapterExecutionGrantContract) -> str:
    return _digest(_without(grant, "grant_fingerprint"))


def build_adapter_execution_grant_claim_fingerprint(
    claim: AdapterExecutionGrantClaimContract,
) -> str:
    return _digest(_without(claim, "claim_fingerprint"))


def build_local_text_file_preflight_attestation_fingerprint(
    attestation: LocalTextFilePreflightAttestationContract,
) -> str:
    return _digest(_without(attestation, "attestation_fingerprint"))


def _build_preflight_fingerprint(preflight: LocalTextFilePreflightContract) -> str:
    return _digest(
        {
            key: value
            for key, value in asdict(preflight).items()
            if key not in {"preflight_fingerprint", "unified_diff"}
        }
    )


def _build_rollback_fingerprint(preflight: LocalTextFilePreflightContract) -> str:
    return _digest(_without(preflight.rollback_plan, "rollback_fingerprint"))


def build_local_text_file_preflight_attestation(
    preflight: LocalTextFilePreflightContract,
    *,
    attestation_id: str,
    attestation_nonce: str,
    attested_at: Timestamp | datetime,
) -> LocalTextFilePreflightAttestationContract:
    _require_preflight_source(preflight, requested_at=attested_at)
    attestation = LocalTextFilePreflightAttestationContract(
        attestation_id=attestation_id,
        attestation_nonce=attestation_nonce,
        trusted_boundary_ref=LOCAL_TEXT_FILE_PREFLIGHT_TRUSTED_BOUNDARY_REF,
        subject_ref=preflight.subject_ref,
        operation=preflight.operation,
        resource_scope=preflight.adapter_request.resource_scope,
        resource_ref=preflight.resource_ref,
        source_preflight_grant_id=preflight.grant_id,
        source_preflight_grant_fingerprint=preflight.grant_fingerprint,
        source_action_fingerprint=preflight.action_fingerprint,
        source_intent_fingerprint=preflight.intent_fingerprint,
        source_descriptor_fingerprint=preflight.descriptor_fingerprint,
        source_registry_fingerprint=preflight.registry_fingerprint,
        preflight_fingerprint=preflight.preflight_fingerprint,
        preflight_prepared_at=preflight.prepared_at,
        preflight_expires_at=preflight.expires_at,
        preflight_authorization_expires_at=preflight.authorization_expires_at,
        root_config_fingerprint=preflight.root_config_fingerprint,
        filesystem_snapshot_fingerprint=preflight.filesystem_snapshot_fingerprint,
        rollback_fingerprint=preflight.rollback_plan.rollback_fingerprint,
        before_exists=preflight.before_exists,
        expected_current_sha256=preflight.expected_current_sha256,
        before_content_sha256=preflight.before_content_sha256,
        desired_content_sha256=preflight.desired_content_sha256,
        preflight_policy_version=preflight.preflight_policy_version,
        preflight_backend_version=preflight.adapter_backend_version,
        attested_at=_parse_time(attested_at).isoformat().replace("+00:00", "Z"),
        attestation_fingerprint="0" * 64,
    )
    attestation = replace(
        attestation,
        attestation_fingerprint=(
            build_local_text_file_preflight_attestation_fingerprint(attestation)
        ),
    )
    require_valid_local_text_file_preflight_attestation(attestation)
    return attestation


def validate_local_text_file_preflight_attestation_fingerprint(
    attestation: LocalTextFilePreflightAttestationContract,
) -> bool:
    return bool(fullmatch(_SHA256, attestation.attestation_fingerprint)) and compare_digest(
        attestation.attestation_fingerprint,
        build_local_text_file_preflight_attestation_fingerprint(attestation),
    )


def validate_local_text_file_preflight_attestation(
    attestation: LocalTextFilePreflightAttestationContract,
    *,
    now: Timestamp | datetime | None = None,
) -> list[str]:
    return _errors(
        lambda: require_valid_local_text_file_preflight_attestation(
            attestation,
            now=now,
        )
    )


def require_valid_local_text_file_preflight_attestation(
    attestation: LocalTextFilePreflightAttestationContract,
    *,
    now: Timestamp | datetime | None = None,
) -> None:
    if not isinstance(attestation, LocalTextFilePreflightAttestationContract):
        raise TypeError("local_text_preflight_attestation_contract_required")
    for value, error in (
        (attestation.attestation_id, "local_text_preflight_attestation_id_invalid"),
        (attestation.trusted_boundary_ref, "local_text_preflight_boundary_ref_invalid"),
        (attestation.subject_ref, "local_text_preflight_attestation_subject_invalid"),
        (
            attestation.source_preflight_grant_id,
            "local_text_preflight_attestation_source_grant_invalid",
        ),
    ):
        _require_canonical_ref(value, resource=False, error=error)
    _require_match(
        attestation.attestation_nonce,
        _NONCE,
        "local_text_preflight_attestation_nonce_invalid",
    )
    _require_canonical_ref(
        attestation.resource_ref,
        resource=True,
        error="local_text_preflight_attestation_resource_invalid",
    )
    if (
        attestation.trusted_boundary_ref
        != LOCAL_TEXT_FILE_PREFLIGHT_TRUSTED_BOUNDARY_REF
        or attestation.operation not in {"create_text", "replace_text"}
        or attestation.resource_scope != "configured_text_root"
    ):
        raise ValueError("local_text_preflight_attestation_scope_invalid")
    for value in (
        attestation.source_preflight_grant_fingerprint,
        attestation.source_action_fingerprint,
        attestation.source_intent_fingerprint,
        attestation.source_descriptor_fingerprint,
        attestation.source_registry_fingerprint,
        attestation.preflight_fingerprint,
        attestation.root_config_fingerprint,
        attestation.filesystem_snapshot_fingerprint,
        attestation.rollback_fingerprint,
        attestation.before_content_sha256,
        attestation.desired_content_sha256,
    ):
        _require_sha256(value, "local_text_preflight_attestation_sha256_invalid")
    if attestation.expected_current_sha256 is not None:
        _require_sha256(
            attestation.expected_current_sha256,
            "local_text_preflight_attestation_expected_current_invalid",
        )
    if attestation.operation == "create_text":
        if (
            attestation.before_exists
            or attestation.expected_current_sha256 is not None
            or attestation.before_content_sha256 != _EMPTY_SHA256
        ):
            raise ValueError("local_text_preflight_attestation_create_state_invalid")
    elif (
        not attestation.before_exists
        or attestation.expected_current_sha256 != attestation.before_content_sha256
    ):
        raise ValueError("local_text_preflight_attestation_replace_state_invalid")
    if (
        attestation.source_descriptor_fingerprint
        != LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint
        or attestation.preflight_policy_version != LOCAL_TEXT_FILE_PREFLIGHT_POLICY_VERSION
        or attestation.preflight_backend_version != LOCAL_TEXT_FILE_PREFLIGHT_BACKEND_VERSION
    ):
        raise ValueError("local_text_preflight_attestation_policy_invalid")
    prepared = _parse_time(attestation.preflight_prepared_at)
    expires = _parse_time(attestation.preflight_expires_at)
    authorization_expires = _parse_time(attestation.preflight_authorization_expires_at)
    attested = _parse_time(attestation.attested_at)
    if (
        prepared >= expires
        or expires > authorization_expires
        or attested < prepared
        or attested >= expires
    ):
        raise ValueError("local_text_preflight_attestation_window_invalid")
    if now is not None and _parse_time(now) != attested:
        raise ValueError("local_text_preflight_attestation_clock_mismatch")
    _require_metadata_only(attestation)
    if not validate_local_text_file_preflight_attestation_fingerprint(attestation):
        raise ValueError("local_text_preflight_attestation_fingerprint_invalid")


def require_local_text_file_preflight_attestation_matches(
    attestation: LocalTextFilePreflightAttestationContract,
    preflight: LocalTextFilePreflightContract,
    *,
    now: Timestamp | datetime,
) -> None:
    """Require an attestation to be the exact content-free projection of a preflight."""

    require_valid_local_text_file_preflight_attestation(attestation, now=now)
    _require_preflight_source(preflight, requested_at=now)
    expected = (
        preflight.subject_ref,
        preflight.operation,
        preflight.adapter_request.resource_scope,
        preflight.resource_ref,
        preflight.grant_id,
        preflight.grant_fingerprint,
        preflight.action_fingerprint,
        preflight.intent_fingerprint,
        preflight.descriptor_fingerprint,
        preflight.registry_fingerprint,
        preflight.preflight_fingerprint,
        preflight.prepared_at,
        preflight.expires_at,
        preflight.authorization_expires_at,
        preflight.root_config_fingerprint,
        preflight.filesystem_snapshot_fingerprint,
        preflight.rollback_plan.rollback_fingerprint,
        preflight.before_exists,
        preflight.expected_current_sha256,
        preflight.before_content_sha256,
        preflight.desired_content_sha256,
        preflight.preflight_policy_version,
        preflight.adapter_backend_version,
    )
    observed = (
        attestation.subject_ref,
        attestation.operation,
        attestation.resource_scope,
        attestation.resource_ref,
        attestation.source_preflight_grant_id,
        attestation.source_preflight_grant_fingerprint,
        attestation.source_action_fingerprint,
        attestation.source_intent_fingerprint,
        attestation.source_descriptor_fingerprint,
        attestation.source_registry_fingerprint,
        attestation.preflight_fingerprint,
        attestation.preflight_prepared_at,
        attestation.preflight_expires_at,
        attestation.preflight_authorization_expires_at,
        attestation.root_config_fingerprint,
        attestation.filesystem_snapshot_fingerprint,
        attestation.rollback_fingerprint,
        attestation.before_exists,
        attestation.expected_current_sha256,
        attestation.before_content_sha256,
        attestation.desired_content_sha256,
        attestation.preflight_policy_version,
        attestation.preflight_backend_version,
    )
    if observed != expected:
        raise ValueError("local_text_preflight_attestation_projection_mismatch")


def build_adapter_execution_descriptor(
    *,
    adapter_id: str,
    adapter_version: str,
    action_kind: str,
    allowed_operations: tuple[str, ...],
    allowed_resource_scopes: tuple[str, ...],
    executor_ref: str,
    execution_policy_version: str,
    execution_backend_version: str,
) -> AdapterExecutionDescriptorContract:
    descriptor = AdapterExecutionDescriptorContract(
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        action_kind=action_kind,
        allowed_operations=tuple(sorted(allowed_operations)),
        allowed_resource_scopes=tuple(sorted(allowed_resource_scopes)),
        executor_ref=executor_ref,
        execution_policy_version=execution_policy_version,
        execution_backend_version=execution_backend_version,
        descriptor_fingerprint="0" * 64,
    )
    descriptor = replace(
        descriptor,
        descriptor_fingerprint=build_adapter_execution_descriptor_fingerprint(descriptor),
    )
    require_valid_adapter_execution_descriptor(descriptor)
    return descriptor


def validate_adapter_execution_descriptor_fingerprint(
    descriptor: AdapterExecutionDescriptorContract,
) -> bool:
    return bool(fullmatch(_SHA256, descriptor.descriptor_fingerprint)) and compare_digest(
        descriptor.descriptor_fingerprint,
        build_adapter_execution_descriptor_fingerprint(descriptor),
    )


def validate_adapter_execution_descriptor(
    descriptor: AdapterExecutionDescriptorContract,
) -> list[str]:
    return _errors(lambda: require_valid_adapter_execution_descriptor(descriptor))


def require_valid_adapter_execution_descriptor(
    descriptor: AdapterExecutionDescriptorContract,
) -> None:
    _require_match(descriptor.adapter_id, _ID, "adapter_execution_id_invalid")
    _require_match(descriptor.adapter_version, _SEMVER, "adapter_execution_version_invalid")
    if descriptor.action_kind != "execute_external_action":
        raise ValueError("adapter_execution_action_kind_invalid")
    if (
        descriptor.adapter_id == LOCAL_TEXT_FILE_DESCRIPTOR.adapter_id
        and descriptor.adapter_version == LOCAL_TEXT_FILE_DESCRIPTOR.adapter_version
    ):
        raise ValueError("adapter_execution_version_not_separate_from_prepare")
    if not descriptor.allowed_operations or len(set(descriptor.allowed_operations)) != len(
        descriptor.allowed_operations
    ):
        raise ValueError("adapter_execution_operations_empty_or_duplicate")
    if not descriptor.allowed_resource_scopes or len(
        set(descriptor.allowed_resource_scopes)
    ) != len(descriptor.allowed_resource_scopes):
        raise ValueError("adapter_execution_scopes_empty_or_duplicate")
    for value in (*descriptor.allowed_operations, *descriptor.allowed_resource_scopes):
        _require_match(value, _ID, "adapter_execution_allowlist_value_invalid")
        if "*" in value:
            raise ValueError("adapter_execution_wildcard_forbidden")
    if "rollback_text" in descriptor.allowed_operations:
        raise ValueError("adapter_execution_rollback_requires_separate_authority")
    _require_canonical_ref(
        descriptor.executor_ref,
        resource=False,
        error="adapter_execution_executor_ref_invalid",
    )
    if (
        descriptor.execution_policy_version != LOCAL_TEXT_FILE_EXECUTION_POLICY_VERSION
        or descriptor.execution_backend_version != LOCAL_TEXT_FILE_EXECUTION_BACKEND_VERSION
        or not descriptor.execution_only
    ):
        raise ValueError("adapter_execution_policy_or_backend_invalid")
    _require_metadata_only(descriptor)
    if not validate_adapter_execution_descriptor_fingerprint(descriptor):
        raise ValueError("adapter_execution_descriptor_fingerprint_invalid")


def build_adapter_execution_registry_snapshot(
    *,
    registry_id: str,
    registry_version: str,
    descriptors: tuple[AdapterExecutionDescriptorContract, ...],
) -> AdapterExecutionRegistrySnapshotContract:
    ordered = tuple(sorted(descriptors, key=lambda item: (item.adapter_id, item.adapter_version)))
    registry = AdapterExecutionRegistrySnapshotContract(
        registry_id=registry_id,
        registry_version=registry_version,
        descriptors=ordered,
        registry_fingerprint="0" * 64,
    )
    registry = replace(
        registry,
        registry_fingerprint=build_adapter_execution_registry_fingerprint(registry),
    )
    require_valid_adapter_execution_registry_snapshot(registry)
    return registry


def validate_adapter_execution_registry_fingerprint(
    registry: AdapterExecutionRegistrySnapshotContract,
) -> bool:
    return bool(fullmatch(_SHA256, registry.registry_fingerprint)) and compare_digest(
        registry.registry_fingerprint,
        build_adapter_execution_registry_fingerprint(registry),
    )


def validate_adapter_execution_registry_snapshot(
    registry: AdapterExecutionRegistrySnapshotContract,
) -> list[str]:
    return _errors(lambda: require_valid_adapter_execution_registry_snapshot(registry))


def require_valid_adapter_execution_registry_snapshot(
    registry: AdapterExecutionRegistrySnapshotContract,
) -> None:
    _require_match(registry.registry_id, _ID, "adapter_execution_registry_id_invalid")
    _require_match(
        registry.registry_version,
        _SEMVER,
        "adapter_execution_registry_version_invalid",
    )
    keys = [(item.adapter_id, item.adapter_version) for item in registry.descriptors]
    if len(keys) != len(set(keys)):
        raise ValueError("adapter_execution_registry_duplicate_key")
    if keys != sorted(keys):
        raise ValueError("adapter_execution_registry_order_not_canonical")
    for descriptor in registry.descriptors:
        require_valid_adapter_execution_descriptor(descriptor)
    _require_metadata_only(registry)
    if not validate_adapter_execution_registry_fingerprint(registry):
        raise ValueError("adapter_execution_registry_fingerprint_invalid")


def resolve_adapter_execution_descriptor(
    registry: AdapterExecutionRegistrySnapshotContract,
    *,
    adapter_id: str,
    adapter_version: str,
) -> AdapterExecutionDescriptorContract | None:
    if validate_adapter_execution_registry_snapshot(registry):
        return None
    return next(
        (
            item
            for item in registry.descriptors
            if item.adapter_id == adapter_id and item.adapter_version == adapter_version
        ),
        None,
    )


def _require_preflight_source(
    preflight: LocalTextFilePreflightContract,
    *,
    requested_at: Timestamp | datetime,
) -> None:
    if not isinstance(preflight, LocalTextFilePreflightContract):
        raise TypeError("local_text_execution_preflight_contract_required")
    require_valid_adapter_action_request(
        preflight.adapter_request,
        descriptor=LOCAL_TEXT_FILE_DESCRIPTOR,
    )
    for value in (
        preflight.grant_fingerprint,
        preflight.action_fingerprint,
        preflight.intent_fingerprint,
        preflight.descriptor_fingerprint,
        preflight.registry_fingerprint,
        preflight.preflight_fingerprint,
        preflight.root_config_fingerprint,
        preflight.filesystem_snapshot_fingerprint,
        preflight.before_content_sha256,
        preflight.desired_content_sha256,
        preflight.diff_sha256,
        preflight.rollback_plan.rollback_fingerprint,
    ):
        _require_sha256(value, "local_text_execution_preflight_sha256_invalid")
    if (
        preflight.preflight_fingerprint != _build_preflight_fingerprint(preflight)
        or sha256(preflight.unified_diff.encode("utf-8")).hexdigest() != preflight.diff_sha256
    ):
        raise ValueError("local_text_execution_preflight_integrity_invalid")
    rollback = preflight.rollback_plan
    if (
        rollback.rollback_fingerprint != _build_rollback_fingerprint(preflight)
        or rollback.operation != preflight.operation
        or rollback.resource_ref != preflight.resource_ref
        or rollback.root_config_fingerprint != preflight.root_config_fingerprint
        or rollback.before_content_sha256 != preflight.before_content_sha256
        or rollback.desired_content_sha256 != preflight.desired_content_sha256
        or rollback.precondition_content_sha256 != preflight.desired_content_sha256
    ):
        raise ValueError("local_text_execution_rollback_binding_invalid")
    if (
        preflight.descriptor_fingerprint != LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint
        or preflight.operation != preflight.adapter_request.operation
        or preflight.resource_ref != preflight.adapter_request.resource_ref
        or preflight.preflight_policy_version != LOCAL_TEXT_FILE_PREFLIGHT_POLICY_VERSION
        or preflight.adapter_backend_version != LOCAL_TEXT_FILE_PREFLIGHT_BACKEND_VERSION
        or preflight.change_status != "change"
    ):
        raise ValueError("local_text_execution_preflight_binding_invalid")
    if preflight.operation == "create_text":
        if (
            preflight.before_exists
            or preflight.expected_current_sha256 is not None
            or preflight.before_content_sha256 != _EMPTY_SHA256
        ):
            raise ValueError("local_text_execution_create_precondition_invalid")
    elif preflight.operation == "replace_text":
        if (
            not preflight.before_exists
            or preflight.expected_current_sha256 != preflight.before_content_sha256
        ):
            raise ValueError("local_text_execution_replace_precondition_invalid")
    else:
        raise ValueError("local_text_execution_operation_invalid")
    if (
        not preflight.execution_grant_required
        or preflight.preflight_grant_reusable_for_execution
        or not preflight.read_only
        or not preflight.immutable
        or any(getattr(preflight, field) for field in _AUTHORITY_FIELDS)
        or any(getattr(rollback, field) for field in _AUTHORITY_FIELDS)
    ):
        raise ValueError("local_text_execution_preflight_authority_invalid")
    prepared = _parse_time(preflight.prepared_at)
    expires = _parse_time(preflight.expires_at)
    authorization_expires = _parse_time(preflight.authorization_expires_at)
    current = _parse_time(requested_at)
    if (
        prepared >= expires
        or expires > authorization_expires
        or current < prepared
        or current >= expires
        or current >= authorization_expires
    ):
        raise ValueError("local_text_execution_preflight_window_inactive")


def require_valid_local_text_file_execution_preflight(
    preflight: LocalTextFilePreflightContract,
    *,
    now: Timestamp | datetime,
) -> None:
    """Validate a full materialized preflight without granting execution authority."""

    _require_preflight_source(preflight, requested_at=now)


def build_adapter_execution_request(
    preflight: LocalTextFilePreflightContract,
    attestation: LocalTextFilePreflightAttestationContract,
) -> AdapterExecutionRequestContract:
    request_time = _parse_time(attestation.attested_at)
    require_local_text_file_preflight_attestation_matches(
        attestation,
        preflight,
        now=request_time,
    )
    request = AdapterExecutionRequestContract(
        adapter_id=LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR.adapter_id,
        adapter_version=LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR.adapter_version,
        action_kind=LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR.action_kind,
        operation=preflight.operation,
        resource_scope=preflight.adapter_request.resource_scope,
        resource_ref=preflight.resource_ref,
        subject_ref=preflight.subject_ref,
        preflight_attestation_id=attestation.attestation_id,
        preflight_attestation_fingerprint=attestation.attestation_fingerprint,
        source_preflight_grant_id=preflight.grant_id,
        source_preflight_grant_fingerprint=preflight.grant_fingerprint,
        source_action_fingerprint=preflight.action_fingerprint,
        source_intent_fingerprint=preflight.intent_fingerprint,
        source_descriptor_fingerprint=preflight.descriptor_fingerprint,
        source_registry_fingerprint=preflight.registry_fingerprint,
        preflight_fingerprint=preflight.preflight_fingerprint,
        preflight_prepared_at=preflight.prepared_at,
        preflight_expires_at=preflight.expires_at,
        preflight_authorization_expires_at=preflight.authorization_expires_at,
        root_config_fingerprint=preflight.root_config_fingerprint,
        filesystem_snapshot_fingerprint=preflight.filesystem_snapshot_fingerprint,
        rollback_fingerprint=preflight.rollback_plan.rollback_fingerprint,
        before_exists=preflight.before_exists,
        expected_current_sha256=preflight.expected_current_sha256,
        before_content_sha256=preflight.before_content_sha256,
        precondition_content_sha256=preflight.before_content_sha256,
        desired_content_sha256=preflight.desired_content_sha256,
        postcondition_content_sha256=preflight.desired_content_sha256,
        preflight_policy_version=preflight.preflight_policy_version,
        preflight_backend_version=preflight.adapter_backend_version,
        execution_policy_version=LOCAL_TEXT_FILE_EXECUTION_POLICY_VERSION,
        execution_backend_version=LOCAL_TEXT_FILE_EXECUTION_BACKEND_VERSION,
        requested_at=request_time.isoformat().replace("+00:00", "Z"),
        execution_request_fingerprint="0" * 64,
    )
    request = replace(
        request,
        execution_request_fingerprint=build_adapter_execution_request_fingerprint(request),
    )
    require_adapter_execution_request_matches_attestation(
        request,
        attestation,
        now=request_time,
    )
    return request


def validate_adapter_execution_request_fingerprint(
    request: AdapterExecutionRequestContract,
) -> bool:
    return bool(fullmatch(_SHA256, request.execution_request_fingerprint)) and compare_digest(
        request.execution_request_fingerprint,
        build_adapter_execution_request_fingerprint(request),
    )


def validate_adapter_execution_request(
    request: AdapterExecutionRequestContract,
    *,
    now: Timestamp | datetime | None = None,
) -> list[str]:
    return _errors(lambda: require_valid_adapter_execution_request(request, now=now))


def require_valid_adapter_execution_request(
    request: AdapterExecutionRequestContract,
    *,
    now: Timestamp | datetime | None = None,
) -> None:
    descriptor = LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR
    if not isinstance(request, AdapterExecutionRequestContract):
        raise TypeError("adapter_execution_request_contract_required")
    if (request.adapter_id, request.adapter_version, request.action_kind) != (
        descriptor.adapter_id,
        descriptor.adapter_version,
        descriptor.action_kind,
    ):
        raise ValueError("adapter_execution_request_descriptor_mismatch")
    if (
        request.operation not in descriptor.allowed_operations
        or request.resource_scope not in descriptor.allowed_resource_scopes
    ):
        raise ValueError("adapter_execution_request_not_allowlisted")
    _require_canonical_ref(
        request.resource_ref,
        resource=True,
        error="adapter_execution_resource_ref_invalid",
    )
    for value, error in (
        (request.subject_ref, "adapter_execution_subject_ref_invalid"),
        (
            request.preflight_attestation_id,
            "adapter_execution_preflight_attestation_id_invalid",
        ),
        (request.source_preflight_grant_id, "adapter_execution_source_grant_id_invalid"),
    ):
        _require_canonical_ref(value, resource=False, error=error)
    for value in (
        request.preflight_attestation_fingerprint,
        request.source_preflight_grant_fingerprint,
        request.source_action_fingerprint,
        request.source_intent_fingerprint,
        request.source_descriptor_fingerprint,
        request.source_registry_fingerprint,
        request.preflight_fingerprint,
        request.root_config_fingerprint,
        request.filesystem_snapshot_fingerprint,
        request.rollback_fingerprint,
        request.before_content_sha256,
        request.precondition_content_sha256,
        request.desired_content_sha256,
        request.postcondition_content_sha256,
    ):
        _require_sha256(value, "adapter_execution_request_sha256_invalid")
    if request.expected_current_sha256 is not None:
        _require_sha256(
            request.expected_current_sha256,
            "adapter_execution_expected_current_sha256_invalid",
        )
    if (
        request.precondition_content_sha256 != request.before_content_sha256
        or request.postcondition_content_sha256 != request.desired_content_sha256
    ):
        raise ValueError("adapter_execution_precondition_or_postcondition_mismatch")
    if request.operation == "create_text":
        if (
            request.before_exists
            or request.expected_current_sha256 is not None
            or request.before_content_sha256 != _EMPTY_SHA256
        ):
            raise ValueError("adapter_execution_create_precondition_invalid")
    elif request.operation == "replace_text":
        if (
            not request.before_exists
            or request.expected_current_sha256 != request.before_content_sha256
        ):
            raise ValueError("adapter_execution_replace_precondition_invalid")
    else:
        raise ValueError("adapter_execution_operation_invalid")
    if (
        request.source_descriptor_fingerprint != LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint
        or request.preflight_policy_version != LOCAL_TEXT_FILE_PREFLIGHT_POLICY_VERSION
        or request.preflight_backend_version != LOCAL_TEXT_FILE_PREFLIGHT_BACKEND_VERSION
        or request.execution_policy_version != descriptor.execution_policy_version
        or request.execution_backend_version != descriptor.execution_backend_version
    ):
        raise ValueError("adapter_execution_request_policy_or_backend_invalid")
    prepared = _parse_time(request.preflight_prepared_at)
    preflight_expires = _parse_time(request.preflight_expires_at)
    authorization_expires = _parse_time(request.preflight_authorization_expires_at)
    requested = _parse_time(request.requested_at)
    if (
        prepared >= preflight_expires
        or preflight_expires > authorization_expires
        or requested < prepared
        or requested >= preflight_expires
    ):
        raise ValueError("adapter_execution_request_window_invalid")
    if now is not None:
        current = _parse_time(now)
        if current < requested or current >= preflight_expires:
            raise ValueError("adapter_execution_request_expired_or_not_yet_valid")
    _require_metadata_only(request)
    if not validate_adapter_execution_request_fingerprint(request):
        raise ValueError("adapter_execution_request_fingerprint_invalid")


def require_adapter_execution_request_matches_attestation(
    request: AdapterExecutionRequestContract,
    attestation: LocalTextFilePreflightAttestationContract,
    *,
    now: Timestamp | datetime | None = None,
) -> None:
    """Require an execution request to match persisted trusted preflight evidence."""

    require_valid_adapter_execution_request(request, now=now)
    require_valid_local_text_file_preflight_attestation(attestation)
    expected = (
        attestation.attestation_id,
        attestation.attestation_fingerprint,
        attestation.subject_ref,
        attestation.operation,
        attestation.resource_scope,
        attestation.resource_ref,
        attestation.source_preflight_grant_id,
        attestation.source_preflight_grant_fingerprint,
        attestation.source_action_fingerprint,
        attestation.source_intent_fingerprint,
        attestation.source_descriptor_fingerprint,
        attestation.source_registry_fingerprint,
        attestation.preflight_fingerprint,
        attestation.preflight_prepared_at,
        attestation.preflight_expires_at,
        attestation.preflight_authorization_expires_at,
        attestation.root_config_fingerprint,
        attestation.filesystem_snapshot_fingerprint,
        attestation.rollback_fingerprint,
        attestation.before_exists,
        attestation.expected_current_sha256,
        attestation.before_content_sha256,
        attestation.before_content_sha256,
        attestation.desired_content_sha256,
        attestation.desired_content_sha256,
        attestation.preflight_policy_version,
        attestation.preflight_backend_version,
        attestation.attested_at,
    )
    observed = (
        request.preflight_attestation_id,
        request.preflight_attestation_fingerprint,
        request.subject_ref,
        request.operation,
        request.resource_scope,
        request.resource_ref,
        request.source_preflight_grant_id,
        request.source_preflight_grant_fingerprint,
        request.source_action_fingerprint,
        request.source_intent_fingerprint,
        request.source_descriptor_fingerprint,
        request.source_registry_fingerprint,
        request.preflight_fingerprint,
        request.preflight_prepared_at,
        request.preflight_expires_at,
        request.preflight_authorization_expires_at,
        request.root_config_fingerprint,
        request.filesystem_snapshot_fingerprint,
        request.rollback_fingerprint,
        request.before_exists,
        request.expected_current_sha256,
        request.before_content_sha256,
        request.precondition_content_sha256,
        request.desired_content_sha256,
        request.postcondition_content_sha256,
        request.preflight_policy_version,
        request.preflight_backend_version,
        request.requested_at,
    )
    if observed != expected:
        raise ValueError("adapter_execution_request_attestation_mismatch")


def _resolve_request_descriptor(
    request: AdapterExecutionRequestContract,
    registry: AdapterExecutionRegistrySnapshotContract,
) -> AdapterExecutionDescriptorContract:
    descriptor = resolve_adapter_execution_descriptor(
        registry,
        adapter_id=request.adapter_id,
        adapter_version=request.adapter_version,
    )
    if descriptor is None:
        raise ValueError("adapter_execution_descriptor_not_in_registry")
    return descriptor


def build_adapter_execution_grant(
    *,
    grant_id: str,
    subject_ref: str,
    request: AdapterExecutionRequestContract,
    descriptor: AdapterExecutionDescriptorContract,
    registry: AdapterExecutionRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    policy_version: str,
    nonce: str,
    issued_at: Timestamp,
    expires_at: Timestamp,
    now: Timestamp | datetime | None = None,
) -> AdapterExecutionGrantContract:
    grant = AdapterExecutionGrantContract(
        grant_id=grant_id,
        subject_ref=subject_ref,
        execution_request=request,
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
    grant = replace(grant, grant_fingerprint=build_adapter_execution_grant_fingerprint(grant))
    require_valid_adapter_execution_grant(
        grant,
        descriptor=descriptor,
        registry=registry,
        intent=intent,
        intent_fingerprint=intent_fingerprint,
        autonomy_decision=autonomy_decision,
        now=now,
    )
    return grant


def validate_adapter_execution_grant_fingerprint(grant: AdapterExecutionGrantContract) -> bool:
    return bool(fullmatch(_SHA256, grant.grant_fingerprint)) and compare_digest(
        grant.grant_fingerprint,
        build_adapter_execution_grant_fingerprint(grant),
    )


def validate_adapter_execution_grant(
    grant: AdapterExecutionGrantContract,
    *,
    descriptor: AdapterExecutionDescriptorContract,
    registry: AdapterExecutionRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    now: Timestamp | datetime | None = None,
) -> list[str]:
    return _errors(
        lambda: require_valid_adapter_execution_grant(
            grant,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            now=now,
        )
    )


def require_valid_adapter_execution_grant(
    grant: AdapterExecutionGrantContract,
    *,
    descriptor: AdapterExecutionDescriptorContract,
    registry: AdapterExecutionRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    now: Timestamp | datetime | None = None,
) -> None:
    _require_canonical_ref(
        grant.grant_id,
        resource=False,
        error="adapter_execution_grant_id_invalid",
    )
    _require_canonical_ref(
        grant.subject_ref,
        resource=False,
        error="adapter_execution_subject_ref_invalid",
    )
    require_valid_adapter_execution_registry_snapshot(registry)
    require_valid_adapter_execution_request(grant.execution_request)
    resolved = _resolve_request_descriptor(grant.execution_request, registry)
    if resolved != descriptor:
        raise ValueError("adapter_execution_descriptor_not_in_registry")
    if grant.descriptor_fingerprint != descriptor.descriptor_fingerprint:
        raise ValueError("adapter_execution_descriptor_fingerprint_drift")
    if grant.registry_fingerprint != registry.registry_fingerprint:
        raise ValueError("adapter_execution_registry_fingerprint_drift")
    if validate_action_intent(intent, now=grant.issued_at):
        raise ValueError("adapter_execution_intent_invalid")
    if not compare_digest(action_intent_fingerprint(intent), intent_fingerprint):
        raise ValueError("adapter_execution_intent_fingerprint_invalid")
    if (grant.intent_id, grant.intent_fingerprint, grant.action_fingerprint) != (
        intent.intent_id,
        intent_fingerprint,
        intent.action_fingerprint,
    ):
        raise ValueError("adapter_execution_intent_binding_drift")
    request = grant.execution_request
    if (
        grant.subject_ref != request.subject_ref
        or grant.subject_ref != intent.operator_identity_ref
        or intent.operation != request.operation
        or intent.target_ref != request.resource_ref
        or intent.handler_id != descriptor.executor_ref
        or intent.handler_version != descriptor.adapter_version
        or intent.content_digest != request.desired_content_sha256
        or intent.precondition_digest != request.execution_request_fingerprint
    ):
        raise ValueError("adapter_execution_intent_exact_binding_mismatch")
    if grant.autonomy_policy_decision_fingerprint != autonomy_policy_decision_fingerprint(
        autonomy_decision
    ):
        raise ValueError("adapter_execution_autonomy_decision_drift")
    if not (
        intent.policy_version
        == grant.policy_version
        == autonomy_decision.policy_version
        == AUTONOMY_ACTION_POLICY_VERSION
    ):
        raise ValueError("adapter_execution_policy_version_invalid")
    if (
        autonomy_decision.action_kind != descriptor.action_kind
        or autonomy_decision.decision != "require_confirmation"
        or not autonomy_decision.confirmation_required
        or autonomy_decision.confirmation_requirement != "explicit_confirmation_required"
        or autonomy_decision.confirmation_evidence_state != "absent"
        or autonomy_decision.side_effect_allowed
        or autonomy_decision.reason_codes != ("exact_confirmation_required",)
        or autonomy_decision.selected_capability_mode
        != "core_with_supervised_external_operation"
        or autonomy_decision.max_capability_mode
        != "core_with_supervised_external_operation"
    ):
        raise ValueError("adapter_execution_autonomy_decision_invalid")
    _require_metadata_only(autonomy_decision)
    if not grant.confirmation_required:
        raise ValueError("adapter_execution_confirmation_required")
    _require_match(grant.nonce, _NONCE, "adapter_execution_grant_nonce_invalid")
    issued = _parse_time(grant.issued_at)
    expires = _parse_time(grant.expires_at)
    if (
        issued < _parse_time(request.requested_at)
        or issued < _parse_time(intent.issued_at)
        or _parse_time(intent.issued_at) < _parse_time(request.requested_at)
        or issued >= expires
        or (expires - issued).total_seconds() > LOCAL_TEXT_FILE_EXECUTION_MAX_TTL_SECONDS
        or expires > _parse_time(intent.expires_at)
        or expires > _parse_time(request.preflight_expires_at)
        or expires > _parse_time(request.preflight_authorization_expires_at)
    ):
        raise ValueError("adapter_execution_grant_window_invalid")
    current = _now(now)
    if current < issued:
        raise ValueError("adapter_execution_grant_not_yet_valid")
    if current >= expires:
        raise ValueError("adapter_execution_grant_expired")
    if not grant.single_use:
        raise ValueError("adapter_execution_grant_not_single_use")
    _require_metadata_only(grant)
    if not validate_adapter_execution_grant_fingerprint(grant):
        raise ValueError("adapter_execution_grant_fingerprint_invalid")


def build_adapter_execution_grant_claim(
    *,
    claim_id: str,
    operation_id: OperationId | str,
    journal_reservation_fingerprint: str,
    grant: AdapterExecutionGrantContract,
    claimed_at: Timestamp,
    confirmation_receipt_id: str,
    confirmation_claim_id: str,
    confirmation_claim_fingerprint: str,
) -> AdapterExecutionGrantClaimContract:
    claim = AdapterExecutionGrantClaimContract(
        claim_id=claim_id,
        grant_id=grant.grant_id,
        grant_fingerprint=grant.grant_fingerprint,
        operation_id=OperationId(str(operation_id)),
        journal_reservation_fingerprint=journal_reservation_fingerprint,
        subject_ref=grant.subject_ref,
        execution_request=grant.execution_request,
        intent_id=grant.intent_id,
        intent_fingerprint=grant.intent_fingerprint,
        action_fingerprint=grant.action_fingerprint,
        claimed_at=claimed_at,
        expires_at=grant.expires_at,
        claim_fingerprint="0" * 64,
        confirmation_receipt_id=confirmation_receipt_id,
        confirmation_claim_id=confirmation_claim_id,
        confirmation_claim_fingerprint=confirmation_claim_fingerprint,
    )
    claim = replace(
        claim,
        claim_fingerprint=build_adapter_execution_grant_claim_fingerprint(claim),
    )
    require_valid_adapter_execution_grant_claim(claim, grant=grant)
    return claim


def validate_adapter_execution_grant_claim_fingerprint(
    claim: AdapterExecutionGrantClaimContract,
) -> bool:
    return bool(fullmatch(_SHA256, claim.claim_fingerprint)) and compare_digest(
        claim.claim_fingerprint,
        build_adapter_execution_grant_claim_fingerprint(claim),
    )


def validate_adapter_execution_grant_claim(
    claim: AdapterExecutionGrantClaimContract,
    *,
    grant: AdapterExecutionGrantContract,
    now: Timestamp | datetime | None = None,
    require_active: bool = False,
) -> list[str]:
    return _errors(
        lambda: require_valid_adapter_execution_grant_claim(
            claim,
            grant=grant,
            now=now,
            require_active=require_active,
        )
    )


def require_valid_adapter_execution_grant_claim(
    claim: AdapterExecutionGrantClaimContract,
    *,
    grant: AdapterExecutionGrantContract,
    now: Timestamp | datetime | None = None,
    require_active: bool = False,
) -> None:
    _require_canonical_ref(
        claim.claim_id,
        resource=False,
        error="adapter_execution_claim_id_invalid",
    )
    _require_canonical_ref(
        str(claim.operation_id),
        resource=False,
        error="adapter_execution_claim_operation_id_invalid",
    )
    _require_sha256(
        claim.journal_reservation_fingerprint,
        "adapter_execution_journal_reservation_fingerprint_invalid",
    )
    expected = (
        grant.grant_id,
        grant.grant_fingerprint,
        grant.subject_ref,
        grant.execution_request,
        grant.intent_id,
        grant.intent_fingerprint,
        grant.action_fingerprint,
        grant.expires_at,
    )
    observed = (
        claim.grant_id,
        claim.grant_fingerprint,
        claim.subject_ref,
        claim.execution_request,
        claim.intent_id,
        claim.intent_fingerprint,
        claim.action_fingerprint,
        claim.expires_at,
    )
    if observed != expected:
        raise ValueError("adapter_execution_claim_binding_drift")
    claimed = _parse_time(claim.claimed_at)
    expires = _parse_time(claim.expires_at)
    if claimed < _parse_time(grant.issued_at) or claimed >= expires:
        raise ValueError("adapter_execution_claim_time_invalid")
    if require_active:
        if now is None:
            raise ValueError("adapter_execution_claim_active_time_required")
        current = _parse_time(now)
        if current < claimed:
            raise ValueError("adapter_execution_claim_not_yet_valid")
        if current >= expires:
            raise ValueError("adapter_execution_claim_expired")
    for value, error in (
        (claim.confirmation_receipt_id, "adapter_execution_confirmation_receipt_required"),
        (claim.confirmation_claim_id, "adapter_execution_confirmation_claim_required"),
    ):
        _require_canonical_ref(value, resource=False, error=error)
    _require_sha256(
        claim.confirmation_claim_fingerprint,
        "adapter_execution_confirmation_claim_fingerprint_invalid",
    )
    if not claim.single_use:
        raise ValueError("adapter_execution_claim_not_single_use")
    _require_metadata_only(claim)
    if not validate_adapter_execution_grant_claim_fingerprint(claim):
        raise ValueError("adapter_execution_claim_fingerprint_invalid")


LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR = build_adapter_execution_descriptor(
    adapter_id="local_text_file",
    adapter_version=LOCAL_TEXT_FILE_EXECUTION_ADAPTER_VERSION,
    action_kind="execute_external_action",
    allowed_operations=("create_text", "replace_text"),
    allowed_resource_scopes=("configured_text_root",),
    executor_ref="adapter-executor://local_text_file",
    execution_policy_version=LOCAL_TEXT_FILE_EXECUTION_POLICY_VERSION,
    execution_backend_version=LOCAL_TEXT_FILE_EXECUTION_BACKEND_VERSION,
)

SEEDED_ADAPTER_EXECUTION_REGISTRY = build_adapter_execution_registry_snapshot(
    registry_id="jarvis.adapter_execution_registry",
    registry_version="1.0.0",
    descriptors=(LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR,),
)
