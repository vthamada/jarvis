"""Append-only persistence for human action confirmations."""

from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps, loads
from pathlib import Path
from sqlite3 import Connection, DatabaseError, IntegrityError, Row, connect
from typing import Callable, TypeVar
from uuid import uuid4

from shared.action_confirmation import (
    action_confirmation_challenge_fingerprint,
    action_confirmation_claim_fingerprint,
    action_intent_fingerprint,
    human_confirmation_receipt_fingerprint,
    require_valid_action_confirmation_challenge,
    require_valid_action_confirmation_claim,
    require_valid_action_intent,
    require_valid_human_confirmation_receipt,
    verify_action_fingerprint,
)
from shared.adapter_execution_permissions import (
    build_adapter_execution_grant_claim,
    build_adapter_execution_request,
    build_local_text_file_preflight_attestation,
    require_adapter_execution_request_matches_attestation,
    require_local_text_file_preflight_attestation_matches,
    require_valid_adapter_execution_descriptor,
    require_valid_adapter_execution_grant,
    require_valid_adapter_execution_grant_claim,
    require_valid_adapter_execution_registry_snapshot,
    require_valid_adapter_execution_request,
    require_valid_local_text_file_execution_preflight,
    require_valid_local_text_file_preflight_attestation,
    resolve_adapter_execution_descriptor,
)
from shared.adapter_permissions import (
    autonomy_policy_decision_fingerprint,
    build_adapter_grant_claim,
    require_valid_adapter_action_request,
    require_valid_adapter_descriptor,
    require_valid_adapter_grant,
    require_valid_adapter_grant_claim,
    require_valid_adapter_registry_snapshot,
    resolve_adapter_descriptor,
)
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import (
    ActionConfirmationChallengeContract,
    ActionConfirmationClaimContract,
    ActionIntentContract,
    AdapterActionRequestContract,
    AdapterDescriptorContract,
    AdapterExecutionDescriptorContract,
    AdapterExecutionGrantClaimContract,
    AdapterExecutionGrantContract,
    AdapterExecutionRegistrySnapshotContract,
    AdapterExecutionRequestContract,
    AdapterGrantClaimContract,
    AdapterGrantContract,
    AdapterRegistrySnapshotContract,
    AutonomyActionPolicyDecisionContract,
    HumanConfirmationReceiptContract,
    LocalTextFilePreflightAttestationContract,
    LocalTextFilePreflightContract,
    LocalTextFileRollbackDescriptorContract,
    LocalTextFileRollbackGrantClaimContract,
    LocalTextFileRollbackGrantContract,
    LocalTextFileRollbackRegistrySnapshotContract,
    LocalTextFileRollbackRequestContract,
    LocalTextMutationReceipt,
    LocalTextRollbackReceipt,
    OperationDispatchContract,
    WorkflowLifecycleTransitionContract,
    WorkflowPolicyDecisionContract,
)
from shared.local_text_rollback_permissions import (
    build_local_text_file_rollback_grant_claim,
    build_local_text_file_rollback_request,
    require_local_text_rollback_receipt_matches_claim,
    require_valid_local_text_file_rollback_descriptor,
    require_valid_local_text_file_rollback_grant,
    require_valid_local_text_file_rollback_grant_claim,
    require_valid_local_text_file_rollback_registry,
    require_valid_local_text_file_rollback_request,
    require_valid_local_text_mutation_receipt,
    resolve_local_text_file_rollback_descriptor,
)
from shared.types import OperationId


@dataclass(frozen=True)
class ActionConfirmationContext:
    """Hash-verified immutable confirmation chain loaded from the ledger."""

    intent: ActionIntentContract
    challenge: ActionConfirmationChallengeContract
    receipt: HumanConfirmationReceiptContract
    claim: ActionConfirmationClaimContract | None = None
    prepared_dispatch: OperationDispatchContract | None = None


@dataclass(frozen=True)
class ActionConfirmationPresentation:
    """One append-only consumption of a claim at the execution boundary."""

    presentation_id: str
    claim_id: str
    claim_fingerprint: str
    receipt_id: str
    operation_id: str
    origin_request_id: str
    action_fingerprint: str
    intent_fingerprint: str
    claimed_at: str
    verified_at: str
    operator_identity_ref: str


@dataclass(frozen=True)
class AdapterRegistryEpoch:
    """One immutable activation of an exact adapter allowlist snapshot."""

    epoch_id: int
    snapshot: AdapterRegistrySnapshotContract
    activated_at: str


@dataclass(frozen=True)
class AdapterGrantContext:
    """Hash-verified immutable adapter permission chain loaded from the ledger."""

    intent: ActionIntentContract
    action_request: AdapterActionRequestContract
    autonomy_decision: AutonomyActionPolicyDecisionContract
    registry: AdapterRegistrySnapshotContract
    descriptor: AdapterDescriptorContract
    grant: AdapterGrantContract
    claim: AdapterGrantClaimContract | None = None
    confirmation_claim: ActionConfirmationClaimContract | None = None


@dataclass(frozen=True)
class AdapterExecutionRegistryEpoch:
    """One immutable activation of an execution-only adapter allowlist."""

    epoch_id: int
    snapshot: AdapterExecutionRegistrySnapshotContract
    activated_at: str


@dataclass(frozen=True)
class AdapterExecutionGrantContext:
    """Hash-verified execution authorization chain loaded from the ledger."""

    intent: ActionIntentContract
    execution_request: AdapterExecutionRequestContract
    autonomy_decision: AutonomyActionPolicyDecisionContract
    registry: AdapterExecutionRegistrySnapshotContract
    descriptor: AdapterExecutionDescriptorContract
    source_prepare_grant: AdapterGrantContract
    preflight_attestation: LocalTextFilePreflightAttestationContract
    grant: AdapterExecutionGrantContract
    claim: AdapterExecutionGrantClaimContract | None = None
    confirmation_claim: ActionConfirmationClaimContract | None = None


@dataclass(frozen=True)
class LocalTextFileRollbackRegistryEpoch:
    """One immutable activation of the dedicated rollback allowlist."""

    epoch_id: int
    snapshot: LocalTextFileRollbackRegistrySnapshotContract
    activated_at: str


@dataclass(frozen=True)
class LocalTextFileRollbackGrantContext:
    """Hash-verified rollback authority chain and its original EXEC evidence."""

    intent: ActionIntentContract
    rollback_request: LocalTextFileRollbackRequestContract
    autonomy_decision: AutonomyActionPolicyDecisionContract
    registry: LocalTextFileRollbackRegistrySnapshotContract
    descriptor: LocalTextFileRollbackDescriptorContract
    mutation_receipt: LocalTextMutationReceipt
    source_execution_context: AdapterExecutionGrantContext
    grant: LocalTextFileRollbackGrantContract
    claim: LocalTextFileRollbackGrantClaimContract | None = None
    confirmation_claim: ActionConfirmationClaimContract | None = None
    rollback_receipt: LocalTextRollbackReceipt | None = None


ContractT = TypeVar(
    "ContractT",
    ActionIntentContract,
    ActionConfirmationChallengeContract,
    HumanConfirmationReceiptContract,
    ActionConfirmationClaimContract,
    ActionConfirmationPresentation,
)


class ActionConfirmationRepository:
    """Store action confirmation evidence in an append-only SQLite ledger."""

    def __init__(
        self,
        database_path: str | Path = ":memory:",
        *,
        trusted_execution_clock: Callable[[], str] | None = None,
    ) -> None:
        self.database_path = str(database_path)
        self._trusted_execution_clock = trusted_execution_clock or (
            lambda: datetime.now(UTC).isoformat()
        )
        if not callable(self._trusted_execution_clock):
            raise TypeError("trusted execution clock must be callable")
        self._anchor_connection: Connection | None = None
        if self.database_path == ":memory:":
            self._connection_target = (
                f"file:jarvis-action-confirmation-{uuid4().hex}?mode=memory&cache=shared"
            )
            self._connection_uri = True
            self._anchor_connection = self._new_connection()
        else:
            resolved_path = Path(self.database_path)
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection_target = str(resolved_path)
            self._connection_uri = False
        self._initialize()

    def close(self) -> None:
        """Close the anchor used by the default shared in-memory database."""

        if self._anchor_connection is not None:
            self._anchor_connection.close()
            self._anchor_connection = None

    def activate_adapter_registry(
        self,
        snapshot: AdapterRegistrySnapshotContract,
        *,
        activated_at: str,
    ) -> AdapterRegistrySnapshotContract:
        """Append one active registry epoch, idempotent only for the current snapshot."""

        require_valid_adapter_registry_snapshot(snapshot)
        self._parse_timestamp(activated_at)
        payload, payload_sha256 = self._serialize(snapshot)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                active = self._load_active_adapter_registry_epoch(
                    connection,
                    required=False,
                )
                if active is not None and active.snapshot == snapshot:
                    connection.commit()
                    return active.snapshot
                existing_fingerprint = connection.execute(
                    """
                    SELECT * FROM adapter_registry_epochs
                    WHERE registry_fingerprint = ?
                    """,
                    (snapshot.registry_fingerprint,),
                ).fetchone()
                if existing_fingerprint is not None:
                    self._decode_adapter_registry_epoch(
                        connection,
                        existing_fingerprint,
                    )
                    raise ValueError("adapter registry snapshot is stale")
                existing_version = connection.execute(
                    """
                    SELECT * FROM adapter_registry_epochs
                    WHERE registry_id = ? AND registry_version = ?
                    """,
                    (snapshot.registry_id, snapshot.registry_version),
                ).fetchone()
                if existing_version is not None:
                    self._decode_adapter_registry_epoch(connection, existing_version)
                    raise ValueError("adapter registry version already has another snapshot")
                if active is not None and active.snapshot.registry_id != snapshot.registry_id:
                    raise ValueError("adapter registry identity cannot change")

                cursor = connection.execute(
                    """
                    INSERT INTO adapter_registry_epochs (
                        registry_id,
                        registry_version,
                        registry_fingerprint,
                        activated_at,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.registry_id,
                        snapshot.registry_version,
                        snapshot.registry_fingerprint,
                        activated_at,
                        payload,
                        payload_sha256,
                    ),
                )
                epoch_id = int(cursor.lastrowid)
                for descriptor in snapshot.descriptors:
                    descriptor_payload, descriptor_payload_sha256 = self._serialize(descriptor)
                    connection.execute(
                        """
                        INSERT INTO adapter_registry_descriptors (
                            epoch_id,
                            registry_fingerprint,
                            descriptor_fingerprint,
                            adapter_id,
                            adapter_version,
                            action_kind,
                            allowed_operations,
                            allowed_resource_scopes,
                            payload,
                            payload_sha256
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            epoch_id,
                            snapshot.registry_fingerprint,
                            descriptor.descriptor_fingerprint,
                            descriptor.adapter_id,
                            descriptor.adapter_version,
                            descriptor.action_kind,
                            self._canonical_sequence(descriptor.allowed_operations),
                            self._canonical_sequence(descriptor.allowed_resource_scopes),
                            descriptor_payload,
                            descriptor_payload_sha256,
                        ),
                    )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return snapshot

    def load_active_adapter_registry(self) -> AdapterRegistrySnapshotContract:
        """Load and reverify the latest append-only registry epoch."""

        with closing(self._new_connection()) as connection:
            epoch = self._load_active_adapter_registry_epoch(connection)
        return epoch.snapshot

    def resolve_active_adapter_descriptor(
        self,
        action_request: AdapterActionRequestContract,
    ) -> tuple[AdapterRegistrySnapshotContract, AdapterDescriptorContract]:
        """Resolve one exact request against the current active registry."""

        with closing(self._new_connection()) as connection:
            epoch = self._load_active_adapter_registry_epoch(connection)
            descriptor = self._resolve_adapter_request(
                epoch.snapshot,
                action_request,
            )
        return epoch.snapshot, descriptor

    def activate_adapter_execution_registry(
        self,
        snapshot: AdapterExecutionRegistrySnapshotContract,
        *,
        activated_at: str,
    ) -> AdapterExecutionRegistrySnapshotContract:
        """Append one explicit execution-only registry epoch."""

        require_valid_adapter_execution_registry_snapshot(snapshot)
        self._parse_timestamp(activated_at)
        payload, payload_sha256 = self._serialize(snapshot)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                active = self._load_active_adapter_execution_registry_epoch(
                    connection,
                    required=False,
                )
                if active is not None and active.snapshot == snapshot:
                    connection.commit()
                    return active.snapshot
                existing_fingerprint = connection.execute(
                    """
                    SELECT * FROM adapter_execution_registry_epochs
                    WHERE registry_fingerprint = ?
                    """,
                    (snapshot.registry_fingerprint,),
                ).fetchone()
                if existing_fingerprint is not None:
                    self._decode_adapter_execution_registry_epoch(
                        connection,
                        existing_fingerprint,
                    )
                    raise ValueError("adapter execution registry snapshot is stale")
                existing_version = connection.execute(
                    """
                    SELECT * FROM adapter_execution_registry_epochs
                    WHERE registry_id = ? AND registry_version = ?
                    """,
                    (snapshot.registry_id, snapshot.registry_version),
                ).fetchone()
                if existing_version is not None:
                    self._decode_adapter_execution_registry_epoch(
                        connection,
                        existing_version,
                    )
                    raise ValueError(
                        "adapter execution registry version already has another snapshot"
                    )
                if active is not None and active.snapshot.registry_id != snapshot.registry_id:
                    raise ValueError("adapter execution registry identity cannot change")
                cursor = connection.execute(
                    """
                    INSERT INTO adapter_execution_registry_epochs (
                        registry_id,
                        registry_version,
                        registry_fingerprint,
                        activated_at,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.registry_id,
                        snapshot.registry_version,
                        snapshot.registry_fingerprint,
                        activated_at,
                        payload,
                        payload_sha256,
                    ),
                )
                epoch_id = int(cursor.lastrowid)
                for descriptor in snapshot.descriptors:
                    descriptor_payload, descriptor_payload_sha256 = self._serialize(descriptor)
                    connection.execute(
                        """
                        INSERT INTO adapter_execution_registry_descriptors (
                            epoch_id,
                            registry_fingerprint,
                            descriptor_fingerprint,
                            adapter_id,
                            adapter_version,
                            action_kind,
                            allowed_operations,
                            allowed_resource_scopes,
                            executor_ref,
                            execution_policy_version,
                            execution_backend_version,
                            payload,
                            payload_sha256
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            epoch_id,
                            snapshot.registry_fingerprint,
                            descriptor.descriptor_fingerprint,
                            descriptor.adapter_id,
                            descriptor.adapter_version,
                            descriptor.action_kind,
                            self._canonical_sequence(descriptor.allowed_operations),
                            self._canonical_sequence(descriptor.allowed_resource_scopes),
                            descriptor.executor_ref,
                            descriptor.execution_policy_version,
                            descriptor.execution_backend_version,
                            descriptor_payload,
                            descriptor_payload_sha256,
                        ),
                    )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return snapshot

    def load_active_adapter_execution_registry(
        self,
    ) -> AdapterExecutionRegistrySnapshotContract:
        """Load and reverify the latest execution-only registry epoch."""

        with closing(self._new_connection()) as connection:
            epoch = self._load_active_adapter_execution_registry_epoch(connection)
        return epoch.snapshot

    def resolve_active_adapter_execution_descriptor(
        self,
        execution_request: AdapterExecutionRequestContract,
    ) -> tuple[
        AdapterExecutionRegistrySnapshotContract,
        AdapterExecutionDescriptorContract,
    ]:
        """Resolve one exact execution request against the active execution registry."""

        with closing(self._new_connection()) as connection:
            epoch = self._load_active_adapter_execution_registry_epoch(connection)
            descriptor = self._resolve_adapter_execution_request(
                epoch.snapshot,
                execution_request,
            )
        return epoch.snapshot, descriptor

    def record_adapter_grant(
        self,
        intent: ActionIntentContract,
        grant: AdapterGrantContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        *,
        verified_at: str,
    ) -> AdapterGrantContract:
        """Append one exact metadata-only grant against the active registry."""

        intent_fingerprint = self._verify_intent(intent)
        self._require_canonical_autonomy_decision(
            autonomy_decision,
            confirmation_evidence_state="absent",
        )
        intent_payload, intent_payload_sha256 = self._serialize(intent)
        grant_payload, grant_payload_sha256 = self._serialize(grant)
        autonomy_payload, autonomy_payload_sha256 = self._serialize(autonomy_decision)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                active = self._load_active_adapter_registry_epoch(connection)
                descriptor = self._resolve_adapter_request(
                    active.snapshot,
                    grant.adapter_request,
                )
                self._verify_adapter_grant(
                    grant,
                    intent=intent,
                    intent_fingerprint=intent_fingerprint,
                    descriptor=descriptor,
                    registry=active.snapshot,
                    autonomy_decision=autonomy_decision,
                    verified_at=verified_at,
                )
                self._record_adapter_intent(
                    connection,
                    intent,
                    intent_fingerprint=intent_fingerprint,
                    payload=intent_payload,
                    payload_sha256=intent_payload_sha256,
                )
                existing = connection.execute(
                    """
                    SELECT * FROM adapter_grants
                    WHERE grant_id = ? OR grant_fingerprint = ? OR intent_id = ?
                    """,
                    (grant.grant_id, grant.grant_fingerprint, intent.intent_id),
                ).fetchone()
                if existing is not None:
                    stored = self._load_adapter_grant_context(
                        connection,
                        grant_id=existing["grant_id"],
                    )
                    if (
                        stored.grant == grant
                        and stored.intent == intent
                        and stored.autonomy_decision == autonomy_decision
                    ):
                        connection.commit()
                        return stored.grant
                    raise ValueError("adapter grant identity already has different evidence")
                connection.execute(
                    """
                    INSERT INTO adapter_grants (
                        grant_id,
                        grant_fingerprint,
                        intent_id,
                        intent_fingerprint,
                        action_fingerprint,
                        subject_ref,
                        adapter_id,
                        adapter_version,
                        action_kind,
                        operation,
                        resource_scope,
                        resource_ref,
                        descriptor_fingerprint,
                        registry_fingerprint,
                        autonomy_policy_decision_fingerprint,
                        policy_version,
                        nonce,
                        confirmation_required,
                        issued_at,
                        expires_at,
                        payload,
                        payload_sha256,
                        autonomy_policy_payload,
                        autonomy_policy_payload_sha256
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        grant.grant_id,
                        grant.grant_fingerprint,
                        grant.intent_id,
                        grant.intent_fingerprint,
                        grant.action_fingerprint,
                        grant.subject_ref,
                        grant.adapter_request.adapter_id,
                        grant.adapter_request.adapter_version,
                        grant.adapter_request.action_kind,
                        grant.adapter_request.operation,
                        grant.adapter_request.resource_scope,
                        grant.adapter_request.resource_ref,
                        grant.descriptor_fingerprint,
                        grant.registry_fingerprint,
                        grant.autonomy_policy_decision_fingerprint,
                        grant.policy_version,
                        grant.nonce,
                        grant.confirmation_required,
                        grant.issued_at,
                        grant.expires_at,
                        grant_payload,
                        grant_payload_sha256,
                        autonomy_payload,
                        autonomy_payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return grant

    def load_adapter_grant_context(self, grant_id: str) -> AdapterGrantContext:
        """Load historical grant evidence without treating it as active authority."""

        with closing(self._new_connection()) as connection:
            return self._load_adapter_grant_context(connection, grant_id=grant_id)

    def verify_adapter_grant_for_preflight_exact(
        self,
        grant_id: str,
        *,
        subject_ref: str,
        action_request: AdapterActionRequestContract,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_content_digest: str,
        expected_precondition_digest: str,
        expected_descriptor_fingerprint: str,
        expected_registry_fingerprint: str,
        expected_authorization_expires_at: str,
        preflight_expires_at: str,
        intent_fingerprint: str,
        verified_at: str,
    ) -> bool:
        """Verify an unclaimed prepare-only grant for read-only preflight."""

        try:
            with closing(self._new_connection()) as connection:
                try:
                    connection.execute("BEGIN")
                    context = self._load_adapter_grant_context(
                        connection,
                        grant_id=grant_id,
                    )
                    if context.claim is not None:
                        connection.rollback()
                        return False
                    self._verify_adapter_grant_for_preflight(
                        connection,
                        context=context,
                        subject_ref=subject_ref,
                        action_request=action_request,
                        expected_grant_fingerprint=expected_grant_fingerprint,
                        expected_action_fingerprint=expected_action_fingerprint,
                        expected_content_digest=expected_content_digest,
                        expected_precondition_digest=expected_precondition_digest,
                        expected_descriptor_fingerprint=expected_descriptor_fingerprint,
                        expected_registry_fingerprint=expected_registry_fingerprint,
                        expected_authorization_expires_at=(expected_authorization_expires_at),
                        preflight_expires_at=preflight_expires_at,
                        intent_fingerprint=intent_fingerprint,
                        verified_at=verified_at,
                    )
                    connection.rollback()
                    return True
                except (
                    AttributeError,
                    DatabaseError,
                    KeyError,
                    OverflowError,
                    TypeError,
                    ValueError,
                ):
                    try:
                        connection.rollback()
                    except DatabaseError:
                        pass
                    return False
        except (
            AttributeError,
            DatabaseError,
            OSError,
            OverflowError,
            TypeError,
            ValueError,
        ):
            return False

    def claim_adapter_grant_exact(
        self,
        grant_id: str,
        *,
        operation_id: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        claimed_at: str,
        confirmation_receipt_id: str | None = None,
    ) -> AdapterGrantClaimContract:
        """Atomically consume a grant and any required exact confirmation receipt."""

        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                context = self._load_adapter_grant_context(
                    connection,
                    grant_id=grant_id,
                )
                if context.claim is not None:
                    raise ValueError("adapter grant is already claimed")
                self._verify_adapter_grant_for_claim(
                    connection,
                    context=context,
                    subject_ref=subject_ref,
                    expected_grant_fingerprint=expected_grant_fingerprint,
                    expected_action_fingerprint=expected_action_fingerprint,
                    intent_fingerprint=intent_fingerprint,
                    verified_at=claimed_at,
                )

                confirmation_claim: ActionConfirmationClaimContract | None = None
                confirmation_context: ActionConfirmationContext | None = None
                if context.grant.confirmation_required:
                    if confirmation_receipt_id is None:
                        raise ValueError("adapter grant requires exact confirmation")
                    confirmation_context = self._load_confirmation_context(
                        connection,
                        receipt_id=confirmation_receipt_id,
                    )
                    if confirmation_context.claim is not None:
                        raise ValueError("action confirmation receipt is already claimed")
                    self._verify_adapter_confirmation_context(
                        context,
                        confirmation_context,
                    )
                    confirmation_claim = self._build_confirmation_claim(
                        confirmation_context,
                        operation_id=operation_id,
                        claimed_at=claimed_at,
                    )
                    self._verify_claim(
                        confirmation_claim,
                        context=confirmation_context,
                        expected_action_fingerprint=context.grant.action_fingerprint,
                        expected_operation_id=operation_id,
                        expected_operator_identity_ref=context.grant.subject_ref,
                        verified_at=claimed_at,
                    )
                elif confirmation_receipt_id is not None:
                    raise ValueError("adapter grant does not accept confirmation evidence")

                claim = build_adapter_grant_claim(
                    claim_id=f"adapter-grant-claim://{uuid4().hex}",
                    operation_id=OperationId(str(operation_id)),
                    grant=context.grant,
                    claimed_at=claimed_at,
                    confirmation_receipt_id=(
                        confirmation_claim.receipt_id if confirmation_claim is not None else None
                    ),
                    confirmation_claim_id=(
                        confirmation_claim.claim_id if confirmation_claim is not None else None
                    ),
                    confirmation_claim_fingerprint=(
                        action_confirmation_claim_fingerprint(confirmation_claim)
                        if confirmation_claim is not None
                        else None
                    ),
                )
                claim_payload, claim_payload_sha256 = self._serialize(claim)
                confirmation_payload: str | None = None
                confirmation_payload_sha256: str | None = None
                if confirmation_claim is not None:
                    confirmation_payload, confirmation_payload_sha256 = self._serialize(
                        confirmation_claim
                    )
                try:
                    if confirmation_claim is not None:
                        if confirmation_payload is None or confirmation_payload_sha256 is None:
                            raise ValueError("confirmation claim payload unavailable")
                        self._insert_confirmation_claim(
                            connection,
                            confirmation_claim,
                            payload=confirmation_payload,
                            payload_sha256=confirmation_payload_sha256,
                        )
                    connection.execute(
                        """
                        INSERT INTO adapter_grant_claims (
                            claim_id,
                            claim_fingerprint,
                            grant_id,
                            grant_fingerprint,
                            operation_id,
                            subject_ref,
                            intent_id,
                            intent_fingerprint,
                            action_fingerprint,
                            adapter_id,
                            adapter_version,
                            action_kind,
                            operation,
                            resource_scope,
                            resource_ref,
                            confirmation_receipt_id,
                            confirmation_claim_id,
                            confirmation_claim_fingerprint,
                            claimed_at,
                            expires_at,
                            payload,
                            payload_sha256
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?
                        )
                        """,
                        (
                            claim.claim_id,
                            claim.claim_fingerprint,
                            claim.grant_id,
                            claim.grant_fingerprint,
                            claim.operation_id,
                            claim.subject_ref,
                            claim.intent_id,
                            claim.intent_fingerprint,
                            claim.action_fingerprint,
                            claim.adapter_request.adapter_id,
                            claim.adapter_request.adapter_version,
                            claim.adapter_request.action_kind,
                            claim.adapter_request.operation,
                            claim.adapter_request.resource_scope,
                            claim.adapter_request.resource_ref,
                            claim.confirmation_receipt_id,
                            claim.confirmation_claim_id,
                            claim.confirmation_claim_fingerprint,
                            claim.claimed_at,
                            claim.expires_at,
                            claim_payload,
                            claim_payload_sha256,
                        ),
                    )
                except IntegrityError as exc:
                    raise ValueError("adapter grant is already claimed") from exc
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return claim

    def verify_adapter_grant_claim_exact(
        self,
        *,
        grant_id: str,
        claim_id: str,
        operation_id: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        claimed_at: str,
        verified_at: str,
        confirmation_receipt_id: str | None = None,
        confirmation_claim_id: str | None = None,
        confirmation_claim_fingerprint: str | None = None,
    ) -> bool:
        """Reopen and reverify one metadata-only claim against current policy state."""

        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                context = self._load_adapter_grant_context(
                    connection,
                    grant_id=grant_id,
                )
                claim = context.claim
                if claim is None:
                    connection.rollback()
                    return False
                self._verify_adapter_grant_for_claim(
                    connection,
                    context=context,
                    subject_ref=subject_ref,
                    expected_grant_fingerprint=expected_grant_fingerprint,
                    expected_action_fingerprint=expected_action_fingerprint,
                    intent_fingerprint=intent_fingerprint,
                    verified_at=verified_at,
                )
                require_valid_adapter_grant_claim(
                    claim,
                    grant=context.grant,
                    now=verified_at,
                )
                exact = all(
                    (
                        claim.claim_id == claim_id,
                        str(claim.operation_id) == str(operation_id),
                        claim.subject_ref == subject_ref,
                        claim.grant_fingerprint == expected_grant_fingerprint,
                        claim.action_fingerprint == expected_action_fingerprint,
                        claim.intent_fingerprint == intent_fingerprint,
                        claim.claimed_at == claimed_at,
                        claim.confirmation_receipt_id == confirmation_receipt_id,
                        claim.confirmation_claim_id == confirmation_claim_id,
                        claim.confirmation_claim_fingerprint == confirmation_claim_fingerprint,
                    )
                )
                if not exact:
                    connection.rollback()
                    return False
                if context.grant.confirmation_required:
                    if context.confirmation_claim is None:
                        connection.rollback()
                        return False
                    confirmation_context = self._load_confirmation_context(
                        connection,
                        receipt_id=context.confirmation_claim.receipt_id,
                    )
                    self._verify_adapter_confirmation_context(
                        context,
                        confirmation_context,
                    )
                    self._verify_claim(
                        context.confirmation_claim,
                        context=confirmation_context,
                        expected_action_fingerprint=expected_action_fingerprint,
                        expected_operation_id=operation_id,
                        expected_operator_identity_ref=subject_ref,
                        verified_at=verified_at,
                    )
                connection.rollback()
                return True
            except (DatabaseError, KeyError, TypeError, ValueError):
                connection.rollback()
                return False

    def record_local_text_file_preflight_attestation(
        self,
        preflight: LocalTextFilePreflightContract,
        *,
        attested_at: str,
    ) -> tuple[
        LocalTextFilePreflightAttestationContract,
        AdapterExecutionRequestContract,
    ]:
        """Attest one materialized preflight and persist its content-free request."""

        attested_at = self._execution_now()
        self._parse_timestamp(attested_at)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                source_context = self._load_adapter_grant_context(
                    connection,
                    grant_id=preflight.grant_id,
                )
                self._verify_local_text_file_preflight_for_attestation(
                    connection,
                    preflight=preflight,
                    source_context=source_context,
                    verified_at=attested_at,
                )
                existing = connection.execute(
                    """
                    SELECT * FROM local_text_file_preflight_attestations
                    WHERE source_preflight_grant_id = ?
                       OR preflight_fingerprint = ?
                    """,
                    (preflight.grant_id, preflight.preflight_fingerprint),
                ).fetchone()
                if existing is not None:
                    attestation, execution_request = (
                        self._decode_local_text_file_preflight_attestation(existing)
                    )
                    require_local_text_file_preflight_attestation_matches(
                        attestation,
                        preflight,
                        now=attestation.attested_at,
                    )
                    require_adapter_execution_request_matches_attestation(
                        execution_request,
                        attestation,
                        now=attested_at,
                    )
                    connection.commit()
                    return attestation, execution_request
                attestation = build_local_text_file_preflight_attestation(
                    preflight,
                    attestation_id=f"preflight-attestation://{uuid4().hex}",
                    attestation_nonce=uuid4().hex,
                    attested_at=attested_at,
                )
                execution_request = build_adapter_execution_request(
                    preflight,
                    attestation,
                )
                attestation_payload, attestation_payload_sha256 = self._serialize(attestation)
                request_payload, request_payload_sha256 = self._serialize(execution_request)
                connection.execute(
                    """
                    INSERT INTO local_text_file_preflight_attestations (
                        attestation_id,
                        attestation_fingerprint,
                        attestation_nonce,
                        trusted_boundary_ref,
                        source_preflight_grant_id,
                        source_preflight_grant_fingerprint,
                        preflight_fingerprint,
                        execution_request_fingerprint,
                        subject_ref,
                        operation,
                        resource_scope,
                        resource_ref,
                        root_config_fingerprint,
                        filesystem_snapshot_fingerprint,
                        before_content_sha256,
                        desired_content_sha256,
                        rollback_fingerprint,
                        preflight_expires_at,
                        attested_at,
                        payload,
                        payload_sha256,
                        request_payload,
                        request_payload_sha256
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        attestation.attestation_id,
                        attestation.attestation_fingerprint,
                        attestation.attestation_nonce,
                        attestation.trusted_boundary_ref,
                        attestation.source_preflight_grant_id,
                        attestation.source_preflight_grant_fingerprint,
                        attestation.preflight_fingerprint,
                        execution_request.execution_request_fingerprint,
                        attestation.subject_ref,
                        attestation.operation,
                        attestation.resource_scope,
                        attestation.resource_ref,
                        attestation.root_config_fingerprint,
                        attestation.filesystem_snapshot_fingerprint,
                        attestation.before_content_sha256,
                        attestation.desired_content_sha256,
                        attestation.rollback_fingerprint,
                        attestation.preflight_expires_at,
                        attestation.attested_at,
                        attestation_payload,
                        attestation_payload_sha256,
                        request_payload,
                        request_payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return attestation, execution_request

    def record_adapter_execution_grant(
        self,
        intent: ActionIntentContract,
        grant: AdapterExecutionGrantContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        *,
        verified_at: str,
    ) -> AdapterExecutionGrantContract:
        """Append one exact execution grant bound to one active preflight."""

        verified_at = self._execution_now()
        intent_fingerprint = self._verify_intent(intent)
        self._require_canonical_autonomy_decision(
            autonomy_decision,
            confirmation_evidence_state="absent",
        )
        intent_payload, intent_payload_sha256 = self._serialize(intent)
        grant_payload, grant_payload_sha256 = self._serialize(grant)
        autonomy_payload, autonomy_payload_sha256 = self._serialize(autonomy_decision)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                active = self._load_active_adapter_execution_registry_epoch(connection)
                descriptor = self._resolve_adapter_execution_request(
                    active.snapshot,
                    grant.execution_request,
                )
                attestation, stored_request = self._load_preflight_attestation(
                    connection,
                    attestation_id=grant.execution_request.preflight_attestation_id,
                )
                if stored_request != grant.execution_request:
                    raise ValueError("adapter execution request is not the attested request")
                require_adapter_execution_request_matches_attestation(
                    grant.execution_request,
                    attestation,
                    now=verified_at,
                )
                source_context = self._load_adapter_grant_context(
                    connection,
                    grant_id=grant.execution_request.source_preflight_grant_id,
                )
                self._verify_adapter_execution_source_prepare(
                    connection,
                    execution_request=grant.execution_request,
                    source_context=source_context,
                    verified_at=verified_at,
                )
                self._verify_adapter_execution_grant(
                    grant,
                    intent=intent,
                    intent_fingerprint=intent_fingerprint,
                    descriptor=descriptor,
                    registry=active.snapshot,
                    autonomy_decision=autonomy_decision,
                    verified_at=verified_at,
                )
                self._record_adapter_intent(
                    connection,
                    intent,
                    intent_fingerprint=intent_fingerprint,
                    payload=intent_payload,
                    payload_sha256=intent_payload_sha256,
                )
                existing = connection.execute(
                    """
                    SELECT * FROM adapter_execution_grants
                    WHERE grant_id = ?
                       OR grant_fingerprint = ?
                       OR intent_id = ?
                       OR execution_request_fingerprint = ?
                       OR preflight_fingerprint = ?
                    """,
                    (
                        grant.grant_id,
                        grant.grant_fingerprint,
                        grant.intent_id,
                        grant.execution_request.execution_request_fingerprint,
                        grant.execution_request.preflight_fingerprint,
                    ),
                ).fetchone()
                if existing is not None:
                    stored = self._load_adapter_execution_grant_context(
                        connection,
                        grant_id=existing["grant_id"],
                    )
                    if (
                        stored.grant == grant
                        and stored.intent == intent
                        and stored.autonomy_decision == autonomy_decision
                    ):
                        connection.commit()
                        return stored.grant
                    raise ValueError("adapter execution preflight already has different authority")
                request = grant.execution_request
                connection.execute(
                    """
                    INSERT INTO adapter_execution_grants (
                        grant_id,
                        grant_fingerprint,
                        intent_id,
                        intent_fingerprint,
                        action_fingerprint,
                        subject_ref,
                        adapter_id,
                        adapter_version,
                        action_kind,
                        operation,
                        resource_scope,
                        resource_ref,
                        source_preflight_grant_id,
                        source_preflight_grant_fingerprint,
                        preflight_attestation_id,
                        preflight_attestation_fingerprint,
                        preflight_fingerprint,
                        execution_request_fingerprint,
                        root_config_fingerprint,
                        before_content_sha256,
                        desired_content_sha256,
                        rollback_fingerprint,
                        descriptor_fingerprint,
                        registry_fingerprint,
                        autonomy_policy_decision_fingerprint,
                        policy_version,
                        nonce,
                        confirmation_required,
                        issued_at,
                        expires_at,
                        payload,
                        payload_sha256,
                        autonomy_policy_payload,
                        autonomy_policy_payload_sha256
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        grant.grant_id,
                        grant.grant_fingerprint,
                        grant.intent_id,
                        grant.intent_fingerprint,
                        grant.action_fingerprint,
                        grant.subject_ref,
                        request.adapter_id,
                        request.adapter_version,
                        request.action_kind,
                        request.operation,
                        request.resource_scope,
                        request.resource_ref,
                        request.source_preflight_grant_id,
                        request.source_preflight_grant_fingerprint,
                        request.preflight_attestation_id,
                        request.preflight_attestation_fingerprint,
                        request.preflight_fingerprint,
                        request.execution_request_fingerprint,
                        request.root_config_fingerprint,
                        request.before_content_sha256,
                        request.desired_content_sha256,
                        request.rollback_fingerprint,
                        grant.descriptor_fingerprint,
                        grant.registry_fingerprint,
                        grant.autonomy_policy_decision_fingerprint,
                        grant.policy_version,
                        grant.nonce,
                        grant.confirmation_required,
                        grant.issued_at,
                        grant.expires_at,
                        grant_payload,
                        grant_payload_sha256,
                        autonomy_payload,
                        autonomy_payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return grant

    def load_adapter_execution_grant_context(
        self,
        grant_id: str,
    ) -> AdapterExecutionGrantContext:
        """Load immutable execution evidence without reopening active authority."""

        with closing(self._new_connection()) as connection:
            return self._load_adapter_execution_grant_context(
                connection,
                grant_id=grant_id,
            )

    def load_adapter_execution_claim_for_recovery_exact(
        self,
        operation_id: str,
        *,
        journal_reservation_fingerprint: str | None = None,
    ) -> AdapterExecutionGrantClaimContract:
        """Locate and verify historical claim evidence without reopening authority."""

        with closing(self._new_connection()) as connection:
            if journal_reservation_fingerprint is None:
                row = connection.execute(
                    """
                    SELECT * FROM adapter_execution_grant_claims
                    WHERE operation_id = ?
                    """,
                    (operation_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT * FROM adapter_execution_grant_claims
                    WHERE operation_id = ? AND journal_reservation_fingerprint = ?
                    """,
                    (operation_id, journal_reservation_fingerprint),
                ).fetchone()
            if row is None:
                raise KeyError(f"unknown adapter execution operation: {operation_id}")
            claim = self._decode_adapter_execution_grant_claim(row)
            context = self._load_adapter_execution_grant_context(
                connection,
                grant_id=claim.grant_id,
            )
            if context.claim != claim:
                raise ValueError("adapter execution recovery claim mismatch")
            self._require_adapter_execution_recovery_context(
                connection,
                context=context,
                claim=claim,
            )
            return claim

    def verify_adapter_execution_grant_for_staging_exact(
        self,
        grant_id: str,
        *,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_execution_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
        verified_at: str,
    ) -> bool:
        """Verify confirmation and active execution authority before any staging I/O."""

        verified_at = self._execution_now()
        try:
            with closing(self._new_connection()) as connection:
                try:
                    connection.execute("BEGIN")
                    context = self._load_adapter_execution_grant_context(
                        connection,
                        grant_id=grant_id,
                    )
                    if context.claim is not None:
                        connection.rollback()
                        return False
                    self._verify_adapter_execution_grant_for_active_use(
                        connection,
                        context=context,
                        subject_ref=subject_ref,
                        expected_grant_fingerprint=expected_grant_fingerprint,
                        expected_action_fingerprint=expected_action_fingerprint,
                        expected_execution_request_fingerprint=(
                            expected_execution_request_fingerprint
                        ),
                        intent_fingerprint=intent_fingerprint,
                        verified_at=verified_at,
                    )
                    confirmation_context = self._load_confirmation_context(
                        connection,
                        receipt_id=confirmation_receipt_id,
                    )
                    if confirmation_context.claim is not None:
                        connection.rollback()
                        return False
                    self._verify_adapter_execution_confirmation_context(
                        context,
                        confirmation_context,
                    )
                    self._verify_receipt(
                        confirmation_context.receipt,
                        intent=confirmation_context.intent,
                        challenge=confirmation_context.challenge,
                        verified_at=verified_at,
                    )
                    connection.rollback()
                    return True
                except (
                    AttributeError,
                    DatabaseError,
                    KeyError,
                    OverflowError,
                    TypeError,
                    ValueError,
                ):
                    try:
                        connection.rollback()
                    except DatabaseError:
                        pass
                    return False
        except (DatabaseError, OSError, OverflowError, TypeError, ValueError):
            return False

    def claim_adapter_execution_grant_exact(
        self,
        grant_id: str,
        *,
        operation_id: str,
        journal_reservation_fingerprint: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_execution_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
        claimed_at: str,
    ) -> AdapterExecutionGrantClaimContract:
        """Atomically claim execution plus confirmation; exact retries are idempotent."""

        claimed_at = self._execution_now()
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                context = self._load_adapter_execution_grant_context(
                    connection,
                    grant_id=grant_id,
                )
                if context.claim is not None:
                    if not self._adapter_execution_claim_matches(
                        context.claim,
                        operation_id=operation_id,
                        journal_reservation_fingerprint=(journal_reservation_fingerprint),
                        subject_ref=subject_ref,
                        expected_grant_fingerprint=expected_grant_fingerprint,
                        expected_action_fingerprint=expected_action_fingerprint,
                        expected_execution_request_fingerprint=(
                            expected_execution_request_fingerprint
                        ),
                        intent_fingerprint=intent_fingerprint,
                        confirmation_receipt_id=confirmation_receipt_id,
                    ):
                        raise ValueError("adapter execution grant is already claimed")
                    connection.commit()
                    return context.claim
                self._verify_adapter_execution_grant_for_active_use(
                    connection,
                    context=context,
                    subject_ref=subject_ref,
                    expected_grant_fingerprint=expected_grant_fingerprint,
                    expected_action_fingerprint=expected_action_fingerprint,
                    expected_execution_request_fingerprint=(expected_execution_request_fingerprint),
                    intent_fingerprint=intent_fingerprint,
                    verified_at=claimed_at,
                )
                confirmation_context = self._load_confirmation_context(
                    connection,
                    receipt_id=confirmation_receipt_id,
                )
                if confirmation_context.claim is not None:
                    raise ValueError("action confirmation receipt is already claimed")
                self._verify_adapter_execution_confirmation_context(
                    context,
                    confirmation_context,
                )
                confirmation_claim = self._build_confirmation_claim(
                    confirmation_context,
                    operation_id=operation_id,
                    claimed_at=claimed_at,
                )
                self._verify_claim(
                    confirmation_claim,
                    context=confirmation_context,
                    expected_action_fingerprint=context.grant.action_fingerprint,
                    expected_operation_id=operation_id,
                    expected_operator_identity_ref=context.grant.subject_ref,
                    verified_at=claimed_at,
                )
                claim = build_adapter_execution_grant_claim(
                    claim_id=f"adapter-execution-claim://{uuid4().hex}",
                    operation_id=OperationId(str(operation_id)),
                    journal_reservation_fingerprint=journal_reservation_fingerprint,
                    grant=context.grant,
                    claimed_at=claimed_at,
                    confirmation_receipt_id=confirmation_claim.receipt_id,
                    confirmation_claim_id=confirmation_claim.claim_id,
                    confirmation_claim_fingerprint=(
                        action_confirmation_claim_fingerprint(confirmation_claim)
                    ),
                )
                confirmation_payload, confirmation_payload_sha256 = self._serialize(
                    confirmation_claim
                )
                claim_payload, claim_payload_sha256 = self._serialize(claim)
                try:
                    self._insert_confirmation_claim(
                        connection,
                        confirmation_claim,
                        payload=confirmation_payload,
                        payload_sha256=confirmation_payload_sha256,
                    )
                    self._insert_adapter_execution_claim(
                        connection,
                        claim,
                        payload=claim_payload,
                        payload_sha256=claim_payload_sha256,
                    )
                except IntegrityError as exc:
                    raise ValueError("adapter execution grant is already claimed") from exc
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return claim

    def verify_adapter_execution_claim_for_effect_start_exact(
        self,
        claim: AdapterExecutionGrantClaimContract,
        *,
        observed_root_config_fingerprint: str,
        observed_precondition_content_sha256: str,
        observed_desired_content_sha256: str,
        verified_at: str,
    ) -> bool:
        """Reverify a persisted claim and active physical bindings before first effect."""

        verified_at = self._execution_now()
        try:
            with closing(self._new_connection()) as connection:
                connection.execute("BEGIN")
                context = self._load_adapter_execution_grant_context(
                    connection,
                    grant_id=claim.grant_id,
                )
                if context.claim != claim:
                    connection.rollback()
                    return False
                require_valid_adapter_execution_grant_claim(
                    claim,
                    grant=context.grant,
                    now=verified_at,
                    require_active=True,
                )
                self._verify_adapter_execution_grant_for_active_use(
                    connection,
                    context=context,
                    subject_ref=claim.subject_ref,
                    expected_grant_fingerprint=claim.grant_fingerprint,
                    expected_action_fingerprint=claim.action_fingerprint,
                    expected_execution_request_fingerprint=(
                        claim.execution_request.execution_request_fingerprint
                    ),
                    intent_fingerprint=claim.intent_fingerprint,
                    verified_at=verified_at,
                )
                request = context.execution_request
                if (
                    observed_root_config_fingerprint != request.root_config_fingerprint
                    or observed_precondition_content_sha256 != request.precondition_content_sha256
                    or observed_desired_content_sha256 != request.desired_content_sha256
                ):
                    connection.rollback()
                    return False
                if context.confirmation_claim is None:
                    connection.rollback()
                    return False
                confirmation_context = self._load_confirmation_context(
                    connection,
                    receipt_id=context.confirmation_claim.receipt_id,
                )
                self._verify_adapter_execution_confirmation_context(
                    context,
                    confirmation_context,
                )
                self._verify_claim(
                    context.confirmation_claim,
                    context=confirmation_context,
                    expected_action_fingerprint=claim.action_fingerprint,
                    expected_operation_id=str(claim.operation_id),
                    expected_operator_identity_ref=claim.subject_ref,
                    verified_at=verified_at,
                )
                connection.rollback()
                return True
        except (
            AttributeError,
            DatabaseError,
            KeyError,
            OSError,
            OverflowError,
            TypeError,
            ValueError,
        ):
            return False

    def verify_adapter_execution_claim_for_recovery_exact(
        self,
        claim: AdapterExecutionGrantClaimContract,
    ) -> bool:
        """Verify historical claim evidence without granting a new mutation."""

        try:
            with closing(self._new_connection()) as connection:
                connection.execute("BEGIN")
                context = self._load_adapter_execution_grant_context(
                    connection,
                    grant_id=claim.grant_id,
                )
                if context.claim != claim:
                    connection.rollback()
                    return False
                self._require_adapter_execution_recovery_context(
                    connection,
                    context=context,
                    claim=claim,
                )
                connection.rollback()
                return True
        except (
            AttributeError,
            DatabaseError,
            KeyError,
            OSError,
            OverflowError,
            TypeError,
            ValueError,
        ):
            return False

    def activate_local_text_file_rollback_registry(
        self,
        snapshot: LocalTextFileRollbackRegistrySnapshotContract,
    ) -> LocalTextFileRollbackRegistrySnapshotContract:
        """Append one explicit rollback-only registry epoch."""

        activated_at = self._execution_now()
        require_valid_local_text_file_rollback_registry(snapshot)
        payload, payload_sha256 = self._serialize(snapshot)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                active = self._load_active_local_text_file_rollback_registry_epoch(
                    connection,
                    required=False,
                )
                if active is not None and active.snapshot == snapshot:
                    connection.commit()
                    return active.snapshot
                existing = connection.execute(
                    """
                    SELECT * FROM local_text_file_rollback_registry_epochs
                    WHERE registry_fingerprint = ?
                       OR (registry_id = ? AND registry_version = ?)
                    """,
                    (
                        snapshot.registry_fingerprint,
                        snapshot.registry_id,
                        snapshot.registry_version,
                    ),
                ).fetchone()
                if existing is not None:
                    self._decode_local_text_file_rollback_registry_epoch(
                        connection,
                        existing,
                    )
                    raise ValueError("local text rollback registry snapshot is stale")
                if active is not None and active.snapshot.registry_id != snapshot.registry_id:
                    raise ValueError("local text rollback registry identity cannot change")
                cursor = connection.execute(
                    """
                    INSERT INTO local_text_file_rollback_registry_epochs (
                        registry_id,
                        registry_version,
                        registry_fingerprint,
                        activated_at,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.registry_id,
                        snapshot.registry_version,
                        snapshot.registry_fingerprint,
                        activated_at,
                        payload,
                        payload_sha256,
                    ),
                )
                epoch_id = int(cursor.lastrowid)
                for descriptor in snapshot.descriptors:
                    descriptor_payload, descriptor_payload_sha256 = self._serialize(descriptor)
                    connection.execute(
                        """
                        INSERT INTO local_text_file_rollback_registry_descriptors (
                            epoch_id,
                            registry_fingerprint,
                            descriptor_fingerprint,
                            adapter_id,
                            adapter_version,
                            action_kind,
                            purpose,
                            allowed_operations,
                            allowed_resource_scopes,
                            executor_ref,
                            rollback_policy_version,
                            rollback_backend_version,
                            payload,
                            payload_sha256
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            epoch_id,
                            snapshot.registry_fingerprint,
                            descriptor.descriptor_fingerprint,
                            descriptor.adapter_id,
                            descriptor.adapter_version,
                            descriptor.action_kind,
                            descriptor.purpose,
                            self._canonical_sequence(descriptor.allowed_operations),
                            self._canonical_sequence(descriptor.allowed_resource_scopes),
                            descriptor.executor_ref,
                            descriptor.rollback_policy_version,
                            descriptor.rollback_backend_version,
                            descriptor_payload,
                            descriptor_payload_sha256,
                        ),
                    )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return snapshot

    def record_local_text_mutation_receipt(
        self,
        receipt: LocalTextMutationReceipt,
    ) -> LocalTextMutationReceipt:
        """Append one exact engine receipt after validating its persisted EXEC chain."""

        verified_at = self._execution_now()
        require_valid_local_text_mutation_receipt(receipt)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                source_context = self._load_adapter_execution_grant_context(
                    connection,
                    grant_id=receipt.execution_grant_id,
                )
                self._require_local_text_mutation_receipt_matches_execution(
                    connection,
                    receipt=receipt,
                    source_context=source_context,
                    verified_at=verified_at,
                )
                existing = connection.execute(
                    """
                    SELECT * FROM local_text_mutation_receipts
                    WHERE receipt_fingerprint = ?
                       OR execution_grant_id = ?
                       OR execution_claim_id = ?
                       OR mutation_operation_id = ?
                       OR applied_event_fingerprint = ?
                    """,
                    (
                        receipt.receipt_fingerprint,
                        receipt.execution_grant_id,
                        receipt.execution_claim_id,
                        receipt.operation_id,
                        receipt.applied_event_fingerprint,
                    ),
                ).fetchone()
                if existing is not None:
                    stored = self._decode_local_text_mutation_receipt(existing)
                    if stored != receipt:
                        raise ValueError("mutation already has different receipt evidence")
                    connection.commit()
                    return stored
                payload, payload_sha256 = self._serialize(receipt)
                connection.execute(
                    """
                    INSERT INTO local_text_mutation_receipts (
                        receipt_fingerprint,
                        mutation_operation_id,
                        execution_grant_id,
                        execution_claim_id,
                        applied_event_fingerprint,
                        resource_ref,
                        subject_ref,
                        preflight_fingerprint,
                        before_content_sha256,
                        desired_content_sha256,
                        root_config_fingerprint,
                        committed_at,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.receipt_fingerprint,
                        receipt.operation_id,
                        receipt.execution_grant_id,
                        receipt.execution_claim_id,
                        receipt.applied_event_fingerprint,
                        receipt.resource_ref,
                        receipt.subject_ref,
                        receipt.preflight_fingerprint,
                        receipt.before_content_sha256,
                        receipt.desired_content_sha256,
                        receipt.root_config_fingerprint,
                        receipt.committed_at,
                        payload,
                        payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return receipt

    def load_local_text_mutation_receipt_exact(
        self,
        operation_id: str,
        *,
        expected_receipt_fingerprint: str,
    ) -> LocalTextMutationReceipt:
        """Load immutable mutation proof only when both exact identities match."""

        verified_at = self._execution_now()
        with closing(self._new_connection()) as connection:
            row = connection.execute(
                """
                SELECT * FROM local_text_mutation_receipts
                WHERE mutation_operation_id = ?
                  AND receipt_fingerprint = ?
                """,
                (operation_id, expected_receipt_fingerprint),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown local text mutation receipt: {operation_id}")
            receipt = self._decode_local_text_mutation_receipt(row)
            source_context = self._load_adapter_execution_grant_context(
                connection,
                grant_id=receipt.execution_grant_id,
            )
            self._require_local_text_mutation_receipt_matches_execution(
                connection,
                receipt=receipt,
                source_context=source_context,
                verified_at=verified_at,
            )
            return receipt

    def verify_local_text_mutation_receipt_exact(
        self,
        receipt: LocalTextMutationReceipt,
    ) -> bool:
        """Fail closed unless caller evidence equals the complete stored proof."""

        try:
            stored = self.load_local_text_mutation_receipt_exact(
                receipt.operation_id,
                expected_receipt_fingerprint=receipt.receipt_fingerprint,
            )
        except Exception:
            return False
        return stored == receipt

    def load_active_local_text_file_rollback_registry(
        self,
    ) -> LocalTextFileRollbackRegistrySnapshotContract:
        with closing(self._new_connection()) as connection:
            epoch = self._load_active_local_text_file_rollback_registry_epoch(connection)
        return epoch.snapshot

    def resolve_active_local_text_file_rollback_descriptor(
        self,
        request: LocalTextFileRollbackRequestContract,
    ) -> tuple[
        LocalTextFileRollbackRegistrySnapshotContract,
        LocalTextFileRollbackDescriptorContract,
    ]:
        with closing(self._new_connection()) as connection:
            epoch = self._load_active_local_text_file_rollback_registry_epoch(connection)
            descriptor = self._resolve_local_text_file_rollback_request(
                epoch.snapshot,
                request,
            )
        return epoch.snapshot, descriptor

    def prepare_local_text_file_rollback(
        self,
        mutation_receipt: LocalTextMutationReceipt,
        *,
        rollback_operation_id: str,
    ) -> LocalTextFileRollbackRequestContract:
        """Load a persisted mutation receipt and derive one exact rollback request."""

        requested_at = self._execution_now()
        require_valid_local_text_mutation_receipt(mutation_receipt)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                stored_receipt = self._load_local_text_mutation_receipt(
                    connection,
                    receipt_fingerprint=mutation_receipt.receipt_fingerprint,
                )
                if stored_receipt != mutation_receipt:
                    raise ValueError("rollback mutation receipt differs from ledger")
                source_context = self._load_adapter_execution_grant_context(
                    connection,
                    grant_id=stored_receipt.execution_grant_id,
                )
                self._require_local_text_mutation_receipt_matches_execution(
                    connection,
                    receipt=stored_receipt,
                    source_context=source_context,
                    verified_at=requested_at,
                )
                if source_context.claim is None:  # narrowed by the exact validator
                    raise ValueError("mutation receipt has no persisted execution claim")
                existing = connection.execute(
                    """
                    SELECT * FROM local_text_file_rollback_requests
                    WHERE rollback_operation_id = ?
                       OR mutation_receipt_fingerprint = ?
                    """,
                    (
                        rollback_operation_id,
                        stored_receipt.receipt_fingerprint,
                    ),
                ).fetchone()
                if existing is not None:
                    stored_request = self._decode_local_text_file_rollback_request(existing)
                    if (
                        str(stored_request.rollback_operation_id) != rollback_operation_id
                        or stored_request.mutation_receipt_fingerprint
                        != stored_receipt.receipt_fingerprint
                    ):
                        raise ValueError("mutation already has another rollback request")
                    self._verify_local_text_file_rollback_source(
                        connection,
                        request=stored_request,
                        mutation_receipt=stored_receipt,
                        source_context=source_context,
                    )
                    connection.commit()
                    return stored_request
                request = build_local_text_file_rollback_request(
                    stored_receipt,
                    source_execution_grant=source_context.grant,
                    source_execution_claim=source_context.claim,
                    rollback_operation_id=rollback_operation_id,
                    requested_at=requested_at,
                )
                request_payload, request_payload_sha256 = self._serialize(request)
                connection.execute(
                    """
                    INSERT INTO local_text_file_rollback_requests (
                        rollback_request_fingerprint,
                        rollback_operation_id,
                        mutation_receipt_fingerprint,
                        requested_at,
                        expires_at,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.rollback_request_fingerprint,
                        request.rollback_operation_id,
                        stored_receipt.receipt_fingerprint,
                        request.requested_at,
                        request.expires_at,
                        request_payload,
                        request_payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return request

    def record_local_text_file_rollback_grant(
        self,
        intent: ActionIntentContract,
        grant: LocalTextFileRollbackGrantContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
    ) -> LocalTextFileRollbackGrantContract:
        verified_at = self._execution_now()
        intent_fingerprint = self._verify_intent(intent)
        self._require_canonical_autonomy_decision(
            autonomy_decision,
            confirmation_evidence_state="absent",
        )
        intent_payload, intent_payload_sha256 = self._serialize(intent)
        grant_payload, grant_payload_sha256 = self._serialize(grant)
        autonomy_payload, autonomy_payload_sha256 = self._serialize(autonomy_decision)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                active = self._load_active_local_text_file_rollback_registry_epoch(connection)
                descriptor = self._resolve_local_text_file_rollback_request(
                    active.snapshot,
                    grant.rollback_request,
                )
                mutation_receipt = self._load_local_text_mutation_receipt(
                    connection,
                    receipt_fingerprint=(grant.rollback_request.mutation_receipt_fingerprint),
                )
                stored_request = self._load_local_text_file_rollback_request(
                    connection,
                    rollback_request_fingerprint=(
                        grant.rollback_request.rollback_request_fingerprint
                    ),
                )
                if stored_request != grant.rollback_request:
                    raise ValueError("rollback grant request is not the persisted request")
                source_context = self._load_adapter_execution_grant_context(
                    connection,
                    grant_id=grant.rollback_request.source_execution_grant_id,
                )
                self._verify_local_text_file_rollback_source(
                    connection,
                    request=grant.rollback_request,
                    mutation_receipt=mutation_receipt,
                    source_context=source_context,
                )
                self._verify_local_text_file_rollback_grant(
                    grant,
                    intent=intent,
                    intent_fingerprint=intent_fingerprint,
                    descriptor=descriptor,
                    registry=active.snapshot,
                    autonomy_decision=autonomy_decision,
                    verified_at=verified_at,
                )
                self._record_adapter_intent(
                    connection,
                    intent,
                    intent_fingerprint=intent_fingerprint,
                    payload=intent_payload,
                    payload_sha256=intent_payload_sha256,
                )
                existing = connection.execute(
                    """
                    SELECT * FROM local_text_file_rollback_grants
                    WHERE grant_id = ?
                       OR grant_fingerprint = ?
                       OR intent_id = ?
                       OR rollback_request_fingerprint = ?
                       OR mutation_receipt_fingerprint = ?
                       OR rollback_operation_id = ?
                    """,
                    (
                        grant.grant_id,
                        grant.grant_fingerprint,
                        grant.intent_id,
                        grant.rollback_request.rollback_request_fingerprint,
                        grant.rollback_request.mutation_receipt_fingerprint,
                        grant.rollback_request.rollback_operation_id,
                    ),
                ).fetchone()
                if existing is not None:
                    stored = self._load_local_text_file_rollback_grant_context(
                        connection,
                        grant_id=existing["grant_id"],
                    )
                    if (
                        stored.grant == grant
                        and stored.intent == intent
                        and stored.autonomy_decision == autonomy_decision
                    ):
                        connection.commit()
                        return stored.grant
                    raise ValueError("mutation already has different rollback authority")
                request = grant.rollback_request
                connection.execute(
                    """
                    INSERT INTO local_text_file_rollback_grants (
                        grant_id,
                        grant_fingerprint,
                        intent_id,
                        intent_fingerprint,
                        action_fingerprint,
                        subject_ref,
                        rollback_operation_id,
                        mutation_operation_id,
                        mutation_receipt_fingerprint,
                        source_execution_grant_id,
                        source_execution_claim_id,
                        rollback_request_fingerprint,
                        resource_ref,
                        root_config_fingerprint,
                        expected_current_sha256,
                        restored_content_sha256,
                        rollback_plan_fingerprint,
                        descriptor_fingerprint,
                        registry_fingerprint,
                        autonomy_policy_decision_fingerprint,
                        policy_version,
                        nonce,
                        confirmation_required,
                        issued_at,
                        expires_at,
                        payload,
                        payload_sha256,
                        autonomy_policy_payload,
                        autonomy_policy_payload_sha256
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        grant.grant_id,
                        grant.grant_fingerprint,
                        grant.intent_id,
                        grant.intent_fingerprint,
                        grant.action_fingerprint,
                        grant.subject_ref,
                        request.rollback_operation_id,
                        request.mutation_operation_id,
                        request.mutation_receipt_fingerprint,
                        request.source_execution_grant_id,
                        request.source_execution_claim_id,
                        request.rollback_request_fingerprint,
                        request.resource_ref,
                        request.root_config_fingerprint,
                        request.expected_current_sha256,
                        request.restored_content_sha256,
                        request.rollback_plan_fingerprint,
                        grant.descriptor_fingerprint,
                        grant.registry_fingerprint,
                        grant.autonomy_policy_decision_fingerprint,
                        grant.policy_version,
                        grant.nonce,
                        grant.confirmation_required,
                        grant.issued_at,
                        grant.expires_at,
                        grant_payload,
                        grant_payload_sha256,
                        autonomy_payload,
                        autonomy_payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return grant

    def load_local_text_file_rollback_grant_context(
        self,
        grant_id: str,
    ) -> LocalTextFileRollbackGrantContext:
        with closing(self._new_connection()) as connection:
            return self._load_local_text_file_rollback_grant_context(
                connection,
                grant_id=grant_id,
            )

    def verify_local_text_file_rollback_grant_for_staging_exact(
        self,
        grant_id: str,
        *,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_rollback_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> bool:
        verified_at = self._execution_now()
        try:
            with closing(self._new_connection()) as connection:
                connection.execute("BEGIN")
                context = self._load_local_text_file_rollback_grant_context(
                    connection,
                    grant_id=grant_id,
                )
                if context.claim is not None or context.rollback_receipt is not None:
                    connection.rollback()
                    return False
                self._verify_local_text_file_rollback_grant_for_active_use(
                    connection,
                    context=context,
                    subject_ref=subject_ref,
                    expected_grant_fingerprint=expected_grant_fingerprint,
                    expected_action_fingerprint=expected_action_fingerprint,
                    expected_rollback_request_fingerprint=(expected_rollback_request_fingerprint),
                    intent_fingerprint=intent_fingerprint,
                    verified_at=verified_at,
                )
                confirmation_context = self._load_confirmation_context(
                    connection,
                    receipt_id=confirmation_receipt_id,
                )
                if confirmation_context.claim is not None:
                    connection.rollback()
                    return False
                self._verify_local_text_file_rollback_confirmation_context(
                    context,
                    confirmation_context,
                )
                self._verify_receipt(
                    confirmation_context.receipt,
                    intent=confirmation_context.intent,
                    challenge=confirmation_context.challenge,
                    verified_at=verified_at,
                )
                connection.rollback()
                return True
        except (
            AttributeError,
            DatabaseError,
            KeyError,
            OSError,
            OverflowError,
            TypeError,
            ValueError,
        ):
            return False

    def claim_local_text_file_rollback_grant_exact(
        self,
        grant_id: str,
        *,
        rollback_operation_id: str,
        rollback_journal_reservation_fingerprint: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_rollback_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> LocalTextFileRollbackGrantClaimContract:
        claimed_at = self._execution_now()
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                context = self._load_local_text_file_rollback_grant_context(
                    connection,
                    grant_id=grant_id,
                )
                source_claim = context.source_execution_context.claim
                if source_claim is None:
                    raise ValueError("local text rollback source claim is missing")
                if (
                    rollback_journal_reservation_fingerprint
                    == source_claim.journal_reservation_fingerprint
                ):
                    raise ValueError("local text rollback reservation must differ from apply")
                if context.claim is not None:
                    if not self._local_text_file_rollback_claim_matches(
                        context.claim,
                        rollback_operation_id=rollback_operation_id,
                        rollback_journal_reservation_fingerprint=(
                            rollback_journal_reservation_fingerprint
                        ),
                        subject_ref=subject_ref,
                        expected_grant_fingerprint=expected_grant_fingerprint,
                        expected_action_fingerprint=expected_action_fingerprint,
                        expected_rollback_request_fingerprint=(
                            expected_rollback_request_fingerprint
                        ),
                        intent_fingerprint=intent_fingerprint,
                        confirmation_receipt_id=confirmation_receipt_id,
                    ):
                        raise ValueError("local text rollback grant is already claimed")
                    connection.commit()
                    return context.claim
                self._verify_local_text_file_rollback_grant_for_active_use(
                    connection,
                    context=context,
                    subject_ref=subject_ref,
                    expected_grant_fingerprint=expected_grant_fingerprint,
                    expected_action_fingerprint=expected_action_fingerprint,
                    expected_rollback_request_fingerprint=(expected_rollback_request_fingerprint),
                    intent_fingerprint=intent_fingerprint,
                    verified_at=claimed_at,
                )
                if rollback_operation_id != str(context.rollback_request.rollback_operation_id):
                    raise ValueError("local text rollback operation id mismatch")
                confirmation_context = self._load_confirmation_context(
                    connection,
                    receipt_id=confirmation_receipt_id,
                )
                if confirmation_context.claim is not None:
                    raise ValueError("action confirmation receipt is already claimed")
                self._verify_local_text_file_rollback_confirmation_context(
                    context,
                    confirmation_context,
                )
                confirmation_claim = self._build_confirmation_claim(
                    confirmation_context,
                    operation_id=rollback_operation_id,
                    claimed_at=claimed_at,
                )
                self._verify_claim(
                    confirmation_claim,
                    context=confirmation_context,
                    expected_action_fingerprint=context.grant.action_fingerprint,
                    expected_operation_id=rollback_operation_id,
                    expected_operator_identity_ref=context.grant.subject_ref,
                    verified_at=claimed_at,
                )
                claim = build_local_text_file_rollback_grant_claim(
                    claim_id=f"local-text-rollback-claim://{uuid4().hex}",
                    grant=context.grant,
                    rollback_journal_reservation_fingerprint=(
                        rollback_journal_reservation_fingerprint
                    ),
                    claimed_at=claimed_at,
                    confirmation_receipt_id=confirmation_claim.receipt_id,
                    confirmation_claim_id=confirmation_claim.claim_id,
                    confirmation_claim_fingerprint=(
                        action_confirmation_claim_fingerprint(confirmation_claim)
                    ),
                )
                confirmation_payload, confirmation_payload_sha256 = self._serialize(
                    confirmation_claim
                )
                claim_payload, claim_payload_sha256 = self._serialize(claim)
                try:
                    self._insert_confirmation_claim(
                        connection,
                        confirmation_claim,
                        payload=confirmation_payload,
                        payload_sha256=confirmation_payload_sha256,
                    )
                    self._insert_local_text_file_rollback_claim(
                        connection,
                        claim,
                        payload=claim_payload,
                        payload_sha256=claim_payload_sha256,
                    )
                except IntegrityError as exc:
                    raise ValueError("local text rollback grant is already claimed") from exc
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return claim

    def verify_local_text_file_rollback_claim_for_effect_start_exact(
        self,
        claim: LocalTextFileRollbackGrantClaimContract,
        *,
        observed_root_config_fingerprint: str,
        observed_expected_current_sha256: str,
        observed_restored_content_sha256: str,
    ) -> bool:
        verified_at = self._execution_now()
        try:
            with closing(self._new_connection()) as connection:
                connection.execute("BEGIN")
                context = self._load_local_text_file_rollback_grant_context(
                    connection,
                    grant_id=claim.grant_id,
                )
                if context.claim != claim or context.rollback_receipt is not None:
                    connection.rollback()
                    return False
                require_valid_local_text_file_rollback_grant_claim(
                    claim,
                    grant=context.grant,
                    now=verified_at,
                    require_active=True,
                )
                self._verify_local_text_file_rollback_grant_for_active_use(
                    connection,
                    context=context,
                    subject_ref=claim.subject_ref,
                    expected_grant_fingerprint=claim.grant_fingerprint,
                    expected_action_fingerprint=claim.action_fingerprint,
                    expected_rollback_request_fingerprint=(
                        claim.rollback_request.rollback_request_fingerprint
                    ),
                    intent_fingerprint=claim.intent_fingerprint,
                    verified_at=verified_at,
                )
                request = context.rollback_request
                if (
                    observed_root_config_fingerprint != request.root_config_fingerprint
                    or observed_expected_current_sha256 != request.expected_current_sha256
                    or observed_restored_content_sha256 != request.restored_content_sha256
                ):
                    connection.rollback()
                    return False
                self._require_local_text_file_rollback_recovery_context(
                    connection,
                    context=context,
                    claim=claim,
                )
                connection.rollback()
                return True
        except (
            AttributeError,
            DatabaseError,
            KeyError,
            OSError,
            OverflowError,
            TypeError,
            ValueError,
        ):
            return False

    def verify_local_text_file_rollback_claim_for_recovery_exact(
        self,
        claim: LocalTextFileRollbackGrantClaimContract,
    ) -> bool:
        try:
            with closing(self._new_connection()) as connection:
                connection.execute("BEGIN")
                context = self._load_local_text_file_rollback_grant_context(
                    connection,
                    grant_id=claim.grant_id,
                )
                self._require_local_text_file_rollback_recovery_context(
                    connection,
                    context=context,
                    claim=claim,
                )
                connection.rollback()
                return True
        except (
            AttributeError,
            DatabaseError,
            KeyError,
            OSError,
            OverflowError,
            TypeError,
            ValueError,
        ):
            return False

    def load_local_text_file_rollback_claim_for_recovery_exact(
        self,
        rollback_operation_id: str,
        *,
        rollback_journal_reservation_fingerprint: str | None = None,
    ) -> LocalTextFileRollbackGrantClaimContract:
        with closing(self._new_connection()) as connection:
            if rollback_journal_reservation_fingerprint is None:
                row = connection.execute(
                    """
                    SELECT * FROM local_text_file_rollback_grant_claims
                    WHERE rollback_operation_id = ?
                    """,
                    (rollback_operation_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT * FROM local_text_file_rollback_grant_claims
                    WHERE rollback_operation_id = ?
                      AND rollback_journal_reservation_fingerprint = ?
                    """,
                    (
                        rollback_operation_id,
                        rollback_journal_reservation_fingerprint,
                    ),
                ).fetchone()
            if row is None:
                raise KeyError(f"unknown local text rollback: {rollback_operation_id}")
            claim = self._decode_local_text_file_rollback_claim(row)
            context = self._load_local_text_file_rollback_grant_context(
                connection,
                grant_id=claim.grant_id,
            )
            self._require_local_text_file_rollback_recovery_context(
                connection,
                context=context,
                claim=claim,
            )
            return claim

    def record_local_text_rollback_receipt(
        self,
        receipt: LocalTextRollbackReceipt,
    ) -> LocalTextRollbackReceipt:
        verified_at = self._execution_now()
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                claim_row = connection.execute(
                    """
                    SELECT * FROM local_text_file_rollback_grant_claims
                    WHERE claim_id = ?
                    """,
                    (receipt.rollback_claim_id,),
                ).fetchone()
                if claim_row is None:
                    raise KeyError("unknown local text rollback claim")
                claim = self._decode_local_text_file_rollback_claim(claim_row)
                context = self._load_local_text_file_rollback_grant_context(
                    connection,
                    grant_id=claim.grant_id,
                )
                self._require_local_text_file_rollback_recovery_context(
                    connection,
                    context=context,
                    claim=claim,
                )
                require_local_text_rollback_receipt_matches_claim(
                    receipt,
                    mutation_receipt=context.mutation_receipt,
                    claim=claim,
                )
                if self._parse_timestamp(receipt.rolled_back_at) > self._parse_timestamp(
                    verified_at
                ):
                    raise ValueError("local text rollback receipt is future-dated")
                existing = connection.execute(
                    """
                    SELECT * FROM local_text_rollback_receipts
                    WHERE rollback_receipt_fingerprint = ?
                       OR rollback_grant_id = ?
                       OR rollback_claim_id = ?
                       OR mutation_receipt_fingerprint = ?
                    """,
                    (
                        receipt.rollback_receipt_fingerprint,
                        receipt.rollback_grant_id,
                        receipt.rollback_claim_id,
                        receipt.mutation_receipt_fingerprint,
                    ),
                ).fetchone()
                if existing is not None:
                    stored = self._decode_local_text_rollback_receipt(existing)
                    if stored != receipt:
                        raise ValueError("rollback already has different receipt evidence")
                    connection.commit()
                    return stored
                payload, payload_sha256 = self._serialize(receipt)
                connection.execute(
                    """
                    INSERT INTO local_text_rollback_receipts (
                        rollback_receipt_fingerprint,
                        rollback_operation_id,
                        mutation_operation_id,
                        rollback_grant_id,
                        rollback_claim_id,
                        mutation_receipt_fingerprint,
                        resource_ref,
                        restored_content_sha256,
                        rolled_back_at,
                        rolled_back_event_fingerprint,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.rollback_receipt_fingerprint,
                        receipt.operation_id,
                        receipt.mutation_operation_id,
                        receipt.rollback_grant_id,
                        receipt.rollback_claim_id,
                        receipt.mutation_receipt_fingerprint,
                        receipt.resource_ref,
                        receipt.restored_content_sha256,
                        receipt.rolled_back_at,
                        receipt.rolled_back_event_fingerprint,
                        payload,
                        payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return receipt

    def load_local_text_rollback_receipt_exact(
        self,
        rollback_operation_id: str,
        *,
        expected_rollback_receipt_fingerprint: str,
    ) -> LocalTextRollbackReceipt:
        """Load immutable rollback proof only for its exact operation and digest."""

        verified_at = self._execution_now()
        with closing(self._new_connection()) as connection:
            row = connection.execute(
                """
                SELECT * FROM local_text_rollback_receipts
                WHERE rollback_operation_id = ?
                  AND rollback_receipt_fingerprint = ?
                """,
                (rollback_operation_id, expected_rollback_receipt_fingerprint),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown local text rollback receipt: {rollback_operation_id}")
            receipt = self._decode_local_text_rollback_receipt(row)
            claim_row = connection.execute(
                """
                SELECT * FROM local_text_file_rollback_grant_claims
                WHERE claim_id = ?
                """,
                (receipt.rollback_claim_id,),
            ).fetchone()
            if claim_row is None:
                raise ValueError("local text rollback receipt has no persisted claim")
            claim = self._decode_local_text_file_rollback_claim(claim_row)
            context = self._load_local_text_file_rollback_grant_context(
                connection,
                grant_id=claim.grant_id,
            )
            self._require_local_text_file_rollback_recovery_context(
                connection,
                context=context,
                claim=claim,
            )
            require_local_text_rollback_receipt_matches_claim(
                receipt,
                mutation_receipt=context.mutation_receipt,
                claim=claim,
            )
            if context.rollback_receipt != receipt:
                raise ValueError("local text rollback receipt differs from persisted context")
            if self._parse_timestamp(receipt.rolled_back_at) > self._parse_timestamp(verified_at):
                raise ValueError("local text rollback receipt is future-dated")
            return receipt

    def verify_local_text_rollback_receipt_exact(
        self,
        receipt: LocalTextRollbackReceipt,
    ) -> bool:
        """Fail closed unless caller rollback evidence equals the stored proof."""

        try:
            stored = self.load_local_text_rollback_receipt_exact(
                receipt.operation_id,
                expected_rollback_receipt_fingerprint=(receipt.rollback_receipt_fingerprint),
            )
        except Exception:
            return False
        return stored == receipt

    def record_intent_and_challenge(
        self,
        intent: ActionIntentContract,
        challenge: ActionConfirmationChallengeContract,
        *,
        prepared_dispatch: OperationDispatchContract | None = None,
    ) -> ActionConfirmationChallengeContract:
        """Atomically append one intent and its exact operator challenge."""

        intent_fingerprint = self._verify_intent(intent)
        challenge_fingerprint = self._verify_challenge(
            challenge,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
        )
        intent_payload, intent_payload_sha256 = self._serialize(intent)
        challenge_payload, challenge_payload_sha256 = self._serialize(challenge)
        prepared_payload: str | None = None
        prepared_payload_sha256: str | None = None
        if prepared_dispatch is not None:
            self._verify_prepared_dispatch(prepared_dispatch, intent=intent)
            prepared_payload, prepared_payload_sha256 = self._serialize(prepared_dispatch)

        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                existing_intent = connection.execute(
                    "SELECT * FROM action_intents WHERE intent_id = ?",
                    (intent.intent_id,),
                ).fetchone()
                if existing_intent is not None:
                    stored_intent = self._decode_intent(existing_intent)
                    if stored_intent != intent:
                        raise ValueError("action intent identity already has different evidence")
                else:
                    connection.execute(
                        """
                        INSERT INTO action_intents (
                            intent_id,
                            intent_fingerprint,
                            action_fingerprint,
                            origin_request_id,
                            session_id,
                            mission_id,
                            operator_identity_ref,
                            operation,
                            issued_at,
                            expires_at,
                            payload,
                            payload_sha256
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            intent.intent_id,
                            intent_fingerprint,
                            intent.action_fingerprint,
                            intent.origin_request_id,
                            intent.session_id,
                            intent.mission_id,
                            intent.operator_identity_ref,
                            intent.operation,
                            intent.issued_at,
                            intent.expires_at,
                            intent_payload,
                            intent_payload_sha256,
                        ),
                    )

                existing_prepared = connection.execute(
                    """
                    SELECT * FROM action_confirmation_prepared_dispatches
                    WHERE intent_id = ?
                    """,
                    (intent.intent_id,),
                ).fetchone()
                if existing_prepared is not None:
                    stored_prepared = self._decode_prepared_dispatch(
                        existing_prepared,
                        intent=intent,
                    )
                    if prepared_dispatch is not None and stored_prepared != prepared_dispatch:
                        raise ValueError("action intent already has a different prepared dispatch")
                elif prepared_dispatch is not None:
                    if existing_intent is not None:
                        raise ValueError(
                            "prepared dispatch must be recorded with its action intent"
                        )
                    if prepared_payload is None or prepared_payload_sha256 is None:
                        raise ValueError("prepared dispatch payload is unavailable")
                    connection.execute(
                        """
                        INSERT INTO action_confirmation_prepared_dispatches (
                            intent_id,
                            intent_fingerprint,
                            action_fingerprint,
                            operation_id,
                            origin_request_id,
                            session_id,
                            mission_id,
                            operator_identity_ref,
                            dispatch_fingerprint,
                            expires_at,
                            payload,
                            payload_sha256
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            intent.intent_id,
                            intent_fingerprint,
                            intent.action_fingerprint,
                            prepared_dispatch.operation_id,
                            prepared_dispatch.request_id,
                            prepared_dispatch.session_id,
                            prepared_dispatch.mission_id,
                            self._dispatch_operator_identity_ref(prepared_dispatch),
                            prepared_payload_sha256,
                            intent.expires_at,
                            prepared_payload,
                            prepared_payload_sha256,
                        ),
                    )

                existing_challenge = connection.execute(
                    "SELECT * FROM action_confirmation_challenges WHERE challenge_id = ?",
                    (challenge.challenge_id,),
                ).fetchone()
                if existing_challenge is not None:
                    stored_challenge = self._decode_challenge(existing_challenge)
                    if stored_challenge != challenge:
                        raise ValueError(
                            "action confirmation challenge identity already has different evidence"
                        )
                else:
                    connection.execute(
                        """
                        INSERT INTO action_confirmation_challenges (
                            challenge_id,
                            challenge_fingerprint,
                            intent_id,
                            intent_fingerprint,
                            action_fingerprint,
                            origin_request_id,
                            session_id,
                            mission_id,
                            operator_identity_ref,
                            operation,
                            issued_at,
                            expires_at,
                            payload,
                            payload_sha256
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            challenge.challenge_id,
                            challenge_fingerprint,
                            challenge.intent_id,
                            challenge.intent_fingerprint,
                            challenge.action_fingerprint,
                            challenge.origin_request_id,
                            challenge.session_id,
                            challenge.mission_id,
                            challenge.operator_identity_ref,
                            challenge.operation,
                            challenge.issued_at,
                            challenge.expires_at,
                            challenge_payload,
                            challenge_payload_sha256,
                        ),
                    )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return challenge

    def load_intent_and_challenge(
        self,
        challenge_id: str,
        *,
        verified_at: str | None = None,
    ) -> tuple[ActionIntentContract, ActionConfirmationChallengeContract]:
        """Load and reverify one exact challenge chain."""

        with closing(self._new_connection()) as connection:
            intent, challenge, _prepared_dispatch = self._load_intent_and_challenge(
                connection,
                challenge_id=challenge_id,
            )
        if verified_at is not None:
            self._require_active(verified_at, challenge.expires_at)
        return intent, challenge

    def record_receipt(
        self,
        receipt: HumanConfirmationReceiptContract,
        *,
        verified_at: str,
    ) -> HumanConfirmationReceiptContract:
        """Append one exact human receipt, at most once per challenge."""

        receipt_payload, receipt_payload_sha256 = self._serialize(receipt)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                intent, challenge, _prepared_dispatch = self._load_intent_and_challenge(
                    connection,
                    challenge_id=receipt.challenge_id,
                )
                receipt_fingerprint = self._verify_receipt(
                    receipt,
                    intent=intent,
                    challenge=challenge,
                    verified_at=verified_at,
                )
                existing = connection.execute(
                    """
                    SELECT * FROM human_confirmation_receipts
                    WHERE challenge_id = ? OR receipt_id = ?
                    """,
                    (receipt.challenge_id, receipt.receipt_id),
                ).fetchone()
                if existing is not None:
                    stored = self._decode_receipt(existing)
                    if stored == receipt:
                        return stored
                    raise ValueError("action confirmation challenge already has a receipt")
                connection.execute(
                    """
                    INSERT INTO human_confirmation_receipts (
                        receipt_id,
                        receipt_fingerprint,
                        challenge_id,
                        challenge_fingerprint,
                        intent_id,
                        intent_fingerprint,
                        action_fingerprint,
                        origin_request_id,
                        session_id,
                        mission_id,
                        operator_identity_ref,
                        operation,
                        confirmed_at,
                        expires_at,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.receipt_id,
                        receipt_fingerprint,
                        receipt.challenge_id,
                        receipt.challenge_fingerprint,
                        receipt.intent_id,
                        receipt.intent_fingerprint,
                        receipt.action_fingerprint,
                        receipt.origin_request_id,
                        receipt.session_id,
                        receipt.mission_id,
                        receipt.operator_identity_ref,
                        receipt.operation,
                        receipt.confirmed_at,
                        receipt.expires_at,
                        receipt_payload,
                        receipt_payload_sha256,
                    ),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return receipt

    def load_confirmation_context(
        self,
        receipt_id: str,
    ) -> ActionConfirmationContext:
        """Load and reverify an immutable intent/challenge/receipt/claim chain."""

        with closing(self._new_connection()) as connection:
            return self._load_confirmation_context(connection, receipt_id=receipt_id)

    def record_claim(
        self,
        claim: ActionConfirmationClaimContract,
        *,
        expected_action_fingerprint: str,
        expected_operation_id: str,
        expected_operator_identity_ref: str,
        verified_at: str,
    ) -> ActionConfirmationClaimContract:
        """Atomically consume one receipt for one exact runtime operation."""

        claim_payload, claim_payload_sha256 = self._serialize(claim)
        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                context = self._load_confirmation_context(
                    connection,
                    receipt_id=claim.receipt_id,
                )
                if context.claim is not None:
                    raise ValueError("action confirmation receipt is already claimed")
                claim_fingerprint = self._verify_claim(
                    claim,
                    context=context,
                    expected_action_fingerprint=expected_action_fingerprint,
                    expected_operation_id=expected_operation_id,
                    expected_operator_identity_ref=expected_operator_identity_ref,
                    verified_at=verified_at,
                )
                try:
                    connection.execute(
                        """
                        INSERT INTO action_confirmation_claims (
                            claim_id,
                            claim_fingerprint,
                            receipt_id,
                            receipt_fingerprint,
                            intent_id,
                            intent_fingerprint,
                            action_fingerprint,
                            operation_id,
                            origin_request_id,
                            session_id,
                            mission_id,
                            operator_identity_ref,
                            operation,
                            claimed_at,
                            expires_at,
                            payload,
                            payload_sha256
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            claim.claim_id,
                            claim_fingerprint,
                            claim.receipt_id,
                            claim.receipt_fingerprint,
                            claim.intent_id,
                            claim.intent_fingerprint,
                            claim.action_fingerprint,
                            claim.operation_id,
                            claim.origin_request_id,
                            claim.session_id,
                            claim.mission_id,
                            claim.operator_identity_ref,
                            claim.operation,
                            claim.claimed_at,
                            claim.expires_at,
                            claim_payload,
                            claim_payload_sha256,
                        ),
                    )
                except IntegrityError as exc:
                    raise ValueError("action confirmation receipt is already claimed") from exc
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return claim

    def verify_claim_exact(
        self,
        *,
        receipt_id: str,
        claim_id: str,
        operation_id: str,
        origin_request_id: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        claimed_at: str,
        verified_at: str,
        operator_identity_ref: str,
    ) -> bool:
        """Atomically present an exact claim once at the execution boundary."""

        with closing(self._new_connection()) as connection:
            self._begin_immediate(connection)
            try:
                context = self._load_confirmation_context(
                    connection,
                    receipt_id=receipt_id,
                )
                claim = context.claim
                if claim is None:
                    connection.rollback()
                    return False
                self._verify_claim(
                    claim,
                    context=context,
                    expected_action_fingerprint=expected_action_fingerprint,
                    expected_operation_id=operation_id,
                    expected_operator_identity_ref=operator_identity_ref,
                    verified_at=verified_at,
                )
                exact = all(
                    (
                        claim.claim_id == claim_id,
                        claim.receipt_id == receipt_id,
                        str(claim.operation_id) == str(operation_id),
                        str(claim.origin_request_id) == str(origin_request_id),
                        claim.intent_fingerprint == intent_fingerprint,
                        claim.claimed_at == claimed_at,
                    )
                )
                if not exact:
                    connection.rollback()
                    return False

                existing = connection.execute(
                    """
                    SELECT * FROM action_confirmation_presentations
                    WHERE claim_id = ? OR operation_id = ?
                    """,
                    (claim_id, operation_id),
                ).fetchone()
                if existing is not None:
                    self._decode_presentation(existing, context=context)
                    connection.rollback()
                    return False

                presentation = ActionConfirmationPresentation(
                    presentation_id=f"confirmation-presentation://{uuid4().hex}",
                    claim_id=claim_id,
                    claim_fingerprint=action_confirmation_claim_fingerprint(claim),
                    receipt_id=receipt_id,
                    operation_id=operation_id,
                    origin_request_id=origin_request_id,
                    action_fingerprint=expected_action_fingerprint,
                    intent_fingerprint=intent_fingerprint,
                    claimed_at=claimed_at,
                    verified_at=verified_at,
                    operator_identity_ref=operator_identity_ref,
                )
                payload, payload_sha256 = self._serialize(presentation)
                presentation_fingerprint = payload_sha256
                connection.execute(
                    """
                    INSERT INTO action_confirmation_presentations (
                        presentation_id,
                        presentation_fingerprint,
                        claim_id,
                        claim_fingerprint,
                        receipt_id,
                        operation_id,
                        origin_request_id,
                        action_fingerprint,
                        intent_fingerprint,
                        claimed_at,
                        verified_at,
                        operator_identity_ref,
                        payload,
                        payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        presentation.presentation_id,
                        presentation_fingerprint,
                        presentation.claim_id,
                        presentation.claim_fingerprint,
                        presentation.receipt_id,
                        presentation.operation_id,
                        presentation.origin_request_id,
                        presentation.action_fingerprint,
                        presentation.intent_fingerprint,
                        presentation.claimed_at,
                        presentation.verified_at,
                        presentation.operator_identity_ref,
                        payload,
                        payload_sha256,
                    ),
                )
                connection.commit()
                return True
            except (DatabaseError, KeyError, TypeError, ValueError):
                connection.rollback()
                return False

    def _load_active_adapter_registry_epoch(
        self,
        connection: Connection,
        *,
        required: bool = True,
    ) -> AdapterRegistryEpoch | None:
        row = connection.execute(
            """
            SELECT * FROM adapter_registry_epochs
            ORDER BY epoch_id DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            if required:
                raise KeyError("no active adapter registry")
            return None
        return self._decode_adapter_registry_epoch(connection, row)

    def _decode_adapter_registry_epoch(
        self,
        connection: Connection,
        row: Row,
    ) -> AdapterRegistryEpoch:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter registry",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("adapter registry payload must be an object")
        values = dict(raw_payload)
        raw_descriptors = values.get("descriptors")
        if not isinstance(raw_descriptors, list):
            raise ValueError("adapter registry descriptors payload is invalid")
        values["descriptors"] = tuple(
            self._hydrate_adapter_descriptor(item) for item in raw_descriptors
        )
        try:
            snapshot = AdapterRegistrySnapshotContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter registry payload") from exc
        require_valid_adapter_registry_snapshot(snapshot)
        canonical_payload, canonical_sha256 = self._serialize(snapshot)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter registry payload is not canonical")
        self._require_adapter_columns(
            row,
            registry_id=snapshot.registry_id,
            registry_version=snapshot.registry_version,
            registry_fingerprint=snapshot.registry_fingerprint,
        )
        self._parse_timestamp(row["activated_at"])
        descriptor_rows = connection.execute(
            """
            SELECT * FROM adapter_registry_descriptors
            WHERE registry_fingerprint = ?
            ORDER BY adapter_id, adapter_version
            """,
            (snapshot.registry_fingerprint,),
        ).fetchall()
        stored_descriptors = tuple(
            self._decode_adapter_descriptor(item) for item in descriptor_rows
        )
        if stored_descriptors != snapshot.descriptors:
            raise ValueError("adapter registry descriptor snapshot mismatch")
        if any(item["epoch_id"] != row["epoch_id"] for item in descriptor_rows):
            raise ValueError("adapter registry descriptor epoch mismatch")
        return AdapterRegistryEpoch(
            epoch_id=int(row["epoch_id"]),
            snapshot=snapshot,
            activated_at=row["activated_at"],
        )

    def _load_active_adapter_execution_registry_epoch(
        self,
        connection: Connection,
        *,
        required: bool = True,
    ) -> AdapterExecutionRegistryEpoch | None:
        row = connection.execute(
            """
            SELECT * FROM adapter_execution_registry_epochs
            ORDER BY epoch_id DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            if required:
                raise KeyError("no active adapter execution registry")
            return None
        return self._decode_adapter_execution_registry_epoch(connection, row)

    def _decode_adapter_execution_registry_epoch(
        self,
        connection: Connection,
        row: Row,
    ) -> AdapterExecutionRegistryEpoch:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter execution registry",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("adapter execution registry payload must be an object")
        values = dict(raw_payload)
        raw_descriptors = values.get("descriptors")
        if not isinstance(raw_descriptors, list):
            raise ValueError("adapter execution registry descriptors payload is invalid")
        values["descriptors"] = tuple(
            self._hydrate_adapter_execution_descriptor(item) for item in raw_descriptors
        )
        try:
            snapshot = AdapterExecutionRegistrySnapshotContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter execution registry payload") from exc
        require_valid_adapter_execution_registry_snapshot(snapshot)
        canonical_payload, canonical_sha256 = self._serialize(snapshot)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter execution registry payload is not canonical")
        self._require_adapter_columns(
            row,
            registry_id=snapshot.registry_id,
            registry_version=snapshot.registry_version,
            registry_fingerprint=snapshot.registry_fingerprint,
        )
        self._parse_timestamp(row["activated_at"])
        descriptor_rows = connection.execute(
            """
            SELECT * FROM adapter_execution_registry_descriptors
            WHERE registry_fingerprint = ?
            ORDER BY adapter_id, adapter_version
            """,
            (snapshot.registry_fingerprint,),
        ).fetchall()
        stored_descriptors = tuple(
            self._decode_adapter_execution_descriptor(item) for item in descriptor_rows
        )
        if stored_descriptors != snapshot.descriptors:
            raise ValueError("adapter execution registry descriptor snapshot mismatch")
        if any(item["epoch_id"] != row["epoch_id"] for item in descriptor_rows):
            raise ValueError("adapter execution registry descriptor epoch mismatch")
        return AdapterExecutionRegistryEpoch(
            epoch_id=int(row["epoch_id"]),
            snapshot=snapshot,
            activated_at=row["activated_at"],
        )

    def _decode_adapter_execution_descriptor(
        self,
        row: Row,
    ) -> AdapterExecutionDescriptorContract:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter execution descriptor",
        )
        descriptor = self._hydrate_adapter_execution_descriptor(raw_payload)
        require_valid_adapter_execution_descriptor(descriptor)
        canonical_payload, canonical_sha256 = self._serialize(descriptor)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter execution descriptor payload is not canonical")
        self._require_adapter_columns(
            row,
            descriptor_fingerprint=descriptor.descriptor_fingerprint,
            adapter_id=descriptor.adapter_id,
            adapter_version=descriptor.adapter_version,
            action_kind=descriptor.action_kind,
            allowed_operations=self._canonical_sequence(descriptor.allowed_operations),
            allowed_resource_scopes=self._canonical_sequence(descriptor.allowed_resource_scopes),
            executor_ref=descriptor.executor_ref,
            execution_policy_version=descriptor.execution_policy_version,
            execution_backend_version=descriptor.execution_backend_version,
        )
        return descriptor

    @staticmethod
    def _hydrate_adapter_execution_descriptor(
        payload: object,
    ) -> AdapterExecutionDescriptorContract:
        if not isinstance(payload, dict):
            raise ValueError("adapter execution descriptor payload must be an object")
        values = dict(payload)
        for field_name in ("allowed_operations", "allowed_resource_scopes"):
            value = values.get(field_name)
            if not isinstance(value, list):
                raise ValueError(f"adapter execution descriptor {field_name} payload is invalid")
            values[field_name] = tuple(value)
        try:
            return AdapterExecutionDescriptorContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter execution descriptor payload") from exc

    def _load_active_local_text_file_rollback_registry_epoch(
        self,
        connection: Connection,
        *,
        required: bool = True,
    ) -> LocalTextFileRollbackRegistryEpoch | None:
        row = connection.execute(
            """
            SELECT * FROM local_text_file_rollback_registry_epochs
            ORDER BY epoch_id DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            if required:
                raise KeyError("no active local text rollback registry")
            return None
        return self._decode_local_text_file_rollback_registry_epoch(connection, row)

    def _decode_local_text_file_rollback_registry_epoch(
        self,
        connection: Connection,
        row: Row,
    ) -> LocalTextFileRollbackRegistryEpoch:
        raw = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text rollback registry",
        )
        if not isinstance(raw, dict) or not isinstance(raw.get("descriptors"), list):
            raise ValueError("local text rollback registry payload is invalid")
        values = dict(raw)
        values["descriptors"] = tuple(
            self._hydrate_local_text_file_rollback_descriptor(item) for item in raw["descriptors"]
        )
        try:
            snapshot = LocalTextFileRollbackRegistrySnapshotContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid local text rollback registry payload") from exc
        require_valid_local_text_file_rollback_registry(snapshot)
        payload, payload_sha256 = self._serialize(snapshot)
        if payload != row["payload"] or payload_sha256 != row["payload_sha256"]:
            raise ValueError("local text rollback registry payload is not canonical")
        self._require_adapter_columns(
            row,
            registry_id=snapshot.registry_id,
            registry_version=snapshot.registry_version,
            registry_fingerprint=snapshot.registry_fingerprint,
        )
        self._parse_timestamp(row["activated_at"])
        descriptor_rows = connection.execute(
            """
            SELECT * FROM local_text_file_rollback_registry_descriptors
            WHERE registry_fingerprint = ?
            ORDER BY adapter_id, adapter_version
            """,
            (snapshot.registry_fingerprint,),
        ).fetchall()
        descriptors = tuple(
            self._decode_local_text_file_rollback_descriptor(item) for item in descriptor_rows
        )
        if descriptors != snapshot.descriptors or any(
            item["epoch_id"] != row["epoch_id"] for item in descriptor_rows
        ):
            raise ValueError("local text rollback registry descriptor mismatch")
        return LocalTextFileRollbackRegistryEpoch(
            epoch_id=int(row["epoch_id"]),
            snapshot=snapshot,
            activated_at=row["activated_at"],
        )

    def _decode_local_text_file_rollback_descriptor(
        self,
        row: Row,
    ) -> LocalTextFileRollbackDescriptorContract:
        raw = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text rollback descriptor",
        )
        descriptor = self._hydrate_local_text_file_rollback_descriptor(raw)
        require_valid_local_text_file_rollback_descriptor(descriptor)
        payload, payload_sha256 = self._serialize(descriptor)
        if payload != row["payload"] or payload_sha256 != row["payload_sha256"]:
            raise ValueError("local text rollback descriptor payload is not canonical")
        self._require_adapter_columns(
            row,
            descriptor_fingerprint=descriptor.descriptor_fingerprint,
            adapter_id=descriptor.adapter_id,
            adapter_version=descriptor.adapter_version,
            action_kind=descriptor.action_kind,
            purpose=descriptor.purpose,
            allowed_operations=self._canonical_sequence(descriptor.allowed_operations),
            allowed_resource_scopes=self._canonical_sequence(descriptor.allowed_resource_scopes),
            executor_ref=descriptor.executor_ref,
            rollback_policy_version=descriptor.rollback_policy_version,
            rollback_backend_version=descriptor.rollback_backend_version,
        )
        return descriptor

    @staticmethod
    def _hydrate_local_text_file_rollback_descriptor(
        payload: object,
    ) -> LocalTextFileRollbackDescriptorContract:
        if not isinstance(payload, dict):
            raise ValueError("local text rollback descriptor payload must be an object")
        values = dict(payload)
        for field_name in ("allowed_operations", "allowed_resource_scopes"):
            value = values.get(field_name)
            if not isinstance(value, list):
                raise ValueError("local text rollback descriptor allowlist is invalid")
            values[field_name] = tuple(value)
        try:
            return LocalTextFileRollbackDescriptorContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid local text rollback descriptor payload") from exc

    def _decode_adapter_descriptor(self, row: Row) -> AdapterDescriptorContract:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter descriptor",
        )
        descriptor = self._hydrate_adapter_descriptor(raw_payload)
        require_valid_adapter_descriptor(descriptor)
        canonical_payload, canonical_sha256 = self._serialize(descriptor)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter descriptor payload is not canonical")
        self._require_adapter_columns(
            row,
            descriptor_fingerprint=descriptor.descriptor_fingerprint,
            adapter_id=descriptor.adapter_id,
            adapter_version=descriptor.adapter_version,
            action_kind=descriptor.action_kind,
            allowed_operations=self._canonical_sequence(descriptor.allowed_operations),
            allowed_resource_scopes=self._canonical_sequence(descriptor.allowed_resource_scopes),
        )
        return descriptor

    @staticmethod
    def _hydrate_adapter_descriptor(payload: object) -> AdapterDescriptorContract:
        if not isinstance(payload, dict):
            raise ValueError("adapter descriptor payload must be an object")
        values = dict(payload)
        for field_name in ("allowed_operations", "allowed_resource_scopes"):
            value = values.get(field_name)
            if not isinstance(value, list):
                raise ValueError(f"adapter descriptor {field_name} payload is invalid")
            values[field_name] = tuple(value)
        try:
            return AdapterDescriptorContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter descriptor payload") from exc

    @staticmethod
    def _hydrate_adapter_action_request(
        payload: object,
    ) -> AdapterActionRequestContract:
        if not isinstance(payload, dict):
            raise ValueError("adapter action request payload must be an object")
        try:
            return AdapterActionRequestContract(**payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter action request payload") from exc

    @staticmethod
    def _hydrate_adapter_execution_request(
        payload: object,
    ) -> AdapterExecutionRequestContract:
        if not isinstance(payload, dict):
            raise ValueError("adapter execution request payload must be an object")
        try:
            return AdapterExecutionRequestContract(**payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter execution request payload") from exc

    def _decode_local_text_file_preflight_attestation(
        self,
        row: Row,
    ) -> tuple[
        LocalTextFilePreflightAttestationContract,
        AdapterExecutionRequestContract,
    ]:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text file preflight attestation",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("preflight attestation payload must be an object")
        try:
            attestation = LocalTextFilePreflightAttestationContract(**raw_payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid preflight attestation payload") from exc
        require_valid_local_text_file_preflight_attestation(attestation)
        canonical_payload, canonical_sha256 = self._serialize(attestation)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("preflight attestation payload is not canonical")
        raw_request = self._decode_json_payload(
            row,
            payload_column="request_payload",
            hash_column="request_payload_sha256",
            label="adapter execution request",
        )
        request = self._hydrate_adapter_execution_request(raw_request)
        require_adapter_execution_request_matches_attestation(request, attestation)
        request_payload, request_payload_sha256 = self._serialize(request)
        if (
            request_payload != row["request_payload"]
            or request_payload_sha256 != row["request_payload_sha256"]
        ):
            raise ValueError("adapter execution request payload is not canonical")
        self._require_adapter_columns(
            row,
            attestation_id=attestation.attestation_id,
            attestation_fingerprint=attestation.attestation_fingerprint,
            attestation_nonce=attestation.attestation_nonce,
            trusted_boundary_ref=attestation.trusted_boundary_ref,
            source_preflight_grant_id=attestation.source_preflight_grant_id,
            source_preflight_grant_fingerprint=(attestation.source_preflight_grant_fingerprint),
            preflight_fingerprint=attestation.preflight_fingerprint,
            execution_request_fingerprint=request.execution_request_fingerprint,
            subject_ref=attestation.subject_ref,
            operation=attestation.operation,
            resource_scope=attestation.resource_scope,
            resource_ref=attestation.resource_ref,
            root_config_fingerprint=attestation.root_config_fingerprint,
            filesystem_snapshot_fingerprint=(attestation.filesystem_snapshot_fingerprint),
            before_content_sha256=attestation.before_content_sha256,
            desired_content_sha256=attestation.desired_content_sha256,
            rollback_fingerprint=attestation.rollback_fingerprint,
            preflight_expires_at=attestation.preflight_expires_at,
            attested_at=attestation.attested_at,
        )
        return attestation, request

    def _load_preflight_attestation(
        self,
        connection: Connection,
        *,
        attestation_id: str,
    ) -> tuple[
        LocalTextFilePreflightAttestationContract,
        AdapterExecutionRequestContract,
    ]:
        row = connection.execute(
            """
            SELECT * FROM local_text_file_preflight_attestations
            WHERE attestation_id = ?
            """,
            (attestation_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown local text preflight attestation: {attestation_id}")
        return self._decode_local_text_file_preflight_attestation(row)

    def _decode_adapter_execution_grant(
        self,
        row: Row,
    ) -> AdapterExecutionGrantContract:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter execution grant",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("adapter execution grant payload must be an object")
        values = dict(raw_payload)
        values["execution_request"] = self._hydrate_adapter_execution_request(
            values.get("execution_request")
        )
        try:
            grant = AdapterExecutionGrantContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter execution grant payload") from exc
        canonical_payload, canonical_sha256 = self._serialize(grant)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter execution grant payload is not canonical")
        request = grant.execution_request
        self._require_adapter_columns(
            row,
            grant_id=grant.grant_id,
            grant_fingerprint=grant.grant_fingerprint,
            intent_id=grant.intent_id,
            intent_fingerprint=grant.intent_fingerprint,
            action_fingerprint=grant.action_fingerprint,
            subject_ref=grant.subject_ref,
            adapter_id=request.adapter_id,
            adapter_version=request.adapter_version,
            action_kind=request.action_kind,
            operation=request.operation,
            resource_scope=request.resource_scope,
            resource_ref=request.resource_ref,
            source_preflight_grant_id=request.source_preflight_grant_id,
            source_preflight_grant_fingerprint=(request.source_preflight_grant_fingerprint),
            preflight_attestation_id=request.preflight_attestation_id,
            preflight_attestation_fingerprint=(request.preflight_attestation_fingerprint),
            preflight_fingerprint=request.preflight_fingerprint,
            execution_request_fingerprint=request.execution_request_fingerprint,
            root_config_fingerprint=request.root_config_fingerprint,
            before_content_sha256=request.before_content_sha256,
            desired_content_sha256=request.desired_content_sha256,
            rollback_fingerprint=request.rollback_fingerprint,
            descriptor_fingerprint=grant.descriptor_fingerprint,
            registry_fingerprint=grant.registry_fingerprint,
            autonomy_policy_decision_fingerprint=(grant.autonomy_policy_decision_fingerprint),
            policy_version=grant.policy_version,
            nonce=grant.nonce,
            confirmation_required=grant.confirmation_required,
            issued_at=grant.issued_at,
            expires_at=grant.expires_at,
        )
        return grant

    def _decode_adapter_execution_grant_claim(
        self,
        row: Row,
    ) -> AdapterExecutionGrantClaimContract:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter execution grant claim",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("adapter execution grant claim payload must be an object")
        values = dict(raw_payload)
        values["execution_request"] = self._hydrate_adapter_execution_request(
            values.get("execution_request")
        )
        values["operation_id"] = OperationId(str(values.get("operation_id")))
        try:
            claim = AdapterExecutionGrantClaimContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter execution grant claim payload") from exc
        canonical_payload, canonical_sha256 = self._serialize(claim)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter execution grant claim payload is not canonical")
        request = claim.execution_request
        self._require_adapter_columns(
            row,
            claim_id=claim.claim_id,
            claim_fingerprint=claim.claim_fingerprint,
            grant_id=claim.grant_id,
            grant_fingerprint=claim.grant_fingerprint,
            operation_id=claim.operation_id,
            journal_reservation_fingerprint=claim.journal_reservation_fingerprint,
            subject_ref=claim.subject_ref,
            intent_id=claim.intent_id,
            intent_fingerprint=claim.intent_fingerprint,
            action_fingerprint=claim.action_fingerprint,
            execution_request_fingerprint=request.execution_request_fingerprint,
            preflight_fingerprint=request.preflight_fingerprint,
            confirmation_receipt_id=claim.confirmation_receipt_id,
            confirmation_claim_id=claim.confirmation_claim_id,
            confirmation_claim_fingerprint=claim.confirmation_claim_fingerprint,
            claimed_at=claim.claimed_at,
            expires_at=claim.expires_at,
        )
        return claim

    @staticmethod
    def _hydrate_local_text_file_rollback_request(
        payload: object,
    ) -> LocalTextFileRollbackRequestContract:
        if not isinstance(payload, dict):
            raise ValueError("local text rollback request payload must be an object")
        values = dict(payload)
        values["rollback_operation_id"] = OperationId(str(values.get("rollback_operation_id")))
        values["mutation_operation_id"] = OperationId(str(values.get("mutation_operation_id")))
        try:
            return LocalTextFileRollbackRequestContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid local text rollback request payload") from exc

    def _decode_local_text_mutation_receipt(
        self,
        row: Row,
    ) -> LocalTextMutationReceipt:
        raw_receipt = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text mutation receipt",
        )
        if not isinstance(raw_receipt, dict):
            raise ValueError("local text mutation receipt payload must be an object")
        try:
            receipt = LocalTextMutationReceipt(**raw_receipt)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid local text mutation receipt payload") from exc
        require_valid_local_text_mutation_receipt(receipt)
        receipt_payload, receipt_payload_sha256 = self._serialize(receipt)
        if receipt_payload != row["payload"] or receipt_payload_sha256 != row["payload_sha256"]:
            raise ValueError("local text mutation receipt is not canonical")
        self._require_adapter_columns(
            row,
            receipt_fingerprint=receipt.receipt_fingerprint,
            mutation_operation_id=receipt.operation_id,
            execution_grant_id=receipt.execution_grant_id,
            execution_claim_id=receipt.execution_claim_id,
            applied_event_fingerprint=receipt.applied_event_fingerprint,
            resource_ref=receipt.resource_ref,
            subject_ref=receipt.subject_ref,
            preflight_fingerprint=receipt.preflight_fingerprint,
            before_content_sha256=receipt.before_content_sha256,
            desired_content_sha256=receipt.desired_content_sha256,
            root_config_fingerprint=receipt.root_config_fingerprint,
            committed_at=receipt.committed_at,
        )
        return receipt

    def _decode_local_text_file_rollback_request(
        self,
        row: Row,
    ) -> LocalTextFileRollbackRequestContract:
        raw = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text rollback request",
        )
        request = self._hydrate_local_text_file_rollback_request(raw)
        require_valid_local_text_file_rollback_request(request)
        payload, payload_sha256 = self._serialize(request)
        if payload != row["payload"] or payload_sha256 != row["payload_sha256"]:
            raise ValueError("local text rollback request is not canonical")
        self._require_adapter_columns(
            row,
            rollback_request_fingerprint=request.rollback_request_fingerprint,
            rollback_operation_id=request.rollback_operation_id,
            mutation_receipt_fingerprint=request.mutation_receipt_fingerprint,
            requested_at=request.requested_at,
            expires_at=request.expires_at,
        )
        return request

    def _load_local_text_mutation_receipt(
        self,
        connection: Connection,
        *,
        receipt_fingerprint: str,
    ) -> LocalTextMutationReceipt:
        row = connection.execute(
            """
            SELECT * FROM local_text_mutation_receipts
            WHERE receipt_fingerprint = ?
            """,
            (receipt_fingerprint,),
        ).fetchone()
        if row is None:
            raise KeyError("unknown local text mutation receipt")
        return self._decode_local_text_mutation_receipt(row)

    def _load_local_text_file_rollback_request(
        self,
        connection: Connection,
        *,
        rollback_request_fingerprint: str,
    ) -> LocalTextFileRollbackRequestContract:
        row = connection.execute(
            """
            SELECT * FROM local_text_file_rollback_requests
            WHERE rollback_request_fingerprint = ?
            """,
            (rollback_request_fingerprint,),
        ).fetchone()
        if row is None:
            raise KeyError("unknown local text rollback request")
        return self._decode_local_text_file_rollback_request(row)

    def _decode_local_text_file_rollback_grant(
        self,
        row: Row,
    ) -> LocalTextFileRollbackGrantContract:
        raw = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text rollback grant",
        )
        if not isinstance(raw, dict):
            raise ValueError("local text rollback grant payload must be an object")
        values = dict(raw)
        values["rollback_request"] = self._hydrate_local_text_file_rollback_request(
            values.get("rollback_request")
        )
        try:
            grant = LocalTextFileRollbackGrantContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid local text rollback grant payload") from exc
        payload, payload_sha256 = self._serialize(grant)
        if payload != row["payload"] or payload_sha256 != row["payload_sha256"]:
            raise ValueError("local text rollback grant payload is not canonical")
        request = grant.rollback_request
        self._require_adapter_columns(
            row,
            grant_id=grant.grant_id,
            grant_fingerprint=grant.grant_fingerprint,
            intent_id=grant.intent_id,
            intent_fingerprint=grant.intent_fingerprint,
            action_fingerprint=grant.action_fingerprint,
            subject_ref=grant.subject_ref,
            rollback_operation_id=request.rollback_operation_id,
            mutation_operation_id=request.mutation_operation_id,
            mutation_receipt_fingerprint=request.mutation_receipt_fingerprint,
            source_execution_grant_id=request.source_execution_grant_id,
            source_execution_claim_id=request.source_execution_claim_id,
            rollback_request_fingerprint=request.rollback_request_fingerprint,
            resource_ref=request.resource_ref,
            root_config_fingerprint=request.root_config_fingerprint,
            expected_current_sha256=request.expected_current_sha256,
            restored_content_sha256=request.restored_content_sha256,
            rollback_plan_fingerprint=request.rollback_plan_fingerprint,
            descriptor_fingerprint=grant.descriptor_fingerprint,
            registry_fingerprint=grant.registry_fingerprint,
            autonomy_policy_decision_fingerprint=(grant.autonomy_policy_decision_fingerprint),
            policy_version=grant.policy_version,
            nonce=grant.nonce,
            confirmation_required=grant.confirmation_required,
            issued_at=grant.issued_at,
            expires_at=grant.expires_at,
        )
        return grant

    def _decode_local_text_file_rollback_claim(
        self,
        row: Row,
    ) -> LocalTextFileRollbackGrantClaimContract:
        raw = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text rollback claim",
        )
        if not isinstance(raw, dict):
            raise ValueError("local text rollback claim payload must be an object")
        values = dict(raw)
        values["rollback_request"] = self._hydrate_local_text_file_rollback_request(
            values.get("rollback_request")
        )
        values["rollback_operation_id"] = OperationId(str(values.get("rollback_operation_id")))
        try:
            claim = LocalTextFileRollbackGrantClaimContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid local text rollback claim payload") from exc
        payload, payload_sha256 = self._serialize(claim)
        if payload != row["payload"] or payload_sha256 != row["payload_sha256"]:
            raise ValueError("local text rollback claim payload is not canonical")
        self._require_adapter_columns(
            row,
            claim_id=claim.claim_id,
            claim_fingerprint=claim.claim_fingerprint,
            grant_id=claim.grant_id,
            grant_fingerprint=claim.grant_fingerprint,
            rollback_operation_id=claim.rollback_operation_id,
            rollback_journal_reservation_fingerprint=(
                claim.rollback_journal_reservation_fingerprint
            ),
            subject_ref=claim.subject_ref,
            intent_id=claim.intent_id,
            intent_fingerprint=claim.intent_fingerprint,
            action_fingerprint=claim.action_fingerprint,
            rollback_request_fingerprint=(claim.rollback_request.rollback_request_fingerprint),
            mutation_receipt_fingerprint=(claim.rollback_request.mutation_receipt_fingerprint),
            confirmation_receipt_id=claim.confirmation_receipt_id,
            confirmation_claim_id=claim.confirmation_claim_id,
            confirmation_claim_fingerprint=claim.confirmation_claim_fingerprint,
            claimed_at=claim.claimed_at,
            expires_at=claim.expires_at,
        )
        return claim

    def _decode_local_text_rollback_receipt(self, row: Row) -> LocalTextRollbackReceipt:
        raw = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="local text rollback receipt",
        )
        if not isinstance(raw, dict):
            raise ValueError("local text rollback receipt payload must be an object")
        try:
            receipt = LocalTextRollbackReceipt(**raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid local text rollback receipt payload") from exc
        payload, payload_sha256 = self._serialize(receipt)
        if payload != row["payload"] or payload_sha256 != row["payload_sha256"]:
            raise ValueError("local text rollback receipt payload is not canonical")
        self._require_adapter_columns(
            row,
            rollback_receipt_fingerprint=receipt.rollback_receipt_fingerprint,
            rollback_operation_id=receipt.operation_id,
            mutation_operation_id=receipt.mutation_operation_id,
            rollback_grant_id=receipt.rollback_grant_id,
            rollback_claim_id=receipt.rollback_claim_id,
            mutation_receipt_fingerprint=receipt.mutation_receipt_fingerprint,
            resource_ref=receipt.resource_ref,
            restored_content_sha256=receipt.restored_content_sha256,
            rolled_back_at=receipt.rolled_back_at,
            rolled_back_event_fingerprint=receipt.rolled_back_event_fingerprint,
        )
        return receipt

    def _decode_adapter_grant(
        self,
        row: Row,
    ) -> AdapterGrantContract:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter grant",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("adapter grant payload must be an object")
        values = dict(raw_payload)
        values["adapter_request"] = self._hydrate_adapter_action_request(
            values.get("adapter_request")
        )
        try:
            grant = AdapterGrantContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter grant payload") from exc
        canonical_payload, canonical_sha256 = self._serialize(grant)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter grant payload is not canonical")
        request = grant.adapter_request
        self._require_adapter_columns(
            row,
            grant_id=grant.grant_id,
            grant_fingerprint=grant.grant_fingerprint,
            intent_id=grant.intent_id,
            intent_fingerprint=grant.intent_fingerprint,
            action_fingerprint=grant.action_fingerprint,
            subject_ref=grant.subject_ref,
            adapter_id=request.adapter_id,
            adapter_version=request.adapter_version,
            action_kind=request.action_kind,
            operation=request.operation,
            resource_scope=request.resource_scope,
            resource_ref=request.resource_ref,
            descriptor_fingerprint=grant.descriptor_fingerprint,
            registry_fingerprint=grant.registry_fingerprint,
            autonomy_policy_decision_fingerprint=(grant.autonomy_policy_decision_fingerprint),
            policy_version=grant.policy_version,
            nonce=grant.nonce,
            confirmation_required=grant.confirmation_required,
            issued_at=grant.issued_at,
            expires_at=grant.expires_at,
        )
        return grant

    def _decode_adapter_grant_claim(self, row: Row) -> AdapterGrantClaimContract:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="payload",
            hash_column="payload_sha256",
            label="adapter grant claim",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("adapter grant claim payload must be an object")
        values = dict(raw_payload)
        values["adapter_request"] = self._hydrate_adapter_action_request(
            values.get("adapter_request")
        )
        values["operation_id"] = OperationId(str(values.get("operation_id")))
        try:
            claim = AdapterGrantClaimContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter grant claim payload") from exc
        canonical_payload, canonical_sha256 = self._serialize(claim)
        if canonical_payload != row["payload"] or canonical_sha256 != row["payload_sha256"]:
            raise ValueError("adapter grant claim payload is not canonical")
        request = claim.adapter_request
        self._require_adapter_columns(
            row,
            claim_id=claim.claim_id,
            claim_fingerprint=claim.claim_fingerprint,
            grant_id=claim.grant_id,
            grant_fingerprint=claim.grant_fingerprint,
            operation_id=claim.operation_id,
            subject_ref=claim.subject_ref,
            intent_id=claim.intent_id,
            intent_fingerprint=claim.intent_fingerprint,
            action_fingerprint=claim.action_fingerprint,
            adapter_id=request.adapter_id,
            adapter_version=request.adapter_version,
            action_kind=request.action_kind,
            operation=request.operation,
            resource_scope=request.resource_scope,
            resource_ref=request.resource_ref,
            confirmation_receipt_id=claim.confirmation_receipt_id,
            confirmation_claim_id=claim.confirmation_claim_id,
            confirmation_claim_fingerprint=claim.confirmation_claim_fingerprint,
            claimed_at=claim.claimed_at,
            expires_at=claim.expires_at,
        )
        return claim

    def _decode_adapter_autonomy_decision(
        self,
        row: Row,
    ) -> AutonomyActionPolicyDecisionContract:
        raw_payload = self._decode_json_payload(
            row,
            payload_column="autonomy_policy_payload",
            hash_column="autonomy_policy_payload_sha256",
            label="adapter autonomy decision",
        )
        if not isinstance(raw_payload, dict):
            raise ValueError("adapter autonomy decision payload must be an object")
        values = dict(raw_payload)
        reason_codes = values.get("reason_codes")
        if not isinstance(reason_codes, list):
            raise ValueError("adapter autonomy reason codes payload is invalid")
        values["reason_codes"] = tuple(reason_codes)
        try:
            decision = AutonomyActionPolicyDecisionContract(**values)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid adapter autonomy decision payload") from exc
        canonical_payload, canonical_sha256 = self._serialize(decision)
        if (
            canonical_payload != row["autonomy_policy_payload"]
            or canonical_sha256 != row["autonomy_policy_payload_sha256"]
        ):
            raise ValueError("adapter autonomy decision payload is not canonical")
        if row["autonomy_policy_decision_fingerprint"] != autonomy_policy_decision_fingerprint(
            decision
        ):
            raise ValueError("adapter autonomy decision stored fingerprint mismatch")
        return decision

    def _load_adapter_grant_context(
        self,
        connection: Connection,
        *,
        grant_id: str,
    ) -> AdapterGrantContext:
        grant_row = connection.execute(
            "SELECT * FROM adapter_grants WHERE grant_id = ?",
            (grant_id,),
        ).fetchone()
        if grant_row is None:
            raise KeyError(f"unknown adapter grant: {grant_id}")
        grant = self._decode_adapter_grant(grant_row)
        intent_row = connection.execute(
            "SELECT * FROM action_intents WHERE intent_id = ?",
            (grant.intent_id,),
        ).fetchone()
        if intent_row is None:
            raise ValueError("adapter grant has no immutable action intent")
        intent = self._decode_intent(intent_row)
        registry_row = connection.execute(
            """
            SELECT * FROM adapter_registry_epochs
            WHERE registry_fingerprint = ?
            """,
            (grant.registry_fingerprint,),
        ).fetchone()
        if registry_row is None:
            raise ValueError("adapter grant has no immutable registry snapshot")
        registry = self._decode_adapter_registry_epoch(
            connection,
            registry_row,
        ).snapshot
        descriptor_row = connection.execute(
            """
            SELECT * FROM adapter_registry_descriptors
            WHERE registry_fingerprint = ? AND descriptor_fingerprint = ?
            """,
            (grant.registry_fingerprint, grant.descriptor_fingerprint),
        ).fetchone()
        if descriptor_row is None:
            raise ValueError("adapter grant has no immutable descriptor snapshot")
        descriptor = self._decode_adapter_descriptor(descriptor_row)
        autonomy_decision = self._decode_adapter_autonomy_decision(grant_row)
        self._verify_adapter_grant(
            grant,
            intent=intent,
            intent_fingerprint=action_intent_fingerprint(intent),
            descriptor=descriptor,
            registry=registry,
            autonomy_decision=autonomy_decision,
            verified_at=grant.issued_at,
        )
        claim_row = connection.execute(
            "SELECT * FROM adapter_grant_claims WHERE grant_id = ?",
            (grant_id,),
        ).fetchone()
        claim = self._decode_adapter_grant_claim(claim_row) if claim_row is not None else None
        confirmation_claim: ActionConfirmationClaimContract | None = None
        if claim is not None:
            require_valid_adapter_grant_claim(
                claim,
                grant=grant,
                now=claim.claimed_at,
            )
            if claim.confirmation_claim_id is not None:
                confirmation_row = connection.execute(
                    """
                    SELECT * FROM action_confirmation_claims
                    WHERE claim_id = ?
                    """,
                    (claim.confirmation_claim_id,),
                ).fetchone()
                if confirmation_row is None:
                    raise ValueError("adapter grant claim has no confirmation claim")
                confirmation_claim = self._decode_claim(confirmation_row)
                if (
                    confirmation_claim.receipt_id != claim.confirmation_receipt_id
                    or action_confirmation_claim_fingerprint(confirmation_claim)
                    != claim.confirmation_claim_fingerprint
                ):
                    raise ValueError("adapter confirmation claim binding mismatch")
        context = AdapterGrantContext(
            intent=intent,
            action_request=grant.adapter_request,
            autonomy_decision=autonomy_decision,
            registry=registry,
            descriptor=descriptor,
            grant=grant,
            claim=claim,
            confirmation_claim=confirmation_claim,
        )
        if claim is not None and confirmation_claim is not None:
            confirmation_context = self._load_confirmation_context(
                connection,
                receipt_id=confirmation_claim.receipt_id,
            )
            self._verify_adapter_confirmation_context(
                context,
                confirmation_context,
            )
            if confirmation_context.claim != confirmation_claim:
                raise ValueError("adapter confirmation persisted claim mismatch")
        return context

    def _load_adapter_execution_grant_context(
        self,
        connection: Connection,
        *,
        grant_id: str,
    ) -> AdapterExecutionGrantContext:
        grant_row = connection.execute(
            "SELECT * FROM adapter_execution_grants WHERE grant_id = ?",
            (grant_id,),
        ).fetchone()
        if grant_row is None:
            raise KeyError(f"unknown adapter execution grant: {grant_id}")
        grant = self._decode_adapter_execution_grant(grant_row)
        intent_row = connection.execute(
            "SELECT * FROM action_intents WHERE intent_id = ?",
            (grant.intent_id,),
        ).fetchone()
        if intent_row is None:
            raise ValueError("adapter execution grant has no immutable action intent")
        intent = self._decode_intent(intent_row)
        registry_row = connection.execute(
            """
            SELECT * FROM adapter_execution_registry_epochs
            WHERE registry_fingerprint = ?
            """,
            (grant.registry_fingerprint,),
        ).fetchone()
        if registry_row is None:
            raise ValueError("adapter execution grant has no immutable registry snapshot")
        registry = self._decode_adapter_execution_registry_epoch(
            connection,
            registry_row,
        ).snapshot
        descriptor_row = connection.execute(
            """
            SELECT * FROM adapter_execution_registry_descriptors
            WHERE registry_fingerprint = ? AND descriptor_fingerprint = ?
            """,
            (grant.registry_fingerprint, grant.descriptor_fingerprint),
        ).fetchone()
        if descriptor_row is None:
            raise ValueError("adapter execution grant has no immutable descriptor snapshot")
        descriptor = self._decode_adapter_execution_descriptor(descriptor_row)
        attestation, stored_request = self._load_preflight_attestation(
            connection,
            attestation_id=grant.execution_request.preflight_attestation_id,
        )
        if stored_request != grant.execution_request:
            raise ValueError("adapter execution grant request differs from attestation")
        source_prepare_context = self._load_adapter_grant_context(
            connection,
            grant_id=grant.execution_request.source_preflight_grant_id,
        )
        autonomy_decision = self._decode_adapter_autonomy_decision(grant_row)
        self._verify_adapter_execution_grant(
            grant,
            intent=intent,
            intent_fingerprint=action_intent_fingerprint(intent),
            descriptor=descriptor,
            registry=registry,
            autonomy_decision=autonomy_decision,
            verified_at=grant.issued_at,
        )
        require_adapter_execution_request_matches_attestation(
            stored_request,
            attestation,
            now=grant.issued_at,
        )
        claim_row = connection.execute(
            "SELECT * FROM adapter_execution_grant_claims WHERE grant_id = ?",
            (grant_id,),
        ).fetchone()
        claim = (
            self._decode_adapter_execution_grant_claim(claim_row) if claim_row is not None else None
        )
        confirmation_claim: ActionConfirmationClaimContract | None = None
        if claim is not None:
            require_valid_adapter_execution_grant_claim(
                claim,
                grant=grant,
                now=claim.claimed_at,
                require_active=True,
            )
            confirmation_row = connection.execute(
                """
                SELECT * FROM action_confirmation_claims
                WHERE claim_id = ?
                """,
                (claim.confirmation_claim_id,),
            ).fetchone()
            if confirmation_row is None:
                raise ValueError("adapter execution claim has no confirmation claim")
            confirmation_claim = self._decode_claim(confirmation_row)
            if (
                confirmation_claim.receipt_id != claim.confirmation_receipt_id
                or action_confirmation_claim_fingerprint(confirmation_claim)
                != claim.confirmation_claim_fingerprint
            ):
                raise ValueError("adapter execution confirmation claim binding mismatch")
        context = AdapterExecutionGrantContext(
            intent=intent,
            execution_request=grant.execution_request,
            autonomy_decision=autonomy_decision,
            registry=registry,
            descriptor=descriptor,
            source_prepare_grant=source_prepare_context.grant,
            preflight_attestation=attestation,
            grant=grant,
            claim=claim,
            confirmation_claim=confirmation_claim,
        )
        if confirmation_claim is not None:
            confirmation_context = self._load_confirmation_context(
                connection,
                receipt_id=confirmation_claim.receipt_id,
            )
            self._verify_adapter_execution_confirmation_context(
                context,
                confirmation_context,
            )
            if confirmation_context.claim != confirmation_claim:
                raise ValueError("execution confirmation persisted claim mismatch")
        return context

    def _verify_adapter_execution_grant(
        self,
        grant: AdapterExecutionGrantContract,
        *,
        intent: ActionIntentContract,
        intent_fingerprint: str,
        descriptor: AdapterExecutionDescriptorContract,
        registry: AdapterExecutionRegistrySnapshotContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        verified_at: str,
    ) -> None:
        self._require_canonical_autonomy_decision(
            autonomy_decision,
            confirmation_evidence_state="absent",
        )
        require_valid_adapter_execution_grant(
            grant,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            now=verified_at,
        )

    def _verify_local_text_file_preflight_for_attestation(
        self,
        connection: Connection,
        *,
        preflight: LocalTextFilePreflightContract,
        source_context: AdapterGrantContext,
        verified_at: str,
    ) -> None:
        require_valid_local_text_file_execution_preflight(
            preflight,
            now=verified_at,
        )
        if source_context.claim is not None:
            raise ValueError("claimed prepare grant cannot be attested for execution")
        self._verify_adapter_grant_for_preflight(
            connection,
            context=source_context,
            subject_ref=preflight.subject_ref,
            action_request=preflight.adapter_request,
            expected_grant_fingerprint=preflight.grant_fingerprint,
            expected_action_fingerprint=preflight.action_fingerprint,
            expected_content_digest=preflight.desired_content_sha256,
            expected_precondition_digest=preflight.root_config_fingerprint,
            expected_descriptor_fingerprint=preflight.descriptor_fingerprint,
            expected_registry_fingerprint=preflight.registry_fingerprint,
            expected_authorization_expires_at=preflight.authorization_expires_at,
            preflight_expires_at=preflight.expires_at,
            intent_fingerprint=preflight.intent_fingerprint,
            verified_at=verified_at,
        )

    def _verify_adapter_execution_source_prepare(
        self,
        connection: Connection,
        *,
        execution_request: AdapterExecutionRequestContract,
        source_context: AdapterGrantContext,
        verified_at: str,
    ) -> None:
        if source_context.claim is not None:
            raise ValueError("claimed prepare grant cannot authorize execution")
        self._verify_adapter_grant_for_preflight(
            connection,
            context=source_context,
            subject_ref=execution_request.subject_ref,
            action_request=source_context.action_request,
            expected_grant_fingerprint=(execution_request.source_preflight_grant_fingerprint),
            expected_action_fingerprint=execution_request.source_action_fingerprint,
            expected_content_digest=execution_request.desired_content_sha256,
            expected_precondition_digest=execution_request.root_config_fingerprint,
            expected_descriptor_fingerprint=(execution_request.source_descriptor_fingerprint),
            expected_registry_fingerprint=execution_request.source_registry_fingerprint,
            expected_authorization_expires_at=(
                execution_request.preflight_authorization_expires_at
            ),
            preflight_expires_at=execution_request.preflight_expires_at,
            intent_fingerprint=execution_request.source_intent_fingerprint,
            verified_at=verified_at,
        )
        request = source_context.action_request
        if (
            execution_request.source_preflight_grant_id != source_context.grant.grant_id
            or execution_request.operation != request.operation
            or execution_request.resource_scope != request.resource_scope
            or execution_request.resource_ref != request.resource_ref
        ):
            raise ValueError("adapter execution source prepare binding mismatch")

    def _verify_adapter_execution_grant_for_active_use(
        self,
        connection: Connection,
        *,
        context: AdapterExecutionGrantContext,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_execution_request_fingerprint: str,
        intent_fingerprint: str,
        verified_at: str,
    ) -> None:
        self._verify_adapter_execution_grant(
            context.grant,
            intent=context.intent,
            intent_fingerprint=action_intent_fingerprint(context.intent),
            descriptor=context.descriptor,
            registry=context.registry,
            autonomy_decision=context.autonomy_decision,
            verified_at=verified_at,
        )
        expected = (
            context.grant.subject_ref,
            context.grant.grant_fingerprint,
            context.grant.action_fingerprint,
            context.execution_request.execution_request_fingerprint,
            context.grant.intent_fingerprint,
        )
        observed = (
            subject_ref,
            expected_grant_fingerprint,
            expected_action_fingerprint,
            expected_execution_request_fingerprint,
            intent_fingerprint,
        )
        if observed != expected:
            raise ValueError("adapter execution active-use binding mismatch")
        require_adapter_execution_request_matches_attestation(
            context.execution_request,
            context.preflight_attestation,
            now=verified_at,
        )
        source_context = self._load_adapter_grant_context(
            connection,
            grant_id=context.source_prepare_grant.grant_id,
        )
        self._verify_adapter_execution_source_prepare(
            connection,
            execution_request=context.execution_request,
            source_context=source_context,
            verified_at=verified_at,
        )
        active = self._load_active_adapter_execution_registry_epoch(connection)
        if active is None:
            raise KeyError("no active adapter execution registry")
        active_descriptor = self._resolve_adapter_execution_request(
            active.snapshot,
            context.execution_request,
        )
        if active_descriptor.descriptor_fingerprint != context.grant.descriptor_fingerprint:
            raise ValueError("adapter execution descriptor is no longer active")
        confirmed_decision = self._evaluate_canonical_autonomy_decision(
            context.autonomy_decision,
            confirmation_evidence_state="verified",
        )
        if confirmed_decision.decision != "allow":
            raise ValueError("adapter execution policy does not allow confirmed effect")

    @staticmethod
    def _verify_adapter_execution_confirmation_context(
        adapter_context: AdapterExecutionGrantContext,
        confirmation_context: ActionConfirmationContext,
    ) -> None:
        if confirmation_context.intent != adapter_context.intent:
            raise ValueError("adapter execution confirmation intent mismatch")
        receipt = confirmation_context.receipt
        expected = (
            adapter_context.grant.intent_id,
            adapter_context.grant.intent_fingerprint,
            adapter_context.grant.action_fingerprint,
            adapter_context.grant.subject_ref,
        )
        observed = (
            receipt.intent_id,
            receipt.intent_fingerprint,
            receipt.action_fingerprint,
            receipt.operator_identity_ref,
        )
        if observed != expected:
            raise ValueError("adapter execution confirmation evidence mismatch")
        if ActionConfirmationRepository._parse_timestamp(
            receipt.expires_at
        ) > ActionConfirmationRepository._parse_timestamp(adapter_context.grant.expires_at):
            raise ValueError("adapter execution confirmation exceeds grant window")

    @staticmethod
    def _adapter_execution_claim_matches(
        claim: AdapterExecutionGrantClaimContract,
        *,
        operation_id: str,
        journal_reservation_fingerprint: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_execution_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> bool:
        return (
            str(claim.operation_id),
            claim.journal_reservation_fingerprint,
            claim.subject_ref,
            claim.grant_fingerprint,
            claim.action_fingerprint,
            claim.execution_request.execution_request_fingerprint,
            claim.intent_fingerprint,
            claim.confirmation_receipt_id,
        ) == (
            str(operation_id),
            journal_reservation_fingerprint,
            subject_ref,
            expected_grant_fingerprint,
            expected_action_fingerprint,
            expected_execution_request_fingerprint,
            intent_fingerprint,
            confirmation_receipt_id,
        )

    def _require_adapter_execution_recovery_context(
        self,
        connection: Connection,
        *,
        context: AdapterExecutionGrantContext,
        claim: AdapterExecutionGrantClaimContract,
    ) -> None:
        if context.claim != claim or context.confirmation_claim is None:
            raise ValueError("adapter execution recovery persisted claim mismatch")
        require_valid_adapter_execution_grant_claim(
            claim,
            grant=context.grant,
            require_active=False,
        )
        confirmation_context = self._load_confirmation_context(
            connection,
            receipt_id=context.confirmation_claim.receipt_id,
        )
        self._verify_adapter_execution_confirmation_context(
            context,
            confirmation_context,
        )
        self._verify_claim(
            context.confirmation_claim,
            context=confirmation_context,
            expected_action_fingerprint=claim.action_fingerprint,
            expected_operation_id=str(claim.operation_id),
            expected_operator_identity_ref=claim.subject_ref,
            verified_at=None,
        )

    def _load_local_text_file_rollback_grant_context(
        self,
        connection: Connection,
        *,
        grant_id: str,
    ) -> LocalTextFileRollbackGrantContext:
        grant_row = connection.execute(
            "SELECT * FROM local_text_file_rollback_grants WHERE grant_id = ?",
            (grant_id,),
        ).fetchone()
        if grant_row is None:
            raise KeyError(f"unknown local text rollback grant: {grant_id}")
        grant = self._decode_local_text_file_rollback_grant(grant_row)
        intent_row = connection.execute(
            "SELECT * FROM action_intents WHERE intent_id = ?",
            (grant.intent_id,),
        ).fetchone()
        if intent_row is None:
            raise ValueError("local text rollback grant has no immutable intent")
        intent = self._decode_intent(intent_row)
        registry_row = connection.execute(
            """
            SELECT * FROM local_text_file_rollback_registry_epochs
            WHERE registry_fingerprint = ?
            """,
            (grant.registry_fingerprint,),
        ).fetchone()
        if registry_row is None:
            raise ValueError("local text rollback grant has no registry snapshot")
        registry = self._decode_local_text_file_rollback_registry_epoch(
            connection,
            registry_row,
        ).snapshot
        descriptor_row = connection.execute(
            """
            SELECT * FROM local_text_file_rollback_registry_descriptors
            WHERE registry_fingerprint = ? AND descriptor_fingerprint = ?
            """,
            (grant.registry_fingerprint, grant.descriptor_fingerprint),
        ).fetchone()
        if descriptor_row is None:
            raise ValueError("local text rollback grant has no descriptor snapshot")
        descriptor = self._decode_local_text_file_rollback_descriptor(descriptor_row)
        mutation_receipt = self._load_local_text_mutation_receipt(
            connection,
            receipt_fingerprint=grant.rollback_request.mutation_receipt_fingerprint,
        )
        stored_request = self._load_local_text_file_rollback_request(
            connection,
            rollback_request_fingerprint=(grant.rollback_request.rollback_request_fingerprint),
        )
        if stored_request != grant.rollback_request:
            raise ValueError("local text rollback grant request differs from ledger")
        source_context = self._load_adapter_execution_grant_context(
            connection,
            grant_id=grant.rollback_request.source_execution_grant_id,
        )
        autonomy_decision = self._decode_adapter_autonomy_decision(grant_row)
        self._verify_local_text_file_rollback_source(
            connection,
            request=grant.rollback_request,
            mutation_receipt=mutation_receipt,
            source_context=source_context,
        )
        self._verify_local_text_file_rollback_grant(
            grant,
            intent=intent,
            intent_fingerprint=action_intent_fingerprint(intent),
            descriptor=descriptor,
            registry=registry,
            autonomy_decision=autonomy_decision,
            verified_at=grant.issued_at,
        )
        claim_row = connection.execute(
            "SELECT * FROM local_text_file_rollback_grant_claims WHERE grant_id = ?",
            (grant_id,),
        ).fetchone()
        claim = (
            self._decode_local_text_file_rollback_claim(claim_row)
            if claim_row is not None
            else None
        )
        confirmation_claim: ActionConfirmationClaimContract | None = None
        if claim is not None:
            require_valid_local_text_file_rollback_grant_claim(
                claim,
                grant=grant,
                now=claim.claimed_at,
                require_active=True,
            )
            confirmation_row = connection.execute(
                "SELECT * FROM action_confirmation_claims WHERE claim_id = ?",
                (claim.confirmation_claim_id,),
            ).fetchone()
            if confirmation_row is None:
                raise ValueError("local text rollback claim has no confirmation claim")
            confirmation_claim = self._decode_claim(confirmation_row)
            if (
                confirmation_claim.receipt_id != claim.confirmation_receipt_id
                or action_confirmation_claim_fingerprint(confirmation_claim)
                != claim.confirmation_claim_fingerprint
            ):
                raise ValueError("local text rollback confirmation claim mismatch")
        rollback_receipt_row = connection.execute(
            "SELECT * FROM local_text_rollback_receipts WHERE rollback_grant_id = ?",
            (grant_id,),
        ).fetchone()
        rollback_receipt = (
            self._decode_local_text_rollback_receipt(rollback_receipt_row)
            if rollback_receipt_row is not None
            else None
        )
        context = LocalTextFileRollbackGrantContext(
            intent=intent,
            rollback_request=grant.rollback_request,
            autonomy_decision=autonomy_decision,
            registry=registry,
            descriptor=descriptor,
            mutation_receipt=mutation_receipt,
            source_execution_context=source_context,
            grant=grant,
            claim=claim,
            confirmation_claim=confirmation_claim,
            rollback_receipt=rollback_receipt,
        )
        if confirmation_claim is not None:
            confirmation_context = self._load_confirmation_context(
                connection,
                receipt_id=confirmation_claim.receipt_id,
            )
            self._verify_local_text_file_rollback_confirmation_context(
                context,
                confirmation_context,
            )
            if confirmation_context.claim != confirmation_claim:
                raise ValueError("rollback confirmation persisted claim mismatch")
        if rollback_receipt is not None:
            if claim is None:
                raise ValueError("rollback receipt has no persisted claim")
            require_local_text_rollback_receipt_matches_claim(
                rollback_receipt,
                mutation_receipt=mutation_receipt,
                claim=claim,
            )
        return context

    def _require_local_text_mutation_receipt_matches_execution(
        self,
        connection: Connection,
        *,
        receipt: LocalTextMutationReceipt,
        source_context: AdapterExecutionGrantContext,
        verified_at: str,
    ) -> None:
        claim = source_context.claim
        if claim is None:
            raise ValueError("mutation receipt has no persisted execution claim")
        self._require_adapter_execution_recovery_context(
            connection,
            context=source_context,
            claim=claim,
        )
        request = source_context.execution_request
        expected = (
            source_context.grant.grant_id,
            claim.claim_id,
            str(claim.operation_id),
            request.operation,
            request.resource_ref,
            request.subject_ref,
            request.preflight_fingerprint,
            request.before_content_sha256,
            request.desired_content_sha256,
            request.root_config_fingerprint,
        )
        observed = (
            receipt.execution_grant_id,
            receipt.execution_claim_id,
            receipt.operation_id,
            receipt.operation,
            receipt.resource_ref,
            receipt.subject_ref,
            receipt.preflight_fingerprint,
            receipt.before_content_sha256,
            receipt.desired_content_sha256,
            receipt.root_config_fingerprint,
        )
        if observed != expected:
            raise ValueError("mutation receipt differs from persisted execution evidence")
        committed_at = self._parse_timestamp(receipt.committed_at)
        if committed_at < self._parse_timestamp(claim.claimed_at):
            raise ValueError("mutation receipt predates execution claim")
        if committed_at > self._parse_timestamp(verified_at):
            raise ValueError("mutation receipt is future-dated")

    def _verify_local_text_file_rollback_source(
        self,
        connection: Connection,
        *,
        request: LocalTextFileRollbackRequestContract,
        mutation_receipt: LocalTextMutationReceipt,
        source_context: AdapterExecutionGrantContext,
    ) -> None:
        if source_context.claim is None:
            raise ValueError("rollback source execution has no claim")
        self._require_adapter_execution_recovery_context(
            connection,
            context=source_context,
            claim=source_context.claim,
        )
        expected = build_local_text_file_rollback_request(
            mutation_receipt,
            source_execution_grant=source_context.grant,
            source_execution_claim=source_context.claim,
            rollback_operation_id=request.rollback_operation_id,
            requested_at=request.requested_at,
            expires_at=request.expires_at,
        )
        if expected != request:
            raise ValueError("rollback request differs from original execution evidence")

    def _verify_local_text_file_rollback_grant(
        self,
        grant: LocalTextFileRollbackGrantContract,
        *,
        intent: ActionIntentContract,
        intent_fingerprint: str,
        descriptor: LocalTextFileRollbackDescriptorContract,
        registry: LocalTextFileRollbackRegistrySnapshotContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        verified_at: str,
    ) -> None:
        self._require_canonical_autonomy_decision(
            autonomy_decision,
            confirmation_evidence_state="absent",
        )
        require_valid_local_text_file_rollback_grant(
            grant,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            now=verified_at,
        )

    def _verify_local_text_file_rollback_grant_for_active_use(
        self,
        connection: Connection,
        *,
        context: LocalTextFileRollbackGrantContext,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_rollback_request_fingerprint: str,
        intent_fingerprint: str,
        verified_at: str,
    ) -> None:
        self._verify_local_text_file_rollback_grant(
            context.grant,
            intent=context.intent,
            intent_fingerprint=action_intent_fingerprint(context.intent),
            descriptor=context.descriptor,
            registry=context.registry,
            autonomy_decision=context.autonomy_decision,
            verified_at=verified_at,
        )
        expected = (
            context.grant.subject_ref,
            context.grant.grant_fingerprint,
            context.grant.action_fingerprint,
            context.rollback_request.rollback_request_fingerprint,
            context.grant.intent_fingerprint,
        )
        observed = (
            subject_ref,
            expected_grant_fingerprint,
            expected_action_fingerprint,
            expected_rollback_request_fingerprint,
            intent_fingerprint,
        )
        if observed != expected:
            raise ValueError("local text rollback active-use binding mismatch")
        self._verify_local_text_file_rollback_source(
            connection,
            request=context.rollback_request,
            mutation_receipt=context.mutation_receipt,
            source_context=context.source_execution_context,
        )
        active = self._load_active_local_text_file_rollback_registry_epoch(connection)
        if active is None:
            raise KeyError("no active local text rollback registry")
        descriptor = self._resolve_local_text_file_rollback_request(
            active.snapshot,
            context.rollback_request,
        )
        if descriptor.descriptor_fingerprint != context.grant.descriptor_fingerprint:
            raise ValueError("local text rollback descriptor is no longer active")
        confirmed = self._evaluate_canonical_autonomy_decision(
            context.autonomy_decision,
            confirmation_evidence_state="verified",
        )
        if confirmed.decision != "allow":
            raise ValueError("local text rollback policy does not allow effect")

    @staticmethod
    def _verify_local_text_file_rollback_confirmation_context(
        rollback_context: LocalTextFileRollbackGrantContext,
        confirmation_context: ActionConfirmationContext,
    ) -> None:
        if confirmation_context.intent != rollback_context.intent:
            raise ValueError("local text rollback confirmation intent mismatch")
        receipt = confirmation_context.receipt
        expected = (
            rollback_context.grant.intent_id,
            rollback_context.grant.intent_fingerprint,
            rollback_context.grant.action_fingerprint,
            rollback_context.grant.subject_ref,
        )
        observed = (
            receipt.intent_id,
            receipt.intent_fingerprint,
            receipt.action_fingerprint,
            receipt.operator_identity_ref,
        )
        if observed != expected:
            raise ValueError("local text rollback confirmation evidence mismatch")
        if ActionConfirmationRepository._parse_timestamp(
            receipt.expires_at
        ) > ActionConfirmationRepository._parse_timestamp(rollback_context.grant.expires_at):
            raise ValueError("local text rollback confirmation exceeds grant window")

    @staticmethod
    def _local_text_file_rollback_claim_matches(
        claim: LocalTextFileRollbackGrantClaimContract,
        *,
        rollback_operation_id: str,
        rollback_journal_reservation_fingerprint: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_rollback_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> bool:
        return (
            str(claim.rollback_operation_id),
            claim.rollback_journal_reservation_fingerprint,
            claim.subject_ref,
            claim.grant_fingerprint,
            claim.action_fingerprint,
            claim.rollback_request.rollback_request_fingerprint,
            claim.intent_fingerprint,
            claim.confirmation_receipt_id,
        ) == (
            rollback_operation_id,
            rollback_journal_reservation_fingerprint,
            subject_ref,
            expected_grant_fingerprint,
            expected_action_fingerprint,
            expected_rollback_request_fingerprint,
            intent_fingerprint,
            confirmation_receipt_id,
        )

    def _require_local_text_file_rollback_recovery_context(
        self,
        connection: Connection,
        *,
        context: LocalTextFileRollbackGrantContext,
        claim: LocalTextFileRollbackGrantClaimContract,
    ) -> None:
        if context.claim != claim or context.confirmation_claim is None:
            raise ValueError("local text rollback persisted claim mismatch")
        require_valid_local_text_file_rollback_grant_claim(
            claim,
            grant=context.grant,
            require_active=False,
        )
        self._verify_local_text_file_rollback_source(
            connection,
            request=context.rollback_request,
            mutation_receipt=context.mutation_receipt,
            source_context=context.source_execution_context,
        )
        confirmation_context = self._load_confirmation_context(
            connection,
            receipt_id=context.confirmation_claim.receipt_id,
        )
        self._verify_local_text_file_rollback_confirmation_context(
            context,
            confirmation_context,
        )
        self._verify_claim(
            context.confirmation_claim,
            context=confirmation_context,
            expected_action_fingerprint=claim.action_fingerprint,
            expected_operation_id=str(claim.rollback_operation_id),
            expected_operator_identity_ref=claim.subject_ref,
            verified_at=None,
        )

    def _verify_adapter_grant(
        self,
        grant: AdapterGrantContract,
        *,
        intent: ActionIntentContract,
        intent_fingerprint: str,
        descriptor: AdapterDescriptorContract,
        registry: AdapterRegistrySnapshotContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        verified_at: str,
    ) -> None:
        self._require_canonical_autonomy_decision(
            autonomy_decision,
            confirmation_evidence_state="absent",
        )
        require_valid_adapter_grant(
            grant,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            now=verified_at,
        )

    def _verify_adapter_grant_for_claim(
        self,
        connection: Connection,
        *,
        context: AdapterGrantContext,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        verified_at: str,
    ) -> None:
        self._verify_adapter_grant(
            context.grant,
            intent=context.intent,
            intent_fingerprint=action_intent_fingerprint(context.intent),
            descriptor=context.descriptor,
            registry=context.registry,
            autonomy_decision=context.autonomy_decision,
            verified_at=verified_at,
        )
        expected = {
            "subject_ref": context.grant.subject_ref,
            "expected_grant_fingerprint": context.grant.grant_fingerprint,
            "expected_action_fingerprint": context.grant.action_fingerprint,
            "intent_fingerprint": context.grant.intent_fingerprint,
        }
        provided = {
            "subject_ref": subject_ref,
            "expected_grant_fingerprint": expected_grant_fingerprint,
            "expected_action_fingerprint": expected_action_fingerprint,
            "intent_fingerprint": intent_fingerprint,
        }
        for field_name, expected_value in expected.items():
            if provided[field_name] != expected_value:
                raise ValueError(f"adapter grant {field_name} mismatch")
        active = self._load_active_adapter_registry_epoch(connection)
        if active is None:
            raise KeyError("no active adapter registry")
        active_descriptor = self._resolve_adapter_request(
            active.snapshot,
            context.action_request,
        )
        if active_descriptor.descriptor_fingerprint != context.grant.descriptor_fingerprint:
            raise ValueError("adapter descriptor is no longer active")
        claim_autonomy = self._evaluate_canonical_autonomy_decision(
            context.autonomy_decision,
            confirmation_evidence_state=(
                "verified" if context.grant.confirmation_required else "absent"
            ),
        )
        if claim_autonomy.decision != "allow":
            raise ValueError("adapter autonomy policy does not allow claim")

    def _verify_adapter_grant_for_preflight(
        self,
        connection: Connection,
        *,
        context: AdapterGrantContext,
        subject_ref: str,
        action_request: AdapterActionRequestContract,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_content_digest: str,
        expected_precondition_digest: str,
        expected_descriptor_fingerprint: str,
        expected_registry_fingerprint: str,
        expected_authorization_expires_at: str,
        preflight_expires_at: str,
        intent_fingerprint: str,
        verified_at: str,
    ) -> None:
        if not isinstance(action_request, AdapterActionRequestContract):
            raise TypeError("adapter preflight action request is invalid")
        if (
            context.action_request.action_kind != "prepare_external_action"
            or action_request.action_kind != "prepare_external_action"
        ):
            raise ValueError("adapter preflight requires prepare-only authority")
        self._verify_adapter_grant(
            context.grant,
            intent=context.intent,
            intent_fingerprint=action_intent_fingerprint(context.intent),
            descriptor=context.descriptor,
            registry=context.registry,
            autonomy_decision=context.autonomy_decision,
            verified_at=verified_at,
        )
        expected = {
            "subject_ref": context.grant.subject_ref,
            "action_request": context.action_request,
            "expected_grant_fingerprint": context.grant.grant_fingerprint,
            "expected_action_fingerprint": context.grant.action_fingerprint,
            "expected_content_digest": context.intent.content_digest,
            "expected_precondition_digest": context.intent.precondition_digest,
            "expected_descriptor_fingerprint": context.grant.descriptor_fingerprint,
            "expected_registry_fingerprint": context.grant.registry_fingerprint,
            "expected_authorization_expires_at": context.grant.expires_at,
            "intent_fingerprint": context.grant.intent_fingerprint,
        }
        provided = {
            "subject_ref": subject_ref,
            "action_request": action_request,
            "expected_grant_fingerprint": expected_grant_fingerprint,
            "expected_action_fingerprint": expected_action_fingerprint,
            "expected_content_digest": expected_content_digest,
            "expected_precondition_digest": expected_precondition_digest,
            "expected_descriptor_fingerprint": expected_descriptor_fingerprint,
            "expected_registry_fingerprint": expected_registry_fingerprint,
            "expected_authorization_expires_at": expected_authorization_expires_at,
            "intent_fingerprint": intent_fingerprint,
        }
        for field_name, expected_value in expected.items():
            if provided[field_name] != expected_value:
                raise ValueError(f"adapter preflight {field_name} mismatch")
        verified = self._parse_timestamp(verified_at)
        preflight_expiry = self._parse_timestamp(preflight_expires_at)
        grant_expiry = self._parse_timestamp(expected_authorization_expires_at)
        if preflight_expiry <= verified or preflight_expiry > grant_expiry:
            raise ValueError("adapter preflight expiry exceeds active grant window")
        active = self._load_active_adapter_registry_epoch(connection)
        if active is None:
            raise KeyError("no active adapter registry")
        active_descriptor = self._resolve_adapter_request(
            active.snapshot,
            action_request,
        )
        if active_descriptor.descriptor_fingerprint != context.grant.descriptor_fingerprint:
            raise ValueError("adapter descriptor is no longer active")
        if context.autonomy_decision.decision not in {
            "allow",
            "require_confirmation",
        }:
            raise ValueError("adapter autonomy policy does not allow preflight")

    @classmethod
    def _require_canonical_autonomy_decision(
        cls,
        decision: AutonomyActionPolicyDecisionContract,
        *,
        confirmation_evidence_state: str,
    ) -> None:
        expected = cls._evaluate_canonical_autonomy_decision(
            decision,
            confirmation_evidence_state=confirmation_evidence_state,
        )
        if expected != decision:
            raise ValueError("adapter autonomy decision is not canonical")

    @staticmethod
    def _evaluate_canonical_autonomy_decision(
        decision: AutonomyActionPolicyDecisionContract,
        *,
        confirmation_evidence_state: str,
    ) -> AutonomyActionPolicyDecisionContract:
        if decision.policy_version != AUTONOMY_ACTION_POLICY_VERSION:
            raise ValueError("adapter autonomy policy version mismatch")
        policy = AUTONOMY_LEVEL_POLICIES.get(str(decision.effective_autonomy_level))
        return evaluate_autonomy_action(
            requested_autonomy_level=decision.requested_autonomy_level,
            max_autonomy_level=decision.max_autonomy_level,
            effective_autonomy_level=decision.effective_autonomy_level,
            autonomy_ladder_status=decision.autonomy_ladder_status,
            action_kind=decision.action_kind,
            selected_capability_mode=decision.selected_capability_mode,
            max_capability_mode=decision.max_capability_mode,
            allowed_runtime_actions=(
                policy["allowed_runtime_actions"] if policy is not None else None
            ),
            blocked_runtime_actions=(
                policy["blocked_runtime_actions"] if policy is not None else None
            ),
            human_confirmation_required=decision.confirmation_required,
            human_confirmation_mode=decision.confirmation_requirement,
            confirmation_evidence_state=confirmation_evidence_state,
            autonomy_validation_errors=(),
        )

    @staticmethod
    def _resolve_adapter_request(
        registry: AdapterRegistrySnapshotContract,
        action_request: AdapterActionRequestContract,
    ) -> AdapterDescriptorContract:
        descriptor = resolve_adapter_descriptor(
            registry,
            adapter_id=action_request.adapter_id,
            adapter_version=action_request.adapter_version,
        )
        if descriptor is None:
            raise ValueError("adapter descriptor is not allowlisted")
        require_valid_adapter_action_request(
            action_request,
            descriptor=descriptor,
        )
        return descriptor

    @staticmethod
    def _resolve_adapter_execution_request(
        registry: AdapterExecutionRegistrySnapshotContract,
        execution_request: AdapterExecutionRequestContract,
    ) -> AdapterExecutionDescriptorContract:
        descriptor = resolve_adapter_execution_descriptor(
            registry,
            adapter_id=execution_request.adapter_id,
            adapter_version=execution_request.adapter_version,
        )
        if descriptor is None:
            raise ValueError("adapter execution descriptor is not allowlisted")
        require_valid_adapter_execution_request(execution_request)
        if (
            execution_request.action_kind != descriptor.action_kind
            or execution_request.operation not in descriptor.allowed_operations
            or execution_request.resource_scope not in descriptor.allowed_resource_scopes
            or execution_request.execution_policy_version != descriptor.execution_policy_version
            or execution_request.execution_backend_version != descriptor.execution_backend_version
        ):
            raise ValueError("adapter execution request descriptor mismatch")
        return descriptor

    @staticmethod
    def _resolve_local_text_file_rollback_request(
        registry: LocalTextFileRollbackRegistrySnapshotContract,
        request: LocalTextFileRollbackRequestContract,
    ) -> LocalTextFileRollbackDescriptorContract:
        descriptor = resolve_local_text_file_rollback_descriptor(
            registry,
            adapter_id=request.adapter_id,
            adapter_version=request.adapter_version,
        )
        if descriptor is None:
            raise ValueError("local text rollback descriptor is not allowlisted")
        require_valid_local_text_file_rollback_request(request)
        if (
            request.action_kind != descriptor.action_kind
            or request.operation not in descriptor.allowed_operations
            or request.resource_scope not in descriptor.allowed_resource_scopes
            or request.rollback_policy_version != descriptor.rollback_policy_version
            or request.rollback_backend_version != descriptor.rollback_backend_version
        ):
            raise ValueError("local text rollback request descriptor mismatch")
        return descriptor

    def _record_adapter_intent(
        self,
        connection: Connection,
        intent: ActionIntentContract,
        *,
        intent_fingerprint: str,
        payload: str,
        payload_sha256: str,
    ) -> None:
        existing = connection.execute(
            "SELECT * FROM action_intents WHERE intent_id = ?",
            (intent.intent_id,),
        ).fetchone()
        if existing is not None:
            if self._decode_intent(existing) != intent:
                raise ValueError("action intent identity already has different evidence")
            return
        connection.execute(
            """
            INSERT INTO action_intents (
                intent_id,
                intent_fingerprint,
                action_fingerprint,
                origin_request_id,
                session_id,
                mission_id,
                operator_identity_ref,
                operation,
                issued_at,
                expires_at,
                payload,
                payload_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intent.intent_id,
                intent_fingerprint,
                intent.action_fingerprint,
                intent.origin_request_id,
                intent.session_id,
                intent.mission_id,
                intent.operator_identity_ref,
                intent.operation,
                intent.issued_at,
                intent.expires_at,
                payload,
                payload_sha256,
            ),
        )

    @staticmethod
    def _verify_adapter_confirmation_context(
        adapter_context: AdapterGrantContext,
        confirmation_context: ActionConfirmationContext,
    ) -> None:
        if confirmation_context.intent != adapter_context.intent:
            raise ValueError("adapter confirmation intent mismatch")
        receipt = confirmation_context.receipt
        expected = (
            adapter_context.grant.intent_id,
            adapter_context.grant.intent_fingerprint,
            adapter_context.grant.action_fingerprint,
            adapter_context.grant.subject_ref,
        )
        observed = (
            receipt.intent_id,
            receipt.intent_fingerprint,
            receipt.action_fingerprint,
            receipt.operator_identity_ref,
        )
        if observed != expected:
            raise ValueError("adapter confirmation evidence mismatch")

    @staticmethod
    def _build_confirmation_claim(
        context: ActionConfirmationContext,
        *,
        operation_id: str,
        claimed_at: str,
    ) -> ActionConfirmationClaimContract:
        intent = context.intent
        receipt = context.receipt
        return ActionConfirmationClaimContract(
            claim_id=f"confirmation-claim://{uuid4().hex}",
            receipt_id=receipt.receipt_id,
            receipt_fingerprint=human_confirmation_receipt_fingerprint(receipt),
            intent_id=intent.intent_id,
            intent_fingerprint=action_intent_fingerprint(intent),
            action_fingerprint=intent.action_fingerprint,
            operation_id=OperationId(str(operation_id)),
            origin_request_id=intent.origin_request_id,
            session_id=intent.session_id,
            mission_id=intent.mission_id,
            operator_identity_ref=intent.operator_identity_ref,
            operation=intent.operation,
            claimed_at=claimed_at,
            expires_at=receipt.expires_at,
        )

    @staticmethod
    def _insert_confirmation_claim(
        connection: Connection,
        claim: ActionConfirmationClaimContract,
        *,
        payload: str,
        payload_sha256: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO action_confirmation_claims (
                claim_id,
                claim_fingerprint,
                receipt_id,
                receipt_fingerprint,
                intent_id,
                intent_fingerprint,
                action_fingerprint,
                operation_id,
                origin_request_id,
                session_id,
                mission_id,
                operator_identity_ref,
                operation,
                claimed_at,
                expires_at,
                payload,
                payload_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.claim_id,
                action_confirmation_claim_fingerprint(claim),
                claim.receipt_id,
                claim.receipt_fingerprint,
                claim.intent_id,
                claim.intent_fingerprint,
                claim.action_fingerprint,
                claim.operation_id,
                claim.origin_request_id,
                claim.session_id,
                claim.mission_id,
                claim.operator_identity_ref,
                claim.operation,
                claim.claimed_at,
                claim.expires_at,
                payload,
                payload_sha256,
            ),
        )

    @staticmethod
    def _insert_adapter_execution_claim(
        connection: Connection,
        claim: AdapterExecutionGrantClaimContract,
        *,
        payload: str,
        payload_sha256: str,
    ) -> None:
        request = claim.execution_request
        connection.execute(
            """
            INSERT INTO adapter_execution_grant_claims (
                claim_id,
                claim_fingerprint,
                grant_id,
                grant_fingerprint,
                operation_id,
                journal_reservation_fingerprint,
                subject_ref,
                intent_id,
                intent_fingerprint,
                action_fingerprint,
                execution_request_fingerprint,
                preflight_fingerprint,
                confirmation_receipt_id,
                confirmation_claim_id,
                confirmation_claim_fingerprint,
                claimed_at,
                expires_at,
                payload,
                payload_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.claim_id,
                claim.claim_fingerprint,
                claim.grant_id,
                claim.grant_fingerprint,
                claim.operation_id,
                claim.journal_reservation_fingerprint,
                claim.subject_ref,
                claim.intent_id,
                claim.intent_fingerprint,
                claim.action_fingerprint,
                request.execution_request_fingerprint,
                request.preflight_fingerprint,
                claim.confirmation_receipt_id,
                claim.confirmation_claim_id,
                claim.confirmation_claim_fingerprint,
                claim.claimed_at,
                claim.expires_at,
                payload,
                payload_sha256,
            ),
        )

    @staticmethod
    def _insert_local_text_file_rollback_claim(
        connection: Connection,
        claim: LocalTextFileRollbackGrantClaimContract,
        *,
        payload: str,
        payload_sha256: str,
    ) -> None:
        request = claim.rollback_request
        connection.execute(
            """
            INSERT INTO local_text_file_rollback_grant_claims (
                claim_id,
                claim_fingerprint,
                grant_id,
                grant_fingerprint,
                rollback_operation_id,
                rollback_journal_reservation_fingerprint,
                subject_ref,
                intent_id,
                intent_fingerprint,
                action_fingerprint,
                rollback_request_fingerprint,
                mutation_receipt_fingerprint,
                confirmation_receipt_id,
                confirmation_claim_id,
                confirmation_claim_fingerprint,
                claimed_at,
                expires_at,
                payload,
                payload_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim.claim_id,
                claim.claim_fingerprint,
                claim.grant_id,
                claim.grant_fingerprint,
                claim.rollback_operation_id,
                claim.rollback_journal_reservation_fingerprint,
                claim.subject_ref,
                claim.intent_id,
                claim.intent_fingerprint,
                claim.action_fingerprint,
                request.rollback_request_fingerprint,
                request.mutation_receipt_fingerprint,
                claim.confirmation_receipt_id,
                claim.confirmation_claim_id,
                claim.confirmation_claim_fingerprint,
                claim.claimed_at,
                claim.expires_at,
                payload,
                payload_sha256,
            ),
        )

    @staticmethod
    def _decode_json_payload(
        row: Row,
        *,
        payload_column: str,
        hash_column: str,
        label: str,
    ) -> object:
        payload = row[payload_column]
        payload_sha256 = sha256(payload.encode("utf-8")).hexdigest()
        if payload_sha256 != row[hash_column]:
            raise ValueError(f"{label} payload hash mismatch")
        try:
            return loads(payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid {label} payload") from exc

    @staticmethod
    def _canonical_sequence(values: tuple[str, ...]) -> str:
        return dumps(
            list(values),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _require_adapter_columns(row: Row, **expected: object) -> None:
        for field_name, expected_value in expected.items():
            if row[field_name] != expected_value:
                raise ValueError(f"adapter stored {field_name} mismatch")

    def _load_intent_and_challenge(
        self,
        connection: Connection,
        *,
        challenge_id: str,
    ) -> tuple[
        ActionIntentContract,
        ActionConfirmationChallengeContract,
        OperationDispatchContract | None,
    ]:
        challenge_row = connection.execute(
            "SELECT * FROM action_confirmation_challenges WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
        if challenge_row is None:
            raise KeyError(f"unknown action confirmation challenge: {challenge_id}")
        challenge = self._decode_challenge(challenge_row)
        intent_row = connection.execute(
            "SELECT * FROM action_intents WHERE intent_id = ?",
            (challenge.intent_id,),
        ).fetchone()
        if intent_row is None:
            raise ValueError("action confirmation challenge has no immutable intent")
        intent = self._decode_intent(intent_row)
        self._verify_challenge(
            challenge,
            intent=intent,
            intent_fingerprint=action_intent_fingerprint(intent),
        )
        prepared_row = connection.execute(
            """
            SELECT * FROM action_confirmation_prepared_dispatches
            WHERE intent_id = ?
            """,
            (intent.intent_id,),
        ).fetchone()
        prepared_dispatch = (
            self._decode_prepared_dispatch(prepared_row, intent=intent)
            if prepared_row is not None
            else None
        )
        return intent, challenge, prepared_dispatch

    def _load_confirmation_context(
        self,
        connection: Connection,
        *,
        receipt_id: str,
    ) -> ActionConfirmationContext:
        receipt_row = connection.execute(
            "SELECT * FROM human_confirmation_receipts WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        if receipt_row is None:
            raise KeyError(f"unknown human confirmation receipt: {receipt_id}")
        receipt = self._decode_receipt(receipt_row)
        intent, challenge, prepared_dispatch = self._load_intent_and_challenge(
            connection,
            challenge_id=receipt.challenge_id,
        )
        self._verify_receipt(
            receipt,
            intent=intent,
            challenge=challenge,
            verified_at=None,
        )
        claim_row = connection.execute(
            "SELECT * FROM action_confirmation_claims WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        claim = self._decode_claim(claim_row) if claim_row is not None else None
        context = ActionConfirmationContext(
            intent=intent,
            challenge=challenge,
            receipt=receipt,
            prepared_dispatch=prepared_dispatch,
            claim=claim,
        )
        if claim is not None:
            self._verify_claim(
                claim,
                context=context,
                expected_action_fingerprint=claim.action_fingerprint,
                expected_operation_id=claim.operation_id,
                expected_operator_identity_ref=claim.operator_identity_ref,
                verified_at=None,
            )
        return context

    def _decode_intent(self, row: Row) -> ActionIntentContract:
        intent = self._decode_contract(row, ActionIntentContract)
        expected = self._verify_intent(intent)
        self._require_columns(
            row,
            intent_id=intent.intent_id,
            intent_fingerprint=expected,
            action_fingerprint=intent.action_fingerprint,
            origin_request_id=intent.origin_request_id,
            session_id=intent.session_id,
            mission_id=intent.mission_id,
            operator_identity_ref=intent.operator_identity_ref,
            operation=intent.operation,
            issued_at=intent.issued_at,
            expires_at=intent.expires_at,
        )
        return intent

    def _decode_prepared_dispatch(
        self,
        row: Row,
        *,
        intent: ActionIntentContract,
    ) -> OperationDispatchContract:
        payload = row["payload"]
        payload_sha256 = sha256(payload.encode("utf-8")).hexdigest()
        if payload_sha256 != row["payload_sha256"]:
            raise ValueError("prepared dispatch payload hash mismatch")
        try:
            raw_payload = loads(payload)
            dispatch = self._hydrate_operation_dispatch(raw_payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid prepared operation dispatch payload") from exc
        canonical_payload, canonical_sha256 = self._serialize(dispatch)
        if canonical_payload != payload or canonical_sha256 != payload_sha256:
            raise ValueError("prepared dispatch payload is not canonical")
        self._verify_prepared_dispatch(dispatch, intent=intent)
        self._require_columns(
            row,
            intent_id=intent.intent_id,
            intent_fingerprint=action_intent_fingerprint(intent),
            action_fingerprint=intent.action_fingerprint,
            operation_id=dispatch.operation_id,
            origin_request_id=dispatch.request_id,
            session_id=dispatch.session_id,
            mission_id=dispatch.mission_id,
            operator_identity_ref=self._dispatch_operator_identity_ref(dispatch),
            dispatch_fingerprint=payload_sha256,
            expires_at=intent.expires_at,
        )
        return dispatch

    @staticmethod
    def _hydrate_operation_dispatch(payload: object) -> OperationDispatchContract:
        if not isinstance(payload, dict):
            raise ValueError("prepared dispatch payload must be an object")
        values = dict(payload)
        workflow_policy = values.get("workflow_policy_decision")
        if isinstance(workflow_policy, dict):
            values["workflow_policy_decision"] = WorkflowPolicyDecisionContract(**workflow_policy)
        elif workflow_policy is not None and not isinstance(
            workflow_policy,
            WorkflowPolicyDecisionContract,
        ):
            raise ValueError("prepared dispatch workflow policy is invalid")
        workflow_transition = values.get("workflow_lifecycle_transition")
        if isinstance(workflow_transition, dict):
            values["workflow_lifecycle_transition"] = WorkflowLifecycleTransitionContract(
                **workflow_transition
            )
        elif workflow_transition is not None and not isinstance(
            workflow_transition,
            WorkflowLifecycleTransitionContract,
        ):
            raise ValueError("prepared dispatch workflow transition is invalid")
        return OperationDispatchContract(**values)

    def _decode_challenge(self, row: Row) -> ActionConfirmationChallengeContract:
        challenge = self._decode_contract(row, ActionConfirmationChallengeContract)
        self._require_columns(
            row,
            challenge_id=challenge.challenge_id,
            challenge_fingerprint=action_confirmation_challenge_fingerprint(challenge),
            intent_id=challenge.intent_id,
            intent_fingerprint=challenge.intent_fingerprint,
            action_fingerprint=challenge.action_fingerprint,
            origin_request_id=challenge.origin_request_id,
            session_id=challenge.session_id,
            mission_id=challenge.mission_id,
            operator_identity_ref=challenge.operator_identity_ref,
            operation=challenge.operation,
            issued_at=challenge.issued_at,
            expires_at=challenge.expires_at,
        )
        return challenge

    def _decode_receipt(self, row: Row) -> HumanConfirmationReceiptContract:
        receipt = self._decode_contract(row, HumanConfirmationReceiptContract)
        self._require_columns(
            row,
            receipt_id=receipt.receipt_id,
            receipt_fingerprint=human_confirmation_receipt_fingerprint(receipt),
            challenge_id=receipt.challenge_id,
            challenge_fingerprint=receipt.challenge_fingerprint,
            intent_id=receipt.intent_id,
            intent_fingerprint=receipt.intent_fingerprint,
            action_fingerprint=receipt.action_fingerprint,
            origin_request_id=receipt.origin_request_id,
            session_id=receipt.session_id,
            mission_id=receipt.mission_id,
            operator_identity_ref=receipt.operator_identity_ref,
            operation=receipt.operation,
            confirmed_at=receipt.confirmed_at,
            expires_at=receipt.expires_at,
        )
        return receipt

    def _decode_claim(self, row: Row) -> ActionConfirmationClaimContract:
        claim = self._decode_contract(row, ActionConfirmationClaimContract)
        self._require_columns(
            row,
            claim_id=claim.claim_id,
            claim_fingerprint=action_confirmation_claim_fingerprint(claim),
            receipt_id=claim.receipt_id,
            receipt_fingerprint=claim.receipt_fingerprint,
            intent_id=claim.intent_id,
            intent_fingerprint=claim.intent_fingerprint,
            action_fingerprint=claim.action_fingerprint,
            operation_id=claim.operation_id,
            origin_request_id=claim.origin_request_id,
            session_id=claim.session_id,
            mission_id=claim.mission_id,
            operator_identity_ref=claim.operator_identity_ref,
            operation=claim.operation,
            claimed_at=claim.claimed_at,
            expires_at=claim.expires_at,
        )
        return claim

    def _decode_presentation(
        self,
        row: Row,
        *,
        context: ActionConfirmationContext,
    ) -> ActionConfirmationPresentation:
        presentation = self._decode_contract(row, ActionConfirmationPresentation)
        claim = context.claim
        if claim is None:
            raise ValueError("action confirmation presentation has no immutable claim")
        presentation_fingerprint = sha256(row["payload"].encode("utf-8")).hexdigest()
        self._require_columns(
            row,
            presentation_id=presentation.presentation_id,
            presentation_fingerprint=presentation_fingerprint,
            claim_id=presentation.claim_id,
            claim_fingerprint=presentation.claim_fingerprint,
            receipt_id=presentation.receipt_id,
            operation_id=presentation.operation_id,
            origin_request_id=presentation.origin_request_id,
            action_fingerprint=presentation.action_fingerprint,
            intent_fingerprint=presentation.intent_fingerprint,
            claimed_at=presentation.claimed_at,
            verified_at=presentation.verified_at,
            operator_identity_ref=presentation.operator_identity_ref,
        )
        self._require_attributes(
            presentation,
            claim_id=claim.claim_id,
            claim_fingerprint=action_confirmation_claim_fingerprint(claim),
            receipt_id=claim.receipt_id,
            operation_id=str(claim.operation_id),
            origin_request_id=str(claim.origin_request_id),
            action_fingerprint=claim.action_fingerprint,
            intent_fingerprint=claim.intent_fingerprint,
            claimed_at=claim.claimed_at,
            operator_identity_ref=claim.operator_identity_ref,
        )
        verified_at = self._parse_timestamp(presentation.verified_at)
        if verified_at < self._parse_timestamp(presentation.claimed_at):
            raise ValueError("action confirmation presentation predates its claim")
        if verified_at >= self._parse_timestamp(claim.expires_at):
            raise ValueError("action confirmation presentation is expired")
        return presentation

    @staticmethod
    def _decode_contract(row: Row, contract_type: type[ContractT]) -> ContractT:
        payload = row["payload"]
        payload_sha256 = sha256(payload.encode("utf-8")).hexdigest()
        if payload_sha256 != row["payload_sha256"]:
            raise ValueError("action confirmation payload hash mismatch")
        try:
            return contract_type(**loads(payload))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid action confirmation payload") from exc

    @staticmethod
    def _serialize(contract: object) -> tuple[str, str]:
        payload = dumps(
            asdict(contract),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return payload, sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def _verify_intent(cls, intent: ActionIntentContract) -> str:
        require_valid_action_intent(intent)
        cls._require_confirmation_shape(intent)
        if not verify_action_fingerprint(intent):
            raise ValueError("action intent fingerprint does not match its exact action")
        cls._require_chronology(intent.issued_at, intent.expires_at)
        return action_intent_fingerprint(intent)

    @classmethod
    def _verify_prepared_dispatch(
        cls,
        dispatch: OperationDispatchContract,
        *,
        intent: ActionIntentContract,
    ) -> None:
        if not isinstance(dispatch, OperationDispatchContract):
            raise TypeError("operation dispatch contract required")
        expected_context = {
            "request_id": intent.origin_request_id,
            "session_id": intent.session_id,
            "mission_id": intent.mission_id,
        }
        cls._require_attributes(dispatch, **expected_context)
        operator_identity_ref = cls._dispatch_operator_identity_ref(dispatch)
        if operator_identity_ref != intent.operator_identity_ref:
            raise ValueError("prepared dispatch operator_identity_ref mismatch")
        optional_bindings = {
            "origin_request_id": intent.origin_request_id,
            "action_fingerprint": intent.action_fingerprint,
            "intent_fingerprint": action_intent_fingerprint(intent),
        }
        for field_name, expected in optional_bindings.items():
            actual = getattr(dispatch, field_name)
            if actual is not None and actual != expected:
                raise ValueError(f"prepared dispatch {field_name} mismatch")
        for field_name in ("receipt_id", "claim_id", "claimed_at"):
            if getattr(dispatch, field_name) is not None:
                raise ValueError(f"prepared dispatch {field_name} must be absent")
        if dispatch.artifact_destination is not None:
            raise ValueError("prepared dispatch caller artifact destination is not allowed")
        if (
            dispatch.autonomy_automatic_promotion_allowed is not False
            or dispatch.autonomy_core_mutation_allowed is not False
        ):
            raise ValueError("prepared dispatch autonomy authority is not allowed")
        if dispatch.autonomy_human_confirmation_required is not True:
            raise ValueError("prepared dispatch must require human confirmation")
        workflow_policy = dispatch.workflow_policy_decision
        if workflow_policy is not None:
            if workflow_policy.read_only is not True or any(
                getattr(workflow_policy, field_name) is not False
                for field_name in (
                    "autonomous_execution_allowed",
                    "automatic_promotion_allowed",
                    "core_mutation_allowed",
                )
            ):
                raise ValueError("prepared dispatch workflow policy has authority")
        workflow_transition = dispatch.workflow_lifecycle_transition
        if workflow_transition is not None:
            if (
                workflow_transition.read_only is not True
                or workflow_transition.immutable is not True
                or any(
                    getattr(workflow_transition, field_name) is not False
                    for field_name in (
                        "active_registry_write_allowed",
                        "runtime_execution_allowed",
                        "automatic_promotion_allowed",
                        "automatic_rollback_allowed",
                        "core_mutation_allowed",
                    )
                )
            ):
                raise ValueError("prepared dispatch workflow transition has authority")

    @staticmethod
    def _dispatch_operator_identity_ref(dispatch: OperationDispatchContract) -> str:
        resolved = dispatch.operator_identity_ref or dispatch.canonical_user_ref
        if not isinstance(resolved, str) or not resolved:
            raise ValueError("prepared dispatch operator identity is required")
        return resolved

    @classmethod
    def _verify_challenge(
        cls,
        challenge: ActionConfirmationChallengeContract,
        *,
        intent: ActionIntentContract,
        intent_fingerprint: str,
    ) -> str:
        require_valid_action_confirmation_challenge(challenge, intent=intent)
        cls._require_confirmation_shape(challenge)
        expected = {
            "intent_id": intent.intent_id,
            "intent_fingerprint": intent_fingerprint,
            "action_fingerprint": intent.action_fingerprint,
            "origin_request_id": intent.origin_request_id,
            "session_id": intent.session_id,
            "mission_id": intent.mission_id,
            "operator_identity_ref": intent.operator_identity_ref,
            "operation": intent.operation,
            "nonce": intent.nonce,
            "expires_at": intent.expires_at,
        }
        cls._require_attributes(challenge, **expected)
        cls._require_chronology(challenge.issued_at, challenge.expires_at)
        if cls._parse_timestamp(challenge.issued_at) < cls._parse_timestamp(intent.issued_at):
            raise ValueError("action confirmation challenge predates its intent")
        return action_confirmation_challenge_fingerprint(challenge)

    @classmethod
    def _verify_receipt(
        cls,
        receipt: HumanConfirmationReceiptContract,
        *,
        intent: ActionIntentContract,
        challenge: ActionConfirmationChallengeContract,
        verified_at: str | None,
    ) -> str:
        require_valid_human_confirmation_receipt(
            receipt,
            challenge=challenge,
            intent=intent,
            now=verified_at,
        )
        cls._require_confirmation_shape(receipt)
        expected = {
            "challenge_id": challenge.challenge_id,
            "challenge_fingerprint": action_confirmation_challenge_fingerprint(challenge),
            "intent_id": intent.intent_id,
            "intent_fingerprint": action_intent_fingerprint(intent),
            "action_fingerprint": intent.action_fingerprint,
            "origin_request_id": intent.origin_request_id,
            "session_id": intent.session_id,
            "mission_id": intent.mission_id,
            "operator_identity_ref": intent.operator_identity_ref,
            "operation": intent.operation,
            "expires_at": challenge.expires_at,
        }
        cls._require_attributes(receipt, **expected)
        confirmed_at = cls._parse_timestamp(receipt.confirmed_at)
        if confirmed_at < cls._parse_timestamp(challenge.issued_at):
            raise ValueError("human confirmation receipt predates its challenge")
        if confirmed_at >= cls._parse_timestamp(receipt.expires_at):
            raise ValueError("human confirmation receipt is expired")
        if verified_at is not None:
            cls._require_active(verified_at, receipt.expires_at)
        return human_confirmation_receipt_fingerprint(receipt)

    @classmethod
    def _verify_claim(
        cls,
        claim: ActionConfirmationClaimContract,
        *,
        context: ActionConfirmationContext,
        expected_action_fingerprint: str,
        expected_operation_id: str,
        expected_operator_identity_ref: str,
        verified_at: str | None,
    ) -> str:
        require_valid_action_confirmation_claim(
            claim,
            receipt=context.receipt,
            challenge=context.challenge,
            intent=context.intent,
            now=verified_at,
            expected_operation_id=expected_operation_id,
        )
        cls._require_confirmation_shape(claim)
        intent = context.intent
        receipt = context.receipt
        expected = {
            "receipt_id": receipt.receipt_id,
            "receipt_fingerprint": human_confirmation_receipt_fingerprint(receipt),
            "intent_id": intent.intent_id,
            "intent_fingerprint": action_intent_fingerprint(intent),
            "action_fingerprint": expected_action_fingerprint,
            "operation_id": expected_operation_id,
            "origin_request_id": intent.origin_request_id,
            "session_id": intent.session_id,
            "mission_id": intent.mission_id,
            "operator_identity_ref": expected_operator_identity_ref,
            "operation": intent.operation,
            "expires_at": receipt.expires_at,
        }
        cls._require_attributes(claim, **expected)
        if expected_action_fingerprint != intent.action_fingerprint:
            raise ValueError("action confirmation claim action fingerprint mismatch")
        if expected_operator_identity_ref != intent.operator_identity_ref:
            raise ValueError("action confirmation claim operator mismatch")
        claimed_at = cls._parse_timestamp(claim.claimed_at)
        if claimed_at < cls._parse_timestamp(receipt.confirmed_at):
            raise ValueError("action confirmation claim predates its receipt")
        if claimed_at >= cls._parse_timestamp(claim.expires_at):
            raise ValueError("action confirmation claim is expired")
        if verified_at is not None:
            cls._require_active(verified_at, claim.expires_at)
        return action_confirmation_claim_fingerprint(claim)

    @staticmethod
    def _require_confirmation_shape(contract: object) -> None:
        for field_name in ("single_use", "read_only", "immutable"):
            if getattr(contract, field_name, None) is not True:
                raise ValueError(f"action confirmation {field_name} must be true")
        for field_name in (
            "execution_authorized",
            "execution_allowed",
            "runtime_execution_allowed",
            "automatic_execution_allowed",
            "delegated_authority",
            "tool_dispatch_allowed",
            "runtime_activation_allowed",
            "promotion_authorized",
            "automatic_promotion_allowed",
            "core_mutation_allowed",
        ):
            if hasattr(contract, field_name) and getattr(contract, field_name) is not False:
                raise ValueError(f"action confirmation {field_name} must be false")

    @staticmethod
    def _require_attributes(contract: object, **expected: object) -> None:
        for field_name, expected_value in expected.items():
            if getattr(contract, field_name, None) != expected_value:
                raise ValueError(f"action confirmation {field_name} mismatch")

    @staticmethod
    def _require_columns(row: Row, **expected: object) -> None:
        for field_name, expected_value in expected.items():
            if row[field_name] != expected_value:
                raise ValueError(f"action confirmation stored {field_name} mismatch")

    @classmethod
    def _require_chronology(cls, issued_at: str, expires_at: str) -> None:
        if cls._parse_timestamp(expires_at) <= cls._parse_timestamp(issued_at):
            raise ValueError("action confirmation expiry must follow issuance")

    @classmethod
    def _require_active(cls, verified_at: str, expires_at: str) -> None:
        if cls._parse_timestamp(verified_at) >= cls._parse_timestamp(expires_at):
            raise ValueError("action confirmation evidence is expired")

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ValueError("action confirmation timestamp must be ISO-8601") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("action confirmation timestamp must be timezone-aware")
        return timestamp.astimezone(UTC)

    def _execution_now(self) -> str:
        value = self._trusted_execution_clock()
        if not isinstance(value, str):
            raise TypeError("trusted execution clock must return an ISO-8601 string")
        return self._parse_timestamp(value).isoformat()

    def _new_connection(self) -> Connection:
        connection = connect(
            self._connection_target,
            timeout=30.0,
            isolation_level=None,
            uri=self._connection_uri,
            check_same_thread=False,
        )
        connection.row_factory = Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @staticmethod
    def _begin_immediate(connection: Connection) -> None:
        connection.execute("BEGIN IMMEDIATE")

    def _initialize(self) -> None:
        with closing(self._new_connection()) as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS action_intents (
                    intent_id TEXT PRIMARY KEY,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    origin_request_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    mission_id TEXT,
                    operator_identity_ref TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    UNIQUE (intent_id, intent_fingerprint, action_fingerprint)
                );

                CREATE TABLE IF NOT EXISTS action_confirmation_prepared_dispatches (
                    intent_id TEXT PRIMARY KEY,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    origin_request_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    mission_id TEXT,
                    operator_identity_ref TEXT NOT NULL,
                    dispatch_fingerprint TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS action_confirmation_challenges (
                    challenge_id TEXT PRIMARY KEY,
                    challenge_fingerprint TEXT NOT NULL UNIQUE,
                    intent_id TEXT NOT NULL UNIQUE,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    origin_request_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    mission_id TEXT,
                    operator_identity_ref TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS human_confirmation_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    receipt_fingerprint TEXT NOT NULL UNIQUE,
                    challenge_id TEXT NOT NULL UNIQUE,
                    challenge_fingerprint TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    origin_request_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    mission_id TEXT,
                    operator_identity_ref TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    confirmed_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (challenge_id)
                        REFERENCES action_confirmation_challenges (challenge_id),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS action_confirmation_claims (
                    claim_id TEXT PRIMARY KEY,
                    claim_fingerprint TEXT NOT NULL UNIQUE,
                    receipt_id TEXT NOT NULL UNIQUE,
                    receipt_fingerprint TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE,
                    origin_request_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    mission_id TEXT,
                    operator_identity_ref TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (receipt_id)
                        REFERENCES human_confirmation_receipts (receipt_id),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS action_confirmation_presentations (
                    presentation_id TEXT PRIMARY KEY,
                    presentation_fingerprint TEXT NOT NULL UNIQUE,
                    claim_id TEXT NOT NULL UNIQUE,
                    claim_fingerprint TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE,
                    origin_request_id TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    intent_fingerprint TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    operator_identity_ref TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (claim_id)
                        REFERENCES action_confirmation_claims (claim_id),
                    FOREIGN KEY (receipt_id)
                        REFERENCES human_confirmation_receipts (receipt_id)
                );

                CREATE TABLE IF NOT EXISTS adapter_registry_epochs (
                    epoch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registry_id TEXT NOT NULL,
                    registry_version TEXT NOT NULL,
                    registry_fingerprint TEXT NOT NULL UNIQUE,
                    activated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    UNIQUE (registry_id, registry_version)
                );

                CREATE TABLE IF NOT EXISTS adapter_registry_descriptors (
                    epoch_id INTEGER NOT NULL,
                    registry_fingerprint TEXT NOT NULL,
                    descriptor_fingerprint TEXT NOT NULL,
                    adapter_id TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    action_kind TEXT NOT NULL,
                    allowed_operations TEXT NOT NULL,
                    allowed_resource_scopes TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    PRIMARY KEY (registry_fingerprint, descriptor_fingerprint),
                    UNIQUE (registry_fingerprint, adapter_id, adapter_version),
                    FOREIGN KEY (epoch_id)
                        REFERENCES adapter_registry_epochs (epoch_id),
                    FOREIGN KEY (registry_fingerprint)
                        REFERENCES adapter_registry_epochs (registry_fingerprint)
                );

                CREATE TABLE IF NOT EXISTS adapter_grants (
                    grant_id TEXT PRIMARY KEY,
                    grant_fingerprint TEXT NOT NULL UNIQUE,
                    intent_id TEXT NOT NULL UNIQUE,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    subject_ref TEXT NOT NULL,
                    adapter_id TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    action_kind TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    resource_scope TEXT NOT NULL,
                    resource_ref TEXT NOT NULL,
                    descriptor_fingerprint TEXT NOT NULL,
                    registry_fingerprint TEXT NOT NULL,
                    autonomy_policy_decision_fingerprint TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    nonce TEXT NOT NULL UNIQUE,
                    confirmation_required INTEGER NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    autonomy_policy_payload TEXT NOT NULL,
                    autonomy_policy_payload_sha256 TEXT NOT NULL,
                    UNIQUE (grant_id, grant_fingerprint),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        ),
                    FOREIGN KEY (registry_fingerprint, descriptor_fingerprint)
                        REFERENCES adapter_registry_descriptors (
                            registry_fingerprint, descriptor_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS adapter_grant_claims (
                    claim_id TEXT PRIMARY KEY,
                    claim_fingerprint TEXT NOT NULL UNIQUE,
                    grant_id TEXT NOT NULL UNIQUE,
                    grant_fingerprint TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE,
                    subject_ref TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    adapter_id TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    action_kind TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    resource_scope TEXT NOT NULL,
                    resource_ref TEXT NOT NULL,
                    confirmation_receipt_id TEXT UNIQUE,
                    confirmation_claim_id TEXT UNIQUE,
                    confirmation_claim_fingerprint TEXT,
                    claimed_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    CHECK (
                        (
                            confirmation_receipt_id IS NULL
                            AND confirmation_claim_id IS NULL
                            AND confirmation_claim_fingerprint IS NULL
                        ) OR (
                            confirmation_receipt_id IS NOT NULL
                            AND confirmation_claim_id IS NOT NULL
                            AND confirmation_claim_fingerprint IS NOT NULL
                        )
                    ),
                    FOREIGN KEY (grant_id, grant_fingerprint)
                        REFERENCES adapter_grants (grant_id, grant_fingerprint),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        ),
                    FOREIGN KEY (confirmation_receipt_id)
                        REFERENCES human_confirmation_receipts (receipt_id),
                    FOREIGN KEY (confirmation_claim_id)
                        REFERENCES action_confirmation_claims (claim_id)
                );

                CREATE TABLE IF NOT EXISTS adapter_execution_registry_epochs (
                    epoch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registry_id TEXT NOT NULL,
                    registry_version TEXT NOT NULL,
                    registry_fingerprint TEXT NOT NULL UNIQUE,
                    activated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    UNIQUE (registry_id, registry_version)
                );

                CREATE TABLE IF NOT EXISTS adapter_execution_registry_descriptors (
                    epoch_id INTEGER NOT NULL,
                    registry_fingerprint TEXT NOT NULL,
                    descriptor_fingerprint TEXT NOT NULL,
                    adapter_id TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    action_kind TEXT NOT NULL,
                    allowed_operations TEXT NOT NULL,
                    allowed_resource_scopes TEXT NOT NULL,
                    executor_ref TEXT NOT NULL,
                    execution_policy_version TEXT NOT NULL,
                    execution_backend_version TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    PRIMARY KEY (registry_fingerprint, descriptor_fingerprint),
                    UNIQUE (registry_fingerprint, adapter_id, adapter_version),
                    FOREIGN KEY (epoch_id)
                        REFERENCES adapter_execution_registry_epochs (epoch_id),
                    FOREIGN KEY (registry_fingerprint)
                        REFERENCES adapter_execution_registry_epochs (registry_fingerprint)
                );

                CREATE TABLE IF NOT EXISTS local_text_file_preflight_attestations (
                    attestation_id TEXT PRIMARY KEY,
                    attestation_fingerprint TEXT NOT NULL UNIQUE,
                    attestation_nonce TEXT NOT NULL UNIQUE,
                    trusted_boundary_ref TEXT NOT NULL,
                    source_preflight_grant_id TEXT NOT NULL UNIQUE,
                    source_preflight_grant_fingerprint TEXT NOT NULL,
                    preflight_fingerprint TEXT NOT NULL UNIQUE,
                    execution_request_fingerprint TEXT NOT NULL UNIQUE,
                    subject_ref TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    resource_scope TEXT NOT NULL,
                    resource_ref TEXT NOT NULL,
                    root_config_fingerprint TEXT NOT NULL,
                    filesystem_snapshot_fingerprint TEXT NOT NULL,
                    before_content_sha256 TEXT NOT NULL,
                    desired_content_sha256 TEXT NOT NULL,
                    rollback_fingerprint TEXT NOT NULL,
                    preflight_expires_at TEXT NOT NULL,
                    attested_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    request_payload TEXT NOT NULL,
                    request_payload_sha256 TEXT NOT NULL,
                    UNIQUE (attestation_id, attestation_fingerprint),
                    FOREIGN KEY (
                        source_preflight_grant_id,
                        source_preflight_grant_fingerprint
                    ) REFERENCES adapter_grants (grant_id, grant_fingerprint)
                );

                CREATE TABLE IF NOT EXISTS adapter_execution_grants (
                    grant_id TEXT PRIMARY KEY,
                    grant_fingerprint TEXT NOT NULL UNIQUE,
                    intent_id TEXT NOT NULL UNIQUE,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    subject_ref TEXT NOT NULL,
                    adapter_id TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    action_kind TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    resource_scope TEXT NOT NULL,
                    resource_ref TEXT NOT NULL,
                    source_preflight_grant_id TEXT NOT NULL UNIQUE,
                    source_preflight_grant_fingerprint TEXT NOT NULL,
                    preflight_attestation_id TEXT NOT NULL UNIQUE,
                    preflight_attestation_fingerprint TEXT NOT NULL,
                    preflight_fingerprint TEXT NOT NULL UNIQUE,
                    execution_request_fingerprint TEXT NOT NULL UNIQUE,
                    root_config_fingerprint TEXT NOT NULL,
                    before_content_sha256 TEXT NOT NULL,
                    desired_content_sha256 TEXT NOT NULL,
                    rollback_fingerprint TEXT NOT NULL,
                    descriptor_fingerprint TEXT NOT NULL,
                    registry_fingerprint TEXT NOT NULL,
                    autonomy_policy_decision_fingerprint TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    nonce TEXT NOT NULL UNIQUE,
                    confirmation_required INTEGER NOT NULL CHECK (confirmation_required = 1),
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    autonomy_policy_payload TEXT NOT NULL,
                    autonomy_policy_payload_sha256 TEXT NOT NULL,
                    UNIQUE (grant_id, grant_fingerprint),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        ),
                    FOREIGN KEY (
                        source_preflight_grant_id,
                        source_preflight_grant_fingerprint
                    ) REFERENCES adapter_grants (grant_id, grant_fingerprint),
                    FOREIGN KEY (
                        preflight_attestation_id,
                        preflight_attestation_fingerprint
                    ) REFERENCES local_text_file_preflight_attestations (
                        attestation_id, attestation_fingerprint
                    ),
                    FOREIGN KEY (registry_fingerprint, descriptor_fingerprint)
                        REFERENCES adapter_execution_registry_descriptors (
                            registry_fingerprint, descriptor_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS adapter_execution_grant_claims (
                    claim_id TEXT PRIMARY KEY,
                    claim_fingerprint TEXT NOT NULL UNIQUE,
                    grant_id TEXT NOT NULL UNIQUE,
                    grant_fingerprint TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE,
                    journal_reservation_fingerprint TEXT NOT NULL UNIQUE,
                    subject_ref TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    execution_request_fingerprint TEXT NOT NULL,
                    preflight_fingerprint TEXT NOT NULL,
                    confirmation_receipt_id TEXT NOT NULL UNIQUE,
                    confirmation_claim_id TEXT NOT NULL UNIQUE,
                    confirmation_claim_fingerprint TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (grant_id, grant_fingerprint)
                        REFERENCES adapter_execution_grants (grant_id, grant_fingerprint),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        ),
                    FOREIGN KEY (confirmation_receipt_id)
                        REFERENCES human_confirmation_receipts (receipt_id),
                    FOREIGN KEY (confirmation_claim_id)
                        REFERENCES action_confirmation_claims (claim_id)
                );

                CREATE TABLE IF NOT EXISTS local_text_file_rollback_registry_epochs (
                    epoch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registry_id TEXT NOT NULL,
                    registry_version TEXT NOT NULL,
                    registry_fingerprint TEXT NOT NULL UNIQUE,
                    activated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    UNIQUE (registry_id, registry_version)
                );

                CREATE TABLE IF NOT EXISTS local_text_file_rollback_registry_descriptors (
                    epoch_id INTEGER NOT NULL,
                    registry_fingerprint TEXT NOT NULL,
                    descriptor_fingerprint TEXT NOT NULL,
                    adapter_id TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    action_kind TEXT NOT NULL,
                    purpose TEXT NOT NULL CHECK (purpose = 'rollback'),
                    allowed_operations TEXT NOT NULL,
                    allowed_resource_scopes TEXT NOT NULL,
                    executor_ref TEXT NOT NULL,
                    rollback_policy_version TEXT NOT NULL,
                    rollback_backend_version TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    PRIMARY KEY (registry_fingerprint, descriptor_fingerprint),
                    UNIQUE (registry_fingerprint, adapter_id, adapter_version),
                    FOREIGN KEY (epoch_id)
                        REFERENCES local_text_file_rollback_registry_epochs (epoch_id),
                    FOREIGN KEY (registry_fingerprint)
                        REFERENCES local_text_file_rollback_registry_epochs (
                            registry_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS local_text_mutation_receipts (
                    receipt_fingerprint TEXT PRIMARY KEY,
                    mutation_operation_id TEXT NOT NULL UNIQUE,
                    execution_grant_id TEXT NOT NULL UNIQUE,
                    execution_claim_id TEXT NOT NULL UNIQUE,
                    applied_event_fingerprint TEXT NOT NULL UNIQUE,
                    resource_ref TEXT NOT NULL,
                    subject_ref TEXT NOT NULL,
                    preflight_fingerprint TEXT NOT NULL,
                    before_content_sha256 TEXT NOT NULL,
                    desired_content_sha256 TEXT NOT NULL,
                    root_config_fingerprint TEXT NOT NULL,
                    committed_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (execution_grant_id)
                        REFERENCES adapter_execution_grants (grant_id),
                    FOREIGN KEY (execution_claim_id)
                        REFERENCES adapter_execution_grant_claims (claim_id)
                );

                CREATE TABLE IF NOT EXISTS local_text_file_rollback_requests (
                    rollback_request_fingerprint TEXT PRIMARY KEY,
                    rollback_operation_id TEXT NOT NULL UNIQUE,
                    mutation_receipt_fingerprint TEXT NOT NULL UNIQUE,
                    requested_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (mutation_receipt_fingerprint)
                        REFERENCES local_text_mutation_receipts (receipt_fingerprint)
                );

                CREATE TABLE IF NOT EXISTS local_text_file_rollback_grants (
                    grant_id TEXT PRIMARY KEY,
                    grant_fingerprint TEXT NOT NULL UNIQUE,
                    intent_id TEXT NOT NULL UNIQUE,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    subject_ref TEXT NOT NULL,
                    rollback_operation_id TEXT NOT NULL UNIQUE,
                    mutation_operation_id TEXT NOT NULL UNIQUE,
                    mutation_receipt_fingerprint TEXT NOT NULL UNIQUE,
                    source_execution_grant_id TEXT NOT NULL UNIQUE,
                    source_execution_claim_id TEXT NOT NULL UNIQUE,
                    rollback_request_fingerprint TEXT NOT NULL UNIQUE,
                    resource_ref TEXT NOT NULL,
                    root_config_fingerprint TEXT NOT NULL,
                    expected_current_sha256 TEXT NOT NULL,
                    restored_content_sha256 TEXT NOT NULL,
                    rollback_plan_fingerprint TEXT NOT NULL,
                    descriptor_fingerprint TEXT NOT NULL,
                    registry_fingerprint TEXT NOT NULL,
                    autonomy_policy_decision_fingerprint TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    nonce TEXT NOT NULL UNIQUE,
                    confirmation_required INTEGER NOT NULL CHECK (confirmation_required = 1),
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    autonomy_policy_payload TEXT NOT NULL,
                    autonomy_policy_payload_sha256 TEXT NOT NULL,
                    UNIQUE (grant_id, grant_fingerprint),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        ),
                    FOREIGN KEY (mutation_receipt_fingerprint)
                        REFERENCES local_text_mutation_receipts (receipt_fingerprint),
                    FOREIGN KEY (rollback_request_fingerprint)
                        REFERENCES local_text_file_rollback_requests (
                            rollback_request_fingerprint
                        ),
                    FOREIGN KEY (source_execution_grant_id)
                        REFERENCES adapter_execution_grants (grant_id),
                    FOREIGN KEY (source_execution_claim_id)
                        REFERENCES adapter_execution_grant_claims (claim_id),
                    FOREIGN KEY (registry_fingerprint, descriptor_fingerprint)
                        REFERENCES local_text_file_rollback_registry_descriptors (
                            registry_fingerprint, descriptor_fingerprint
                        )
                );

                CREATE TABLE IF NOT EXISTS local_text_file_rollback_grant_claims (
                    claim_id TEXT PRIMARY KEY,
                    claim_fingerprint TEXT NOT NULL UNIQUE,
                    grant_id TEXT NOT NULL UNIQUE,
                    grant_fingerprint TEXT NOT NULL,
                    rollback_operation_id TEXT NOT NULL UNIQUE,
                    rollback_journal_reservation_fingerprint TEXT NOT NULL UNIQUE,
                    subject_ref TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    intent_fingerprint TEXT NOT NULL,
                    action_fingerprint TEXT NOT NULL,
                    rollback_request_fingerprint TEXT NOT NULL,
                    mutation_receipt_fingerprint TEXT NOT NULL UNIQUE,
                    confirmation_receipt_id TEXT NOT NULL UNIQUE,
                    confirmation_claim_id TEXT NOT NULL UNIQUE,
                    confirmation_claim_fingerprint TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (grant_id, grant_fingerprint)
                        REFERENCES local_text_file_rollback_grants (
                            grant_id, grant_fingerprint
                        ),
                    FOREIGN KEY (intent_id, intent_fingerprint, action_fingerprint)
                        REFERENCES action_intents (
                            intent_id, intent_fingerprint, action_fingerprint
                        ),
                    FOREIGN KEY (mutation_receipt_fingerprint)
                        REFERENCES local_text_mutation_receipts (receipt_fingerprint),
                    FOREIGN KEY (rollback_request_fingerprint)
                        REFERENCES local_text_file_rollback_requests (
                            rollback_request_fingerprint
                        ),
                    FOREIGN KEY (confirmation_receipt_id)
                        REFERENCES human_confirmation_receipts (receipt_id),
                    FOREIGN KEY (confirmation_claim_id)
                        REFERENCES action_confirmation_claims (claim_id)
                );

                CREATE TABLE IF NOT EXISTS local_text_rollback_receipts (
                    rollback_receipt_fingerprint TEXT PRIMARY KEY,
                    rollback_operation_id TEXT NOT NULL UNIQUE,
                    mutation_operation_id TEXT NOT NULL UNIQUE,
                    rollback_grant_id TEXT NOT NULL UNIQUE,
                    rollback_claim_id TEXT NOT NULL UNIQUE,
                    mutation_receipt_fingerprint TEXT NOT NULL UNIQUE,
                    resource_ref TEXT NOT NULL,
                    restored_content_sha256 TEXT NOT NULL,
                    rolled_back_at TEXT NOT NULL,
                    rolled_back_event_fingerprint TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (rollback_grant_id)
                        REFERENCES local_text_file_rollback_grants (grant_id),
                    FOREIGN KEY (rollback_claim_id)
                        REFERENCES local_text_file_rollback_grant_claims (claim_id),
                    FOREIGN KEY (mutation_receipt_fingerprint)
                        REFERENCES local_text_mutation_receipts (receipt_fingerprint)
                );

                CREATE INDEX IF NOT EXISTS action_intents_origin_idx
                    ON action_intents (origin_request_id, session_id, mission_id);
                CREATE INDEX IF NOT EXISTS action_confirmation_prepared_expiry_idx
                    ON action_confirmation_prepared_dispatches (
                        expires_at, intent_id
                    );
                CREATE INDEX IF NOT EXISTS action_confirmation_challenges_expiry_idx
                    ON action_confirmation_challenges (expires_at, challenge_id);
                CREATE INDEX IF NOT EXISTS human_confirmation_receipts_expiry_idx
                    ON human_confirmation_receipts (expires_at, receipt_id);
                CREATE INDEX IF NOT EXISTS action_confirmation_presentations_time_idx
                    ON action_confirmation_presentations (verified_at, presentation_id);
                CREATE INDEX IF NOT EXISTS adapter_registry_epochs_active_idx
                    ON adapter_registry_epochs (epoch_id DESC);
                CREATE INDEX IF NOT EXISTS adapter_registry_descriptors_lookup_idx
                    ON adapter_registry_descriptors (
                        registry_fingerprint, adapter_id, adapter_version
                    );
                CREATE INDEX IF NOT EXISTS adapter_grants_expiry_idx
                    ON adapter_grants (expires_at, grant_id);
                CREATE INDEX IF NOT EXISTS adapter_grant_claims_expiry_idx
                    ON adapter_grant_claims (expires_at, claim_id);
                CREATE INDEX IF NOT EXISTS adapter_execution_registry_active_idx
                    ON adapter_execution_registry_epochs (epoch_id DESC);
                CREATE INDEX IF NOT EXISTS adapter_execution_registry_lookup_idx
                    ON adapter_execution_registry_descriptors (
                        registry_fingerprint, adapter_id, adapter_version
                    );
                CREATE INDEX IF NOT EXISTS local_text_preflight_attestation_expiry_idx
                    ON local_text_file_preflight_attestations (
                        preflight_expires_at, attestation_id
                    );
                CREATE INDEX IF NOT EXISTS adapter_execution_grants_expiry_idx
                    ON adapter_execution_grants (expires_at, grant_id);
                CREATE INDEX IF NOT EXISTS adapter_execution_claims_recovery_idx
                    ON adapter_execution_grant_claims (
                        operation_id, journal_reservation_fingerprint
                    );
                CREATE INDEX IF NOT EXISTS local_text_rollback_registry_active_idx
                    ON local_text_file_rollback_registry_epochs (epoch_id DESC);
                CREATE INDEX IF NOT EXISTS local_text_mutation_receipts_time_idx
                    ON local_text_mutation_receipts (committed_at, receipt_fingerprint);
                CREATE INDEX IF NOT EXISTS local_text_rollback_requests_expiry_idx
                    ON local_text_file_rollback_requests (
                        expires_at, rollback_request_fingerprint
                    );
                CREATE INDEX IF NOT EXISTS local_text_rollback_grants_expiry_idx
                    ON local_text_file_rollback_grants (expires_at, grant_id);
                CREATE INDEX IF NOT EXISTS local_text_rollback_claims_recovery_idx
                    ON local_text_file_rollback_grant_claims (
                        rollback_operation_id,
                        rollback_journal_reservation_fingerprint
                    );

                CREATE TRIGGER IF NOT EXISTS action_intents_no_update
                BEFORE UPDATE ON action_intents
                BEGIN
                    SELECT RAISE(ABORT, 'action_intents is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS action_intents_no_delete
                BEFORE DELETE ON action_intents
                BEGIN
                    SELECT RAISE(ABORT, 'action_intents is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS action_confirmation_prepared_no_update
                BEFORE UPDATE ON action_confirmation_prepared_dispatches
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'action_confirmation_prepared_dispatches is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS action_confirmation_prepared_no_delete
                BEFORE DELETE ON action_confirmation_prepared_dispatches
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'action_confirmation_prepared_dispatches is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS action_confirmation_challenges_no_update
                BEFORE UPDATE ON action_confirmation_challenges
                BEGIN
                    SELECT RAISE(ABORT, 'action_confirmation_challenges is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS action_confirmation_challenges_no_delete
                BEFORE DELETE ON action_confirmation_challenges
                BEGIN
                    SELECT RAISE(ABORT, 'action_confirmation_challenges is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS human_confirmation_receipts_no_update
                BEFORE UPDATE ON human_confirmation_receipts
                BEGIN
                    SELECT RAISE(ABORT, 'human_confirmation_receipts is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS human_confirmation_receipts_no_delete
                BEFORE DELETE ON human_confirmation_receipts
                BEGIN
                    SELECT RAISE(ABORT, 'human_confirmation_receipts is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS action_confirmation_claims_no_update
                BEFORE UPDATE ON action_confirmation_claims
                BEGIN
                    SELECT RAISE(ABORT, 'action_confirmation_claims is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS action_confirmation_claims_no_delete
                BEFORE DELETE ON action_confirmation_claims
                BEGIN
                    SELECT RAISE(ABORT, 'action_confirmation_claims is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS action_confirmation_presentations_no_update
                BEFORE UPDATE ON action_confirmation_presentations
                BEGIN
                    SELECT RAISE(ABORT, 'action_confirmation_presentations is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS action_confirmation_presentations_no_delete
                BEFORE DELETE ON action_confirmation_presentations
                BEGIN
                    SELECT RAISE(ABORT, 'action_confirmation_presentations is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS adapter_registry_epochs_no_update
                BEFORE UPDATE ON adapter_registry_epochs
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_registry_epochs is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_registry_epochs_no_delete
                BEFORE DELETE ON adapter_registry_epochs
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_registry_epochs is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS adapter_registry_descriptors_no_update
                BEFORE UPDATE ON adapter_registry_descriptors
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_registry_descriptors is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_registry_descriptors_no_delete
                BEFORE DELETE ON adapter_registry_descriptors
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_registry_descriptors is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS adapter_grants_no_update
                BEFORE UPDATE ON adapter_grants
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_grants is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_grants_no_delete
                BEFORE DELETE ON adapter_grants
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_grants is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS adapter_grant_claims_no_update
                BEFORE UPDATE ON adapter_grant_claims
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_grant_claims is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_grant_claims_no_delete
                BEFORE DELETE ON adapter_grant_claims
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_grant_claims is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS adapter_execution_registry_no_update
                BEFORE UPDATE ON adapter_execution_registry_epochs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_execution_registry_epochs is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_execution_registry_no_delete
                BEFORE DELETE ON adapter_execution_registry_epochs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_execution_registry_epochs is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_execution_descriptors_no_update
                BEFORE UPDATE ON adapter_execution_registry_descriptors
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_execution_registry_descriptors is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_execution_descriptors_no_delete
                BEFORE DELETE ON adapter_execution_registry_descriptors
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_execution_registry_descriptors is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_preflight_attestations_no_update
                BEFORE UPDATE ON local_text_file_preflight_attestations
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_preflight_attestations is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_preflight_attestations_no_delete
                BEFORE DELETE ON local_text_file_preflight_attestations
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_preflight_attestations is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_execution_grants_no_update
                BEFORE UPDATE ON adapter_execution_grants
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_execution_grants is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_execution_grants_no_delete
                BEFORE DELETE ON adapter_execution_grants
                BEGIN
                    SELECT RAISE(ABORT, 'adapter_execution_grants is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_execution_claims_no_update
                BEFORE UPDATE ON adapter_execution_grant_claims
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_execution_grant_claims is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS adapter_execution_claims_no_delete
                BEFORE DELETE ON adapter_execution_grant_claims
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'adapter_execution_grant_claims is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS local_text_rollback_registry_no_update
                BEFORE UPDATE ON local_text_file_rollback_registry_epochs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_registry_epochs is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_registry_no_delete
                BEFORE DELETE ON local_text_file_rollback_registry_epochs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_registry_epochs is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_descriptors_no_update
                BEFORE UPDATE ON local_text_file_rollback_registry_descriptors
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_registry_descriptors is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_descriptors_no_delete
                BEFORE DELETE ON local_text_file_rollback_registry_descriptors
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_registry_descriptors is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_mutation_receipts_no_update
                BEFORE UPDATE ON local_text_mutation_receipts
                BEGIN
                    SELECT RAISE(ABORT, 'local_text_mutation_receipts is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_mutation_receipts_no_delete
                BEFORE DELETE ON local_text_mutation_receipts
                BEGIN
                    SELECT RAISE(ABORT, 'local_text_mutation_receipts is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_requests_no_update
                BEFORE UPDATE ON local_text_file_rollback_requests
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_requests is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_requests_no_delete
                BEFORE DELETE ON local_text_file_rollback_requests
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_requests is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_grants_no_update
                BEFORE UPDATE ON local_text_file_rollback_grants
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_grants is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_grants_no_delete
                BEFORE DELETE ON local_text_file_rollback_grants
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_grants is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_claims_no_update
                BEFORE UPDATE ON local_text_file_rollback_grant_claims
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_grant_claims is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_claims_no_delete
                BEFORE DELETE ON local_text_file_rollback_grant_claims
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'local_text_file_rollback_grant_claims is append-only'
                    );
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_receipts_no_update
                BEFORE UPDATE ON local_text_rollback_receipts
                BEGIN
                    SELECT RAISE(ABORT, 'local_text_rollback_receipts is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS local_text_rollback_receipts_no_delete
                BEFORE DELETE ON local_text_rollback_receipts
                BEGIN
                    SELECT RAISE(ABORT, 'local_text_rollback_receipts is append-only');
                END;
                """
            )
