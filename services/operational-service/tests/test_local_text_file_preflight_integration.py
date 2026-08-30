from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from sqlite3 import connect

import pytest
from governance_service.service import GovernanceService
from operational_service.adapters import local_text_file as local_text_file_module
from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)
from operational_service.service import OperationalService

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.adapter_permissions import (
    SEEDED_ADAPTER_REGISTRY,
    build_adapter_registry_snapshot,
)
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import (
    ActionIntentContract,
    AdapterActionRequestContract,
    AdapterGrantContract,
    LocalTextFilePreflightRequestContract,
)
from shared.types import RiskLevel

ISSUED_AT = "2026-08-29T12:00:00Z"
PREFLIGHT_AT = "2026-08-29T12:02:00Z"
PREFLIGHT_EXPIRES_AT = "2026-08-29T12:05:00Z"
GRANT_EXPIRES_AT = "2026-08-29T12:10:00Z"
INTENT_EXPIRES_AT = "2026-08-29T12:20:00Z"
PREFLIGHT_NOW = datetime(2026, 8, 29, 12, 2, tzinfo=UTC)


@dataclass(frozen=True)
class _PreflightHarness:
    database_path: Path
    text_root: Path
    artifact_root: Path
    governance: GovernanceService
    operational: OperationalService
    intent: ActionIntentContract
    grant: AdapterGrantContract
    request: LocalTextFilePreflightRequestContract


def _action_request(**changes: str) -> AdapterActionRequestContract:
    values = {
        "adapter_id": "local_text_file",
        "adapter_version": "1.0.0",
        "action_kind": "prepare_external_action",
        "operation": "create_text",
        "resource_scope": "configured_text_root",
        "resource_ref": "text:notes/mb215.txt",
    }
    values.update(changes)
    return AdapterActionRequestContract(**values)


def _autonomy_decision(*, confirmation_required: bool):  # type: ignore[no-untyped-def]
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
        human_confirmation_required=confirmation_required,
        human_confirmation_mode=(
            "explicit_confirmation_required" if confirmation_required else "not_required"
        ),
        confirmation_evidence_state="absent",
    )


def _build_harness(
    tmp_path: Path,
    *,
    confirmation_required: bool = False,
    grant_expires_at: str = GRANT_EXPIRES_AT,
    preflight_expires_at: str = PREFLIGHT_EXPIRES_AT,
) -> _PreflightHarness:
    text_root = tmp_path / "configured-text-root"
    text_root.mkdir()
    artifact_root = tmp_path / "operational-artifacts"
    database_path = tmp_path / "governance.db"
    governance = GovernanceService(database_path)
    governance.activate_adapter_registry(
        SEEDED_ADAPTER_REGISTRY,
        activated_at=ISSUED_AT,
    )
    operational = OperationalService(
        artifact_dir=str(artifact_root),
        adapter_preflight_verifier=(governance.verify_adapter_grant_for_preflight_exact),
        local_text_file_roots={"notes": text_root},
    )
    root_config_fingerprint = operational.local_text_file_root_config_fingerprint()
    action_request = _action_request()
    desired_text = "MB-215 prepared safely.\n"
    intent = build_action_intent(
        intent_id="adapter-intent://mb215/integration",
        origin_request_id="request://mb215/integration",
        session_id="session://mb215/integration",
        mission_id="mission://mb215/integration",
        operator_identity_ref="operator://local/vtham",
        handler_id="adapter://local_text_file",
        handler_version="1.0.0",
        operation=action_request.operation,
        target_ref=action_request.resource_ref,
        content_digest=sha256(desired_text.encode("utf-8")).hexdigest(),
        precondition_digest=root_config_fingerprint,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce="adapterIntentNonceMb215Integration123456",
        issued_at=ISSUED_AT,
        expires_at=INTENT_EXPIRES_AT,
        now=ISSUED_AT,
    )
    registry, descriptor = governance.resolve_active_adapter_descriptor(action_request)
    grant = governance.issue_adapter_grant(
        intent,
        action_request,
        _autonomy_decision(confirmation_required=confirmation_required),
        expected_registry_fingerprint=registry.registry_fingerprint,
        expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        issued_at=ISSUED_AT,
        expires_at=grant_expires_at,
    )
    request = LocalTextFilePreflightRequestContract(
        grant_id=grant.grant_id,
        grant_fingerprint=grant.grant_fingerprint,
        action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        descriptor_fingerprint=grant.descriptor_fingerprint,
        registry_fingerprint=grant.registry_fingerprint,
        subject_ref=intent.operator_identity_ref,
        adapter_request=action_request,
        desired_text=desired_text,
        expected_root_config_fingerprint=root_config_fingerprint,
        preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
        diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
        diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
        prepared_at=PREFLIGHT_AT,
        expires_at=preflight_expires_at,
        authorization_expires_at=grant.expires_at,
    )
    return _PreflightHarness(
        database_path=database_path,
        text_root=text_root,
        artifact_root=artifact_root,
        governance=governance,
        operational=operational,
        intent=intent,
        grant=grant,
        request=request,
    )


def _row_counts(database_path: Path) -> dict[str, int]:
    tables = (
        "action_intents",
        "action_confirmation_challenges",
        "human_confirmation_receipts",
        "action_confirmation_claims",
        "adapter_registry_epochs",
        "adapter_registry_descriptors",
        "adapter_grants",
        "adapter_grant_claims",
    )
    with connect(database_path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def _tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes | None], ...]:
    return tuple(
        (
            path.relative_to(root).as_posix(),
            "directory" if path.is_dir() else "file",
            None if path.is_dir() else path.read_bytes(),
        )
        for path in sorted(root.rglob("*"))
    )


def _forbid_adapter_filesystem_io(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    calls: list[object] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise AssertionError("adapter filesystem I/O preceded exact grant verification")

    monkeypatch.setattr(local_text_file_module.os, "lstat", forbidden)
    monkeypatch.setattr(local_text_file_module.os, "scandir", forbidden)
    return calls


@pytest.mark.parametrize("confirmation_required", (False, True))
def test_real_prepare_grant_preflights_without_consuming_or_writing(
    tmp_path: Path,
    confirmation_required: bool,
) -> None:
    harness = _build_harness(
        tmp_path,
        confirmation_required=confirmation_required,
    )
    rows_before = _row_counts(harness.database_path)
    root_before = _tree_snapshot(harness.text_root)

    result = harness.operational.preflight_local_text_file(
        harness.request,
        now=PREFLIGHT_NOW,
    )

    assert result.grant_id == harness.grant.grant_id
    assert result.resource_ref == "text:notes/mb215.txt"
    assert result.before_exists is False
    assert result.execution_allowed is False
    assert result.tool_dispatch_allowed is False
    assert result.preflight_grant_reusable_for_execution is False
    assert result.contains_sensitive_diff is True
    assert result.persistence_allowed is False
    assert result.telemetry_allowed is False
    assert _row_counts(harness.database_path) == rows_before
    assert rows_before["adapter_grant_claims"] == 0
    assert rows_before["human_confirmation_receipts"] == 0
    assert rows_before["action_confirmation_claims"] == 0
    assert _tree_snapshot(harness.text_root) == root_before
    assert harness.artifact_root.exists() is False


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_grant",
        "grant_fingerprint",
        "action_fingerprint",
        "descriptor_fingerprint",
        "registry_fingerprint",
        "authorization_expires_at",
        "subject_ref",
        "resource_ref",
        "desired_text",
    ),
)
def test_forged_or_mismatched_context_is_rejected_before_filesystem_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    harness = _build_harness(tmp_path)
    request = harness.request
    if mutation == "missing_grant":
        request = replace(request, grant_id="adapter-grant://missing")
    elif mutation == "resource_ref":
        request = replace(
            request,
            adapter_request=replace(
                request.adapter_request,
                resource_ref="text:notes/forged.txt",
            ),
        )
    elif mutation == "subject_ref":
        request = replace(request, subject_ref="operator://local/spoof")
    elif mutation == "authorization_expires_at":
        request = replace(
            request,
            authorization_expires_at="2026-08-29T12:11:00Z",
        )
    elif mutation == "desired_text":
        request = replace(request, desired_text="forged desired bytes\n")
    else:
        request = replace(request, **{mutation: "0" * 64})
    rows_before = _row_counts(harness.database_path)
    calls = _forbid_adapter_filesystem_io(monkeypatch)

    expected_error = (
        "local_text_descriptor_fingerprint_drift"
        if mutation == "descriptor_fingerprint"
        else "local_text_preflight_context_not_verified"
    )
    with pytest.raises(ValueError, match=expected_error):
        harness.operational.preflight_local_text_file(request, now=PREFLIGHT_NOW)

    assert calls == []
    assert _row_counts(harness.database_path) == rows_before


def test_reconfigured_root_cannot_rebind_existing_grant_before_filesystem_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_harness(tmp_path)
    previous_fingerprint = harness.request.expected_root_config_fingerprint
    reconfigured_root = tmp_path / "reconfigured-text-root"
    reconfigured_root.mkdir()
    reconfigured = OperationalService(
        artifact_dir=str(tmp_path / "reconfigured-operational-artifacts"),
        adapter_preflight_verifier=(harness.governance.verify_adapter_grant_for_preflight_exact),
        local_text_file_roots={"notes": reconfigured_root},
    )
    current_fingerprint = reconfigured.local_text_file_root_config_fingerprint()
    assert current_fingerprint != previous_fingerprint
    request = replace(
        harness.request,
        expected_root_config_fingerprint=current_fingerprint,
    )
    rows_before = _row_counts(harness.database_path)
    calls = _forbid_adapter_filesystem_io(monkeypatch)

    with pytest.raises(ValueError, match="local_text_preflight_context_not_verified"):
        reconfigured.preflight_local_text_file(request, now=PREFLIGHT_NOW)

    assert calls == []
    assert _row_counts(harness.database_path) == rows_before


def test_claimed_grant_is_rejected_before_filesystem_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_harness(tmp_path)
    harness.governance.claim_adapter_grant_exact(
        harness.grant.grant_id,
        operation_id="operation://mb215/claimed",
        subject_ref=harness.intent.operator_identity_ref,
        expected_grant_fingerprint=harness.grant.grant_fingerprint,
        expected_action_fingerprint=harness.intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(harness.intent),
        claimed_at=PREFLIGHT_AT,
    )
    rows_before = _row_counts(harness.database_path)
    calls = _forbid_adapter_filesystem_io(monkeypatch)

    with pytest.raises(ValueError, match="local_text_preflight_context_not_verified"):
        harness.operational.preflight_local_text_file(
            harness.request,
            now=PREFLIGHT_NOW,
        )

    assert calls == []
    assert _row_counts(harness.database_path) == rows_before


def test_removed_descriptor_is_rejected_before_filesystem_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_harness(tmp_path)
    harness.governance.activate_adapter_registry(
        build_adapter_registry_snapshot(
            registry_id=SEEDED_ADAPTER_REGISTRY.registry_id,
            registry_version="1.1.0",
            descriptors=(),
        ),
        activated_at="2026-08-29T12:01:00Z",
    )
    rows_before = _row_counts(harness.database_path)
    calls = _forbid_adapter_filesystem_io(monkeypatch)

    with pytest.raises(ValueError, match="local_text_preflight_context_not_verified"):
        harness.operational.preflight_local_text_file(
            harness.request,
            now=PREFLIGHT_NOW,
        )

    assert calls == []
    assert _row_counts(harness.database_path) == rows_before


def test_expired_window_is_rejected_before_filesystem_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_harness(
        tmp_path,
        grant_expires_at="2026-08-29T12:03:00Z",
        preflight_expires_at="2026-08-29T12:03:00Z",
    )
    rows_before = _row_counts(harness.database_path)
    calls = _forbid_adapter_filesystem_io(monkeypatch)

    with pytest.raises(ValueError, match="local_text_preflight_window_inactive"):
        harness.operational.preflight_local_text_file(
            harness.request,
            now=datetime(2026, 8, 29, 12, 3, tzinfo=UTC),
        )

    assert calls == []
    assert _row_counts(harness.database_path) == rows_before


@pytest.mark.parametrize("verifier_mode", ("absent", "raises", "non_bool_truthy"))
def test_missing_or_invalid_verifier_fails_closed_before_filesystem_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    verifier_mode: str,
) -> None:
    harness = _build_harness(tmp_path)

    def raising_verifier(*_: object, **__: object) -> bool:
        raise RuntimeError("governance unavailable")

    verifier = {
        "absent": None,
        "raises": raising_verifier,
        "non_bool_truthy": lambda *_args, **_kwargs: 1,
    }[verifier_mode]
    blocked = OperationalService(
        artifact_dir=str(harness.artifact_root),
        adapter_preflight_verifier=verifier,  # type: ignore[arg-type]
        local_text_file_roots={"notes": harness.text_root},
    )
    calls = _forbid_adapter_filesystem_io(monkeypatch)

    with pytest.raises(ValueError, match="local_text_preflight_context_not_verified"):
        blocked.preflight_local_text_file(harness.request, now=PREFLIGHT_NOW)

    assert calls == []
    assert harness.artifact_root.exists() is False


def test_local_text_preflight_is_opt_in() -> None:
    service = OperationalService()

    with pytest.raises(ValueError, match="local_text_file_preflight_not_configured"):
        service.local_text_file_root_config_fingerprint()
