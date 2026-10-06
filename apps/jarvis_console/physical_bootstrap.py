# ruff: noqa: E402
"""Explicit local-file composition; no implicit roots or legacy database reuse."""

import os
import re
import stat
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
from operational_service.adapters.local_text_governance import LocalTextGovernanceAuthorityAdapter
from operational_service.adapters.local_text_transaction import LocalTextTransactionEngine
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from shared.adapter_execution_permissions import SEEDED_ADAPTER_EXECUTION_REGISTRY
from shared.adapter_permissions import SEEDED_ADAPTER_REGISTRY
from shared.artifact_physical_attestation_authority import ArtifactPhysicalAttestationLeaseAuthority
from shared.local_text_rollback_permissions import SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY


class _LocalObservability(ObservabilityService):
    @staticmethod
    def _build_agentic_adapter():
        return None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _reject_redirects(path: Path) -> None:
    """Reject symlinks, Windows reparse points and multiply-linked ledger files.

    This is configuration validation, not a sandbox against a hostile same-user
    process racing the filesystem. Linux request/transaction stores also pin fds.
    """
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("redirected_physical_path")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError("multiply_linked_physical_file")


def _validate_runtime_entries(runtime: Path) -> None:
    for name in ("governance.db", "memory.db", "observability.db"):
        for suffix in ("", "-wal", "-shm", "-journal"):
            path = runtime / (name + suffix)
            _reject_redirects(path)
            if path.exists() and not path.is_file():
                raise ValueError("invalid_physical_ledger")
    for name in ("artifacts", "physical-requests"):
        path = runtime / name
        _reject_redirects(path)
        if path.exists() and not path.is_dir():
            raise ValueError("invalid_physical_directory")


def _exclusive_runtime_anchor(info, *, child_owner: int, user_id: int) -> bool:
    if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, user_id}:
        return False
    return not stat.S_IMODE(info.st_mode) & 0o022 or (
        bool(info.st_mode & stat.S_ISVTX) and child_owner == user_id
    )


def _validate_linux_runtime_anchors(runtime: Path) -> None:
    if sys.platform != "linux":
        return
    user_id = os.geteuid()
    child_owner = user_id
    if runtime.exists():
        info = runtime.stat()
        if info.st_uid != user_id or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("private_owned_physical_runtime_required")
        child_owner = info.st_uid
    for parent in runtime.parents:
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        if not _exclusive_runtime_anchor(info, child_owner=child_owner, user_id=user_id):
            raise ValueError("unsafe_physical_runtime_anchor")
        child_owner = info.st_uid


def validate_physical_configuration(
    runtime_dir: Path, roots: Mapping[str, Path], *, enable_execution: bool,
) -> tuple[Path, dict[str, Path]]:
    if type(enable_execution) is not bool or not 1 <= len(roots) <= 16:
        raise ValueError("invalid_physical_configuration")
    if enable_execution and sys.platform != "linux":
        # No runtime/journal/ledger creation before this platform refusal.
        raise ValueError("physical_execution_backend_unavailable")
    if enable_execution:
        LocalTextTransactionEngine._require_posix_mutation_backend()
    runtime = Path(runtime_dir)
    if not runtime.is_absolute() or runtime.is_symlink():
        raise ValueError("invalid_physical_runtime")
    _reject_redirects(runtime)
    if runtime.exists() and not runtime.is_dir():
        raise ValueError("invalid_physical_runtime")
    runtime = runtime.resolve()
    _validate_runtime_entries(runtime)
    _validate_linux_runtime_anchors(runtime)
    validated = {}
    for alias, value in roots.items():
        if type(alias) is not str or re.fullmatch(r"[a-z][a-z0-9-]{0,63}", alias) is None:
            raise ValueError("invalid_physical_root_alias")
        root = Path(value)
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise ValueError("existing_physical_root_required")
        _reject_redirects(root)
        root = root.resolve(strict=True)
        if root == Path(root.anchor) or root == runtime or root in runtime.parents:
            raise ValueError("physical_runtime_root_overlap")
        if runtime in root.parents:
            raise ValueError("physical_runtime_root_overlap")
        for existing in validated.values():
            if root == existing or root in existing.parents or existing in root.parents:
                raise ValueError("physical_roots_overlap")
        if enable_execution:
            journal = root / ".jarvis-transactions"
            if journal.is_symlink() or not journal.is_dir():
                raise ValueError("existing_private_transaction_directory_required")
        validated[alias] = root
    return runtime, validated


def build_physical_orchestrator(
    *, runtime_dir: Path, roots: Mapping[str, Path], enable_execution: bool = False,
) -> OrchestratorService:
    """Prepare-only on Windows; execution opt-in retains all MB217 authorities.

    Operators must provide existing target roots and, for Linux execution,
    existing private .jarvis-transactions directories. This function creates
    databases only in the explicitly selected runtime. No external tracing.
    """
    runtime, validated = validate_physical_configuration(
        runtime_dir, roots, enable_execution=enable_execution,
    )
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    _validate_linux_runtime_anchors(runtime)
    _validate_runtime_entries(runtime)
    governance = GovernanceService(runtime / "governance.db")
    # Seed activation is explicit in this opt-in composition and idempotent.
    # Existing immutable registries cannot be silently downgraded/rebound.
    governance.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY)
    governance.activate_adapter_execution_registry(SEEDED_ADAPTER_EXECUTION_REGISTRY)
    governance.activate_local_text_file_rollback_registry(SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY)
    attestation = ArtifactPhysicalAttestationLeaseAuthority()
    memory = MemoryService(
        database_url=f"sqlite:///{(runtime / 'memory.db').as_posix()}",
        artifact_physical_mutation_verifier=lambda receipt, proof: (
            governance.verify_local_text_mutation_receipt_exact(receipt)
            and attestation.verify_and_consume(receipt, proof)
        ),
        artifact_physical_rollback_verifier=lambda receipt, proof: (
            governance.verify_local_text_rollback_receipt_exact(receipt)
            and attestation.verify_and_consume(receipt, proof)
        ),
    )
    arguments = {
        "artifact_dir": str(runtime / "artifacts"),
        "action_confirmation_verifier": governance.verify_action_confirmation_claim,
        "adapter_preflight_verifier": governance.verify_adapter_grant_for_preflight_exact,
        "local_text_file_roots": validated,
        "local_text_file_preflight_attestor": governance.attest_local_text_file_preflight,
    }
    if enable_execution:
        authority = LocalTextGovernanceAuthorityAdapter(governance)
        arguments.update({
            "local_text_file_transaction_roots": {
                alias: root / ".jarvis-transactions" for alias, root in validated.items()
            },
            "local_text_file_staging_authorization_verifier": authority.verify_staging,
            "local_text_file_effect_start_claim_verifier": authority.verify_effect_start,
            "local_text_file_historical_claim_lookup": authority.lookup_historical,
            "local_text_file_historical_claim_verifier": authority.verify_historical,
            "local_text_file_authorization_lease_provider": authority.claim,
            "local_text_file_trusted_transaction_clock": _utc_now,
            "local_text_file_mutation_receipt_recorder": authority.record_mutation_receipt,
            "local_text_file_rollback_receipt_recorder": authority.record_rollback_receipt,
            "local_text_file_mutation_receipt_verifier":
                governance.verify_local_text_mutation_receipt_exact,
            "local_text_file_rollback_receipt_verifier":
                governance.verify_local_text_rollback_receipt_exact,
            "local_text_file_canonical_physical_effect_authorizer":
                memory.authorize_artifact_physical_effect,
            "local_text_file_canonical_physical_effect_scope_provider":
                memory.artifact_physical_effect_scope,
            "local_text_file_resource_physical_binding_lookup":
                memory.is_local_text_resource_physically_bound,
            "local_text_file_canonical_commit_receipt_verifier":
                memory.verify_artifact_physical_canonical_commit_receipt,
            "local_text_file_physical_attestation_lease_provider": attestation.issue,
        })
    return OrchestratorService(
        governance_service=governance, memory_service=memory,
        operational_service=OperationalService(**arguments),
        observability_service=_LocalObservability(str(runtime / "observability.db")),
        artifact_physical_clock=lambda: _utc_now().isoformat(),
        artifact_physical_attestation_authority=attestation,
    )
