"""Durable, idempotent local-text mutation engine.

The module deliberately owns no governance decisions.  Its authorization port
returns an already-claimed, single-use execution lease.  A prepare-only
preflight can therefore never authorize a filesystem effect by itself.

Physical mutation is currently enabled only on POSIX systems with the required
``openat``/``renameat`` primitives.  Windows fails closed until the equivalent
handle-relative rename backend is available.
"""

from __future__ import annotations

import errno
import json
import os
import platform
import re
import sqlite3
import stat
import sys
import threading
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from typing import Callable, Iterator, Protocol
from uuid import uuid4

from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_ADAPTER_BACKEND_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
    LocalTextFilePreflightAdapter,
    _canonical_digest,
    _digest_bytes,
    _is_reparse_or_link,
    _NodeObservation,
    require_valid_local_text_file_preflight,
)
from shared.artifact_physical_saga import (
    require_valid_artifact_physical_apply_plan,
    require_valid_artifact_physical_canonical_commit_receipt,
    require_valid_artifact_physical_rollback_plan,
    require_valid_local_text_physical_state_attestation,
    require_valid_local_text_resource_ref,
    seal_local_text_physical_state_attestation,
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
from shared.local_text_rollback_permissions import (
    build_mutation_receipt_fingerprint,
    build_rollback_receipt_fingerprint,
    require_valid_local_text_mutation_receipt,
    require_valid_local_text_rollback_receipt,
)

if os.name == "nt":
    import msvcrt
else:
    import fcntl

LOCAL_TEXT_TRANSACTION_POLICY_VERSION = "1.0.0"
LOCAL_TEXT_TRANSACTION_BACKEND_VERSION = "posix-openat-1.0.0"
_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_EMPTY_SHA256 = sha256(b"").hexdigest()
_RENAMEAT2_SYSCALLS = {
    "aarch64": 276,
    "amd64": 316,
    "arm64": 276,
    "i386": 353,
    "i686": 353,
    "riscv64": 276,
    "x86_64": 316,
}
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | int(getattr(os, "O_DIRECTORY", 0))
    | int(getattr(os, "O_NOFOLLOW", 0))
    | int(getattr(os, "O_NONBLOCK", 0))
)
_FILE_READ_FLAGS = (
    os.O_RDONLY | int(getattr(os, "O_NOFOLLOW", 0)) | int(getattr(os, "O_NONBLOCK", 0))
)
_ALLOWED_TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset({"reserved"}),
    "reserved": frozenset({"desired_durable"}),
    "desired_durable": frozenset({"backup_durable", "staged"}),
    "backup_durable": frozenset({"staged"}),
    "staged": frozenset({"claimed"}),
    "claimed": frozenset({"renamed"}),
    "renamed": frozenset({"applied"}),
    "applied": frozenset({"receipt"}),
    "receipt": frozenset({"cleaned", "rollback_reserved"}),
    "cleaned": frozenset({"rollback_reserved"}),
    "rollback_reserved": frozenset({"rollback_claimed"}),
    "rollback_claimed": frozenset({"rollback_renamed"}),
    "rollback_renamed": frozenset({"rolled_back"}),
    "rolled_back": frozenset({"rollback_receipt"}),
    "rollback_receipt": frozenset(),
}


class InjectedTransactionFailure(RuntimeError):
    """Deterministic crash boundary used by failure-injection tests."""


@dataclass(frozen=True)
class LocalTextExecutionAuthorizationRequest:
    purpose: str
    operation_id: str
    action_kind: str
    operation: str
    resource_ref: str
    subject_ref: str
    preflight_fingerprint: str
    before_content_sha256: str
    desired_content_sha256: str
    root_config_fingerprint: str
    transaction_policy_version: str
    execution_grant_id: str
    execution_grant_fingerprint: str
    action_fingerprint: str
    execution_request_fingerprint: str
    intent_fingerprint: str
    confirmation_receipt_id: str
    journal_reservation_fingerprint: str
    mutation_receipt_fingerprint: str | None = None


@dataclass(frozen=True)
class LocalTextExecutionAuthorizationContext:
    purpose: str
    operation_id: str
    execution_grant_id: str
    execution_claim_id: str
    action_kind: str
    operation: str
    resource_ref: str
    subject_ref: str
    preflight_fingerprint: str
    before_content_sha256: str
    desired_content_sha256: str
    root_config_fingerprint: str
    claimed_at: str
    expires_at: str
    authority_fingerprint: str
    execution_grant_fingerprint: str
    action_fingerprint: str
    execution_request_fingerprint: str
    intent_fingerprint: str
    confirmation_receipt_id: str
    journal_reservation_fingerprint: str
    mutation_receipt_fingerprint: str | None = None
    claimed: bool = True
    single_use: bool = True
    execution_allowed: bool = True
    prepare_grant_reusable_for_execution: bool = False


class LocalTextClaimedAuthorizationLease(Protocol):
    """A live claim used only at the one transition from staged to claimed."""

    @property
    def context(self) -> LocalTextExecutionAuthorizationContext: ...

    def complete(self, receipt_fingerprint: str) -> None: ...

    def interrupt(self, reason: str) -> None: ...


AuthorizationLeaseProvider = Callable[
    [LocalTextExecutionAuthorizationRequest, datetime],
    LocalTextClaimedAuthorizationLease,
]
FailureInjector = Callable[[str], None]
TrustedTransactionClock = Callable[[], datetime]
MutationReceiptVerifier = Callable[[LocalTextMutationReceipt], bool]
RollbackReceiptVerifier = Callable[[LocalTextRollbackReceipt], bool]
MutationReceiptRecorder = Callable[[LocalTextMutationReceipt], LocalTextMutationReceipt]
RollbackReceiptRecorder = Callable[[LocalTextRollbackReceipt], LocalTextRollbackReceipt]
ApplyCanonicalCommit = Callable[
    [
        ArtifactPhysicalApplyPlanContract,
        LocalTextMutationReceipt,
        LocalTextPhysicalStateAttestationContract,
    ],
    ArtifactPhysicalCanonicalCommitReceiptContract,
]
RollbackCanonicalCommit = Callable[
    [
        ArtifactPhysicalRollbackPlanContract,
        LocalTextRollbackReceipt,
        LocalTextPhysicalStateAttestationContract,
    ],
    ArtifactPhysicalCanonicalCommitReceiptContract,
]
CanonicalCommitReceiptVerifier = Callable[[ArtifactPhysicalCanonicalCommitReceiptContract], bool]
PhysicalAttestationLeaseProvider = Callable[
    [
        ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
        LocalTextMutationReceipt | LocalTextRollbackReceipt,
        LocalTextPhysicalStateAttestationContract,
    ],
    AbstractContextManager[None],
]


@dataclass(frozen=True)
class LocalTextStagingAuthorizationRequest:
    purpose: str
    operation_id: str
    operation: str
    resource_ref: str
    subject_ref: str
    preflight_fingerprint: str
    before_content_sha256: str
    desired_content_sha256: str
    root_config_fingerprint: str
    execution_binding: LocalTextExecutionGrantBinding
    mutation_receipt_fingerprint: str | None = None


StagingAuthorizationVerifier = Callable[[LocalTextStagingAuthorizationRequest, datetime], bool]
HistoricalClaimVerifier = Callable[[LocalTextExecutionAuthorizationContext, datetime], bool]
EffectStartClaimVerifier = Callable[[LocalTextExecutionAuthorizationContext, datetime], bool]
HistoricalClaimLookup = Callable[
    [LocalTextExecutionAuthorizationRequest, datetime],
    LocalTextExecutionAuthorizationContext | None,
]


@dataclass(frozen=True)
class LocalTextExecutionGrantBinding:
    execution_grant_id: str
    execution_grant_fingerprint: str
    action_fingerprint: str
    execution_request_fingerprint: str
    intent_fingerprint: str
    confirmation_receipt_id: str


CanonicalPhysicalEffectAuthorizer = Callable[
    [ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract], bool
]
ResourcePhysicalBindingLookup = Callable[[str], bool]


@dataclass(frozen=True)
class LocalTextMutationRequest:
    operation_id: str
    preflight: LocalTextFilePreflightContract
    desired_text: str
    execution_binding: LocalTextExecutionGrantBinding


@dataclass(frozen=True)
class LocalTextRollbackRequest:
    rollback_operation_id: str
    receipt: LocalTextMutationReceipt
    execution_binding: LocalTextExecutionGrantBinding


@dataclass(frozen=True)
class _JournalEvent:
    operation_id: str
    sequence: int
    phase: str
    metadata: dict[str, object]
    recorded_at: str
    previous_event_fingerprint: str | None
    event_fingerprint: str


@dataclass
class _PinnedPosixTarget:
    root_path: Path
    parent_segments: tuple[str, ...]
    root_fd: int
    parent_fd: int
    transaction_fd: int
    target_fd: int | None
    directory_fds: tuple[int, ...]
    target_name: str
    before_bytes: bytes
    before_identity: dict[str, int] | None
    current_hash: str | None

    def close(self) -> None:
        descriptors = {
            self.root_fd,
            self.parent_fd,
            self.transaction_fd,
            *self.directory_fds,
        }
        if self.target_fd is not None:
            descriptors.add(self.target_fd)
        for descriptor in descriptors:
            os.close(descriptor)


def build_execution_authority_fingerprint(
    context: LocalTextExecutionAuthorizationContext,
) -> str:
    payload = asdict(context)
    payload.pop("authority_fingerprint", None)
    return _canonical_digest(payload)


def _canonical_time(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("local_text_transaction_now_not_timezone_aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str, error: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise ValueError(error) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(error)
    return parsed.astimezone(timezone.utc)


def _node_identity(observed: os.stat_result) -> dict[str, int]:
    return {
        "device": int(observed.st_dev),
        "inode": int(observed.st_ino),
        "mode": int(observed.st_mode),
        "links": int(observed.st_nlink),
        "size": int(observed.st_size),
        "mtime_ns": int(observed.st_mtime_ns),
        "ctime_ns": int(observed.st_ctime_ns),
    }


def _directory_identity(observed: os.stat_result) -> dict[str, int]:
    return {
        "device": int(observed.st_dev),
        "inode": int(observed.st_ino),
        "mode": int(observed.st_mode),
        "file_attributes": int(getattr(observed, "st_file_attributes", 0)),
    }


def _require_safe_owned_directory(observed: os.stat_result) -> None:
    if not stat.S_ISDIR(observed.st_mode) or _is_reparse_or_link(observed):
        raise ValueError("local_text_transaction_directory_not_safe")
    if os.name != "nt" and (
        int(observed.st_uid) != os.geteuid() or stat.S_IMODE(observed.st_mode) & 0o022
    ):
        raise ValueError("local_text_transaction_directory_not_exclusive")


def _require_safe_state_directory(observed: os.stat_result) -> None:
    _require_safe_owned_directory(observed)
    if os.name != "nt" and stat.S_IMODE(observed.st_mode) & 0o077:
        raise ValueError("local_text_transaction_state_directory_not_private")


def _require_same_device(observed: os.stat_result, expected_device: int) -> None:
    if int(observed.st_dev) != int(expected_device):
        raise ValueError("local_text_transaction_path_cross_device")


def _observe_safe_root_anchors(
    root: Path, root_observed: os.stat_result
) -> tuple[tuple[Path, dict[str, int]], ...]:
    anchors: list[tuple[Path, dict[str, int]]] = []
    child_observed = root_observed
    anchor = root.parent
    while True:
        observed = os.lstat(anchor)
        if not stat.S_ISDIR(observed.st_mode) or _is_reparse_or_link(observed):
            raise ValueError("local_text_transaction_root_anchor_not_safe")
        writable_by_others = bool(stat.S_IMODE(observed.st_mode) & 0o022)
        sticky_protects_entry = (
            bool(observed.st_mode & stat.S_ISVTX)
            and int(child_observed.st_uid) == os.geteuid()
            and int(observed.st_uid) in {0, os.geteuid()}
        )
        if writable_by_others and not sticky_protects_entry:
            raise ValueError("local_text_transaction_root_anchor_not_exclusive")
        anchors.append((anchor, _directory_identity(observed)))
        if anchor.parent == anchor:
            break
        child_observed = observed
        anchor = anchor.parent
    return tuple(anchors)


class LocalTextTransactionEngine:
    """Execute, recover, and roll back an exact preflight-bound mutation."""

    def __init__(
        self,
        *,
        preflight_adapter: LocalTextFilePreflightAdapter,
        transaction_roots: dict[str, str | os.PathLike[str]],
        staging_authorization_verifier: StagingAuthorizationVerifier,
        effect_start_claim_verifier: EffectStartClaimVerifier,
        historical_claim_lookup: HistoricalClaimLookup,
        historical_claim_verifier: HistoricalClaimVerifier,
        authorization_lease_provider: AuthorizationLeaseProvider,
        trusted_transaction_clock: TrustedTransactionClock,
        mutation_receipt_verifier: MutationReceiptVerifier | None = None,
        rollback_receipt_verifier: RollbackReceiptVerifier | None = None,
        canonical_physical_effect_authorizer: CanonicalPhysicalEffectAuthorizer | None = None,
        resource_physical_binding_lookup: ResourcePhysicalBindingLookup | None = None,
        canonical_commit_receipt_verifier: CanonicalCommitReceiptVerifier | None = None,
        physical_attestation_lease_provider: PhysicalAttestationLeaseProvider | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        configured_roots = getattr(preflight_adapter, "_roots", None)
        if configured_roots is None:
            raise ValueError("local_text_preflight_adapter_roots_unavailable")
        if not callable(authorization_lease_provider):
            raise ValueError("local_text_execution_lease_provider_required")
        if not callable(staging_authorization_verifier):
            raise ValueError("local_text_staging_authorization_verifier_required")
        if not callable(effect_start_claim_verifier):
            raise ValueError("local_text_effect_start_claim_verifier_required")
        if not callable(historical_claim_verifier):
            raise ValueError("local_text_historical_claim_verifier_required")
        if not callable(historical_claim_lookup):
            raise ValueError("local_text_historical_claim_lookup_required")
        if not callable(trusted_transaction_clock):
            raise ValueError("local_text_trusted_transaction_clock_required")
        if mutation_receipt_verifier is not None and not callable(mutation_receipt_verifier):
            raise ValueError("local_text_mutation_receipt_verifier_invalid")
        if rollback_receipt_verifier is not None and not callable(rollback_receipt_verifier):
            raise ValueError("local_text_rollback_receipt_verifier_invalid")
        if canonical_physical_effect_authorizer is not None and not callable(
            canonical_physical_effect_authorizer
        ):
            raise ValueError("local_text_canonical_physical_effect_authorizer_invalid")
        if resource_physical_binding_lookup is not None and not callable(
            resource_physical_binding_lookup
        ):
            raise ValueError("local_text_resource_physical_binding_lookup_invalid")
        if canonical_commit_receipt_verifier is not None and not callable(
            canonical_commit_receipt_verifier
        ):
            raise ValueError("local_text_canonical_commit_receipt_verifier_invalid")
        if physical_attestation_lease_provider is not None and not callable(
            physical_attestation_lease_provider
        ):
            raise ValueError("local_text_physical_attestation_lease_provider_invalid")
        canonical_ports = (
            canonical_physical_effect_authorizer,
            resource_physical_binding_lookup,
            canonical_commit_receipt_verifier,
            physical_attestation_lease_provider,
        )
        if any(port is not None for port in canonical_ports) and any(
            port is None for port in canonical_ports
        ):
            raise ValueError("local_text_canonical_physical_ports_incomplete")
        if set(transaction_roots) != set(configured_roots):
            raise ValueError("local_text_transaction_root_aliases_mismatch")
        if os.name == "nt":
            raise ValueError("local_text_transaction_backend_not_handle_safe")
        self._require_posix_mutation_backend()
        validated: dict[str, Path] = {}
        identities: dict[str, dict[str, int]] = {}
        anchor_identities: dict[str, tuple[tuple[Path, dict[str, int]], ...]] = {}
        for alias, configured in transaction_roots.items():
            root = configured_roots[alias]
            transaction_root = Path(configured)
            if (
                not transaction_root.is_absolute()
                or transaction_root.parent != root
                or transaction_root.name != ".jarvis-transactions"
            ):
                raise ValueError("local_text_transaction_root_invalid")
            root_observed = os.lstat(root)
            observed = os.lstat(transaction_root)
            anchor_identities[alias] = _observe_safe_root_anchors(root, root_observed)
            _require_safe_owned_directory(root_observed)
            _require_safe_state_directory(observed)
            if observed.st_dev != root_observed.st_dev:
                raise ValueError("local_text_transaction_root_cross_device")
            validated[alias] = transaction_root
            identities[alias] = _directory_identity(observed)
        self._preflight_adapter = preflight_adapter
        self._transaction_roots = validated
        self._transaction_root_identities = identities
        self._root_anchor_identities = anchor_identities
        self._authorization_lease_provider = authorization_lease_provider
        self._staging_authorization_verifier = staging_authorization_verifier
        self._effect_start_claim_verifier = effect_start_claim_verifier
        self._historical_claim_verifier = historical_claim_verifier
        self._historical_claim_lookup = historical_claim_lookup
        self._trusted_transaction_clock = trusted_transaction_clock
        self._mutation_receipt_verifier = mutation_receipt_verifier
        self._rollback_receipt_verifier = rollback_receipt_verifier
        self._canonical_physical_effect_authorizer = canonical_physical_effect_authorizer
        self._resource_physical_binding_lookup = resource_physical_binding_lookup
        self._canonical_commit_receipt_verifier = canonical_commit_receipt_verifier
        self._physical_attestation_lease_provider = physical_attestation_lease_provider
        self._trusted_clock_lock = threading.Lock()
        self._last_trusted_time: datetime | None = None
        self._failure_injector = failure_injector
        self._thread_locks: dict[str, threading.Lock] = {}
        self._thread_locks_guard = threading.Lock()
        for alias in validated:
            self._initialize_journal(alias)

    @staticmethod
    def _require_posix_mutation_backend() -> None:
        if sys.platform != "linux" or platform.machine().casefold() not in _RENAMEAT2_SYSCALLS:
            raise ValueError("local_text_transaction_create_noreplace_backend_missing")

    def _inject(self, seam: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(seam)

    def _trusted_now(self) -> datetime:
        with self._trusted_clock_lock:
            try:
                current = self._trusted_transaction_clock()
            except Exception:
                raise ValueError("local_text_trusted_transaction_clock_failed") from None
            if not isinstance(current, datetime):
                raise ValueError("local_text_trusted_transaction_clock_invalid")
            try:
                _canonical_time(current)
            except ValueError:
                raise ValueError("local_text_trusted_transaction_clock_invalid") from None
            instant = current.astimezone(timezone.utc)
            if self._last_trusted_time is not None and instant < self._last_trusted_time:
                raise ValueError("local_text_trusted_transaction_clock_regressed")
            self._last_trusted_time = instant
            return instant

    def _require_transaction_root_current(self, alias: str) -> None:
        self._require_root_anchors_current(alias)
        observed = os.lstat(self._transaction_roots[alias])
        _require_safe_state_directory(observed)
        if _directory_identity(observed) != self._transaction_root_identities[alias]:
            raise ValueError("local_text_transaction_root_changed")

    def _require_root_anchors_current(self, alias: str) -> None:
        for path, expected in self._root_anchor_identities[alias]:
            observed = os.lstat(path)
            if _directory_identity(observed) != expected:
                raise ValueError("local_text_transaction_root_anchor_changed")

    def _journal_path(self, alias: str) -> Path:
        return self._transaction_roots[alias] / "journal.sqlite3"

    @contextmanager
    def _open_state_directory(self, alias: str) -> Iterator[int | None]:
        if os.name == "nt":
            self._require_transaction_root_current(alias)
            yield None
            return
        root = getattr(self._preflight_adapter, "_roots")[alias]
        self._require_root_anchors_current(alias)
        root_fd = os.open(root, _DIRECTORY_FLAGS)
        state_fd: int | None = None
        try:
            _require_safe_owned_directory(os.fstat(root_fd))
            state_fd = os.open(".jarvis-transactions", _DIRECTORY_FLAGS, dir_fd=root_fd)
            observed = os.fstat(state_fd)
            _require_safe_state_directory(observed)
            if _directory_identity(observed) != self._transaction_root_identities[alias]:
                raise ValueError("local_text_transaction_root_changed")
            yield state_fd
        finally:
            if state_fd is not None:
                os.close(state_fd)
            os.close(root_fd)

    @contextmanager
    def _journal_connection(self, alias: str) -> Iterator[sqlite3.Connection]:
        with self._open_state_directory(alias) as state_fd:
            if state_fd is None:
                location = os.fspath(self._journal_path(alias))
            else:
                proc_directory = f"/proc/self/fd/{state_fd}"
                if not os.path.isdir(proc_directory):
                    raise ValueError("local_text_transaction_pinned_journal_backend_missing")
                location = f"{proc_directory}/journal.sqlite3"
            connection = sqlite3.connect(location, timeout=30)
            try:
                yield connection
            finally:
                connection.close()

    def _require_journal_files_safe(self, alias: str) -> None:
        with self._open_state_directory(alias) as state_fd:
            for name in ("journal.sqlite3", "journal.sqlite3-wal", "journal.sqlite3-shm"):
                try:
                    if state_fd is None:
                        observed = os.lstat(self._transaction_roots[alias] / name)
                    else:
                        observed = os.stat(name, dir_fd=state_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if (
                    not stat.S_ISREG(observed.st_mode)
                    or _is_reparse_or_link(observed)
                    or observed.st_nlink != 1
                    or (os.name != "nt" and stat.S_IMODE(observed.st_mode) != 0o600)
                ):
                    raise ValueError("local_text_transaction_journal_file_not_safe")

    def _make_journal_files_private(self, alias: str) -> None:
        if os.name == "nt":
            return
        with self._open_state_directory(alias) as state_fd:
            assert state_fd is not None
            for name in ("journal.sqlite3", "journal.sqlite3-wal", "journal.sqlite3-shm"):
                try:
                    os.chmod(name, 0o600, dir_fd=state_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue

    def _prepare_journal_main_file(self, alias: str) -> None:
        """Create/open the SQLite main file without following a planted link.

        The owner of the private state directory is part of the local TCB:
        sqlite3's stdlib API cannot retain this fd as its database handle.
        """

        with self._open_state_directory(alias) as state_fd:
            assert state_fd is not None
            flags = os.O_RDWR | os.O_CREAT | int(getattr(os, "O_NOFOLLOW", 0))
            descriptor = os.open("journal.sqlite3", flags, 0o600, dir_fd=state_fd)
            try:
                observed = os.fstat(descriptor)
                if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                    raise ValueError("local_text_transaction_journal_file_not_safe")
                os.fchmod(descriptor, 0o600)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.fsync(state_fd)

    def _initialize_journal(self, alias: str) -> None:
        self._require_transaction_root_current(alias)
        self._require_journal_files_safe(alias)
        self._prepare_journal_main_file(alias)
        self._require_journal_files_safe(alias)
        with self._journal_connection(alias) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS local_text_transaction_events (
                    operation_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    previous_event_fingerprint TEXT,
                    event_fingerprint TEXT NOT NULL,
                    PRIMARY KEY (operation_id, sequence),
                    UNIQUE (event_fingerprint)
                );
                CREATE TRIGGER IF NOT EXISTS local_text_transaction_events_no_update
                BEFORE UPDATE ON local_text_transaction_events
                BEGIN SELECT RAISE(ABORT, 'append_only_transaction_journal'); END;
                CREATE TRIGGER IF NOT EXISTS local_text_transaction_events_no_delete
                BEFORE DELETE ON local_text_transaction_events
                BEGIN SELECT RAISE(ABORT, 'append_only_transaction_journal'); END;
                """
            )
            self._make_journal_files_private(alias)
        self._require_journal_files_safe(alias)

    @staticmethod
    def _event_fingerprint(
        *,
        operation_id: str,
        sequence: int,
        phase: str,
        metadata: dict[str, object],
        recorded_at: str,
        previous_event_fingerprint: str | None,
    ) -> str:
        return _canonical_digest(
            {
                "operation_id": operation_id,
                "sequence": sequence,
                "phase": phase,
                "metadata": metadata,
                "recorded_at": recorded_at,
                "previous_event_fingerprint": previous_event_fingerprint,
            }
        )

    def _load_events(self, alias: str, operation_id: str) -> list[_JournalEvent]:
        self._require_transaction_root_current(alias)
        self._require_journal_files_safe(alias)
        with self._journal_connection(alias) as connection:
            rows = connection.execute(
                """SELECT operation_id, sequence, phase, metadata_json, recorded_at,
                          previous_event_fingerprint, event_fingerprint
                   FROM local_text_transaction_events
                   WHERE operation_id = ? ORDER BY sequence""",
                (operation_id,),
            ).fetchall()
        events: list[_JournalEvent] = []
        previous: str | None = None
        previous_phase: str | None = None
        for expected_sequence, row in enumerate(rows):
            metadata = json.loads(row[3])
            event = _JournalEvent(
                operation_id=str(row[0]),
                sequence=int(row[1]),
                phase=str(row[2]),
                metadata=metadata,
                recorded_at=str(row[4]),
                previous_event_fingerprint=row[5],
                event_fingerprint=str(row[6]),
            )
            expected_fingerprint = self._event_fingerprint(
                operation_id=event.operation_id,
                sequence=event.sequence,
                phase=event.phase,
                metadata=event.metadata,
                recorded_at=event.recorded_at,
                previous_event_fingerprint=event.previous_event_fingerprint,
            )
            if (
                event.sequence != expected_sequence
                or event.previous_event_fingerprint != previous
                or event.phase not in _ALLOWED_TRANSITIONS.get(previous_phase, frozenset())
                or not compare_digest(event.event_fingerprint, expected_fingerprint)
            ):
                raise ValueError("local_text_transaction_journal_tampered")
            events.append(event)
            previous = event.event_fingerprint
            previous_phase = event.phase
        return events

    def _append_event(
        self,
        *,
        alias: str,
        operation_id: str,
        phase: str,
        metadata: dict[str, object],
        current: datetime,
    ) -> _JournalEvent:
        del current
        self._require_transaction_root_current(alias)
        self._require_journal_files_safe(alias)
        recorded_at = _canonical_time(self._trusted_now())
        with self._journal_connection(alias) as connection:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT sequence, phase, event_fingerprint
                   FROM local_text_transaction_events
                   WHERE operation_id = ? ORDER BY sequence DESC LIMIT 1""",
                (operation_id,),
            ).fetchone()
            sequence = 0 if row is None else int(row[0]) + 1
            previous_phase = None if row is None else str(row[1])
            previous = None if row is None else str(row[2])
            if phase not in _ALLOWED_TRANSITIONS.get(previous_phase, frozenset()):
                raise ValueError("local_text_transaction_phase_transition_invalid")
            fingerprint = self._event_fingerprint(
                operation_id=operation_id,
                sequence=sequence,
                phase=phase,
                metadata=metadata,
                recorded_at=recorded_at,
                previous_event_fingerprint=previous,
            )
            metadata_json = json.dumps(
                metadata,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            connection.execute(
                """INSERT INTO local_text_transaction_events
                   (operation_id, sequence, phase, metadata_json, recorded_at,
                    previous_event_fingerprint, event_fingerprint)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    sequence,
                    phase,
                    metadata_json,
                    recorded_at,
                    previous,
                    fingerprint,
                ),
            )
            connection.commit()
        return _JournalEvent(
            operation_id,
            sequence,
            phase,
            metadata,
            recorded_at,
            previous,
            fingerprint,
        )

    @staticmethod
    def _operation_key(operation_id: str) -> str:
        return sha256(operation_id.encode("utf-8")).hexdigest()

    def _state_names(self, operation_id: str) -> tuple[str, str]:
        key = self._operation_key(operation_id)
        return f"{key}.desired", f"{key}.backup"

    def _root_alias_from_resource_ref(self, resource_ref: str) -> str:
        matching_aliases: list[str] = []
        for alias in self._transaction_roots:
            try:
                require_valid_local_text_resource_ref(resource_ref, alias)
            except ValueError:
                continue
            matching_aliases.append(alias)
        if len(matching_aliases) != 1:
            raise ValueError("local_text_transaction_resource_ref_invalid")
        return matching_aliases[0]

    @contextmanager
    def _resource_lock(self, alias: str, resource_ref: str) -> Iterator[None]:
        lock_key = f"{alias}:{resource_ref}"
        with self._thread_locks_guard:
            thread_lock = self._thread_locks.setdefault(lock_key, threading.Lock())
        with thread_lock:
            lock_name = sha256(lock_key.encode("utf-8")).hexdigest() + ".lock"
            flags = os.O_RDWR | os.O_CREAT | int(getattr(os, "O_NOFOLLOW", 0))
            with self._open_state_directory(alias) as state_fd:
                if state_fd is None:
                    descriptor = os.open(self._transaction_roots[alias] / lock_name, flags, 0o600)
                else:
                    descriptor = os.open(lock_name, flags, 0o600, dir_fd=state_fd)
                try:
                    observed = os.fstat(descriptor)
                    if (
                        not stat.S_ISREG(observed.st_mode)
                        or observed.st_nlink != 1
                        or (os.name != "nt" and stat.S_IMODE(observed.st_mode) != 0o600)
                    ):
                        raise ValueError("local_text_transaction_lock_not_safe")
                    if observed.st_size == 0:
                        os.write(descriptor, b"\0")
                        os.fsync(descriptor)
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    if os.name == "nt":
                        msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
                    else:
                        fcntl.flock(descriptor, fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        os.lseek(descriptor, 0, os.SEEK_SET)
                        if os.name == "nt":
                            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    @staticmethod
    def _require_operation_id(operation_id: str) -> None:
        if _ID_PATTERN.fullmatch(operation_id) is None:
            raise ValueError("local_text_transaction_operation_id_invalid")

    @staticmethod
    def _require_execution_binding(binding: LocalTextExecutionGrantBinding) -> None:
        if (
            _ID_PATTERN.fullmatch(binding.execution_grant_id) is None
            or _ID_PATTERN.fullmatch(binding.confirmation_receipt_id) is None
            or any(
                _SHA256_PATTERN.fullmatch(value) is None
                for value in (
                    binding.execution_grant_fingerprint,
                    binding.action_fingerprint,
                    binding.execution_request_fingerprint,
                    binding.intent_fingerprint,
                )
            )
        ):
            raise ValueError("local_text_execution_grant_binding_invalid")

    def _validate_request(self, request: LocalTextMutationRequest) -> bytes:
        self._require_operation_id(request.operation_id)
        self._require_execution_binding(request.execution_binding)
        require_valid_local_text_file_preflight(request.preflight)
        if request.preflight.change_status == "no_change":
            raise ValueError("local_text_transaction_no_change_not_executable")
        if request.preflight.root_alias not in self._transaction_roots:
            raise ValueError("local_text_transaction_root_alias_unknown")
        if request.preflight.relative_path.split("/", 1)[0] == ".jarvis-transactions":
            raise ValueError("local_text_transaction_reserved_path")
        try:
            desired = request.desired_text.encode("utf-8", errors="strict")
        except UnicodeError:
            raise ValueError("local_text_transaction_desired_encoding_invalid") from None
        if _digest_bytes(desired) != request.preflight.desired_content_sha256:
            raise ValueError("local_text_transaction_desired_hash_mismatch")
        return desired

    @staticmethod
    def _staging_authorization_request(
        request: LocalTextMutationRequest,
    ) -> LocalTextStagingAuthorizationRequest:
        preflight = request.preflight
        return LocalTextStagingAuthorizationRequest(
            purpose="execute",
            operation_id=request.operation_id,
            operation=preflight.operation,
            resource_ref=preflight.resource_ref,
            subject_ref=preflight.subject_ref,
            preflight_fingerprint=preflight.preflight_fingerprint,
            before_content_sha256=preflight.before_content_sha256,
            desired_content_sha256=preflight.desired_content_sha256,
            root_config_fingerprint=preflight.root_config_fingerprint,
            execution_binding=request.execution_binding,
        )

    @staticmethod
    def _execution_staging_request_from_metadata(
        metadata: dict[str, object],
        operation_id: str,
    ) -> LocalTextStagingAuthorizationRequest:
        binding = LocalTextExecutionGrantBinding(
            execution_grant_id=str(metadata["requested_execution_grant_id"]),
            execution_grant_fingerprint=str(metadata["execution_grant_fingerprint"]),
            action_fingerprint=str(metadata["execution_action_fingerprint"]),
            execution_request_fingerprint=str(metadata["execution_request_fingerprint"]),
            intent_fingerprint=str(metadata["execution_intent_fingerprint"]),
            confirmation_receipt_id=str(metadata["confirmation_receipt_id"]),
        )
        return LocalTextStagingAuthorizationRequest(
            purpose="execute",
            operation_id=operation_id,
            operation=str(metadata["operation"]),
            resource_ref=str(metadata["resource_ref"]),
            subject_ref=str(metadata["subject_ref"]),
            preflight_fingerprint=str(metadata["preflight_fingerprint"]),
            before_content_sha256=str(metadata["before_content_sha256"]),
            desired_content_sha256=str(metadata["desired_content_sha256"]),
            root_config_fingerprint=str(metadata["root_config_fingerprint"]),
            execution_binding=binding,
        )

    def _require_staging_authorization(
        self, request: LocalTextStagingAuthorizationRequest, current: datetime
    ) -> None:
        del current
        try:
            verified = self._staging_authorization_verifier(request, self._trusted_now())
        except Exception:
            raise ValueError("local_text_staging_authorization_verification_failed") from None
        if verified is not True:
            raise ValueError("local_text_staging_authorization_not_verified")

    def _require_fresh_claim_at_effect_start(
        self,
        context: LocalTextExecutionAuthorizationContext,
        current: datetime,
    ) -> None:
        try:
            verified = self._effect_start_claim_verifier(context, current)
        except Exception:
            raise ValueError("local_text_effect_start_claim_verification_failed") from None
        if verified is not True:
            raise ValueError("local_text_effect_start_claim_not_verified")

    def _base_metadata(self, request: LocalTextMutationRequest) -> dict[str, object]:
        preflight = request.preflight
        desired_name, backup_name = self._state_names(request.operation_id)
        binding = request.execution_binding
        return {
            "action_kind": "execute_external_action",
            "operation": preflight.operation,
            "resource_ref": preflight.resource_ref,
            "relative_path": preflight.relative_path,
            "root_alias": preflight.root_alias,
            "subject_ref": preflight.subject_ref,
            "preflight_fingerprint": preflight.preflight_fingerprint,
            "preflight_grant_id": preflight.grant_id,
            "before_content_sha256": preflight.before_content_sha256,
            "desired_content_sha256": preflight.desired_content_sha256,
            "root_config_fingerprint": preflight.root_config_fingerprint,
            "filesystem_snapshot_fingerprint": (preflight.filesystem_snapshot_fingerprint),
            "transaction_policy_version": LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
            "transaction_backend_version": LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
            "desired_state_name": desired_name,
            "backup_state_name": backup_name if preflight.operation == "replace_text" else None,
            "requested_execution_grant_id": binding.execution_grant_id,
            "execution_grant_fingerprint": binding.execution_grant_fingerprint,
            "execution_action_fingerprint": binding.action_fingerprint,
            "execution_request_fingerprint": binding.execution_request_fingerprint,
            "execution_intent_fingerprint": binding.intent_fingerprint,
            "confirmation_receipt_id": binding.confirmation_receipt_id,
        }

    @staticmethod
    def _require_retry_binding(
        metadata: dict[str, object], request: LocalTextMutationRequest
    ) -> None:
        preflight = request.preflight
        expected = (
            preflight.operation,
            preflight.resource_ref,
            preflight.relative_path,
            preflight.root_alias,
            preflight.subject_ref,
            preflight.preflight_fingerprint,
            preflight.before_content_sha256,
            preflight.desired_content_sha256,
            preflight.root_config_fingerprint,
            preflight.filesystem_snapshot_fingerprint,
            request.execution_binding.execution_grant_id,
            request.execution_binding.execution_grant_fingerprint,
            request.execution_binding.action_fingerprint,
            request.execution_binding.execution_request_fingerprint,
            request.execution_binding.intent_fingerprint,
            request.execution_binding.confirmation_receipt_id,
        )
        observed = tuple(
            metadata[key]
            for key in (
                "operation",
                "resource_ref",
                "relative_path",
                "root_alias",
                "subject_ref",
                "preflight_fingerprint",
                "before_content_sha256",
                "desired_content_sha256",
                "root_config_fingerprint",
                "filesystem_snapshot_fingerprint",
                "requested_execution_grant_id",
                "execution_grant_fingerprint",
                "execution_action_fingerprint",
                "execution_request_fingerprint",
                "execution_intent_fingerprint",
                "confirmation_receipt_id",
            )
        )
        if observed != expected:
            raise ValueError("local_text_transaction_retry_binding_mismatch")

    @staticmethod
    def _require_transaction_versions(metadata: dict[str, object]) -> None:
        if (
            metadata.get("transaction_policy_version") != LOCAL_TEXT_TRANSACTION_POLICY_VERSION
            or metadata.get("transaction_backend_version") != LOCAL_TEXT_TRANSACTION_BACKEND_VERSION
        ):
            raise ValueError("local_text_transaction_version_mismatch")

    def _authority_request(
        self,
        metadata: dict[str, object],
        operation_id: str,
        *,
        purpose: str,
        mutation_receipt_fingerprint: str | None = None,
        execution_binding: LocalTextExecutionGrantBinding | None = None,
        logical_operation: str | None = None,
        journal_reservation_fingerprint: str | None = None,
    ) -> LocalTextExecutionAuthorizationRequest:
        if execution_binding is None:
            execution_binding = LocalTextExecutionGrantBinding(
                execution_grant_id=str(metadata["requested_execution_grant_id"]),
                execution_grant_fingerprint=str(metadata["execution_grant_fingerprint"]),
                action_fingerprint=str(metadata["execution_action_fingerprint"]),
                execution_request_fingerprint=str(metadata["execution_request_fingerprint"]),
                intent_fingerprint=str(metadata["execution_intent_fingerprint"]),
                confirmation_receipt_id=str(metadata["confirmation_receipt_id"]),
            )
        rollback = purpose == "rollback"
        return LocalTextExecutionAuthorizationRequest(
            purpose=purpose,
            operation_id=operation_id,
            action_kind=str(metadata["action_kind"]),
            operation=logical_operation or str(metadata["operation"]),
            resource_ref=str(metadata["resource_ref"]),
            subject_ref=str(metadata["subject_ref"]),
            preflight_fingerprint=str(metadata["preflight_fingerprint"]),
            before_content_sha256=str(
                metadata["desired_content_sha256"]
                if rollback
                else metadata["before_content_sha256"]
            ),
            desired_content_sha256=(
                _EMPTY_SHA256
                if rollback and metadata["operation"] == "create_text"
                else str(
                    metadata["before_content_sha256"]
                    if rollback
                    else metadata["desired_content_sha256"]
                )
            ),
            root_config_fingerprint=str(metadata["root_config_fingerprint"]),
            transaction_policy_version=LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
            execution_grant_id=execution_binding.execution_grant_id,
            execution_grant_fingerprint=execution_binding.execution_grant_fingerprint,
            action_fingerprint=execution_binding.action_fingerprint,
            execution_request_fingerprint=execution_binding.execution_request_fingerprint,
            intent_fingerprint=execution_binding.intent_fingerprint,
            confirmation_receipt_id=execution_binding.confirmation_receipt_id,
            journal_reservation_fingerprint=(
                journal_reservation_fingerprint or str(metadata["journal_reservation_fingerprint"])
            ),
            mutation_receipt_fingerprint=mutation_receipt_fingerprint,
        )

    def _claim(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        current: datetime,
    ) -> LocalTextClaimedAuthorizationLease:
        del current
        lease = self._authorization_lease_provider(request, self._trusted_now())
        context = lease.context
        expected = (
            request.purpose,
            request.operation_id,
            request.action_kind,
            request.operation,
            request.resource_ref,
            request.subject_ref,
            request.preflight_fingerprint,
            request.before_content_sha256,
            request.desired_content_sha256,
            request.root_config_fingerprint,
            request.execution_grant_id,
            request.execution_grant_fingerprint,
            request.action_fingerprint,
            request.execution_request_fingerprint,
            request.intent_fingerprint,
            request.confirmation_receipt_id,
            request.journal_reservation_fingerprint,
            request.mutation_receipt_fingerprint,
        )
        observed = (
            context.purpose,
            context.operation_id,
            context.action_kind,
            context.operation,
            context.resource_ref,
            context.subject_ref,
            context.preflight_fingerprint,
            context.before_content_sha256,
            context.desired_content_sha256,
            context.root_config_fingerprint,
            context.execution_grant_id,
            context.execution_grant_fingerprint,
            context.action_fingerprint,
            context.execution_request_fingerprint,
            context.intent_fingerprint,
            context.confirmation_receipt_id,
            context.journal_reservation_fingerprint,
            context.mutation_receipt_fingerprint,
        )
        if (
            observed != expected
            or not context.claimed
            or not context.single_use
            or not context.execution_allowed
            or context.prepare_grant_reusable_for_execution
            or _ID_PATTERN.fullmatch(context.execution_grant_id) is None
            or _ID_PATTERN.fullmatch(context.execution_claim_id) is None
            or _SHA256_PATTERN.fullmatch(context.authority_fingerprint) is None
            or not compare_digest(
                context.authority_fingerprint,
                build_execution_authority_fingerprint(context),
            )
        ):
            raise ValueError("local_text_execution_claim_binding_invalid")
        claimed_at = _parse_time(context.claimed_at, "local_text_execution_claim_time_invalid")
        expires_at = _parse_time(context.expires_at, "local_text_execution_expiry_invalid")
        instant = self._trusted_now()
        if claimed_at > instant or instant >= expires_at:
            raise ValueError("local_text_execution_claim_inactive")
        return lease

    def _lookup_historical_context(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        current: datetime,
    ) -> LocalTextExecutionAuthorizationContext | None:
        context = self._historical_claim_lookup(request, current)
        if context is None:
            return None
        expected = (
            request.purpose,
            request.operation_id,
            request.action_kind,
            request.operation,
            request.resource_ref,
            request.subject_ref,
            request.preflight_fingerprint,
            request.before_content_sha256,
            request.desired_content_sha256,
            request.root_config_fingerprint,
            request.execution_grant_id,
            request.execution_grant_fingerprint,
            request.action_fingerprint,
            request.execution_request_fingerprint,
            request.intent_fingerprint,
            request.confirmation_receipt_id,
            request.journal_reservation_fingerprint,
            request.mutation_receipt_fingerprint,
        )
        observed = (
            context.purpose,
            context.operation_id,
            context.action_kind,
            context.operation,
            context.resource_ref,
            context.subject_ref,
            context.preflight_fingerprint,
            context.before_content_sha256,
            context.desired_content_sha256,
            context.root_config_fingerprint,
            context.execution_grant_id,
            context.execution_grant_fingerprint,
            context.action_fingerprint,
            context.execution_request_fingerprint,
            context.intent_fingerprint,
            context.confirmation_receipt_id,
            context.journal_reservation_fingerprint,
            context.mutation_receipt_fingerprint,
        )
        if (
            observed != expected
            or not context.claimed
            or not context.single_use
            or not context.execution_allowed
            or context.prepare_grant_reusable_for_execution
            or not compare_digest(
                context.authority_fingerprint,
                build_execution_authority_fingerprint(context),
            )
        ):
            raise ValueError("local_text_historical_claim_binding_invalid")
        if _parse_time(
            context.claimed_at, "local_text_execution_claim_time_invalid"
        ) >= _parse_time(context.expires_at, "local_text_execution_expiry_invalid"):
            raise ValueError("local_text_historical_claim_window_invalid")
        try:
            verified = self._historical_claim_verifier(context, current)
        except Exception:
            raise ValueError("local_text_historical_claim_verification_failed") from None
        if verified is not True:
            raise ValueError("local_text_historical_claim_not_verified")
        return context

    @contextmanager
    def _open_pinned_posix(
        self,
        metadata: dict[str, object],
        *,
        allow_applied: bool,
    ) -> Iterator[_PinnedPosixTarget]:
        if os.name == "nt" or not getattr(os, "O_NOFOLLOW", 0) or not getattr(os, "O_DIRECTORY", 0):
            raise ValueError("local_text_transaction_backend_not_handle_safe")
        alias = str(metadata["root_alias"])
        self._require_root_anchors_current(alias)
        if self._preflight_adapter.root_config_fingerprint() != metadata["root_config_fingerprint"]:
            raise ValueError("local_text_transaction_root_config_changed")
        root = getattr(self._preflight_adapter, "_roots")[alias]
        segments = str(metadata["relative_path"]).split("/")
        opened: list[int] = []
        pinned: _PinnedPosixTarget | None = None
        try:
            root_fd = os.open(root, _DIRECTORY_FLAGS)
            opened.append(root_fd)
            root_observed = os.fstat(root_fd)
            _require_safe_owned_directory(root_observed)
            root_device = int(root_observed.st_dev)
            parent_fd = root_fd
            for segment in segments[:-1]:
                next_fd = os.open(segment, _DIRECTORY_FLAGS, dir_fd=parent_fd)
                opened.append(next_fd)
                next_observed = os.fstat(next_fd)
                _require_safe_owned_directory(next_observed)
                _require_same_device(next_observed, root_device)
                parent_fd = next_fd
            directory_fds = tuple(opened)
            transaction_fd = os.open(".jarvis-transactions", _DIRECTORY_FLAGS, dir_fd=root_fd)
            opened.append(transaction_fd)
            transaction_observed = os.fstat(transaction_fd)
            _require_safe_state_directory(transaction_observed)
            _require_same_device(transaction_observed, root_device)
            if (
                _directory_identity(transaction_observed)
                != self._transaction_root_identities[alias]
            ):
                raise ValueError("local_text_transaction_root_changed")
            target_name = segments[-1]
            target_fd: int | None = None
            before_bytes = b""
            before_identity: dict[str, int] | None = None
            current_hash: str | None = None
            try:
                target_fd = os.open(target_name, _FILE_READ_FLAGS, dir_fd=parent_fd)
            except FileNotFoundError:
                if metadata["operation"] != "create_text":
                    raise ValueError(
                        "local_text_transaction_replace_precondition_missing"
                    ) from None
                parent_before = _node_identity(os.fstat(parent_fd))
                names = [entry.name for entry in os.scandir(parent_fd)]
                if _node_identity(os.fstat(parent_fd)) != parent_before:
                    raise ValueError("local_text_transaction_parent_changed")
                if any(name.casefold() == target_name.casefold() for name in names):
                    raise ValueError("local_text_transaction_create_casefold_collision")
            else:
                opened.append(target_fd)
                observed = os.fstat(target_fd)
                _require_same_device(observed, root_device)
                if (
                    not stat.S_ISREG(observed.st_mode)
                    or _is_reparse_or_link(observed)
                    or observed.st_nlink != 1
                    or (
                        os.name != "nt"
                        and (
                            observed.st_uid != os.geteuid()
                            or stat.S_IMODE(observed.st_mode) & 0o022
                        )
                    )
                ):
                    raise ValueError("local_text_transaction_target_not_safe")
                before_identity = _node_identity(observed)
                before_bytes = self._read_fd_bounded(target_fd)
                if _node_identity(os.fstat(target_fd)) != before_identity:
                    raise ValueError("local_text_transaction_target_changed_during_read")
                current_hash = _digest_bytes(before_bytes)
                expected_before = str(metadata["before_content_sha256"])
                expected_desired = str(metadata["desired_content_sha256"])
                if metadata["operation"] == "create_text":
                    if not allow_applied or current_hash != expected_desired:
                        raise ValueError("local_text_transaction_create_precondition_stale")
                elif current_hash != expected_before and (
                    not allow_applied or current_hash != expected_desired
                ):
                    raise ValueError("local_text_transaction_precondition_hash_mismatch")
            pinned = _PinnedPosixTarget(
                root,
                tuple(segments[:-1]),
                root_fd,
                parent_fd,
                transaction_fd,
                target_fd,
                directory_fds,
                target_name,
                before_bytes,
                before_identity,
                current_hash,
            )
            opened.clear()
            yield pinned
        finally:
            if pinned is not None:
                pinned.close()
            else:
                for descriptor in set(opened):
                    os.close(descriptor)

    def _read_fd_bounded(self, descriptor: int) -> bytes:
        observed = os.fstat(descriptor)
        max_bytes = int(getattr(self._preflight_adapter, "_max_bytes"))
        if observed.st_size > max_bytes:
            raise ValueError("local_text_transaction_content_too_large")
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > max_bytes:
            raise ValueError("local_text_transaction_content_too_large")
        return content

    def _write_state_file(
        self,
        pinned: _PinnedPosixTarget,
        name: str,
        content: bytes,
        expected_hash: str,
        *,
        partial_seam: bool,
    ) -> dict[str, int]:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_NOFOLLOW", 0))
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=pinned.transaction_fd)
        except FileExistsError:
            try:
                existing = self._read_state_file(pinned.transaction_fd, name, expected_hash)
            except ValueError:
                self._state_file_identity(pinned.transaction_fd, name)
                os.unlink(name, dir_fd=pinned.transaction_fd)
                os.fsync(pinned.transaction_fd)
                return self._write_state_file(
                    pinned,
                    name,
                    content,
                    expected_hash,
                    partial_seam=partial_seam,
                )
            if existing != content:
                raise ValueError("local_text_transaction_state_file_conflict")
            return self._state_file_identity(pinned.transaction_fd, name)
        try:
            offset = 0
            seam_fired = False
            while offset < len(content):
                written = os.write(descriptor, content[offset:])
                if written <= 0:
                    raise OSError("local_text_transaction_short_write")
                offset += written
                if partial_seam and not seam_fired:
                    seam_fired = True
                    self._inject("after_partial_stage")
            observed = os.fstat(descriptor)
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                raise ValueError("local_text_transaction_state_file_not_safe")
            os.fsync(descriptor)
        except Exception:
            os.close(descriptor)
            try:
                os.unlink(name, dir_fd=pinned.transaction_fd)
                os.fsync(pinned.transaction_fd)
            except OSError:
                pass
            raise
        else:
            os.close(descriptor)
        os.fsync(pinned.transaction_fd)
        if self._read_state_file(pinned.transaction_fd, name, expected_hash) != content:
            raise ValueError("local_text_transaction_state_file_verification_failed")
        return self._state_file_identity(pinned.transaction_fd, name)

    @staticmethod
    def _state_file_identity(transaction_fd: int, name: str) -> dict[str, int]:
        observed = os.stat(name, dir_fd=transaction_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(observed.st_mode)
            or _is_reparse_or_link(observed)
            or observed.st_nlink != 1
            or (os.name != "nt" and stat.S_IMODE(observed.st_mode) != 0o600)
        ):
            raise ValueError("local_text_transaction_state_file_not_private")
        return _node_identity(observed)

    def _read_state_file(self, transaction_fd: int, name: str, expected_hash: str) -> bytes:
        descriptor = os.open(name, _FILE_READ_FLAGS, dir_fd=transaction_fd)
        try:
            observed = os.fstat(descriptor)
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                raise ValueError("local_text_transaction_state_file_not_safe")
            content = self._read_fd_bounded(descriptor)
            if _digest_bytes(content) != expected_hash:
                raise ValueError("local_text_transaction_state_file_hash_mismatch")
            return content
        finally:
            os.close(descriptor)

    def _revalidate_pinned_before(
        self, pinned: _PinnedPosixTarget, metadata: dict[str, object]
    ) -> None:
        self._require_named_chain_still_pinned(pinned)
        _require_safe_owned_directory(os.fstat(pinned.root_fd))
        _require_safe_owned_directory(os.fstat(pinned.parent_fd))
        _require_safe_owned_directory(os.fstat(pinned.transaction_fd))
        if metadata["operation"] == "create_text":
            try:
                os.stat(pinned.target_name, dir_fd=pinned.parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            raise ValueError("local_text_transaction_create_precondition_stale")
        if pinned.target_fd is None or pinned.before_identity is None:
            raise ValueError("local_text_transaction_target_handle_missing")
        if _node_identity(os.fstat(pinned.target_fd)) != pinned.before_identity:
            raise ValueError("local_text_transaction_target_changed")
        path_observed = os.stat(pinned.target_name, dir_fd=pinned.parent_fd, follow_symlinks=False)
        if _node_identity(path_observed) != pinned.before_identity:
            raise ValueError("local_text_transaction_target_swapped")
        content = self._read_fd_bounded(pinned.target_fd)
        if _digest_bytes(content) != metadata["before_content_sha256"]:
            raise ValueError("local_text_transaction_precondition_hash_mismatch")

    @staticmethod
    def _require_named_chain_still_pinned(pinned: _PinnedPosixTarget) -> None:
        root_path_observed = os.stat(pinned.root_path, follow_symlinks=False)
        if _directory_identity(root_path_observed) != _directory_identity(os.fstat(pinned.root_fd)):
            raise ValueError("local_text_transaction_root_swapped")
        current_fd = os.dup(pinned.root_fd)
        try:
            for index, segment in enumerate(pinned.parent_segments, start=1):
                next_fd = os.open(segment, _DIRECTORY_FLAGS, dir_fd=current_fd)
                os.close(current_fd)
                current_fd = next_fd
                if _directory_identity(os.fstat(current_fd)) != _directory_identity(
                    os.fstat(pinned.directory_fds[index])
                ):
                    raise ValueError("local_text_transaction_parent_chain_detached")
            if _directory_identity(os.fstat(current_fd)) != _directory_identity(
                os.fstat(pinned.parent_fd)
            ):
                raise ValueError("local_text_transaction_parent_chain_detached")
        finally:
            os.close(current_fd)

    def _require_preflight_snapshot(
        self, pinned: _PinnedPosixTarget, metadata: dict[str, object]
    ) -> None:
        directories = [
            asdict(
                _NodeObservation.from_stat(
                    "root" if index == 0 else f"parent:{index}",
                    os.fstat(descriptor),
                )
            )
            for index, descriptor in enumerate(pinned.directory_fds)
        ]
        target = None
        if pinned.target_fd is not None:
            target = asdict(_NodeObservation.from_stat("target", os.fstat(pinned.target_fd)))
        payload = {
            "directories": directories,
            "target": target,
            "target_absent": pinned.target_fd is None,
        }
        if _canonical_digest(payload) != metadata["filesystem_snapshot_fingerprint"]:
            raise ValueError("local_text_transaction_filesystem_snapshot_changed")
        metadata["pre_effect_directories"] = directories
        metadata["pre_effect_target"] = target

    @staticmethod
    def _current_directory_observations(
        pinned: _PinnedPosixTarget,
    ) -> list[dict[str, object]]:
        return [
            asdict(
                _NodeObservation.from_stat(
                    "root" if index == 0 else f"parent:{index}",
                    os.fstat(descriptor),
                )
            )
            for index, descriptor in enumerate(pinned.directory_fds)
        ]

    @classmethod
    def _require_pre_effect_directories(
        cls, pinned: _PinnedPosixTarget, metadata: dict[str, object]
    ) -> None:
        observed = cls._current_directory_observations(pinned)
        if observed != metadata.get("pre_effect_directories"):
            raise ValueError("local_text_transaction_parent_chain_changed")

    @classmethod
    def _require_rollback_pre_effect_directories(
        cls,
        pinned: _PinnedPosixTarget,
        metadata: dict[str, object],
    ) -> None:
        observed = cls._current_directory_observations(pinned)
        if observed != metadata.get("rollback_pre_effect_directories"):
            raise ValueError("local_text_rollback_parent_chain_changed")

    @staticmethod
    def _require_stage_became_target(identity: dict[str, int], metadata: dict[str, object]) -> None:
        stage = metadata.get("desired_stage_identity")
        if not isinstance(stage, dict) or any(
            int(identity[key]) != int(stage[key]) for key in ("device", "inode", "mode", "size")
        ):
            raise ValueError("local_text_transaction_recovery_target_not_staged_file")

    def _stage(
        self,
        pinned: _PinnedPosixTarget,
        metadata: dict[str, object],
        desired: bytes,
        operation_id: str,
        alias: str,
        current: datetime,
        last_phase: str,
    ) -> str:
        desired_name = str(metadata["desired_state_name"])
        backup_name = str(metadata["backup_state_name"])
        phase = last_phase
        if phase == "reserved":
            desired_identity = self._write_state_file(
                pinned,
                desired_name,
                desired,
                str(metadata["desired_content_sha256"]),
                partial_seam=True,
            )
            metadata["desired_stage_identity"] = desired_identity
            self._append_event(
                alias=alias,
                operation_id=operation_id,
                phase="desired_durable",
                metadata=metadata,
                current=current,
            )
            self._inject("after_stage_durable")
            phase = "desired_durable"
        else:
            self._read_state_file(
                pinned.transaction_fd,
                desired_name,
                str(metadata["desired_content_sha256"]),
            )
            if self._state_file_identity(pinned.transaction_fd, desired_name) != metadata.get(
                "desired_stage_identity"
            ):
                raise ValueError("local_text_transaction_desired_stage_changed")
        if metadata["operation"] == "replace_text" and phase == "desired_durable":
            backup_identity = self._write_state_file(
                pinned,
                backup_name,
                pinned.before_bytes,
                str(metadata["before_content_sha256"]),
                partial_seam=False,
            )
            metadata["backup_stage_identity"] = backup_identity
            self._append_event(
                alias=alias,
                operation_id=operation_id,
                phase="backup_durable",
                metadata=metadata,
                current=current,
            )
            self._inject("after_backup_durable")
            phase = "backup_durable"
        if phase in {"desired_durable", "backup_durable"}:
            self._append_event(
                alias=alias,
                operation_id=operation_id,
                phase="staged",
                metadata=metadata,
                current=current,
            )
            phase = "staged"
        return phase

    def _require_staged_state_files(
        self,
        pinned: _PinnedPosixTarget,
        metadata: dict[str, object],
    ) -> None:
        desired_name = str(metadata["desired_state_name"])
        self._read_state_file(
            pinned.transaction_fd,
            desired_name,
            str(metadata["desired_content_sha256"]),
        )
        if self._state_file_identity(pinned.transaction_fd, desired_name) != metadata.get(
            "desired_stage_identity"
        ):
            raise ValueError("local_text_transaction_desired_stage_changed")
        if metadata["operation"] != "replace_text":
            return
        backup_name = str(metadata["backup_state_name"])
        try:
            self._read_state_file(
                pinned.transaction_fd,
                backup_name,
                str(metadata["before_content_sha256"]),
            )
            observed_backup_identity = self._state_file_identity(pinned.transaction_fd, backup_name)
        except FileNotFoundError:
            raise ValueError("local_text_transaction_backup_stage_missing") from None
        if observed_backup_identity != metadata.get("backup_stage_identity"):
            raise ValueError("local_text_transaction_backup_stage_changed")

    def _claim_and_record(
        self,
        *,
        alias: str,
        operation_id: str,
        metadata: dict[str, object],
        current: datetime,
        purpose: str,
        mutation_receipt_fingerprint: str | None = None,
        execution_binding: LocalTextExecutionGrantBinding | None = None,
        authority_operation_id: str | None = None,
        logical_operation: str | None = None,
        journal_reservation_fingerprint: str | None = None,
    ) -> tuple[LocalTextClaimedAuthorizationLease, dict[str, object]]:
        request = self._authority_request(
            metadata,
            authority_operation_id or operation_id,
            purpose=purpose,
            mutation_receipt_fingerprint=mutation_receipt_fingerprint,
            execution_binding=execution_binding,
            logical_operation=logical_operation,
            journal_reservation_fingerprint=journal_reservation_fingerprint,
        )
        lease = self._claim(request, current)
        context = lease.context
        self._inject(f"after_{purpose}_claim_before_journal")
        claimed_metadata = self._metadata_with_claim(metadata, context, purpose=purpose)
        self._append_event(
            alias=alias,
            operation_id=operation_id,
            phase="claimed" if purpose == "execute" else "rollback_claimed",
            metadata=claimed_metadata,
            current=current,
        )
        return lease, claimed_metadata

    @staticmethod
    def _metadata_with_claim(
        metadata: dict[str, object],
        context: LocalTextExecutionAuthorizationContext,
        *,
        purpose: str,
    ) -> dict[str, object]:
        claimed_metadata = dict(metadata)
        if purpose == "execute":
            claimed_metadata.update(
                {
                    "execution_grant_id": context.execution_grant_id,
                    "execution_claim_id": context.execution_claim_id,
                    "authority_fingerprint": context.authority_fingerprint,
                    "authority_claimed_at": context.claimed_at,
                    "authority_expires_at": context.expires_at,
                }
            )
        else:
            claimed_metadata.update(
                {
                    "rollback_grant_id": context.execution_grant_id,
                    "rollback_claim_id": context.execution_claim_id,
                    "rollback_grant_fingerprint": context.execution_grant_fingerprint,
                    "rollback_action_fingerprint": context.action_fingerprint,
                    "rollback_execution_request_fingerprint": (
                        context.execution_request_fingerprint
                    ),
                    "rollback_intent_fingerprint": context.intent_fingerprint,
                    "rollback_confirmation_receipt_id": (context.confirmation_receipt_id),
                    "rollback_authority_fingerprint": context.authority_fingerprint,
                    "rollback_authority_claimed_at": context.claimed_at,
                    "rollback_authority_expires_at": context.expires_at,
                    "mutation_receipt_fingerprint": context.mutation_receipt_fingerprint,
                }
            )
        return claimed_metadata

    @staticmethod
    def _historical_context(
        metadata: dict[str, object], operation_id: str, *, purpose: str = "execute"
    ) -> LocalTextExecutionAuthorizationContext:
        rollback = purpose == "rollback"
        return LocalTextExecutionAuthorizationContext(
            purpose=purpose,
            operation_id=(str(metadata["rollback_operation_id"]) if rollback else operation_id),
            execution_grant_id=str(
                metadata["rollback_grant_id" if rollback else "execution_grant_id"]
            ),
            execution_claim_id=str(
                metadata["rollback_claim_id" if rollback else "execution_claim_id"]
            ),
            action_kind=str(metadata["action_kind"]),
            operation=(
                str(metadata["rollback_operation"]) if rollback else str(metadata["operation"])
            ),
            resource_ref=str(metadata["resource_ref"]),
            subject_ref=str(metadata["subject_ref"]),
            preflight_fingerprint=str(metadata["preflight_fingerprint"]),
            before_content_sha256=str(
                metadata["desired_content_sha256"]
                if rollback
                else metadata["before_content_sha256"]
            ),
            desired_content_sha256=(
                _EMPTY_SHA256
                if rollback and metadata["operation"] == "create_text"
                else str(
                    metadata["before_content_sha256"]
                    if rollback
                    else metadata["desired_content_sha256"]
                )
            ),
            root_config_fingerprint=str(metadata["root_config_fingerprint"]),
            claimed_at=str(
                metadata["rollback_authority_claimed_at" if rollback else "authority_claimed_at"]
            ),
            expires_at=str(
                metadata["rollback_authority_expires_at" if rollback else "authority_expires_at"]
            ),
            authority_fingerprint=str(
                metadata["rollback_authority_fingerprint" if rollback else "authority_fingerprint"]
            ),
            execution_grant_fingerprint=str(
                metadata[
                    "rollback_grant_fingerprint" if rollback else "execution_grant_fingerprint"
                ]
            ),
            action_fingerprint=str(
                metadata[
                    "rollback_action_fingerprint" if rollback else "execution_action_fingerprint"
                ]
            ),
            execution_request_fingerprint=str(
                metadata[
                    "rollback_execution_request_fingerprint"
                    if rollback
                    else "execution_request_fingerprint"
                ]
            ),
            intent_fingerprint=str(
                metadata[
                    "rollback_intent_fingerprint" if rollback else "execution_intent_fingerprint"
                ]
            ),
            confirmation_receipt_id=str(
                metadata[
                    "rollback_confirmation_receipt_id" if rollback else "confirmation_receipt_id"
                ]
            ),
            journal_reservation_fingerprint=str(
                metadata[
                    "rollback_journal_reservation_fingerprint"
                    if rollback
                    else "journal_reservation_fingerprint"
                ]
            ),
            mutation_receipt_fingerprint=(
                str(metadata["mutation_receipt_fingerprint"]) if rollback else None
            ),
        )

    def _require_historical_claim(
        self,
        metadata: dict[str, object],
        operation_id: str,
        current: datetime,
        purpose: str = "execute",
    ) -> None:
        context = self._historical_context(metadata, operation_id, purpose=purpose)
        if not compare_digest(
            context.authority_fingerprint,
            build_execution_authority_fingerprint(context),
        ):
            raise ValueError("local_text_historical_claim_fingerprint_invalid")
        try:
            verified = self._historical_claim_verifier(context, current)
        except Exception:
            raise ValueError("local_text_historical_claim_verification_failed") from None
        if verified is not True:
            raise ValueError("local_text_historical_claim_not_verified")

    def _atomic_commit_posix(self, pinned: _PinnedPosixTarget, metadata: dict[str, object]) -> None:
        desired_name = str(metadata["desired_state_name"])
        if metadata["operation"] == "create_text":
            self._rename_noreplace_linux(
                pinned.transaction_fd,
                desired_name,
                pinned.parent_fd,
                pinned.target_name,
            )
        else:
            os.replace(
                desired_name,
                pinned.target_name,
                src_dir_fd=pinned.transaction_fd,
                dst_dir_fd=pinned.parent_fd,
            )

    @staticmethod
    def _rename_noreplace_linux(
        source_fd: int,
        source_name: str,
        target_fd: int,
        target_name: str,
    ) -> None:
        if sys.platform != "linux":
            raise ValueError("local_text_transaction_create_noreplace_backend_missing")
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is not None:
            renameat2.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            renameat2.restype = ctypes.c_int
            result = renameat2(
                source_fd,
                os.fsencode(source_name),
                target_fd,
                os.fsencode(target_name),
                1,
            )
        else:
            syscall_number = _RENAMEAT2_SYSCALLS.get(platform.machine().casefold())
            syscall = getattr(libc, "syscall", None)
            if syscall_number is None or syscall is None:
                raise ValueError("local_text_transaction_create_noreplace_backend_missing")
            syscall.restype = ctypes.c_long
            result = syscall(
                ctypes.c_long(syscall_number),
                ctypes.c_int(source_fd),
                ctypes.c_char_p(os.fsencode(source_name)),
                ctypes.c_int(target_fd),
                ctypes.c_char_p(os.fsencode(target_name)),
                ctypes.c_uint(1),
            )
        if result != 0:
            error = ctypes.get_errno()
            if error == errno.EEXIST:
                raise FileExistsError(target_name)
            raise OSError(error, os.strerror(error), target_name)

    def _reconcile_applied(
        self, pinned: _PinnedPosixTarget, metadata: dict[str, object]
    ) -> dict[str, int] | None:
        self._require_named_chain_still_pinned(pinned)
        try:
            descriptor = os.open(pinned.target_name, _FILE_READ_FLAGS, dir_fd=pinned.parent_fd)
        except FileNotFoundError:
            return None
        try:
            observed = os.fstat(descriptor)
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
                raise ValueError("local_text_transaction_applied_target_not_safe")
            content = self._read_fd_bounded(descriptor)
            after = os.fstat(descriptor)
            if _node_identity(after) != _node_identity(observed):
                raise ValueError("local_text_transaction_applied_target_unstable")
            if _digest_bytes(content) != metadata["desired_content_sha256"]:
                return None
            return _node_identity(after)
        finally:
            os.close(descriptor)

    def _apply_and_record(
        self,
        *,
        pinned: _PinnedPosixTarget,
        alias: str,
        operation_id: str,
        metadata: dict[str, object],
        current: datetime,
        already_renamed: bool,
        fresh_claim_context: LocalTextExecutionAuthorizationContext | None,
    ) -> _JournalEvent:
        if not already_renamed:
            self._revalidate_pinned_before(pinned, metadata)
            self._require_pre_effect_directories(pinned, metadata)
            if fresh_claim_context is not None:
                self._require_fresh_claim_at_effect_start(fresh_claim_context, self._trusted_now())
            self._atomic_commit_posix(pinned, metadata)
            self._inject("after_rename_before_directory_flush")
            self._append_event(
                alias=alias,
                operation_id=operation_id,
                phase="renamed",
                metadata=metadata,
                current=current,
            )
        identity = self._reconcile_applied(pinned, metadata)
        if identity is None:
            raise ValueError("local_text_transaction_commit_verification_failed")
        self._require_stage_became_target(identity, metadata)
        os.fsync(pinned.parent_fd)
        os.fsync(pinned.transaction_fd)
        os.fsync(pinned.root_fd)
        self._inject("after_directory_flush_before_applied")
        applied_metadata = dict(metadata)
        applied_metadata["post_write_identity"] = identity
        return self._append_event(
            alias=alias,
            operation_id=operation_id,
            phase="applied",
            metadata=applied_metadata,
            current=current,
        )

    def _receipt_from_applied(self, event: _JournalEvent) -> LocalTextMutationReceipt:
        metadata = event.metadata
        receipt = LocalTextMutationReceipt(
            operation_id=event.operation_id,
            execution_grant_id=str(metadata["execution_grant_id"]),
            execution_claim_id=str(metadata["execution_claim_id"]),
            operation=str(metadata["operation"]),
            resource_ref=str(metadata["resource_ref"]),
            subject_ref=str(metadata["subject_ref"]),
            preflight_fingerprint=str(metadata["preflight_fingerprint"]),
            before_content_sha256=str(metadata["before_content_sha256"]),
            desired_content_sha256=str(metadata["desired_content_sha256"]),
            root_config_fingerprint=str(metadata["root_config_fingerprint"]),
            applied_event_fingerprint=event.event_fingerprint,
            committed_at=event.recorded_at,
            mutation_status="applied",
            receipt_fingerprint="0" * 64,
        )
        return replace(receipt, receipt_fingerprint=build_mutation_receipt_fingerprint(receipt))

    def _seal_receipt(
        self,
        *,
        alias: str,
        applied: _JournalEvent,
        current: datetime,
    ) -> LocalTextMutationReceipt:
        receipt = self._receipt_from_applied(applied)
        metadata = dict(applied.metadata)
        metadata.update(
            {
                "applied_event_fingerprint": applied.event_fingerprint,
                "receipt_fingerprint": receipt.receipt_fingerprint,
            }
        )
        self._append_event(
            alias=alias,
            operation_id=applied.operation_id,
            phase="receipt",
            metadata=metadata,
            current=current,
        )
        return receipt

    @staticmethod
    def _find_event(events: list[_JournalEvent], phase: str) -> _JournalEvent:
        for event in reversed(events):
            if event.phase == phase:
                return event
        raise ValueError("local_text_transaction_journal_phase_missing")

    def execute(
        self,
        request: LocalTextMutationRequest,
    ) -> LocalTextMutationReceipt:
        result = self._execute(
            request,
            plan=None,
            receipt_recorder=None,
            canonical_commit=None,
        )
        if not isinstance(result, LocalTextMutationReceipt):
            raise ValueError("local_text_transaction_result_invalid")
        return result

    def execute_and_commit_apply(
        self,
        plan: ArtifactPhysicalApplyPlanContract,
        request: LocalTextMutationRequest,
        *,
        receipt_recorder: MutationReceiptRecorder,
        canonical_commit: ApplyCanonicalCommit,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Execute and canonicalize one exact apply without releasing its lock."""

        self._require_canonical_commit_ports_configured()
        self._require_apply_plan_receipt_request_binding(plan=plan, request=request)
        if not callable(receipt_recorder) or not callable(canonical_commit):
            raise ValueError("local_text_canonical_apply_callbacks_required")
        result = self._execute(
            request,
            plan=plan,
            receipt_recorder=receipt_recorder,
            canonical_commit=canonical_commit,
        )
        if not isinstance(result, ArtifactPhysicalCanonicalCommitReceiptContract):
            raise ValueError("local_text_canonical_apply_result_invalid")
        return result

    def _execute(
        self,
        request: LocalTextMutationRequest,
        *,
        plan: ArtifactPhysicalApplyPlanContract | None,
        receipt_recorder: MutationReceiptRecorder | None,
        canonical_commit: ApplyCanonicalCommit | None,
    ) -> LocalTextMutationReceipt | ArtifactPhysicalCanonicalCommitReceiptContract:
        current = self._trusted_now()
        desired = self._validate_request(request)
        staging_request = self._staging_authorization_request(request)
        self._require_staging_authorization(staging_request, current)
        if os.name == "nt":
            raise ValueError("local_text_transaction_backend_not_handle_safe")
        if self._preflight_adapter.root_config_fingerprint() != (
            request.preflight.root_config_fingerprint
        ):
            raise ValueError("local_text_transaction_root_config_changed")
        alias = request.preflight.root_alias
        with self._resource_lock(alias, request.preflight.resource_ref):
            self._require_canonical_physical_binding(
                purpose="apply",
                operation_id=request.operation_id,
                mutation_operation_id=None,
                mutation_receipt_fingerprint=None,
                resource_ref=request.preflight.resource_ref,
                root_alias=alias,
                plan=plan,
            )
            events = self._load_events(alias, request.operation_id)
            if events:
                self._require_retry_binding(events[-1].metadata, request)
                if events[-1].phase in {"receipt", "cleaned"}:
                    receipt = self._receipt_from_applied(self._find_event(events, "applied"))
                    return self._commit_apply_locked_if_requested(
                        plan=plan,
                        root_alias=alias,
                        receipt=receipt,
                        receipt_recorder=receipt_recorder,
                        canonical_commit=canonical_commit,
                    )
                if events[-1].phase in {
                    "rollback_claimed",
                    "rollback_renamed",
                    "rolled_back",
                    "rollback_receipt",
                }:
                    raise ValueError("local_text_transaction_already_rolling_back")
            else:
                metadata = self._base_metadata(request)
                reservation = self._append_event(
                    alias=alias,
                    operation_id=request.operation_id,
                    phase="reserved",
                    metadata=metadata,
                    current=current,
                )
                metadata = dict(metadata)
                metadata["journal_reservation_fingerprint"] = reservation.event_fingerprint
                events = self._load_events(alias, request.operation_id)
                events[-1] = replace(events[-1], metadata=metadata)
            receipt = self._continue(
                alias=alias,
                operation_id=request.operation_id,
                desired=desired,
                events=events,
                current=current,
                allow_new_claim=True,
                staging_request=staging_request,
            )
            return self._commit_apply_locked_if_requested(
                plan=plan,
                root_alias=alias,
                receipt=receipt,
                receipt_recorder=receipt_recorder,
                canonical_commit=canonical_commit,
            )

    def _continue(
        self,
        *,
        alias: str,
        operation_id: str,
        desired: bytes,
        events: list[_JournalEvent],
        current: datetime,
        allow_new_claim: bool,
        staging_request: LocalTextStagingAuthorizationRequest | None,
    ) -> LocalTextMutationReceipt:
        metadata = events[-1].metadata
        metadata = dict(metadata)
        self._require_transaction_versions(metadata)
        metadata.setdefault("journal_reservation_fingerprint", events[0].event_fingerprint)
        phase = events[-1].phase
        lease: LocalTextClaimedAuthorizationLease | None = None
        with self._open_pinned_posix(
            metadata,
            allow_applied=phase in {"claimed", "renamed", "applied"},
        ) as pinned:
            if phase in {"reserved", "desired_durable", "backup_durable"}:
                if staging_request is None:
                    raise ValueError("local_text_transaction_staging_verification_required")
                self._require_staging_authorization(staging_request, current)
            if phase in {"reserved", "desired_durable", "backup_durable", "staged"}:
                self._require_preflight_snapshot(pinned, metadata)
                phase = self._stage(
                    pinned,
                    metadata,
                    desired,
                    operation_id,
                    alias,
                    current,
                    phase,
                )
            if phase == "staged":
                self._require_staged_state_files(pinned, metadata)
                self._require_preflight_snapshot(pinned, metadata)
                self._revalidate_pinned_before(pinned, metadata)
                authority_request = self._authority_request(
                    metadata, operation_id, purpose="execute"
                )
                historical = self._lookup_historical_context(authority_request, current)
                if historical is not None:
                    metadata = self._metadata_with_claim(metadata, historical, purpose="execute")
                    self._append_event(
                        alias=alias,
                        operation_id=operation_id,
                        phase="claimed",
                        metadata=metadata,
                        current=current,
                    )
                else:
                    if not allow_new_claim or staging_request is None:
                        raise ValueError("local_text_transaction_claim_required")
                    self._require_staging_authorization(staging_request, current)
                    lease, metadata = self._claim_and_record(
                        alias=alias,
                        operation_id=operation_id,
                        metadata=metadata,
                        current=current,
                        purpose="execute",
                    )
                self._inject("after_claim")
                phase = "claimed"
            try:
                if phase in {"claimed", "renamed"}:
                    if lease is None:
                        self._require_historical_claim(metadata, operation_id, current)
                    if phase == "claimed":
                        existing_identity = self._reconcile_applied(pinned, metadata)
                        if existing_identity is not None:
                            self._require_stage_became_target(existing_identity, metadata)
                            self._append_event(
                                alias=alias,
                                operation_id=operation_id,
                                phase="renamed",
                                metadata=metadata,
                                current=current,
                            )
                            phase = "renamed"
                    if phase == "renamed":
                        existing_identity = self._reconcile_applied(pinned, metadata)
                        if existing_identity is None:
                            if self._state_file_identity(
                                pinned.transaction_fd,
                                str(metadata["desired_state_name"]),
                            ) != metadata.get("desired_stage_identity"):
                                raise ValueError("local_text_transaction_recovery_stage_changed")
                            self._revalidate_pinned_before(pinned, metadata)
                            self._require_pre_effect_directories(pinned, metadata)
                            self._atomic_commit_posix(pinned, metadata)
                            self._inject("after_rename_before_directory_flush")
                    applied = self._apply_and_record(
                        pinned=pinned,
                        alias=alias,
                        operation_id=operation_id,
                        metadata=metadata,
                        current=current,
                        already_renamed=phase == "renamed",
                        fresh_claim_context=lease.context if lease is not None else None,
                    )
                    phase = "applied"
                else:
                    applied = self._find_event(events, "applied")
                if phase == "applied":
                    if lease is None:
                        self._require_historical_claim(applied.metadata, operation_id, current)
                    applied_identity = self._reconcile_applied(pinned, applied.metadata)
                    if applied_identity != applied.metadata.get("post_write_identity"):
                        raise ValueError("local_text_transaction_applied_identity_changed")
                    self._inject("after_applied_before_receipt")
                    receipt = self._seal_receipt(
                        alias=alias,
                        applied=applied,
                        current=current,
                    )
                    phase = "receipt"
                else:
                    receipt = self._receipt_from_applied(applied)
                if lease is not None:
                    lease.complete(receipt.receipt_fingerprint)
                if phase == "receipt":
                    self._inject("after_receipt_before_cleanup")
                    desired_name = str(metadata["desired_state_name"])
                    try:
                        os.unlink(desired_name, dir_fd=pinned.transaction_fd)
                    except FileNotFoundError:
                        pass
                    os.fsync(pinned.transaction_fd)
                    cleanup_metadata = dict(metadata)
                    cleanup_metadata["receipt_fingerprint"] = receipt.receipt_fingerprint
                    self._append_event(
                        alias=alias,
                        operation_id=operation_id,
                        phase="cleaned",
                        metadata=cleanup_metadata,
                        current=current,
                    )
                return receipt
            except Exception as exc:
                if lease is not None:
                    lease.interrupt(type(exc).__name__)
                raise

    def recover(
        self,
        *,
        root_alias: str,
        operation_id: str,
    ) -> LocalTextMutationReceipt:
        result = self._recover(
            root_alias=root_alias,
            operation_id=operation_id,
            plan=None,
            receipt_recorder=None,
            canonical_commit=None,
        )
        if not isinstance(result, LocalTextMutationReceipt):
            raise ValueError("local_text_transaction_result_invalid")
        return result

    def recover_and_commit_apply(
        self,
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        root_alias: str,
        operation_id: str,
        receipt_recorder: MutationReceiptRecorder,
        canonical_commit: ApplyCanonicalCommit,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Recover and canonicalize one apply without releasing its resource lock."""

        self._require_canonical_commit_ports_configured()
        require_valid_artifact_physical_apply_plan(plan)
        if (
            plan.physical_operation_id != operation_id
            or plan.root_alias != root_alias
            or not callable(receipt_recorder)
            or not callable(canonical_commit)
        ):
            raise ValueError("local_text_canonical_apply_recovery_binding_invalid")
        result = self._recover(
            root_alias=root_alias,
            operation_id=operation_id,
            plan=plan,
            receipt_recorder=receipt_recorder,
            canonical_commit=canonical_commit,
        )
        if not isinstance(result, ArtifactPhysicalCanonicalCommitReceiptContract):
            raise ValueError("local_text_canonical_apply_result_invalid")
        return result

    def _recover(
        self,
        *,
        root_alias: str,
        operation_id: str,
        plan: ArtifactPhysicalApplyPlanContract | None,
        receipt_recorder: MutationReceiptRecorder | None,
        canonical_commit: ApplyCanonicalCommit | None,
    ) -> LocalTextMutationReceipt | ArtifactPhysicalCanonicalCommitReceiptContract:
        self._require_operation_id(operation_id)
        current = self._trusted_now()
        events = self._load_events(root_alias, operation_id)
        if not events:
            raise ValueError("local_text_transaction_journal_missing")
        metadata = events[-1].metadata
        self._require_transaction_versions(metadata)
        phase = events[-1].phase
        staging_request: LocalTextStagingAuthorizationRequest | None = None
        if phase in {"desired_durable", "backup_durable", "staged"}:
            staging_request = self._execution_staging_request_from_metadata(metadata, operation_id)
            historical = None
            if phase == "staged":
                historical = self._lookup_historical_context(
                    self._authority_request(metadata, operation_id, purpose="execute"),
                    current,
                )
            if historical is None:
                self._require_staging_authorization(staging_request, current)
        with self._resource_lock(root_alias, str(metadata["resource_ref"])):
            self._require_canonical_physical_binding(
                purpose="apply",
                operation_id=operation_id,
                mutation_operation_id=None,
                mutation_receipt_fingerprint=None,
                resource_ref=str(metadata["resource_ref"]),
                root_alias=root_alias,
                plan=plan,
            )
            events = self._load_events(root_alias, operation_id)
            phase = events[-1].phase
            if phase in {"receipt", "cleaned"}:
                receipt = self._receipt_from_applied(self._find_event(events, "applied"))
                return self._commit_apply_locked_if_requested(
                    plan=plan,
                    root_alias=root_alias,
                    receipt=receipt,
                    receipt_recorder=receipt_recorder,
                    canonical_commit=canonical_commit,
                )
            if phase in {
                "rollback_claimed",
                "rollback_renamed",
                "rolled_back",
                "rollback_receipt",
            }:
                raise ValueError("local_text_transaction_not_recoverable_as_mutation")
            if os.name == "nt":
                raise ValueError("local_text_transaction_backend_not_handle_safe")
            if phase == "reserved":
                raise ValueError("local_text_transaction_retry_request_required")
            if phase in {"desired_durable", "backup_durable", "staged"}:
                staging_request = self._execution_staging_request_from_metadata(
                    metadata, operation_id
                )
                if phase in {"desired_durable", "backup_durable"}:
                    self._require_staging_authorization(staging_request, current)
            receipt = self._continue(
                alias=root_alias,
                operation_id=operation_id,
                desired=b"",
                events=events,
                current=current,
                allow_new_claim=phase
                in {
                    "reserved",
                    "desired_durable",
                    "backup_durable",
                    "staged",
                },
                staging_request=staging_request,
            )
            return self._commit_apply_locked_if_requested(
                plan=plan,
                root_alias=root_alias,
                receipt=receipt,
                receipt_recorder=receipt_recorder,
                canonical_commit=canonical_commit,
            )

    def rollback(
        self,
        request: LocalTextRollbackRequest,
    ) -> LocalTextRollbackReceipt:
        result = self._rollback(
            request,
            plan=None,
            receipt_recorder=None,
            canonical_commit=None,
        )
        if not isinstance(result, LocalTextRollbackReceipt):
            raise ValueError("local_text_rollback_result_invalid")
        return result

    def rollback_and_commit(
        self,
        plan: ArtifactPhysicalRollbackPlanContract,
        request: LocalTextRollbackRequest,
        *,
        receipt_recorder: RollbackReceiptRecorder,
        canonical_commit: RollbackCanonicalCommit,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Roll back and canonicalize without releasing the source resource lock."""

        self._require_canonical_commit_ports_configured()
        self._require_rollback_plan_request_binding(
            plan=plan,
            request=request,
        )
        if not callable(receipt_recorder) or not callable(canonical_commit):
            raise ValueError("local_text_canonical_rollback_callbacks_required")
        result = self._rollback(
            request,
            plan=plan,
            receipt_recorder=receipt_recorder,
            canonical_commit=canonical_commit,
        )
        if not isinstance(result, ArtifactPhysicalCanonicalCommitReceiptContract):
            raise ValueError("local_text_canonical_rollback_result_invalid")
        return result

    def _rollback(
        self,
        request: LocalTextRollbackRequest,
        *,
        plan: ArtifactPhysicalRollbackPlanContract | None,
        receipt_recorder: RollbackReceiptRecorder | None,
        canonical_commit: RollbackCanonicalCommit | None,
    ) -> LocalTextRollbackReceipt | ArtifactPhysicalCanonicalCommitReceiptContract:
        current = self._trusted_now()
        receipt = request.receipt
        self._require_operation_id(request.rollback_operation_id)
        if request.rollback_operation_id == receipt.operation_id:
            raise ValueError("local_text_rollback_operation_id_not_distinct")
        self._require_execution_binding(request.execution_binding)
        if not compare_digest(
            receipt.receipt_fingerprint,
            build_mutation_receipt_fingerprint(receipt),
        ):
            raise ValueError("local_text_mutation_receipt_invalid")
        if request.execution_binding.execution_grant_id == receipt.execution_grant_id:
            raise ValueError("local_text_rollback_requires_distinct_execution_grant")
        rollback_staging_request = LocalTextStagingAuthorizationRequest(
            purpose="rollback",
            operation_id=request.rollback_operation_id,
            operation="rollback_text",
            resource_ref=receipt.resource_ref,
            subject_ref=receipt.subject_ref,
            preflight_fingerprint=receipt.preflight_fingerprint,
            before_content_sha256=receipt.desired_content_sha256,
            desired_content_sha256=(
                _EMPTY_SHA256
                if receipt.operation == "create_text"
                else receipt.before_content_sha256
            ),
            root_config_fingerprint=receipt.root_config_fingerprint,
            execution_binding=request.execution_binding,
            mutation_receipt_fingerprint=receipt.receipt_fingerprint,
        )
        self._require_staging_authorization(rollback_staging_request, current)
        alias = self._root_alias_from_resource_ref(receipt.resource_ref)
        events = self._load_events(alias, receipt.operation_id)
        if not events:
            raise ValueError("local_text_transaction_journal_missing")
        self._require_transaction_versions(events[-1].metadata)
        if (
            events[-1].metadata.get("root_alias") != alias
            or events[-1].metadata.get("resource_ref") != receipt.resource_ref
        ):
            raise ValueError("local_text_mutation_receipt_resource_binding_mismatch")
        with self._resource_lock(alias, receipt.resource_ref):
            self._require_canonical_physical_binding(
                purpose="rollback",
                operation_id=request.rollback_operation_id,
                mutation_operation_id=receipt.operation_id,
                mutation_receipt_fingerprint=receipt.receipt_fingerprint,
                resource_ref=receipt.resource_ref,
                root_alias=alias,
                plan=plan,
            )
            events = self._load_events(alias, receipt.operation_id)
            self._require_transaction_versions(events[-1].metadata)
            if (
                events[-1].metadata.get("root_alias") != alias
                or events[-1].metadata.get("resource_ref") != receipt.resource_ref
            ):
                raise ValueError("local_text_mutation_receipt_resource_binding_mismatch")
            if events[-1].phase == "rollback_receipt":
                rollback_receipt = self._rollback_receipt_from_event(events[-1])
                return self._commit_rollback_locked_if_requested(
                    plan=plan,
                    root_alias=alias,
                    receipt=rollback_receipt,
                    receipt_recorder=receipt_recorder,
                    canonical_commit=canonical_commit,
                )
            if events[-1].phase not in {"receipt", "cleaned", "rollback_reserved"}:
                raise ValueError("local_text_transaction_not_rollback_ready")
            applied = self._find_event(events, "applied")
            if applied.event_fingerprint != receipt.applied_event_fingerprint:
                raise ValueError("local_text_mutation_receipt_journal_mismatch")
            metadata = (
                events[-1].metadata if events[-1].phase == "rollback_reserved" else applied.metadata
            )
            with self._open_pinned_posix(metadata, allow_applied=True) as pinned:
                identity = self._reconcile_applied(pinned, metadata)
                if identity is None or identity != metadata["post_write_identity"]:
                    raise ValueError("local_text_rollback_later_edit_detected")
                rollback_metadata = dict(metadata)
                if events[-1].phase != "rollback_reserved":
                    self._require_staging_authorization(rollback_staging_request, current)
                    rollback_metadata.update(
                        {
                            "rollback_operation_id": request.rollback_operation_id,
                            "rollback_operation": "rollback_text",
                            "rollback_requested_grant_id": (
                                request.execution_binding.execution_grant_id
                            ),
                            "rollback_grant_fingerprint": (
                                request.execution_binding.execution_grant_fingerprint
                            ),
                            "rollback_action_fingerprint": (
                                request.execution_binding.action_fingerprint
                            ),
                            "rollback_execution_request_fingerprint": (
                                request.execution_binding.execution_request_fingerprint
                            ),
                            "rollback_intent_fingerprint": (
                                request.execution_binding.intent_fingerprint
                            ),
                            "rollback_confirmation_receipt_id": (
                                request.execution_binding.confirmation_receipt_id
                            ),
                            "mutation_receipt_fingerprint": receipt.receipt_fingerprint,
                            "rollback_pre_effect_directories": (
                                self._current_directory_observations(pinned)
                            ),
                        }
                    )
                    rollback_reservation = self._append_event(
                        alias=alias,
                        operation_id=receipt.operation_id,
                        phase="rollback_reserved",
                        metadata=rollback_metadata,
                        current=current,
                    )
                    rollback_metadata["rollback_journal_reservation_fingerprint"] = (
                        rollback_reservation.event_fingerprint
                    )
                else:
                    if (
                        rollback_metadata.get("rollback_operation_id")
                        != request.rollback_operation_id
                        or rollback_metadata.get("rollback_requested_grant_id")
                        != request.execution_binding.execution_grant_id
                        or rollback_metadata.get("mutation_receipt_fingerprint")
                        != receipt.receipt_fingerprint
                    ):
                        raise ValueError("local_text_rollback_retry_binding_mismatch")
                    rollback_reservation = events[-1]
                    rollback_metadata["rollback_journal_reservation_fingerprint"] = (
                        rollback_reservation.event_fingerprint
                    )
                self._require_rollback_pre_effect_directories(pinned, rollback_metadata)
                authority_request = self._authority_request(
                    rollback_metadata,
                    request.rollback_operation_id,
                    purpose="rollback",
                    mutation_receipt_fingerprint=receipt.receipt_fingerprint,
                    execution_binding=request.execution_binding,
                    logical_operation="rollback_text",
                    journal_reservation_fingerprint=rollback_reservation.event_fingerprint,
                )
                historical = self._lookup_historical_context(authority_request, current)
                lease: LocalTextClaimedAuthorizationLease | None = None
                if historical is not None:
                    rollback_metadata = self._metadata_with_claim(
                        rollback_metadata, historical, purpose="rollback"
                    )
                    self._append_event(
                        alias=alias,
                        operation_id=receipt.operation_id,
                        phase="rollback_claimed",
                        metadata=rollback_metadata,
                        current=current,
                    )
                else:
                    if events[-1].phase == "rollback_reserved":
                        self._require_staging_authorization(rollback_staging_request, current)
                    lease, rollback_metadata = self._claim_and_record(
                        alias=alias,
                        operation_id=receipt.operation_id,
                        metadata=rollback_metadata,
                        current=current,
                        purpose="rollback",
                        mutation_receipt_fingerprint=receipt.receipt_fingerprint,
                        execution_binding=request.execution_binding,
                        authority_operation_id=request.rollback_operation_id,
                        logical_operation="rollback_text",
                        journal_reservation_fingerprint=(rollback_reservation.event_fingerprint),
                    )
                try:
                    self._inject("after_rollback_claim")
                    self._require_rollback_pre_effect_directories(pinned, rollback_metadata)
                    self._apply_rollback_pinned(
                        pinned,
                        rollback_metadata,
                        current=current,
                        fresh_claim_context=lease.context if lease is not None else None,
                    )
                    self._inject("after_rollback_rename_before_flush")
                    if not self._rollback_is_already_applied(pinned, rollback_metadata):
                        raise ValueError("local_text_rollback_verification_failed")
                    self._append_event(
                        alias=alias,
                        operation_id=receipt.operation_id,
                        phase="rollback_renamed",
                        metadata=rollback_metadata,
                        current=current,
                    )
                    self._inject("after_rollback_renamed_before_directory_flush")
                    os.fsync(pinned.parent_fd)
                    os.fsync(pinned.transaction_fd)
                    self._inject("after_rollback_flush_before_applied")
                    rolled_back = self._append_event(
                        alias=alias,
                        operation_id=receipt.operation_id,
                        phase="rolled_back",
                        metadata=rollback_metadata,
                        current=current,
                    )
                    rollback_receipt = self._rollback_receipt_from_rolled_back(rolled_back)
                    self._inject("after_rollback_applied_before_receipt")
                    final_metadata = dict(rollback_metadata)
                    final_metadata["rolled_back_event_fingerprint"] = rolled_back.event_fingerprint
                    final_metadata["rolled_back_at"] = rolled_back.recorded_at
                    final_metadata["rollback_receipt_fingerprint"] = (
                        rollback_receipt.rollback_receipt_fingerprint
                    )
                    final = self._append_event(
                        alias=alias,
                        operation_id=receipt.operation_id,
                        phase="rollback_receipt",
                        metadata=final_metadata,
                        current=current,
                    )
                    if lease is not None:
                        lease.complete(rollback_receipt.rollback_receipt_fingerprint)
                    exact_rollback_receipt = self._rollback_receipt_from_event(final)
                    return self._commit_rollback_locked_if_requested(
                        plan=plan,
                        root_alias=alias,
                        receipt=exact_rollback_receipt,
                        receipt_recorder=receipt_recorder,
                        canonical_commit=canonical_commit,
                    )
                except Exception as exc:
                    if lease is not None:
                        lease.interrupt(type(exc).__name__)
                    raise

    def recover_rollback(
        self,
        *,
        root_alias: str,
        operation_id: str,
    ) -> LocalTextRollbackReceipt:
        result = self._recover_rollback(
            root_alias=root_alias,
            operation_id=operation_id,
            plan=None,
            receipt_recorder=None,
            canonical_commit=None,
        )
        if not isinstance(result, LocalTextRollbackReceipt):
            raise ValueError("local_text_rollback_result_invalid")
        return result

    def recover_rollback_and_commit(
        self,
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        root_alias: str,
        operation_id: str,
        receipt_recorder: RollbackReceiptRecorder,
        canonical_commit: RollbackCanonicalCommit,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Recover and canonicalize one rollback under the same resource lock."""

        self._require_canonical_commit_ports_configured()
        require_valid_artifact_physical_rollback_plan(plan)
        if (
            plan.physical_operation_id != operation_id
            or plan.root_alias != root_alias
            or not callable(receipt_recorder)
            or not callable(canonical_commit)
        ):
            raise ValueError("local_text_canonical_rollback_recovery_binding_invalid")
        result = self._recover_rollback(
            root_alias=root_alias,
            operation_id=plan.mutation_operation_id,
            plan=plan,
            receipt_recorder=receipt_recorder,
            canonical_commit=canonical_commit,
        )
        if not isinstance(result, ArtifactPhysicalCanonicalCommitReceiptContract):
            raise ValueError("local_text_canonical_rollback_result_invalid")
        return result

    def _recover_rollback(
        self,
        *,
        root_alias: str,
        operation_id: str,
        plan: ArtifactPhysicalRollbackPlanContract | None,
        receipt_recorder: RollbackReceiptRecorder | None,
        canonical_commit: RollbackCanonicalCommit | None,
    ) -> LocalTextRollbackReceipt | ArtifactPhysicalCanonicalCommitReceiptContract:
        self._require_operation_id(operation_id)
        current = self._trusted_now()
        events = self._load_events(root_alias, operation_id)
        if not events:
            raise ValueError("local_text_transaction_journal_missing")
        metadata = events[-1].metadata
        self._require_transaction_versions(metadata)
        with self._resource_lock(root_alias, str(metadata["resource_ref"])):
            self._require_canonical_physical_binding(
                purpose="rollback",
                operation_id=str(metadata.get("rollback_operation_id", "")),
                mutation_operation_id=operation_id,
                mutation_receipt_fingerprint=(
                    str(metadata["mutation_receipt_fingerprint"])
                    if metadata.get("mutation_receipt_fingerprint") is not None
                    else None
                ),
                resource_ref=str(metadata["resource_ref"]),
                root_alias=root_alias,
                plan=plan,
            )
            events = self._load_events(root_alias, operation_id)
            phase = events[-1].phase
            if phase == "rollback_receipt":
                receipt = self._rollback_receipt_from_event(events[-1])
                return self._commit_rollback_locked_if_requested(
                    plan=plan,
                    root_alias=root_alias,
                    receipt=receipt,
                    receipt_recorder=receipt_recorder,
                    canonical_commit=canonical_commit,
                )
            if phase not in {
                "rollback_reserved",
                "rollback_claimed",
                "rollback_renamed",
                "rolled_back",
            }:
                raise ValueError("local_text_rollback_not_recoverable")
            metadata = events[-1].metadata
            self._require_transaction_versions(metadata)
            if phase == "rollback_reserved":
                metadata = dict(metadata)
                metadata["rollback_journal_reservation_fingerprint"] = events[-1].event_fingerprint
                binding = LocalTextExecutionGrantBinding(
                    execution_grant_id=str(metadata["rollback_requested_grant_id"]),
                    execution_grant_fingerprint=str(metadata["rollback_grant_fingerprint"]),
                    action_fingerprint=str(metadata["rollback_action_fingerprint"]),
                    execution_request_fingerprint=str(
                        metadata["rollback_execution_request_fingerprint"]
                    ),
                    intent_fingerprint=str(metadata["rollback_intent_fingerprint"]),
                    confirmation_receipt_id=str(metadata["rollback_confirmation_receipt_id"]),
                )
                authority_request = self._authority_request(
                    metadata,
                    str(metadata["rollback_operation_id"]),
                    purpose="rollback",
                    mutation_receipt_fingerprint=str(metadata["mutation_receipt_fingerprint"]),
                    execution_binding=binding,
                    logical_operation="rollback_text",
                    journal_reservation_fingerprint=events[-1].event_fingerprint,
                )
                historical = self._lookup_historical_context(authority_request, current)
                if historical is None:
                    raise ValueError("local_text_rollback_claim_required")
                metadata = self._metadata_with_claim(metadata, historical, purpose="rollback")
                self._append_event(
                    alias=root_alias,
                    operation_id=operation_id,
                    phase="rollback_claimed",
                    metadata=metadata,
                    current=current,
                )
                phase = "rollback_claimed"
            self._require_historical_claim(
                metadata,
                operation_id,
                current,
                purpose="rollback",
            )
            if phase == "rolled_back":
                rolled_back = events[-1]
            else:
                with self._open_pinned_posix(metadata, allow_applied=True) as pinned:
                    rollback_applied = self._rollback_is_already_applied(pinned, metadata)
                    if not rollback_applied:
                        self._require_rollback_pre_effect_directories(pinned, metadata)
                        self._apply_rollback_pinned(
                            pinned,
                            metadata,
                            current=current,
                            fresh_claim_context=None,
                        )
                        rollback_applied = self._rollback_is_already_applied(pinned, metadata)
                    if phase == "rollback_claimed":
                        self._append_event(
                            alias=root_alias,
                            operation_id=operation_id,
                            phase="rollback_renamed",
                            metadata=metadata,
                            current=current,
                        )
                    if not rollback_applied:
                        raise ValueError("local_text_rollback_recovery_target_drift")
                    os.fsync(pinned.parent_fd)
                    os.fsync(pinned.transaction_fd)
                    rolled_back = self._append_event(
                        alias=root_alias,
                        operation_id=operation_id,
                        phase="rolled_back",
                        metadata=metadata,
                        current=current,
                    )
            receipt = self._rollback_receipt_from_rolled_back(rolled_back)
            final_metadata = dict(rolled_back.metadata)
            final_metadata.update(
                {
                    "rolled_back_event_fingerprint": rolled_back.event_fingerprint,
                    "rolled_back_at": rolled_back.recorded_at,
                    "rollback_receipt_fingerprint": (receipt.rollback_receipt_fingerprint),
                }
            )
            final = self._append_event(
                alias=root_alias,
                operation_id=operation_id,
                phase="rollback_receipt",
                metadata=final_metadata,
                current=current,
            )
            exact_receipt = self._rollback_receipt_from_event(final)
            return self._commit_rollback_locked_if_requested(
                plan=plan,
                root_alias=root_alias,
                receipt=exact_receipt,
                receipt_recorder=receipt_recorder,
                canonical_commit=canonical_commit,
            )

    def verify_mutation_receipt_current(
        self,
        *,
        root_alias: str,
        receipt: LocalTextMutationReceipt,
    ) -> LocalTextMutationReceipt:
        """Return exact mutation proof only while its applied state is still current."""

        require_valid_local_text_mutation_receipt(receipt)
        self._require_receipt_root_alias(root_alias, receipt.resource_ref)
        self._require_persisted_mutation_receipt(receipt)
        with self._resource_lock(root_alias, receipt.resource_ref):
            exact, _, _ = self._verify_mutation_receipt_current_locked(
                root_alias=root_alias,
                receipt=receipt,
            )
            return exact

    def commit_mutation_if_current(
        self,
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        root_alias: str,
        receipt: LocalTextMutationReceipt,
        canonical_commit: Callable[
            [
                ArtifactPhysicalApplyPlanContract,
                LocalTextMutationReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Run one canonical commit under the lock after exact fresh proof."""

        self._require_canonical_commit_ports_configured()
        if not callable(canonical_commit):
            raise ValueError("local_text_canonical_commit_invalid")
        require_valid_local_text_mutation_receipt(receipt)
        self._require_apply_plan_receipt_binding(
            plan=plan,
            receipt=receipt,
            root_alias=root_alias,
        )
        self._require_receipt_root_alias(root_alias, receipt.resource_ref)
        self._require_persisted_mutation_receipt(receipt)
        with self._resource_lock(root_alias, receipt.resource_ref):
            return self._commit_mutation_current_locked(
                plan=plan,
                root_alias=root_alias,
                receipt=receipt,
                canonical_commit=canonical_commit,
            )

    def verify_rollback_receipt_current(
        self,
        *,
        root_alias: str,
        receipt: LocalTextRollbackReceipt,
    ) -> LocalTextRollbackReceipt:
        """Return exact rollback proof only while restored state is still current."""

        require_valid_local_text_rollback_receipt(receipt)
        self._require_receipt_root_alias(root_alias, receipt.resource_ref)
        self._require_persisted_rollback_receipt(receipt)
        with self._resource_lock(root_alias, receipt.resource_ref):
            exact, _, _ = self._verify_rollback_receipt_current_locked(
                root_alias=root_alias,
                receipt=receipt,
            )
            return exact

    def commit_rollback_if_current(
        self,
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        root_alias: str,
        receipt: LocalTextRollbackReceipt,
        canonical_commit: Callable[
            [
                ArtifactPhysicalRollbackPlanContract,
                LocalTextRollbackReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Run one canonical rollback commit under exact fresh restored proof."""

        self._require_canonical_commit_ports_configured()
        if not callable(canonical_commit):
            raise ValueError("local_text_canonical_commit_invalid")
        require_valid_local_text_rollback_receipt(receipt)
        self._require_rollback_plan_receipt_binding(
            plan=plan,
            receipt=receipt,
            root_alias=root_alias,
        )
        self._require_receipt_root_alias(root_alias, receipt.resource_ref)
        self._require_persisted_rollback_receipt(receipt)
        with self._resource_lock(root_alias, receipt.resource_ref):
            return self._commit_rollback_current_locked(
                plan=plan,
                root_alias=root_alias,
                receipt=receipt,
                canonical_commit=canonical_commit,
            )

    def _commit_apply_locked_if_requested(
        self,
        *,
        plan: ArtifactPhysicalApplyPlanContract | None,
        root_alias: str,
        receipt: LocalTextMutationReceipt,
        receipt_recorder: MutationReceiptRecorder | None,
        canonical_commit: ApplyCanonicalCommit | None,
    ) -> LocalTextMutationReceipt | ArtifactPhysicalCanonicalCommitReceiptContract:
        if plan is None:
            if receipt_recorder is not None or canonical_commit is not None:
                raise ValueError("local_text_canonical_apply_plan_required")
            return receipt
        if receipt_recorder is None or canonical_commit is None:
            raise ValueError("local_text_canonical_apply_callbacks_required")
        try:
            recorded = receipt_recorder(receipt)
        except Exception:
            raise ValueError("local_text_mutation_receipt_recording_failed") from None
        if recorded != receipt:
            raise ValueError("local_text_mutation_receipt_recording_mismatch")
        return self._commit_mutation_current_locked(
            plan=plan,
            root_alias=root_alias,
            receipt=recorded,
            canonical_commit=canonical_commit,
        )

    def _commit_rollback_locked_if_requested(
        self,
        *,
        plan: ArtifactPhysicalRollbackPlanContract | None,
        root_alias: str,
        receipt: LocalTextRollbackReceipt,
        receipt_recorder: RollbackReceiptRecorder | None,
        canonical_commit: RollbackCanonicalCommit | None,
    ) -> LocalTextRollbackReceipt | ArtifactPhysicalCanonicalCommitReceiptContract:
        if plan is None:
            if receipt_recorder is not None or canonical_commit is not None:
                raise ValueError("local_text_canonical_rollback_plan_required")
            return receipt
        if receipt_recorder is None or canonical_commit is None:
            raise ValueError("local_text_canonical_rollback_callbacks_required")
        try:
            recorded = receipt_recorder(receipt)
        except Exception:
            raise ValueError("local_text_rollback_receipt_recording_failed") from None
        if recorded != receipt:
            raise ValueError("local_text_rollback_receipt_recording_mismatch")
        return self._commit_rollback_current_locked(
            plan=plan,
            root_alias=root_alias,
            receipt=recorded,
            canonical_commit=canonical_commit,
        )

    def _require_canonical_physical_binding(
        self,
        *,
        purpose: str,
        operation_id: str,
        mutation_operation_id: str | None,
        mutation_receipt_fingerprint: str | None,
        resource_ref: str,
        root_alias: str,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract | None,
    ) -> None:
        try:
            require_valid_local_text_resource_ref(resource_ref, root_alias)
        except ValueError:
            raise ValueError("local_text_canonical_physical_resource_scope_mismatch") from None
        if root_alias not in self._transaction_roots:
            raise ValueError("local_text_canonical_physical_resource_scope_mismatch")
        if plan is None:
            lookup = self._resource_physical_binding_lookup
            if lookup is None:
                return
            try:
                bound = lookup(resource_ref)
            except Exception:
                raise ValueError("local_text_resource_physical_binding_lookup_failed") from None
            if bound is not False:
                raise ValueError("local_text_resource_physically_bound")
            return

        authorizer = self._canonical_physical_effect_authorizer
        if authorizer is None:
            raise ValueError("local_text_canonical_physical_effect_authorizer_not_configured")
        if isinstance(plan, ArtifactPhysicalApplyPlanContract):
            require_valid_artifact_physical_apply_plan(plan)
            expected = (
                "apply",
                plan.physical_operation_id,
                None,
                None,
                plan.resource_ref,
                plan.root_alias,
            )
        elif isinstance(plan, ArtifactPhysicalRollbackPlanContract):
            require_valid_artifact_physical_rollback_plan(plan)
            expected = (
                "rollback",
                plan.physical_operation_id,
                plan.mutation_operation_id,
                plan.mutation_receipt_fingerprint,
                plan.resource_ref,
                plan.root_alias,
            )
        else:
            raise ValueError("local_text_canonical_physical_plan_invalid")
        observed = (
            purpose,
            operation_id,
            mutation_operation_id,
            mutation_receipt_fingerprint,
            resource_ref,
            root_alias,
        )
        if observed != expected:
            raise ValueError("local_text_canonical_physical_plan_binding_mismatch")
        try:
            authorized = authorizer(plan)
        except Exception:
            raise ValueError("local_text_canonical_physical_effect_authorization_failed") from None
        if authorized is not True:
            raise ValueError("local_text_canonical_physical_effect_not_authorized")

    def _require_canonical_commit_ports_configured(self) -> None:
        if self._canonical_physical_effect_authorizer is None:
            raise ValueError("local_text_canonical_physical_effect_authorizer_not_configured")
        if self._resource_physical_binding_lookup is None:
            raise ValueError("local_text_resource_physical_binding_lookup_not_configured")
        if self._canonical_commit_receipt_verifier is None:
            raise ValueError("local_text_canonical_commit_receipt_verifier_not_configured")
        if self._physical_attestation_lease_provider is None:
            raise ValueError("local_text_physical_attestation_lease_provider_not_configured")

    def _run_canonical_commit_under_attestation_lease(
        self,
        *,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
        receipt: LocalTextMutationReceipt | LocalTextRollbackReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
        canonical_commit: ApplyCanonicalCommit | RollbackCanonicalCommit,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        provider = self._physical_attestation_lease_provider
        if provider is None:
            raise ValueError("local_text_physical_attestation_lease_provider_not_configured")
        try:
            lease = provider(plan, receipt, attestation)
        except Exception:
            raise ValueError("local_text_physical_attestation_lease_issue_failed") from None
        try:
            enter = lease.__enter__
            exit_lease = lease.__exit__
        except AttributeError:
            raise ValueError("local_text_physical_attestation_lease_invalid") from None
        del enter, exit_lease
        with lease:
            return canonical_commit(plan, receipt, attestation)

    @staticmethod
    def _require_apply_plan_receipt_request_binding(
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        request: LocalTextMutationRequest,
    ) -> None:
        require_valid_artifact_physical_apply_plan(plan)
        preflight = request.preflight
        expected_transition = "register" if preflight.operation == "create_text" else "replace"
        expected = (
            request.operation_id,
            preflight.resource_ref,
            preflight.root_alias,
            preflight.preflight_fingerprint,
            preflight.root_config_fingerprint,
            preflight.before_content_sha256,
            preflight.desired_content_sha256,
            expected_transition,
            preflight.preflight_policy_version,
            LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
            LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
            preflight.adapter_backend_version,
        )
        observed = (
            plan.physical_operation_id,
            plan.resource_ref,
            plan.root_alias,
            plan.preflight_fingerprint,
            plan.root_config_fingerprint,
            plan.before_content_sha256,
            plan.desired_content_sha256,
            plan.transition,
            plan.preflight_policy_version,
            plan.transaction_policy_version,
            plan.transaction_backend_version,
            plan.adapter_backend_version,
        )
        if observed != expected:
            raise ValueError("local_text_physical_apply_plan_request_binding_mismatch")

    def _require_rollback_plan_request_binding(
        self,
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        request: LocalTextRollbackRequest,
    ) -> None:
        require_valid_artifact_physical_rollback_plan(plan)
        receipt = request.receipt
        require_valid_local_text_mutation_receipt(receipt)
        root_alias = self._root_alias_from_resource_ref(receipt.resource_ref)
        expected = (
            request.rollback_operation_id,
            receipt.operation_id,
            receipt.receipt_fingerprint,
            receipt.resource_ref,
            root_alias,
            receipt.desired_content_sha256,
            _EMPTY_SHA256 if receipt.operation == "create_text" else receipt.before_content_sha256,
        )
        observed = (
            plan.physical_operation_id,
            plan.mutation_operation_id,
            plan.mutation_receipt_fingerprint,
            plan.resource_ref,
            plan.root_alias,
            plan.expected_current_sha256,
            plan.restored_content_sha256,
        )
        if observed != expected:
            raise ValueError("local_text_physical_rollback_plan_request_binding_mismatch")

    def _commit_mutation_current_locked(
        self,
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        root_alias: str,
        receipt: LocalTextMutationReceipt,
        canonical_commit: ApplyCanonicalCommit,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        self._require_canonical_physical_binding(
            purpose="apply",
            operation_id=receipt.operation_id,
            mutation_operation_id=None,
            mutation_receipt_fingerprint=None,
            resource_ref=receipt.resource_ref,
            root_alias=root_alias,
            plan=plan,
        )
        exact, observed_identity, metadata = self._verify_mutation_receipt_current_locked(
            root_alias=root_alias,
            receipt=receipt,
        )
        self._require_apply_plan_receipt_binding(
            plan=plan,
            receipt=exact,
            root_alias=root_alias,
        )
        self._require_apply_plan_physical_binding(plan=plan, metadata=metadata)
        attestation = self._build_physical_state_attestation(
            purpose="mutation_current",
            receipt=exact,
            rollback_operation_id=None,
            root_alias=root_alias,
            physical_state="applied",
            observed_content_sha256=exact.desired_content_sha256,
            observed_identity=observed_identity,
            journal_event_fingerprint=exact.applied_event_fingerprint,
            metadata=metadata,
        )
        result = self._run_canonical_commit_under_attestation_lease(
            plan=plan,
            receipt=exact,
            attestation=attestation,
            canonical_commit=canonical_commit,
        )
        self._require_apply_commit_receipt_binding(
            result=result,
            plan=plan,
            receipt=exact,
            attestation=attestation,
        )
        self._require_persisted_canonical_commit_receipt(result)
        return result

    def _commit_rollback_current_locked(
        self,
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        root_alias: str,
        receipt: LocalTextRollbackReceipt,
        canonical_commit: RollbackCanonicalCommit,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        self._require_canonical_physical_binding(
            purpose="rollback",
            operation_id=receipt.operation_id,
            mutation_operation_id=receipt.mutation_operation_id,
            mutation_receipt_fingerprint=receipt.mutation_receipt_fingerprint,
            resource_ref=receipt.resource_ref,
            root_alias=root_alias,
            plan=plan,
        )
        exact, observed_identity, metadata = self._verify_rollback_receipt_current_locked(
            root_alias=root_alias,
            receipt=receipt,
        )
        self._require_rollback_plan_receipt_binding(
            plan=plan,
            receipt=exact,
            root_alias=root_alias,
        )
        self._require_rollback_plan_physical_binding(
            plan=plan,
            receipt=exact,
            metadata=metadata,
        )
        physical_state = "absent" if metadata["operation"] == "create_text" else "restored"
        attestation = self._build_physical_state_attestation(
            purpose="rollback_current",
            receipt=exact,
            rollback_operation_id=exact.operation_id,
            root_alias=root_alias,
            physical_state=physical_state,
            observed_content_sha256=exact.restored_content_sha256,
            observed_identity=observed_identity,
            journal_event_fingerprint=exact.rolled_back_event_fingerprint,
            metadata=metadata,
        )
        result = self._run_canonical_commit_under_attestation_lease(
            plan=plan,
            receipt=exact,
            attestation=attestation,
            canonical_commit=canonical_commit,
        )
        self._require_rollback_commit_receipt_binding(
            result=result,
            plan=plan,
            receipt=exact,
            attestation=attestation,
        )
        self._require_persisted_canonical_commit_receipt(result)
        return result

    def _verify_mutation_receipt_current_locked(
        self,
        *,
        root_alias: str,
        receipt: LocalTextMutationReceipt,
    ) -> tuple[LocalTextMutationReceipt, dict[str, int], dict[str, object]]:
        require_valid_local_text_mutation_receipt(receipt)
        events = self._load_events(root_alias, receipt.operation_id)
        if not events:
            raise ValueError("local_text_transaction_journal_missing")
        metadata = events[-1].metadata
        self._require_transaction_versions(metadata)
        if (
            metadata.get("root_alias") != root_alias
            or metadata.get("resource_ref") != receipt.resource_ref
        ):
            raise ValueError("local_text_mutation_receipt_resource_binding_mismatch")
        applied = self._find_event(events, "applied")
        receipt_event = self._find_event(events, "receipt")
        persisted = self._receipt_from_applied(applied)
        if (
            persisted != receipt
            or receipt_event.metadata.get("receipt_fingerprint") != receipt.receipt_fingerprint
            or receipt_event.metadata.get("applied_event_fingerprint")
            != receipt.applied_event_fingerprint
        ):
            raise ValueError("local_text_mutation_receipt_journal_mismatch")
        self._require_persisted_mutation_receipt(persisted)
        try:
            with self._open_pinned_posix(applied.metadata, allow_applied=True) as pinned:
                current_identity = self._reconcile_applied(pinned, applied.metadata)
                expected_identity = applied.metadata.get("post_write_identity")
                if (
                    current_identity is None
                    or not isinstance(expected_identity, dict)
                    or current_identity != expected_identity
                ):
                    raise ValueError("local_text_mutation_receipt_physical_state_mismatch")
        except ValueError as exc:
            if str(exc) in {
                "local_text_transaction_create_precondition_stale",
                "local_text_transaction_precondition_hash_mismatch",
            }:
                raise ValueError("local_text_mutation_receipt_physical_state_mismatch") from None
            raise
        return persisted, current_identity, applied.metadata

    def _verify_rollback_receipt_current_locked(
        self,
        *,
        root_alias: str,
        receipt: LocalTextRollbackReceipt,
    ) -> tuple[
        LocalTextRollbackReceipt,
        dict[str, int] | None,
        dict[str, object],
    ]:
        require_valid_local_text_rollback_receipt(receipt)
        events = self._load_events(root_alias, receipt.mutation_operation_id)
        if not events:
            raise ValueError("local_text_transaction_journal_missing")
        metadata = events[-1].metadata
        self._require_transaction_versions(metadata)
        if (
            metadata.get("root_alias") != root_alias
            or metadata.get("resource_ref") != receipt.resource_ref
            or metadata.get("rollback_operation_id") != receipt.operation_id
        ):
            raise ValueError("local_text_rollback_receipt_resource_binding_mismatch")
        receipt_event = self._find_event(events, "rollback_receipt")
        persisted = self._rollback_receipt_from_event(receipt_event)
        if persisted != receipt:
            raise ValueError("local_text_rollback_receipt_journal_mismatch")
        self._require_persisted_rollback_receipt(persisted)
        try:
            with self._open_pinned_posix(metadata, allow_applied=True) as pinned:
                if not self._rollback_is_already_applied(pinned, metadata):
                    raise ValueError("local_text_rollback_receipt_physical_state_mismatch")
                observed_identity = (
                    None
                    if metadata["operation"] == "create_text"
                    else metadata.get("backup_stage_identity")
                )
                if observed_identity is not None and not isinstance(observed_identity, dict):
                    raise ValueError("local_text_rollback_receipt_physical_state_mismatch")
        except ValueError as exc:
            if str(exc) in {
                "local_text_transaction_create_precondition_stale",
                "local_text_transaction_precondition_hash_mismatch",
            }:
                raise ValueError("local_text_rollback_receipt_physical_state_mismatch") from None
            raise
        return persisted, observed_identity, metadata

    def _build_physical_state_attestation(
        self,
        *,
        purpose: str,
        receipt: LocalTextMutationReceipt | LocalTextRollbackReceipt,
        rollback_operation_id: str | None,
        root_alias: str,
        physical_state: str,
        observed_content_sha256: str,
        observed_identity: dict[str, int] | None,
        journal_event_fingerprint: str,
        metadata: dict[str, object],
    ) -> LocalTextPhysicalStateAttestationContract:
        mutation_operation_id = (
            receipt.operation_id
            if isinstance(receipt, LocalTextMutationReceipt)
            else receipt.mutation_operation_id
        )
        receipt_fingerprint = (
            receipt.receipt_fingerprint
            if isinstance(receipt, LocalTextMutationReceipt)
            else receipt.rollback_receipt_fingerprint
        )
        attestation = LocalTextPhysicalStateAttestationContract(
            attestation_id=f"local-text-physical-attestation://{uuid4()}",
            purpose=purpose,
            receipt_fingerprint=receipt_fingerprint,
            mutation_operation_id=mutation_operation_id,
            rollback_operation_id=rollback_operation_id,
            resource_ref=receipt.resource_ref,
            root_alias=root_alias,
            root_config_fingerprint=str(metadata["root_config_fingerprint"]),
            physical_state=physical_state,
            observed_content_sha256=observed_content_sha256,
            observed_identity_fingerprint=_canonical_digest(
                {
                    "physical_state": physical_state,
                    "identity": observed_identity if observed_identity is not None else "absent",
                }
            ),
            journal_event_fingerprint=journal_event_fingerprint,
            transaction_policy_version=str(metadata["transaction_policy_version"]),
            transaction_backend_version=str(metadata["transaction_backend_version"]),
            verified_at=_canonical_time(self._trusted_now()),
            attestation_fingerprint="0" * 64,
        )
        sealed = seal_local_text_physical_state_attestation(attestation)
        require_valid_local_text_physical_state_attestation(sealed)
        return sealed

    @staticmethod
    def _require_apply_plan_receipt_binding(
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        receipt: LocalTextMutationReceipt,
        root_alias: str,
    ) -> None:
        require_valid_artifact_physical_apply_plan(plan)
        expected_transition = "register" if receipt.operation == "create_text" else "replace"
        expected = (
            receipt.operation_id,
            receipt.resource_ref,
            root_alias,
            receipt.preflight_fingerprint,
            receipt.root_config_fingerprint,
            receipt.before_content_sha256,
            receipt.desired_content_sha256,
            expected_transition,
            LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
            LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
            LOCAL_TEXT_ADAPTER_BACKEND_VERSION,
        )
        observed = (
            plan.physical_operation_id,
            plan.resource_ref,
            plan.root_alias,
            plan.preflight_fingerprint,
            plan.root_config_fingerprint,
            plan.before_content_sha256,
            plan.desired_content_sha256,
            plan.transition,
            plan.preflight_policy_version,
            plan.transaction_backend_version,
            plan.adapter_backend_version,
        )
        if observed != expected:
            raise ValueError("local_text_physical_apply_plan_receipt_binding_mismatch")

    @staticmethod
    def _require_apply_plan_physical_binding(
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        metadata: dict[str, object],
    ) -> None:
        expected = (
            plan.resource_ref,
            plan.root_alias,
            plan.root_config_fingerprint,
            plan.before_content_sha256,
            plan.desired_content_sha256,
            plan.transaction_backend_version,
        )
        observed = tuple(
            metadata.get(field_name)
            for field_name in (
                "resource_ref",
                "root_alias",
                "root_config_fingerprint",
                "before_content_sha256",
                "desired_content_sha256",
                "transaction_backend_version",
            )
        )
        if observed != expected:
            raise ValueError("local_text_physical_apply_plan_journal_binding_mismatch")

    @staticmethod
    def _require_rollback_plan_receipt_binding(
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        receipt: LocalTextRollbackReceipt,
        root_alias: str,
    ) -> None:
        require_valid_artifact_physical_rollback_plan(plan)
        expected = (
            receipt.operation_id,
            receipt.mutation_operation_id,
            receipt.mutation_receipt_fingerprint,
            receipt.resource_ref,
            root_alias,
            receipt.restored_content_sha256,
        )
        observed = (
            plan.physical_operation_id,
            plan.mutation_operation_id,
            plan.mutation_receipt_fingerprint,
            plan.resource_ref,
            plan.root_alias,
            plan.restored_content_sha256,
        )
        if observed != expected:
            raise ValueError("local_text_physical_rollback_plan_receipt_binding_mismatch")

    @staticmethod
    def _require_rollback_plan_physical_binding(
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        receipt: LocalTextRollbackReceipt,
        metadata: dict[str, object],
    ) -> None:
        expected = (
            receipt.resource_ref,
            plan.root_alias,
            receipt.mutation_operation_id,
            receipt.operation_id,
            receipt.mutation_receipt_fingerprint,
            plan.expected_current_sha256,
            receipt.restored_content_sha256,
        )
        observed = (
            metadata.get("resource_ref"),
            metadata.get("root_alias"),
            receipt.mutation_operation_id,
            metadata.get("rollback_operation_id"),
            metadata.get("mutation_receipt_fingerprint"),
            metadata.get("desired_content_sha256"),
            (
                _EMPTY_SHA256
                if metadata.get("operation") == "create_text"
                else metadata.get("before_content_sha256")
            ),
        )
        if observed != expected:
            raise ValueError("local_text_physical_rollback_plan_journal_binding_mismatch")

    @staticmethod
    def _require_apply_commit_receipt_binding(
        *,
        result: ArtifactPhysicalCanonicalCommitReceiptContract,
        plan: ArtifactPhysicalApplyPlanContract,
        receipt: LocalTextMutationReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> None:
        if not isinstance(result, ArtifactPhysicalCanonicalCommitReceiptContract):
            raise ValueError("local_text_canonical_apply_commit_receipt_invalid")
        require_valid_artifact_physical_canonical_commit_receipt(result)
        expected = (
            "apply",
            plan.saga_id,
            plan.plan_fingerprint,
            str(plan.mission_id),
            plan.artifact_ref,
            plan.artifact_version,
            plan.lineage_root_ref,
            plan.expected_lineage_revision + 1,
            plan.physical_operation_id,
            plan.resource_ref,
            plan.root_alias,
            receipt.receipt_fingerprint,
            None,
            attestation.attestation_fingerprint,
        )
        observed = (
            result.purpose,
            result.saga_id,
            result.plan_fingerprint,
            str(result.mission_id),
            result.artifact_ref,
            result.artifact_version,
            result.lineage_root_ref,
            result.lineage_revision,
            result.physical_operation_id,
            result.resource_ref,
            result.root_alias,
            result.mutation_receipt_fingerprint,
            result.rollback_receipt_fingerprint,
            result.physical_state_attestation_fingerprint,
        )
        if observed != expected or _parse_time(
            result.committed_at,
            "local_text_canonical_apply_commit_time_invalid",
        ) < _parse_time(
            attestation.verified_at,
            "local_text_physical_attestation_time_invalid",
        ):
            raise ValueError("local_text_canonical_apply_commit_receipt_binding_mismatch")

    @staticmethod
    def _require_rollback_commit_receipt_binding(
        *,
        result: ArtifactPhysicalCanonicalCommitReceiptContract,
        plan: ArtifactPhysicalRollbackPlanContract,
        receipt: LocalTextRollbackReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> None:
        if not isinstance(result, ArtifactPhysicalCanonicalCommitReceiptContract):
            raise ValueError("local_text_canonical_rollback_commit_receipt_invalid")
        require_valid_artifact_physical_canonical_commit_receipt(result)
        expected_artifact_ref = (
            plan.restored_artifact_ref if plan.canonical_effect_expected else None
        )
        expected_revision = plan.expected_lineage_revision + int(plan.canonical_effect_expected)
        expected = (
            "rollback",
            plan.saga_id,
            plan.plan_fingerprint,
            str(plan.mission_id),
            expected_artifact_ref,
            plan.lineage_root_ref,
            expected_revision,
            plan.physical_operation_id,
            plan.resource_ref,
            plan.root_alias,
            receipt.mutation_receipt_fingerprint,
            receipt.rollback_receipt_fingerprint,
            attestation.attestation_fingerprint,
        )
        observed = (
            result.purpose,
            result.saga_id,
            result.plan_fingerprint,
            str(result.mission_id),
            result.artifact_ref,
            result.lineage_root_ref,
            result.lineage_revision,
            result.physical_operation_id,
            result.resource_ref,
            result.root_alias,
            result.mutation_receipt_fingerprint,
            result.rollback_receipt_fingerprint,
            result.physical_state_attestation_fingerprint,
        )
        artifact_version_valid = (
            result.artifact_version is not None
            if plan.canonical_effect_expected
            else result.artifact_version is None
        )
        if (
            observed != expected
            or not artifact_version_valid
            or _parse_time(
                result.committed_at,
                "local_text_canonical_rollback_commit_time_invalid",
            )
            < _parse_time(
                attestation.verified_at,
                "local_text_physical_attestation_time_invalid",
            )
        ):
            raise ValueError("local_text_canonical_rollback_commit_receipt_binding_mismatch")

    def _require_receipt_root_alias(self, root_alias: str, resource_ref: str) -> None:
        if self._root_alias_from_resource_ref(resource_ref) != root_alias:
            raise ValueError("local_text_receipt_root_alias_mismatch")

    def _require_persisted_mutation_receipt(
        self,
        receipt: LocalTextMutationReceipt,
    ) -> None:
        verifier = self._mutation_receipt_verifier
        if verifier is None:
            raise ValueError("local_text_mutation_receipt_verifier_not_configured")
        try:
            verified = verifier(receipt)
        except Exception:
            raise ValueError("local_text_mutation_receipt_verification_failed") from None
        if verified is not True:
            raise ValueError("local_text_mutation_receipt_not_verified")

    def _require_persisted_rollback_receipt(
        self,
        receipt: LocalTextRollbackReceipt,
    ) -> None:
        verifier = self._rollback_receipt_verifier
        if verifier is None:
            raise ValueError("local_text_rollback_receipt_verifier_not_configured")
        try:
            verified = verifier(receipt)
        except Exception:
            raise ValueError("local_text_rollback_receipt_verification_failed") from None
        if verified is not True:
            raise ValueError("local_text_rollback_receipt_not_verified")

    def _require_persisted_canonical_commit_receipt(
        self,
        receipt: ArtifactPhysicalCanonicalCommitReceiptContract,
    ) -> None:
        verifier = self._canonical_commit_receipt_verifier
        if verifier is None:
            raise ValueError("local_text_canonical_commit_receipt_verifier_not_configured")
        try:
            verified = verifier(receipt)
        except Exception:
            raise ValueError("local_text_canonical_commit_receipt_verification_failed") from None
        if verified is not True:
            raise ValueError("local_text_canonical_commit_receipt_not_verified")

    def _rollback_is_already_applied(
        self, pinned: _PinnedPosixTarget, metadata: dict[str, object]
    ) -> bool:
        self._require_named_chain_still_pinned(pinned)
        if metadata["operation"] == "create_text":
            try:
                os.stat(
                    pinned.target_name,
                    dir_fd=pinned.parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return True
            return False
        try:
            descriptor = os.open(pinned.target_name, _FILE_READ_FLAGS, dir_fd=pinned.parent_fd)
        except FileNotFoundError:
            return False
        try:
            current = _node_identity(os.fstat(descriptor))
            content = self._read_fd_bounded(descriptor)
            if _digest_bytes(content) != metadata["before_content_sha256"]:
                return False
        finally:
            os.close(descriptor)
        backup = metadata.get("backup_stage_identity")
        return isinstance(backup, dict) and all(
            int(current[key]) == int(backup[key]) for key in ("device", "inode", "mode", "size")
        )

    def _apply_rollback_pinned(
        self,
        pinned: _PinnedPosixTarget,
        metadata: dict[str, object],
        *,
        current: datetime,
        fresh_claim_context: LocalTextExecutionAuthorizationContext | None,
    ) -> None:
        self._require_named_chain_still_pinned(pinned)
        current_identity = self._reconcile_applied(pinned, metadata)
        if current_identity is None or current_identity != metadata["post_write_identity"]:
            raise ValueError("local_text_rollback_later_edit_detected")
        if metadata["operation"] == "create_text":
            if fresh_claim_context is not None:
                self._require_fresh_claim_at_effect_start(fresh_claim_context, self._trusted_now())
            os.unlink(pinned.target_name, dir_fd=pinned.parent_fd)
            return
        backup_name = str(metadata["backup_state_name"])
        if self._state_file_identity(pinned.transaction_fd, backup_name) != metadata.get(
            "backup_stage_identity"
        ):
            raise ValueError("local_text_transaction_backup_stage_changed")
        self._read_state_file(
            pinned.transaction_fd,
            backup_name,
            str(metadata["before_content_sha256"]),
        )
        if fresh_claim_context is not None:
            self._require_fresh_claim_at_effect_start(fresh_claim_context, self._trusted_now())
        os.replace(
            backup_name,
            pinned.target_name,
            src_dir_fd=pinned.transaction_fd,
            dst_dir_fd=pinned.parent_fd,
        )

    def _rollback_receipt_from_rolled_back(self, event: _JournalEvent) -> LocalTextRollbackReceipt:
        metadata = event.metadata
        receipt = LocalTextRollbackReceipt(
            operation_id=str(metadata["rollback_operation_id"]),
            mutation_operation_id=event.operation_id,
            rollback_grant_id=str(metadata["rollback_grant_id"]),
            rollback_claim_id=str(metadata["rollback_claim_id"]),
            mutation_receipt_fingerprint=str(metadata["mutation_receipt_fingerprint"]),
            resource_ref=str(metadata["resource_ref"]),
            restored_content_sha256=(
                _EMPTY_SHA256
                if metadata["operation"] == "create_text"
                else str(metadata["before_content_sha256"])
            ),
            rolled_back_at=event.recorded_at,
            rolled_back_event_fingerprint=event.event_fingerprint,
            rollback_receipt_fingerprint="0" * 64,
        )
        return replace(
            receipt,
            rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(receipt),
        )

    def _rollback_receipt_from_event(self, event: _JournalEvent) -> LocalTextRollbackReceipt:
        rolled_back = _JournalEvent(
            operation_id=event.operation_id,
            sequence=event.sequence - 1,
            phase="rolled_back",
            metadata=event.metadata,
            recorded_at=str(event.metadata["rolled_back_at"]),
            previous_event_fingerprint=None,
            event_fingerprint=str(event.metadata["rolled_back_event_fingerprint"]),
        )
        receipt = self._rollback_receipt_from_rolled_back(rolled_back)
        if receipt.rollback_receipt_fingerprint != event.metadata["rollback_receipt_fingerprint"]:
            raise ValueError("local_text_rollback_receipt_journal_mismatch")
        return receipt
