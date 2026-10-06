"""Explicit operator boundary for MB-214/217 physical text artifact sagas.

Preparation never confirms or dispatches. Sensitive preflight previews stay
ephemeral; operator-supplied input and metadata are stored in a private store.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Callable
from uuid import uuid4

from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)
from operational_service.adapters.local_text_transaction import (
    LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
    LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
    LocalTextExecutionGrantBinding,
    LocalTextMutationRequest,
    LocalTextRollbackRequest,
)

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.artifact_physical_saga import (
    require_valid_artifact_physical_apply_plan,
    require_valid_artifact_physical_rollback_plan,
    require_valid_local_text_resource_ref,
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
    LocalTextFilePreflightRequestContract,
)
from shared.events import InternalEventEnvelope
from shared.local_text_rollback_permissions import LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR
from shared.types import MissionStatus, RiskLevel


def _time(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("physical_console_clock_invalid")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _decision(confirm: bool):
    policy = AUTONOMY_LEVEL_POLICIES["supervised_external_action"]
    return evaluate_autonomy_action(
        requested_autonomy_level="supervised_external_action",
        max_autonomy_level="supervised_external_action",
        effective_autonomy_level="supervised_external_action",
        autonomy_ladder_status="within_limit",
        action_kind="execute_external_action" if confirm else "prepare_external_action",
        selected_capability_mode="core_with_supervised_external_operation",
        max_capability_mode="core_with_supervised_external_operation",
        allowed_runtime_actions=policy["allowed_runtime_actions"],
        blocked_runtime_actions=policy["blocked_runtime_actions"],
        human_confirmation_required=confirm,
        human_confirmation_mode="explicit_confirmation_required" if confirm else "not_required",
        confirmation_evidence_state="absent",
    )


def _canonical_binding(plan: dict) -> str:
    # Pin canonical intent fields in Governance's immutable origin request ID.
    # File permissions alone are not an integrity proof of this local cache.
    fields = (
        "purpose",
        "mission_id",
        "owner_mission_id",
        "objective_ref",
        "work_item_ref",
        "lineage_root_ref",
        "expected_lineage_revision",
        "resource_ref",
        "root_alias",
        "artifact_ref",
        "artifact_version",
        "supersedes_artifact_ref",
        "transition",
        "active_artifact_ref",
        "active_artifact_version",
        "restored_artifact_ref",
        "restored_artifact_version",
        "mutation_operation_id",
        "source_apply_saga_id",
        "rollback_mode",
        "canonical_effect_expected",
        "mutation_receipt_fingerprint",
    )
    data = {name: plan.get(name) for name in fields}
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class _RequestStore:
    """Small protected request store, not a canonical ledger or authority issuer.

    Files are pinned through an owned 0700 directory descriptor, regular,
    single-link and 0600. Windows durable storage is intentionally unavailable.
    """

    def __init__(self, runtime_dir: Path | None):
        self._memory = {}
        self._fd = None
        if runtime_dir is None:
            return
        if sys.platform != "linux" or not hasattr(os, "O_NOFOLLOW"):
            raise ValueError("physical_console_private_store_unavailable")
        path = Path(runtime_dir).absolute()
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError("physical_console_store_symlink")
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        observed = os.fstat(fd)
        if observed.st_uid != os.getuid() or stat.S_IMODE(observed.st_mode) != 0o700:
            os.close(fd)
            raise ValueError("physical_console_store_permissions")
        self._fd = fd

    @property
    def durable(self) -> bool:
        return self._fd is not None

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def _require_private_directory(self) -> None:
        if self._fd is not None:
            observed = os.fstat(self._fd)
            if observed.st_uid != os.getuid() or stat.S_IMODE(observed.st_mode) != 0o700:
                raise ValueError("physical_console_store_permissions")

    @staticmethod
    def _name(request_id: str) -> str:
        if not isinstance(request_id, str) or not re.fullmatch(r"[0-9a-f]{32}", request_id):
            raise ValueError("physical_console_request_id_invalid")
        return f"{request_id}.json"

    def save(self, request_id: str, record: dict, *, replace: bool = False) -> None:
        self._require_private_directory()
        name = self._name(request_id)
        payload = json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True).encode()
        if len(payload) > 2_097_152:
            raise ValueError("physical_console_request_limit")
        if self._fd is None:
            if not replace and request_id in self._memory:
                raise ValueError("physical_console_request_exists")
            self._memory[request_id] = payload
            return
        if replace:
            self.load(request_id)  # Validate an existing destination before replacing it.
        # Never publish a partial initial record. A no-overwrite hard-link
        # install preserves create semantics after the staged file is fsynced.
        temporary = f".{uuid4().hex}.tmp"
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=self._fd,
        )
        try:
            try:
                observed = os.fstat(fd)
                if stat.S_IMODE(observed.st_mode) != 0o600:
                    raise ValueError("physical_console_store_permissions")
                with os.fdopen(fd, "wb", closefd=False) as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(fd)
            finally:
                os.close(fd)
            self._require_private_directory()
            if replace:
                self.load(request_id)
                os.replace(temporary, name, src_dir_fd=self._fd, dst_dir_fd=self._fd)
            else:
                os.link(
                    temporary, name, src_dir_fd=self._fd, dst_dir_fd=self._fd,
                    follow_symlinks=False,
                )
                os.unlink(temporary, dir_fd=self._fd)
            os.fsync(self._fd)
        finally:
            # Exceptions must not strand the staged sensitive operator input.
            # Process termination may still leave a private orphan; never sweep
            # arbitrary files automatically or claim secure RAM/disk erasure.
            try:
                os.unlink(temporary, dir_fd=self._fd)
            except FileNotFoundError:
                pass

    def load(self, request_id: str) -> dict:
        self._require_private_directory()
        name = self._name(request_id)
        if self._fd is None:
            try:
                payload = self._memory[request_id]
            except KeyError:
                raise KeyError("physical_console_request_unknown") from None
        else:
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self._fd)
            except OSError:
                raise ValueError("physical_console_request_unavailable") from None
            try:
                observed = os.fstat(fd)
                if (
                    not stat.S_ISREG(observed.st_mode)
                    or observed.st_nlink != 1
                    or observed.st_uid != os.getuid()
                    or stat.S_IMODE(observed.st_mode) != 0o600
                    or observed.st_size > 2_097_152
                ):
                    raise ValueError("physical_console_store_permissions")
                with os.fdopen(fd, "rb", closefd=False) as handle:
                    payload = handle.read(2_097_153)
            finally:
                os.close(fd)
        try:
            record = json.loads(payload)
        except (ValueError, UnicodeError):
            raise ValueError("physical_console_request_corrupt") from None
        if not isinstance(record, dict) or record.get("request_id") != request_id:
            raise ValueError("physical_console_request_corrupt")
        return record


class PhysicalOperationsConsole:
    """Human-invoked prepare/inspect/confirm/execute with exact canonical binding.

    The builder supplies opt-in roots, registries, identity and real services.
    A None runtime_dir is explicitly ephemeral, suitable for prepare-only tests.
    """

    def __init__(
        self,
        orchestrator,
        operator_identity_ref: str,
        canonical_user_ref: str,
        *,
        runtime_dir: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        for value in (operator_identity_ref, canonical_user_ref):
            if not isinstance(value, str) or not value or len(value) > 512:
                raise ValueError("physical_console_identity_required")
        self.orchestrator = orchestrator
        self.operator_identity_ref = operator_identity_ref
        self.canonical_user_ref = canonical_user_ref
        self._store = _RequestStore(runtime_dir)
        self._clock = clock or (lambda: datetime.now(UTC))

    def close(self) -> None:
        self._store.close()

    def _now(self) -> datetime:
        try:
            value = self._clock()
            _time(value)
        except Exception:
            raise ValueError("physical_console_clock_invalid") from None
        return value.astimezone(UTC)

    def _mission(self, mission_id: str, work_item_ref: str, session_id: str):
        mission = self.orchestrator.memory_service.get_mission_state(mission_id)
        if mission is None:
            raise ValueError("physical_console_mission_unknown")
        if mission.mission_status != MissionStatus.ACTIVE:
            raise ValueError("physical_console_mission_not_active")
        owner = mission.owner_context
        if owner is not None and owner not in {
            self.operator_identity_ref,
            self.canonical_user_ref,
        }:
            raise ValueError("physical_console_owner_mismatch")
        item = next(
            (item for item in mission.work_items if item.work_item_ref == work_item_ref), None
        )
        if (
            item is None
            or str(item.mission_id) != str(mission.mission_id)
            or item.work_item_status != "active"
            or item.blocking_state != "ready"
        ):
            raise ValueError("physical_console_work_item_mismatch")
        return mission

    def _intent(
        self,
        request_id: str,
        *,
        mission_id: str,
        session_id: str,
        operation: str,
        resource_ref: str,
        content_digest: str,
        precondition_digest: str,
        handler_id: str,
        handler_version: str,
        ttl: int = 90,
        purpose: str = "execute",
        canonical_binding: dict | None = None,
    ):
        now = self._now()
        stamp = (
            (lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ")) if purpose == "prepare" else _time
        )
        return build_action_intent(
            intent_id=f"intent://physical-console/{request_id}/{purpose}",
            origin_request_id=(
                f"request://physical-console/{request_id}"
                + (f"/{_canonical_binding(canonical_binding)}" if canonical_binding else "")
            ),
            session_id=session_id,
            mission_id=mission_id,
            operator_identity_ref=self.operator_identity_ref,
            handler_id=handler_id,
            handler_version=handler_version,
            operation=operation,
            target_ref=resource_ref,
            content_digest=content_digest,
            precondition_digest=precondition_digest,
            risk_level=RiskLevel.MODERATE,
            policy_version=AUTONOMY_ACTION_POLICY_VERSION,
            nonce=uuid4().hex,
            issued_at=stamp(now),
            expires_at=stamp(now + timedelta(seconds=ttl)),
            now=now,
        )

    def _emit(self, event_name: str, record: dict) -> None:
        self.orchestrator.observability_service.ingest_events(
            [
                InternalEventEnvelope(
                    event_id=f"event://physical-console/{uuid4().hex}",
                    event_name=event_name,
                    timestamp=_time(self._now()),
                    source_service="jarvis-console",
                    payload={
                        "request_id": record["request_id"],
                        "purpose": record["purpose"],
                        "action_fingerprint": record["action_fingerprint"],
                        "contains_content": False,
                    },
                    correlation_id=record["request_id"],
                    tags=["physical-console", "content-free"],
                )
            ]
        )

    def prepare(
        self,
        *,
        mission_id: str,
        work_item_ref: str,
        artifact_ref: str,
        resource_ref: str,
        desired_text: str,
        session_id: str,
        operation: str = "create_text",
        expected_current_sha256: str | None = None,
        supersedes_artifact_ref: str | None = None,
    ) -> dict:
        mission = self._mission(mission_id, work_item_ref, session_id)
        if operation not in {"create_text", "replace_text"}:
            raise ValueError("physical_console_operation_invalid")
        if not isinstance(desired_text, str) or len(desired_text.encode("utf-8")) > 262_144:
            raise ValueError("physical_console_content_limit")
        if (
            not isinstance(artifact_ref, str)
            or re.fullmatch(r"artifact://[A-Za-z0-9][A-Za-z0-9_./-]{0,479}", artifact_ref) is None
        ):
            raise ValueError("physical_console_artifact_ref_invalid")
        try:
            root_alias = resource_ref.removeprefix("text:").split("/", 1)[0]
            require_valid_local_text_resource_ref(resource_ref, root_alias)
        except (TypeError, ValueError, AttributeError):
            raise ValueError("physical_console_resource_invalid") from None
        memory = self.orchestrator.memory_service
        predecessor = None
        lineage = None
        if supersedes_artifact_ref is not None:
            predecessor = memory.get_artifact_physical_version(supersedes_artifact_ref)
            if predecessor is None or str(predecessor.owner_mission_id) != mission_id:
                raise ValueError("physical_console_predecessor_invalid")
            lineage = memory.get_artifact_physical_lineage(mission_id, predecessor.lineage_root_ref)
            if (
                lineage is None
                or lineage.active_artifact_ref != supersedes_artifact_ref
                or predecessor.resource_ref != resource_ref
                or predecessor.work_item_ref != work_item_ref
            ):
                raise ValueError("physical_console_lineage_mismatch")
        elif operation == "replace_text":
            raise ValueError("physical_console_replace_requires_canonical_predecessor")
        if memory.get_artifact_physical_version(artifact_ref) is not None:
            raise ValueError("physical_console_artifact_already_bound")
        request_id = uuid4().hex
        operational = self.orchestrator.operational_service
        governance = self.orchestrator.governance_service
        root_fingerprint = operational.local_text_file_root_config_fingerprint()
        adapter_request = AdapterActionRequestContract(
            adapter_id="local_text_file",
            adapter_version="1.0.0",
            action_kind="prepare_external_action",
            operation=operation,
            resource_scope="configured_text_root",
            resource_ref=resource_ref,
        )
        prepare_intent = self._intent(
            request_id,
            mission_id=mission_id,
            session_id=session_id,
            operation=operation,
            resource_ref=resource_ref,
            content_digest=sha256(desired_text.encode()).hexdigest(),
            precondition_digest=root_fingerprint,
            handler_id="adapter://local_text_file",
            handler_version="1.0.0",
            ttl=600,
            purpose="prepare",
        )
        registry, descriptor = governance.resolve_active_adapter_descriptor(adapter_request)
        grant = governance.issue_adapter_grant(
            prepare_intent,
            adapter_request,
            _decision(False),
            expected_registry_fingerprint=registry.registry_fingerprint,
            expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        )
        now = self._now()
        preparation = LocalTextFilePreflightRequestContract(
            grant_id=grant.grant_id,
            grant_fingerprint=grant.grant_fingerprint,
            action_fingerprint=prepare_intent.action_fingerprint,
            intent_fingerprint=action_intent_fingerprint(prepare_intent),
            descriptor_fingerprint=grant.descriptor_fingerprint,
            registry_fingerprint=grant.registry_fingerprint,
            subject_ref=self.operator_identity_ref,
            adapter_request=adapter_request,
            desired_text=desired_text,
            expected_root_config_fingerprint=root_fingerprint,
            preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
            diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
            diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
            prepared_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            expires_at=(now + timedelta(seconds=300)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            authorization_expires_at=grant.expires_at,
            expected_current_sha256=expected_current_sha256,
        )
        preflight, _attestation, execution_request = (
            operational.preflight_and_attest_local_text_file(
                preparation,
                now=now,
            )
        )
        execution_intent = self._intent(
            request_id,
            mission_id=mission_id,
            session_id=session_id,
            operation=operation,
            resource_ref=resource_ref,
            content_digest=execution_request.desired_content_sha256,
            precondition_digest=execution_request.execution_request_fingerprint,
            handler_id="adapter-executor://local_text_file",
            handler_version="2.0.0",
            canonical_binding={
                "purpose": "apply",
                "mission_id": mission.mission_id,
                "owner_mission_id": mission.mission_id,
                "objective_ref": mission.objective_ref,
                "work_item_ref": work_item_ref,
                "lineage_root_ref": predecessor.lineage_root_ref if predecessor else artifact_ref,
                "expected_lineage_revision": lineage.revision if lineage else 0,
                "resource_ref": resource_ref,
                "root_alias": root_alias,
                "artifact_ref": artifact_ref,
                "artifact_version": predecessor.artifact_version + 1 if predecessor else 1,
                "supersedes_artifact_ref": supersedes_artifact_ref,
                "transition": "replace" if predecessor else "register",
            },
        )
        registry, descriptor = governance.resolve_active_adapter_execution_descriptor(
            execution_request
        )
        execution_grant = governance.issue_adapter_execution_grant(
            execution_intent,
            execution_request,
            _decision(True),
            expected_registry_fingerprint=registry.registry_fingerprint,
            expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        )
        challenge = governance.issue_action_confirmation_challenge(execution_intent)
        plan = seal_artifact_physical_apply_plan(
            ArtifactPhysicalApplyPlanContract(
                saga_id=f"saga://physical-console/{request_id}",
                mission_id=mission.mission_id,
                artifact_ref=artifact_ref,
                artifact_version=predecessor.artifact_version + 1 if predecessor else 1,
                owner_mission_id=mission.mission_id,
                objective_ref=mission.objective_ref,
                work_item_ref=work_item_ref,
                lineage_root_ref=predecessor.lineage_root_ref if predecessor else artifact_ref,
                supersedes_artifact_ref=supersedes_artifact_ref,
                transition="replace" if predecessor else "register",
                physical_operation_id=f"operation://physical-console/{request_id}",
                resource_ref=resource_ref,
                root_alias=root_alias,
                preflight_fingerprint=preflight.preflight_fingerprint,
                root_config_fingerprint=preflight.root_config_fingerprint,
                preflight_policy_version=preflight.preflight_policy_version,
                transaction_policy_version=LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
                transaction_backend_version=LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
                adapter_backend_version=preflight.adapter_backend_version,
                before_content_sha256=preflight.before_content_sha256,
                desired_content_sha256=preflight.desired_content_sha256,
                rollback_plan_ref=preflight.rollback_plan.rollback_fingerprint,
                expected_lineage_revision=lineage.revision if lineage else 0,
                created_at=execution_intent.issued_at,
                plan_fingerprint="0" * 64,
            )
        )
        require_valid_artifact_physical_apply_plan(plan)
        record = self._record(request_id, "apply", challenge, execution_grant, plan)
        # Persist operator input, never serialize the ephemeral preflight contract.
        # Authority and preparation metadata is loaded from Governance on reuse.
        record["operator_input"] = {"desired_text": desired_text}
        record["operation"] = operation
        self._store.save(request_id, record)
        self._emit("action_confirmation_challenged", record)
        return {
            **self._metadata(record),
            "preview": preflight.unified_diff,
            "preview_sensitive": True,
            "before_sha256": preflight.before_content_sha256,
            "desired_sha256": preflight.desired_content_sha256,
        }

    def _record(self, request_id, purpose, challenge, grant, plan):
        return {
            "schema_version": "physical-console-v1",
            "request_id": request_id,
            "purpose": purpose,
            "operator_identity_ref": self.operator_identity_ref,
            "canonical_user_ref": self.canonical_user_ref,
            "challenge_id": challenge.challenge_id,
            "action_fingerprint": challenge.action_fingerprint,
            "expires_at": challenge.expires_at,
            "execution_grant_id": grant.grant_id,
            "plan": asdict(plan),
            "confirmation_receipt_id": None,
        }

    def _load(self, request_id: str) -> tuple[dict, object, object]:
        try:
            return self._load_record(request_id)
        except ValueError as exc:
            if str(exc).startswith("physical_console_"):
                raise
            raise ValueError("physical_console_request_corrupt") from None
        except (KeyError, TypeError, AttributeError, UnicodeError, RecursionError):
            raise ValueError("physical_console_request_corrupt") from None

    def _load_record(self, request_id: str) -> tuple[dict, object, object]:
        record = self._store.load(request_id)
        if (
            record.get("schema_version") != "physical-console-v1"
            or record.get("operator_identity_ref") != self.operator_identity_ref
            or record.get("canonical_user_ref") != self.canonical_user_ref
        ):
            raise ValueError("physical_console_identity_mismatch")
        governance = self.orchestrator.governance_service
        if record.get("purpose") == "apply":
            plan = ArtifactPhysicalApplyPlanContract(**record["plan"])
            require_valid_artifact_physical_apply_plan(plan)
            context = governance.load_adapter_execution_grant_context(record["execution_grant_id"])
            if context.execution_request.preflight_fingerprint != plan.preflight_fingerprint:
                raise ValueError("physical_console_preflight_binding_mismatch")
            request = context.execution_request
            if (
                request.before_content_sha256 != plan.before_content_sha256
                or request.desired_content_sha256 != plan.desired_content_sha256
                or request.root_config_fingerprint != plan.root_config_fingerprint
                or request.rollback_fingerprint != plan.rollback_plan_ref
                or request.preflight_policy_version != plan.preflight_policy_version
                or request.preflight_backend_version != plan.adapter_backend_version
                or record.get("operation") != request.operation
                or plan.transaction_policy_version != LOCAL_TEXT_TRANSACTION_POLICY_VERSION
                or plan.transaction_backend_version != LOCAL_TEXT_TRANSACTION_BACKEND_VERSION
            ):
                raise ValueError("physical_console_preflight_binding_mismatch")
            desired = record.get("operator_input", {}).get("desired_text")
            if (
                not isinstance(desired, str)
                or len(desired.encode("utf-8")) > 262_144
                or sha256(desired.encode("utf-8")).hexdigest() != request.desired_content_sha256
            ):
                raise ValueError("physical_console_input_changed")
        elif record.get("purpose") == "rollback":
            plan = ArtifactPhysicalRollbackPlanContract(**record["plan"])
            require_valid_artifact_physical_rollback_plan(plan)
            context = governance.load_local_text_file_rollback_grant_context(
                record["execution_grant_id"]
            )
            if (
                context.rollback_request.mutation_receipt_fingerprint
                != plan.mutation_receipt_fingerprint
            ):
                raise ValueError("physical_console_rollback_binding_mismatch")
            request = context.rollback_request
            if (
                request.mutation_operation_id != plan.mutation_operation_id
                or request.expected_current_sha256 != plan.expected_current_sha256
                or request.restored_content_sha256 != plan.restored_content_sha256
            ):
                raise ValueError("physical_console_rollback_binding_mismatch")
        else:
            raise ValueError("physical_console_purpose_invalid")
        if (
            context.intent.operator_identity_ref != self.operator_identity_ref
            or context.intent.action_fingerprint != record["action_fingerprint"]
            or context.intent.origin_request_id
            != (f"request://physical-console/{request_id}/{_canonical_binding(record['plan'])}")
            or str(context.intent.mission_id) != str(plan.mission_id)
            or plan.physical_operation_id != f"operation://physical-console/{request_id}"
            or plan.saga_id != f"saga://physical-console/{request_id}"
            or context.intent.target_ref != plan.resource_ref
            or record["expires_at"] != context.intent.expires_at
            or plan.created_at != context.intent.issued_at
        ):
            raise ValueError("physical_console_exact_binding_mismatch")
        intent, challenge = governance.action_confirmation_repository.load_intent_and_challenge(
            record["challenge_id"],
            verified_at=context.intent.issued_at,
        )
        if intent != context.intent or challenge.action_fingerprint != record["action_fingerprint"]:
            raise ValueError("physical_console_challenge_mismatch")
        if record["confirmation_receipt_id"] is not None:
            confirmation = governance.load_action_confirmation_context(
                record["confirmation_receipt_id"]
            )
            if (
                confirmation.intent != intent
                or confirmation.challenge != challenge
                or confirmation.receipt.receipt_id != record["confirmation_receipt_id"]
                or confirmation.receipt.challenge_id != record["challenge_id"]
                or confirmation.receipt.operator_identity_ref != self.operator_identity_ref
                or confirmation.receipt.action_fingerprint != record["action_fingerprint"]
            ):
                raise ValueError("physical_console_receipt_mismatch")
        else:
            # Governance is authoritative if the process crashed after its
            # receipt commit but before updating this non-authoritative cache.
            # Only reconcile an existing exact receipt: never implicitly confirm,
            # renew validity, consume a claim, or issue another receipt.
            confirmation = governance.load_action_confirmation_context_for_challenge(
                record["challenge_id"]
            )
            if confirmation is not None:
                if (
                    confirmation.intent != intent
                    or confirmation.challenge != challenge
                    or confirmation.receipt.challenge_id != record["challenge_id"]
                    or confirmation.receipt.operator_identity_ref != self.operator_identity_ref
                    or confirmation.receipt.action_fingerprint != record["action_fingerprint"]
                ):
                    raise ValueError("physical_console_receipt_mismatch")
                record["confirmation_receipt_id"] = confirmation.receipt.receipt_id
                self._store.save(request_id, record, replace=True)
        return record, plan, context

    def _metadata(self, record: dict) -> dict:
        plan = record["plan"]
        return {
            "request_id": record["request_id"],
            "purpose": record["purpose"],
            "challenge_id": record["challenge_id"],
            "action_fingerprint": record["action_fingerprint"],
            "confirmation_receipt_id": record["confirmation_receipt_id"],
            "expires_at": record["expires_at"],
            "risk_level": "moderate",
            "root_alias": plan["root_alias"],
            "relative_path": plan["resource_ref"].split("/", 1)[1],
            "artifact_ref": plan.get("artifact_ref", plan.get("active_artifact_ref")),
            "saga_id": plan["saga_id"],
            "plan_fingerprint": plan["plan_fingerprint"],
            "durable": self._store.durable,
            "contains_content": False,
            "operation": "rollback" if record["purpose"] == "rollback" else record["operation"],
        }

    def _fresh_preflight(self, record: dict, plan):
        context = self.orchestrator.governance_service.load_adapter_execution_grant_context(
            record["execution_grant_id"]
        )
        source = context.source_prepare_grant
        attestation = context.preflight_attestation
        data = dict(
            grant_id=source.grant_id,
            grant_fingerprint=source.grant_fingerprint,
            action_fingerprint=source.action_fingerprint,
            intent_fingerprint=source.intent_fingerprint,
            descriptor_fingerprint=source.descriptor_fingerprint,
            registry_fingerprint=source.registry_fingerprint,
            subject_ref=source.subject_ref,
            adapter_request=source.adapter_request,
            desired_text=record["operator_input"]["desired_text"],
            expected_root_config_fingerprint=attestation.root_config_fingerprint,
            preflight_policy_version=attestation.preflight_policy_version,
            diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
            diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
            prepared_at=attestation.preflight_prepared_at,
            expires_at=attestation.preflight_expires_at,
            authorization_expires_at=source.expires_at,
            expected_current_sha256=attestation.expected_current_sha256,
        )
        preflight = self.orchestrator.operational_service.preflight_local_text_file(
            LocalTextFilePreflightRequestContract(**data),
            now=self._now(),
        )
        if preflight.preflight_fingerprint != plan.preflight_fingerprint:
            raise ValueError("physical_console_preflight_changed")
        return preflight

    def inspect(self, request_id: str) -> dict:
        record, plan, _context = self._load(request_id)
        result = self.status(request_id)
        if record["purpose"] == "apply" and result["phase"] in {"prepared", "confirmed"}:
            preflight = self._fresh_preflight(record, plan)
            result.update(
                preview=preflight.unified_diff,
                preview_sensitive=True,
                before_sha256=preflight.before_content_sha256,
                desired_sha256=preflight.desired_content_sha256,
            )
        return result

    def status(self, request_id: str) -> dict:
        record, plan, _context = self._load(request_id)
        saga = self._saga(plan.saga_id)
        phase = (
            saga.phase
            if saga is not None
            else ("confirmed" if record["confirmation_receipt_id"] else "prepared")
        )
        return {
            **self._metadata(record),
            "phase": phase,
            "physical_state_verification": "not_performed_by_status",
            "challenge_state": (
                "expired"
                if self._now()
                >= datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
                else "active"
            ),
            "before_sha256": plan.before_content_sha256
            if record["purpose"] == "apply"
            else plan.expected_current_sha256,
            "desired_sha256": plan.desired_content_sha256
            if record["purpose"] == "apply"
            else plan.restored_content_sha256,
        }

    def _saga(self, saga_id: str):
        memory = self.orchestrator.memory_service
        if memory.repository.fetch_artifact_physical_saga_plan(saga_id) is None:
            return None
        return memory.get_artifact_physical_saga(saga_id)

    def _exact(self, record: dict, challenge_id: str, action_fingerprint: str) -> None:
        if (challenge_id, action_fingerprint) != (
            record["challenge_id"],
            record["action_fingerprint"],
        ):
            raise ValueError("physical_console_challenge_mismatch")

    def confirm(self, request_id: str, *, challenge_id: str, action_fingerprint: str) -> dict:
        record, _plan, _context = self._load(request_id)
        if record["purpose"] != "apply":
            raise ValueError("physical_console_wrong_confirmation_command")
        return self._confirm(record, challenge_id, action_fingerprint)

    def _confirm(self, record: dict, challenge_id: str, action_fingerprint: str) -> dict:
        self._exact(record, challenge_id, action_fingerprint)
        if record["confirmation_receipt_id"] is not None:
            raise ValueError("physical_console_already_confirmed")
        receipt = self.orchestrator.governance_service.confirm_action_challenge(
            challenge_id,
            operator_identity_ref=self.operator_identity_ref,
            expected_action_fingerprint=action_fingerprint,
            confirmed_at=_time(self._now()),
        )
        record["confirmation_receipt_id"] = receipt.receipt_id
        self._store.save(record["request_id"], record, replace=True)
        self._emit("action_confirmation_recorded", record)
        return self.status(record["request_id"])

    def _authorized(self, request_id, challenge_id, action_fingerprint, confirmation_receipt_id):
        record, plan, context = self._load(request_id)
        self._exact(record, challenge_id, action_fingerprint)
        if (
            not confirmation_receipt_id
            or confirmation_receipt_id != record["confirmation_receipt_id"]
        ):
            raise ValueError("physical_console_receipt_mismatch")
        confirmation = self.orchestrator.governance_service.load_action_confirmation_context(
            confirmation_receipt_id
        )
        if (
            confirmation.intent != context.intent
            or confirmation.challenge.challenge_id != challenge_id
            or confirmation.receipt.receipt_id != confirmation_receipt_id
            or confirmation.receipt.challenge_id != challenge_id
            or confirmation.receipt.operator_identity_ref != self.operator_identity_ref
            or confirmation.receipt.action_fingerprint != action_fingerprint
        ):
            raise ValueError("physical_console_receipt_mismatch")
        return record, plan, context

    def _require_execution_platform(self) -> None:
        if sys.platform != "linux":
            raise ValueError("physical_console_execution_backend_unavailable")
        if (
            getattr(
                self.orchestrator.operational_service, "_local_text_file_transaction_engine", None
            )
            is None
        ):
            raise ValueError("physical_console_execution_not_enabled")

    def _binding(self, context, receipt_id):
        request = (
            context.execution_request
            if hasattr(context, "execution_request")
            else context.rollback_request
        )
        fingerprint = (
            request.execution_request_fingerprint
            if hasattr(request, "execution_request_fingerprint")
            else request.rollback_request_fingerprint
        )
        grant = context.grant
        return LocalTextExecutionGrantBinding(
            execution_grant_id=grant.grant_id,
            execution_grant_fingerprint=grant.grant_fingerprint,
            action_fingerprint=grant.action_fingerprint,
            execution_request_fingerprint=fingerprint,
            intent_fingerprint=grant.intent_fingerprint,
            confirmation_receipt_id=receipt_id,
        )

    def execute(
        self,
        request_id: str,
        *,
        challenge_id: str,
        action_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> dict:
        record, plan, context = self._authorized(
            request_id, challenge_id, action_fingerprint, confirmation_receipt_id
        )
        self._require_execution_platform()
        if record["purpose"] != "apply":
            raise ValueError("physical_console_wrong_execution_command")
        if self._saga(plan.saga_id) is not None:
            raise ValueError("physical_console_execution_started_use_recover")
        mission = self._mission(
            str(plan.mission_id), plan.work_item_ref, str(context.intent.session_id)
        )
        if mission.objective_ref != plan.objective_ref:
            raise ValueError("physical_console_objective_changed")
        preflight = self._fresh_preflight(record, plan)
        request = LocalTextMutationRequest(
            operation_id=plan.physical_operation_id,
            preflight=preflight,
            desired_text=record["operator_input"]["desired_text"],
            execution_binding=self._binding(context, confirmation_receipt_id),
        )
        self.orchestrator.execute_artifact_physical_apply(plan, request)
        return self.status(request_id)

    def recover(
        self,
        request_id: str,
        *,
        challenge_id: str,
        action_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> dict:
        record, plan, context = self._authorized(
            request_id, challenge_id, action_fingerprint, confirmation_receipt_id
        )
        self._require_execution_platform()
        saga = self._saga(plan.saga_id)
        if saga is None:
            raise ValueError("physical_console_recovery_requires_started_saga")
        if record["purpose"] == "apply":
            request = None
            if saga.phase == "reserved":
                request = LocalTextMutationRequest(
                    plan.physical_operation_id,
                    self._fresh_preflight(record, plan),
                    record["operator_input"]["desired_text"],
                    self._binding(context, confirmation_receipt_id),
                )
            try:
                self.orchestrator.recover_artifact_physical_apply(plan.saga_id, request=request)
            except ValueError as exc:
                # Crash after canonical dispatch marker but before the physical
                # journal exists: retry the exact original request, never issue
                # a new confirmation. Any tamper/expiry/other error propagates.
                if str(exc) != "local_text_transaction_journal_missing" or request is not None:
                    raise
                mission = self._mission(
                    str(plan.mission_id), plan.work_item_ref, str(context.intent.session_id)
                )
                if mission.objective_ref != plan.objective_ref:
                    raise ValueError("physical_console_objective_changed")
                request = LocalTextMutationRequest(
                    plan.physical_operation_id,
                    self._fresh_preflight(record, plan),
                    record["operator_input"]["desired_text"],
                    self._binding(context, confirmation_receipt_id),
                )
                self.orchestrator.recover_artifact_physical_apply(plan.saga_id, request=request)
        else:
            request = (
                self._rollback_request(plan, context, confirmation_receipt_id)
                if saga.phase == "rollback_reserved"
                else None
            )
            try:
                self.orchestrator.recover_artifact_physical_rollback(plan.saga_id, request=request)
            except ValueError as exc:
                if str(exc) not in {
                    "local_text_transaction_journal_missing",
                    "local_text_rollback_request_required_before_journal",
                } or request is not None:
                    raise
                mission = self._mission(
                    str(plan.mission_id), plan.work_item_ref, str(context.intent.session_id)
                )
                if mission.objective_ref != plan.objective_ref:
                    raise ValueError("physical_console_objective_changed")
                self.orchestrator.recover_artifact_physical_rollback(
                    plan.saga_id,
                    request=self._rollback_request(plan, context, confirmation_receipt_id),
                )
        return self.status(request_id)

    def prepare_rollback(self, request_id: str, *, session_id: str) -> dict:
        source, source_plan, _context = self._load(request_id)
        if source["purpose"] != "apply":
            raise ValueError("physical_console_rollback_requires_apply")
        memory = self.orchestrator.memory_service
        governance = self.orchestrator.governance_service
        self._mission(str(source_plan.mission_id), source_plan.work_item_ref, session_id)
        version = memory.get_artifact_physical_version(source_plan.artifact_ref)
        lineage = memory.get_artifact_physical_lineage(
            str(source_plan.mission_id), source_plan.lineage_root_ref
        )
        if (
            version is None
            or lineage is None
            or lineage.active_artifact_ref != source_plan.artifact_ref
        ):
            raise ValueError("physical_console_rollback_head_mismatch")
        if source_plan.supersedes_artifact_ref is None:
            raise ValueError("physical_console_initial_version_has_no_canonical_predecessor")
        restored = memory.get_artifact_physical_version(source_plan.supersedes_artifact_ref)
        if restored is None:
            raise ValueError("physical_console_rollback_predecessor_missing")
        receipt = governance.load_local_text_mutation_receipt_exact(
            source_plan.physical_operation_id,
            expected_receipt_fingerprint=version.mutation_receipt_fingerprint,
        )
        rollback_id = uuid4().hex
        rollback_request = governance.prepare_local_text_file_rollback(
            receipt,
            rollback_operation_id=f"operation://physical-console/{rollback_id}",
        )
        intent = self._intent(
            rollback_id,
            mission_id=str(source_plan.mission_id),
            session_id=session_id,
            operation=rollback_request.operation,
            resource_ref=source_plan.resource_ref,
            content_digest=rollback_request.restored_content_sha256,
            precondition_digest=rollback_request.rollback_request_fingerprint,
            handler_id=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.executor_ref,
            handler_version=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.adapter_version,
            canonical_binding={
                "purpose": "rollback",
                "mission_id": source_plan.mission_id,
                "owner_mission_id": source_plan.owner_mission_id,
                "objective_ref": source_plan.objective_ref,
                "work_item_ref": source_plan.work_item_ref,
                "lineage_root_ref": source_plan.lineage_root_ref,
                "expected_lineage_revision": lineage.revision,
                "resource_ref": source_plan.resource_ref,
                "root_alias": source_plan.root_alias,
                "active_artifact_ref": source_plan.artifact_ref,
                "active_artifact_version": source_plan.artifact_version,
                "restored_artifact_ref": restored.artifact_ref,
                "restored_artifact_version": restored.artifact_version,
                "mutation_operation_id": source_plan.physical_operation_id,
                "source_apply_saga_id": source_plan.saga_id,
                "rollback_mode": "canonical_rollback",
                "canonical_effect_expected": True,
                "mutation_receipt_fingerprint": receipt.receipt_fingerprint,
            },
        )
        registry, descriptor = governance.resolve_active_local_text_file_rollback_descriptor(
            rollback_request
        )
        grant = governance.issue_local_text_file_rollback_grant(
            intent,
            rollback_request,
            _decision(True),
            expected_registry_fingerprint=registry.registry_fingerprint,
            expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        )
        challenge = governance.issue_action_confirmation_challenge(intent)
        plan = seal_artifact_physical_rollback_plan(
            ArtifactPhysicalRollbackPlanContract(
                saga_id=f"saga://physical-console/{rollback_id}",
                mission_id=source_plan.mission_id,
                active_artifact_ref=source_plan.artifact_ref,
                active_artifact_version=source_plan.artifact_version,
                restored_artifact_ref=restored.artifact_ref,
                restored_artifact_version=restored.artifact_version,
                owner_mission_id=source_plan.owner_mission_id,
                objective_ref=source_plan.objective_ref,
                work_item_ref=source_plan.work_item_ref,
                lineage_root_ref=source_plan.lineage_root_ref,
                physical_operation_id=rollback_request.rollback_operation_id,
                mutation_operation_id=source_plan.physical_operation_id,
                source_apply_saga_id=source_plan.saga_id,
                rollback_mode="canonical_rollback",
                canonical_effect_expected=True,
                mutation_receipt_fingerprint=receipt.receipt_fingerprint,
                resource_ref=source_plan.resource_ref,
                root_alias=source_plan.root_alias,
                expected_current_sha256=rollback_request.expected_current_sha256,
                restored_content_sha256=rollback_request.restored_content_sha256,
                expected_lineage_revision=lineage.revision,
                created_at=intent.issued_at,
                plan_fingerprint="0" * 64,
            )
        )
        require_valid_artifact_physical_rollback_plan(plan)
        record = self._record(rollback_id, "rollback", challenge, grant, plan)
        record["source_request_id"] = request_id
        self._store.save(rollback_id, record)
        self._emit("action_confirmation_challenged", record)
        return self.status(rollback_id)

    def confirm_rollback(
        self, request_id: str, *, challenge_id: str, action_fingerprint: str
    ) -> dict:
        record, _plan, _context = self._load(request_id)
        if record["purpose"] != "rollback":
            raise ValueError("physical_console_wrong_confirmation_command")
        return self._confirm(record, challenge_id, action_fingerprint)

    def _rollback_request(self, plan, context, receipt_id):
        receipt = self.orchestrator.governance_service.load_local_text_mutation_receipt_exact(
            plan.mutation_operation_id,
            expected_receipt_fingerprint=plan.mutation_receipt_fingerprint,
        )
        return LocalTextRollbackRequest(
            plan.physical_operation_id, receipt, self._binding(context, receipt_id)
        )

    def rollback(
        self,
        request_id: str,
        *,
        challenge_id: str,
        action_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> dict:
        record, plan, context = self._authorized(
            request_id, challenge_id, action_fingerprint, confirmation_receipt_id
        )
        self._require_execution_platform()
        if record["purpose"] != "rollback":
            raise ValueError("physical_console_wrong_execution_command")
        if self._saga(plan.saga_id) is not None:
            raise ValueError("physical_console_execution_started_use_recover")
        self._mission(str(plan.mission_id), plan.work_item_ref, str(context.intent.session_id))
        self.orchestrator.execute_artifact_physical_rollback(
            plan,
            self._rollback_request(plan, context, confirmation_receipt_id),
        )
        return self.status(request_id)
