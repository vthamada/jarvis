from __future__ import annotations

import json
import multiprocessing
import os
import platform
import sqlite3
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest
from operational_service.adapters import (
    LocalTextExecutionAuthorizationContext,
    LocalTextExecutionAuthorizationRequest,
    LocalTextExecutionGrantBinding,
    LocalTextFilePreflightAdapter,
    LocalTextMutationRequest,
    LocalTextRollbackRequest,
    LocalTextTransactionEngine,
    build_execution_authority_fingerprint,
)
from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)

from shared.adapter_permissions import LOCAL_TEXT_FILE_DESCRIPTOR, SEEDED_ADAPTER_REGISTRY
from shared.contracts import (
    AdapterActionRequestContract,
    LocalTextFilePreflightContract,
    LocalTextFilePreflightRequestContract,
    LocalTextMutationReceipt,
)

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
ROLLBACK_NOW = NOW + timedelta(minutes=1)
RECOVERY_NOW = NOW + timedelta(hours=1)
HARD_CRASH_EXIT_CODE = 86
_SUPPORTED_LINUX_MACHINES = {
    "aarch64",
    "amd64",
    "arm64",
    "i386",
    "i686",
    "riscv64",
    "x86_64",
}

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or platform.machine().casefold() not in _SUPPORTED_LINUX_MACHINES,
    reason="Linux renameat2/openat hard-crash backend required",
)


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _binding(seed: str) -> LocalTextExecutionGrantBinding:
    return LocalTextExecutionGrantBinding(
        execution_grant_id=f"execution-grant://hard-crash/{seed}",
        execution_grant_fingerprint=_digest(f"{seed}:grant".encode()),
        action_fingerprint=_digest(f"{seed}:action".encode()),
        execution_request_fingerprint=_digest(f"{seed}:request".encode()),
        intent_fingerprint=_digest(f"{seed}:intent".encode()),
        confirmation_receipt_id=f"confirmation://hard-crash/{seed}",
    )


def _preflight(
    adapter: LocalTextFilePreflightAdapter,
    *,
    operation: str,
    desired_text: str,
    expected_current_sha256: str | None,
) -> LocalTextFilePreflightContract:
    request = LocalTextFilePreflightRequestContract(
        grant_id="adapter-grant://hard-crash/preflight",
        grant_fingerprint="1" * 64,
        action_fingerprint="2" * 64,
        intent_fingerprint="3" * 64,
        descriptor_fingerprint=LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint,
        registry_fingerprint=SEEDED_ADAPTER_REGISTRY.registry_fingerprint,
        subject_ref="operator://local/hard-crash",
        adapter_request=AdapterActionRequestContract(
            adapter_id="local_text_file",
            adapter_version="1.0.0",
            action_kind="prepare_external_action",
            operation=operation,
            resource_scope="configured_text_root",
            resource_ref="text:workspace/docs/note.txt",
        ),
        desired_text=desired_text,
        expected_root_config_fingerprint=adapter.root_config_fingerprint(),
        preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
        diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
        diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
        prepared_at="2026-08-30T11:59:00Z",
        expires_at="2026-08-30T12:04:00Z",
        authorization_expires_at="2026-08-30T12:10:00Z",
        expected_current_sha256=expected_current_sha256,
    )
    return adapter.preflight(request, now=NOW)


class _DurableAuthority:
    """Tiny durable test double for the Governance claim/recovery boundary."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS durable_claims (
                    operation_id TEXT PRIMARY KEY,
                    journal_reservation_fingerprint TEXT NOT NULL UNIQUE,
                    request_json TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    claim_attempts INTEGER NOT NULL,
                    completed_receipt_fingerprint TEXT,
                    interrupted_reason TEXT
                )
                """
            )
            connection.commit()

    def claim(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        current: datetime,
    ) -> _DurableLease:
        request_json = _canonical(asdict(request))
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT request_json, context_json
                FROM durable_claims
                WHERE operation_id = ? OR journal_reservation_fingerprint = ?
                """,
                (request.operation_id, request.journal_reservation_fingerprint),
            ).fetchone()
            if row is not None:
                if row[0] != request_json:
                    raise ValueError("durable test authority claim binding mismatch")
                context = LocalTextExecutionAuthorizationContext(**json.loads(row[1]))
                connection.execute(
                    """
                    UPDATE durable_claims
                    SET claim_attempts = claim_attempts + 1
                    WHERE operation_id = ?
                    """,
                    (request.operation_id,),
                )
                connection.commit()
                return _DurableLease(self, context)
            context = LocalTextExecutionAuthorizationContext(
                purpose=request.purpose,
                operation_id=request.operation_id,
                execution_grant_id=request.execution_grant_id,
                execution_claim_id=(
                    f"execution-claim://hard-crash/{sha256(request_json.encode()).hexdigest()[:24]}"
                ),
                action_kind=request.action_kind,
                operation=request.operation,
                resource_ref=request.resource_ref,
                subject_ref=request.subject_ref,
                preflight_fingerprint=request.preflight_fingerprint,
                before_content_sha256=request.before_content_sha256,
                desired_content_sha256=request.desired_content_sha256,
                root_config_fingerprint=request.root_config_fingerprint,
                claimed_at=_timestamp(current),
                expires_at=_timestamp(current + timedelta(minutes=5)),
                authority_fingerprint="0" * 64,
                execution_grant_fingerprint=request.execution_grant_fingerprint,
                action_fingerprint=request.action_fingerprint,
                execution_request_fingerprint=request.execution_request_fingerprint,
                intent_fingerprint=request.intent_fingerprint,
                confirmation_receipt_id=request.confirmation_receipt_id,
                journal_reservation_fingerprint=(request.journal_reservation_fingerprint),
                mutation_receipt_fingerprint=request.mutation_receipt_fingerprint,
            )
            context = replace(
                context,
                authority_fingerprint=build_execution_authority_fingerprint(context),
            )
            connection.execute(
                """
                INSERT INTO durable_claims (
                    operation_id,
                    journal_reservation_fingerprint,
                    request_json,
                    context_json,
                    claim_attempts
                ) VALUES (?, ?, ?, ?, 1)
                """,
                (
                    request.operation_id,
                    request.journal_reservation_fingerprint,
                    request_json,
                    _canonical(asdict(context)),
                ),
            )
            connection.commit()
        return _DurableLease(self, context)

    def lookup_historical(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        _current: datetime,
    ) -> LocalTextExecutionAuthorizationContext | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT request_json, context_json
                FROM durable_claims
                WHERE operation_id = ? AND journal_reservation_fingerprint = ?
                """,
                (request.operation_id, request.journal_reservation_fingerprint),
            ).fetchone()
        if row is None or row[0] != _canonical(asdict(request)):
            return None
        return LocalTextExecutionAuthorizationContext(**json.loads(row[1]))

    def verify_historical(
        self,
        context: LocalTextExecutionAuthorizationContext,
        _current: datetime,
    ) -> bool:
        stored = self._load_context(context.operation_id)
        return stored == context

    def verify_effect_start(
        self,
        context: LocalTextExecutionAuthorizationContext,
        current: datetime,
    ) -> bool:
        stored = self._load_context(context.operation_id)
        return bool(
            stored == context
            and datetime.strptime(
                context.claimed_at,
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            <= current
            < datetime.strptime(
                context.expires_at,
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
        )

    def complete(self, operation_id: str, receipt_fingerprint: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE durable_claims
                SET completed_receipt_fingerprint = ?
                WHERE operation_id = ?
                """,
                (receipt_fingerprint, operation_id),
            )
            connection.commit()

    def interrupt(self, operation_id: str, reason: str) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE durable_claims
                SET interrupted_reason = ?
                WHERE operation_id = ?
                """,
                (reason, operation_id),
            )
            connection.commit()

    def claim_count(self) -> int:
        with sqlite3.connect(self.database_path) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM durable_claims").fetchone()[0])

    def claim_attempt_count(self) -> int:
        with sqlite3.connect(self.database_path) as connection:
            return int(
                connection.execute(
                    "SELECT COALESCE(SUM(claim_attempts), 0) FROM durable_claims"
                ).fetchone()[0]
            )

    def _load_context(
        self,
        operation_id: str,
    ) -> LocalTextExecutionAuthorizationContext | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT context_json FROM durable_claims WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        return LocalTextExecutionAuthorizationContext(**json.loads(row[0]))


@dataclass
class _DurableLease:
    authority: _DurableAuthority
    _context: LocalTextExecutionAuthorizationContext

    @property
    def context(self) -> LocalTextExecutionAuthorizationContext:
        return self._context

    def complete(self, receipt_fingerprint: str) -> None:
        self.authority.complete(self._context.operation_id, receipt_fingerprint)

    def interrupt(self, reason: str) -> None:
        self.authority.interrupt(self._context.operation_id, reason)


def _setup(tmp_path: Path) -> tuple[Path, Path, Path, LocalTextFilePreflightAdapter]:
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    (root / "docs").mkdir(mode=0o700)
    state = root / ".jarvis-transactions"
    state.mkdir(mode=0o700)
    authority_database = tmp_path / "durable-authority.sqlite3"
    _DurableAuthority(authority_database)
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
        max_bytes=4096,
    )
    return root, state, authority_database, adapter


def _new_engine(
    root: Path,
    state: Path,
    authority_database: Path,
    *,
    current: datetime,
    crash_seam: str | None = None,
) -> LocalTextTransactionEngine:
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
        max_bytes=4096,
    )
    authority = _DurableAuthority(authority_database)

    def inject(observed: str) -> None:
        if observed == crash_seam:
            os._exit(HARD_CRASH_EXIT_CODE)

    return LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots={"workspace": state},
        staging_authorization_verifier=lambda _request, _current: True,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=authority.claim,
        trusted_transaction_clock=lambda: current,
        failure_injector=inject if crash_seam is not None else None,
    )


def _child_execute(
    root_text: str,
    state_text: str,
    authority_database_text: str,
    request: LocalTextMutationRequest,
    crash_seam: str,
) -> None:
    engine = _new_engine(
        Path(root_text),
        Path(state_text),
        Path(authority_database_text),
        current=NOW,
        crash_seam=crash_seam,
    )
    engine.execute(request)
    os._exit(0)


def _child_rollback(
    root_text: str,
    state_text: str,
    authority_database_text: str,
    receipt: LocalTextMutationReceipt,
    rollback_binding: LocalTextExecutionGrantBinding,
) -> None:
    engine = _new_engine(
        Path(root_text),
        Path(state_text),
        Path(authority_database_text),
        current=ROLLBACK_NOW,
        crash_seam="after_rollback_rename_before_flush",
    )
    engine.rollback(
        LocalTextRollbackRequest(
            "operation-hard-crash-rollback",
            receipt,
            rollback_binding,
        )
    )
    os._exit(0)


def _run_hard_crash_child(
    target: Callable[..., None],
    args: tuple[object, ...],
) -> None:
    context = multiprocessing.get_context("fork")
    process = context.Process(target=target, args=args)
    process.start()
    process.join(timeout=20)
    if process.is_alive():
        process.kill()
        process.join(timeout=5)
        pytest.fail("hard-crash subprocess did not terminate")
    assert process.exitcode == HARD_CRASH_EXIT_CODE


def _journal_phases(state: Path) -> list[str]:
    with sqlite3.connect(state / "journal.sqlite3") as connection:
        return [
            str(row[0])
            for row in connection.execute(
                """
                SELECT phase
                FROM local_text_transaction_events
                ORDER BY sequence
                """
            ).fetchall()
        ]


def test_hard_crash_after_claim_before_journal_recovers_once(tmp_path: Path) -> None:
    root, state, authority_database, adapter = _setup(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        desired_text="claim survived\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest(
        "operation-hard-crash-claim",
        preflight,
        "claim survived\n",
        _binding("execute-claim"),
    )

    _run_hard_crash_child(
        _child_execute,
        (
            os.fspath(root),
            os.fspath(state),
            os.fspath(authority_database),
            request,
            "after_execute_claim_before_journal",
        ),
    )

    assert _journal_phases(state)[-1] == "staged"
    assert not (root / "docs" / "note.txt").exists()
    assert _DurableAuthority(authority_database).claim_count() == 1
    assert _DurableAuthority(authority_database).claim_attempt_count() == 1

    restarted = _new_engine(
        root,
        state,
        authority_database,
        current=RECOVERY_NOW,
    )
    recovered = restarted.recover(
        root_alias="workspace",
        operation_id=request.operation_id,
    )
    repeated = restarted.recover(
        root_alias="workspace",
        operation_id=request.operation_id,
    )

    assert repeated == recovered
    assert (root / "docs" / "note.txt").read_bytes() == b"claim survived\n"
    assert _DurableAuthority(authority_database).claim_count() == 1
    assert _DurableAuthority(authority_database).claim_attempt_count() == 1
    phases = _journal_phases(state)
    assert phases.count("claimed") == 1
    assert phases.count("applied") == 1
    assert phases.count("receipt") == 1


def test_hard_crash_after_rename_before_journal_and_fsync_recovers_once(
    tmp_path: Path,
) -> None:
    root, state, authority_database, adapter = _setup(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        desired_text="rename survived\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest(
        "operation-hard-crash-rename",
        preflight,
        "rename survived\n",
        _binding("execute-rename"),
    )

    _run_hard_crash_child(
        _child_execute,
        (
            os.fspath(root),
            os.fspath(state),
            os.fspath(authority_database),
            request,
            "after_rename_before_directory_flush",
        ),
    )

    assert _journal_phases(state)[-1] == "claimed"
    assert (root / "docs" / "note.txt").read_bytes() == b"rename survived\n"
    assert _DurableAuthority(authority_database).claim_count() == 1
    assert _DurableAuthority(authority_database).claim_attempt_count() == 1

    restarted = _new_engine(
        root,
        state,
        authority_database,
        current=RECOVERY_NOW,
    )
    recovered = restarted.recover(
        root_alias="workspace",
        operation_id=request.operation_id,
    )
    repeated = restarted.recover(
        root_alias="workspace",
        operation_id=request.operation_id,
    )

    assert repeated == recovered
    assert (root / "docs" / "note.txt").read_bytes() == b"rename survived\n"
    assert _DurableAuthority(authority_database).claim_count() == 1
    assert _DurableAuthority(authority_database).claim_attempt_count() == 1
    phases = _journal_phases(state)
    assert phases.count("renamed") == 1
    assert phases.count("applied") == 1
    assert phases.count("receipt") == 1


def test_hard_crash_after_rollback_rename_before_journal_and_fsync_recovers_once(
    tmp_path: Path,
) -> None:
    root, state, authority_database, adapter = _setup(tmp_path)
    target = root / "docs" / "note.txt"
    target.write_bytes(b"before\n")
    preflight = _preflight(
        adapter,
        operation="replace_text",
        desired_text="after\n",
        expected_current_sha256=_digest(b"before\n"),
    )
    mutation_operation_id = "operation-hard-crash-rollback-source"
    apply_engine = _new_engine(
        root,
        state,
        authority_database,
        current=NOW,
    )
    mutation_receipt = apply_engine.execute(
        LocalTextMutationRequest(
            mutation_operation_id,
            preflight,
            "after\n",
            _binding("execute-before-rollback"),
        )
    )
    assert target.read_bytes() == b"after\n"
    assert _DurableAuthority(authority_database).claim_count() == 1
    assert _DurableAuthority(authority_database).claim_attempt_count() == 1

    _run_hard_crash_child(
        _child_rollback,
        (
            os.fspath(root),
            os.fspath(state),
            os.fspath(authority_database),
            mutation_receipt,
            _binding("rollback"),
        ),
    )

    assert _journal_phases(state)[-1] == "rollback_claimed"
    assert target.read_bytes() == b"before\n"
    assert _DurableAuthority(authority_database).claim_count() == 2
    assert _DurableAuthority(authority_database).claim_attempt_count() == 2

    restarted = _new_engine(
        root,
        state,
        authority_database,
        current=RECOVERY_NOW,
    )
    recovered = restarted.recover_rollback(
        root_alias="workspace",
        operation_id=mutation_operation_id,
    )
    repeated = restarted.recover_rollback(
        root_alias="workspace",
        operation_id=mutation_operation_id,
    )

    assert repeated == recovered
    assert recovered.operation_id == "operation-hard-crash-rollback"
    assert recovered.mutation_operation_id == mutation_operation_id
    assert target.read_bytes() == b"before\n"
    assert _DurableAuthority(authority_database).claim_count() == 2
    assert _DurableAuthority(authority_database).claim_attempt_count() == 2
    phases = _journal_phases(state)
    assert phases.count("rollback_renamed") == 1
    assert phases.count("rolled_back") == 1
    assert phases.count("rollback_receipt") == 1
