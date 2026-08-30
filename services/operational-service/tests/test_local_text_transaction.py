from __future__ import annotations

import ctypes
import errno
import inspect
import multiprocessing
import os
import sqlite3
import threading
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import operational_service.adapters.local_text_transaction as transaction_module
import pytest
from operational_service.adapters import (
    InjectedTransactionFailure,
    LocalTextExecutionAuthorizationContext,
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
    LocalTextFilePreflightRequestContract,
)

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _binding(seed: str = "a") -> LocalTextExecutionGrantBinding:
    return LocalTextExecutionGrantBinding(
        execution_grant_id=f"execution-grant://test/{seed}",
        execution_grant_fingerprint=_digest(f"{seed}:grant".encode()),
        action_fingerprint=_digest(f"{seed}:action".encode()),
        execution_request_fingerprint=_digest(f"{seed}:request".encode()),
        intent_fingerprint=_digest(f"{seed}:intent".encode()),
        confirmation_receipt_id=f"confirmation://test/{seed}",
    )


class _Clock:
    def __init__(self, current: datetime = NOW, *, step: timedelta = timedelta(0)) -> None:
        self.current = current
        self.step = step

    def __call__(self) -> datetime:
        observed = self.current
        self.current += self.step
        return observed


class _Lease:
    def __init__(self, context: LocalTextExecutionAuthorizationContext) -> None:
        self._context = context
        self.completed: list[str] = []
        self.interrupted: list[str] = []

    @property
    def context(self) -> LocalTextExecutionAuthorizationContext:
        return self._context

    def complete(self, receipt_fingerprint: str) -> None:
        self.completed.append(receipt_fingerprint)

    def interrupt(self, reason: str) -> None:
        self.interrupted.append(reason)


class _Authority:
    def __init__(self) -> None:
        self.requests = []
        self.leases: list[_Lease] = []
        self.historical = []
        self.lookup_result = None
        self.effect_start_allowed = True
        self.effect_starts = []
        self.clock = _Clock()

    def claim(self, request, current: datetime) -> _Lease:
        self.requests.append(request)
        context = LocalTextExecutionAuthorizationContext(
            purpose=request.purpose,
            operation_id=request.operation_id,
            execution_grant_id=request.execution_grant_id,
            execution_claim_id=f"claim://test/{len(self.requests)}",
            action_kind=request.action_kind,
            operation=request.operation,
            resource_ref=request.resource_ref,
            subject_ref=request.subject_ref,
            preflight_fingerprint=request.preflight_fingerprint,
            before_content_sha256=request.before_content_sha256,
            desired_content_sha256=request.desired_content_sha256,
            root_config_fingerprint=request.root_config_fingerprint,
            claimed_at=current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            expires_at=(current + timedelta(minutes=5))
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            authority_fingerprint="0" * 64,
            execution_grant_fingerprint=request.execution_grant_fingerprint,
            action_fingerprint=request.action_fingerprint,
            execution_request_fingerprint=request.execution_request_fingerprint,
            intent_fingerprint=request.intent_fingerprint,
            confirmation_receipt_id=request.confirmation_receipt_id,
            journal_reservation_fingerprint=request.journal_reservation_fingerprint,
            mutation_receipt_fingerprint=request.mutation_receipt_fingerprint,
        )
        context = replace(
            context,
            authority_fingerprint=build_execution_authority_fingerprint(context),
        )
        self.lookup_result = context
        lease = _Lease(context)
        self.leases.append(lease)
        return lease

    def verify_historical(self, context, current: datetime) -> bool:
        self.historical.append((context, current))
        return True

    def verify_effect_start(self, context, current: datetime) -> bool:
        self.effect_starts.append((context, current))
        return self.effect_start_allowed

    def lookup_historical(self, request, _current):
        if self.lookup_result is None:
            return None
        if self.lookup_result.operation_id != request.operation_id:
            return None
        return self.lookup_result


def _preflight(
    adapter: LocalTextFilePreflightAdapter,
    *,
    operation: str,
    relative_path: str,
    desired_text: str,
    expected_current_sha256: str | None,
    root_alias: str = "workspace",
):
    request = LocalTextFilePreflightRequestContract(
        grant_id="adapter-grant://test/preflight",
        grant_fingerprint="1" * 64,
        action_fingerprint="2" * 64,
        intent_fingerprint="3" * 64,
        descriptor_fingerprint=LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint,
        registry_fingerprint=SEEDED_ADAPTER_REGISTRY.registry_fingerprint,
        subject_ref="operator://local/tester",
        adapter_request=AdapterActionRequestContract(
            adapter_id="local_text_file",
            adapter_version="1.0.0",
            action_kind="prepare_external_action",
            operation=operation,
            resource_scope="configured_text_root",
            resource_ref=f"text:{root_alias}/{relative_path}",
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


def _harness(tmp_path: Path, *, failure_injector=None, staging=True):
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    (root / "docs").mkdir()
    state = root / ".jarvis-transactions"
    state.mkdir(mode=0o700)
    if os.name != "nt":
        state.chmod(0o700)
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
        max_bytes=4096,
    )
    authority = _Authority()
    staging_calls = []

    def staging_verifier(request, current):
        staging_calls.append((request, current))
        return staging

    engine = LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots={"workspace": state},
        staging_authorization_verifier=staging_verifier,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=authority.claim,
        trusted_transaction_clock=authority.clock,
        failure_injector=failure_injector,
    )
    return root, state, adapter, engine, authority, staging_calls


def _journal_rows(state: Path) -> list[tuple[str, str]]:
    with sqlite3.connect(state / "journal.sqlite3") as connection:
        return connection.execute(
            "SELECT phase, metadata_json FROM local_text_transaction_events ORDER BY sequence"
        ).fetchall()


def _state_tree_snapshot(state: Path) -> dict[str, tuple[int, bytes | None]]:
    snapshot: dict[str, tuple[int, bytes | None]] = {}
    for path in sorted(state.rglob("*")):
        relative = path.relative_to(state).as_posix()
        observed = path.lstat()
        snapshot[relative] = (
            int(observed.st_mode),
            path.read_bytes() if path.is_file() else None,
        )
    return snapshot


def _process_execute_same_operation(
    root_text: str,
    state_text: str,
    preflight,
    binding: LocalTextExecutionGrantBinding,
    counter,
    barrier,
    results,
) -> None:
    root = Path(root_text)
    state = Path(state_text)
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
        max_bytes=4096,
    )
    authority = _Authority()

    def claim(request, current):
        with counter.get_lock():
            counter.value += 1
        return authority.claim(request, current)

    engine = LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots={"workspace": state},
        staging_authorization_verifier=lambda _request, _current: True,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=claim,
        trusted_transaction_clock=authority.clock,
    )
    barrier.wait()
    try:
        receipt = engine.execute(
            LocalTextMutationRequest("operation-process", preflight, "process once\n", binding),
        )
    except Exception as exc:  # pragma: no cover - asserted in parent process
        results.put(("error", repr(exc)))
    else:
        results.put(("ok", receipt.receipt_fingerprint))


def test_execution_authority_fingerprint_is_deterministic_and_tamper_evident() -> None:
    context = LocalTextExecutionAuthorizationContext(
        purpose="execute",
        operation_id="operation-fingerprint",
        execution_grant_id="execution-grant://test/a",
        execution_claim_id="claim://test/1",
        action_kind="execute_external_action",
        operation="create_text",
        resource_ref="text:workspace/docs/note.txt",
        subject_ref="operator://local/tester",
        preflight_fingerprint="1" * 64,
        before_content_sha256=_digest(b""),
        desired_content_sha256=_digest(b"value\n"),
        root_config_fingerprint="2" * 64,
        claimed_at="2026-08-30T12:00:00Z",
        expires_at="2026-08-30T12:05:00Z",
        authority_fingerprint="0" * 64,
        execution_grant_fingerprint="3" * 64,
        action_fingerprint="4" * 64,
        execution_request_fingerprint="5" * 64,
        intent_fingerprint="6" * 64,
        confirmation_receipt_id="confirmation://test/a",
        journal_reservation_fingerprint="7" * 64,
    )
    fingerprint = build_execution_authority_fingerprint(context)
    sealed = replace(context, authority_fingerprint=fingerprint)

    assert build_execution_authority_fingerprint(sealed) == fingerprint
    assert (
        build_execution_authority_fingerprint(replace(sealed, desired_content_sha256="8" * 64))
        != fingerprint
    )


def test_linux_create_noreplace_uses_syscall_when_libc_symbol_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, ...]] = []

    class FakeSyscall:
        restype = None

        def __call__(self, *arguments):
            calls.append(arguments)
            return 0

    class FakeLibc:
        syscall = FakeSyscall()

    monkeypatch.setattr(transaction_module.sys, "platform", "linux")
    monkeypatch.setattr(transaction_module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(ctypes, "CDLL", lambda *_args, **_kwargs: FakeLibc())

    LocalTextTransactionEngine._rename_noreplace_linux(
        11,
        "stage",
        12,
        "target.txt",
    )

    assert len(calls) == 1
    assert calls[0][0].value == 316
    assert calls[0][1].value == 11
    assert calls[0][3].value == 12
    assert calls[0][5].value == 1


def test_cross_device_path_observation_fails_closed() -> None:
    with pytest.raises(ValueError, match="path_cross_device"):
        transaction_module._require_same_device(SimpleNamespace(st_dev=22), 11)


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_transaction_time_is_constructor_injected_and_invalid_clock_precedes_state_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="clocked\n",
        expected_current_sha256=None,
    )
    before = _state_tree_snapshot(state)
    authority.clock.current = NOW.replace(tzinfo=None)
    lock_attempted = False

    def fail_if_lock_is_attempted(_alias: str, _resource_ref: str):
        nonlocal lock_attempted
        lock_attempted = True
        raise AssertionError("resource lock must follow trusted clock validation")

    monkeypatch.setattr(engine, "_resource_lock", fail_if_lock_is_attempted)

    with pytest.raises(ValueError, match="trusted_transaction_clock_invalid"):
        engine.execute(
            LocalTextMutationRequest("operation-clock", preflight, "clocked\n", _binding())
        )

    assert "now" not in inspect.signature(engine.execute).parameters
    assert "now" not in inspect.signature(engine.recover).parameters
    assert "now" not in inspect.signature(engine.rollback).parameters
    assert "now" not in inspect.signature(engine.recover_rollback).parameters
    assert _state_tree_snapshot(state) == before
    assert not lock_attempted
    assert not (root / "docs" / "note.txt").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_claim_validation_refreshes_trusted_clock_after_provider_returns(
    tmp_path: Path,
) -> None:
    root, _state, adapter, engine, authority, _calls = _harness(tmp_path)
    original_claim = authority.claim

    def delayed_claim(request, current: datetime):
        authority.clock.current = current + timedelta(seconds=10)
        return original_claim(request, authority.clock.current)

    engine._authorization_lease_provider = delayed_claim
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="delayed claim\n",
        expected_current_sha256=None,
    )

    receipt = engine.execute(
        LocalTextMutationRequest(
            "operation-delayed-claim", preflight, "delayed claim\n", _binding()
        )
    )

    assert (root / "docs" / "note.txt").read_bytes() == b"delayed claim\n"
    assert _timestamp(receipt.committed_at) >= _timestamp(authority.leases[0].context.claimed_at)


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_staging_verifier_rejection_has_zero_state_or_target_delta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state, adapter, engine, authority, calls = _harness(tmp_path, staging=False)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="hello\n",
        expected_current_sha256=None,
    )
    before = _state_tree_snapshot(state)
    lock_attempted = False

    def fail_if_lock_is_attempted(_alias: str, _resource_ref: str):
        nonlocal lock_attempted
        lock_attempted = True
        raise AssertionError("resource lock must follow staging verification")

    monkeypatch.setattr(engine, "_resource_lock", fail_if_lock_is_attempted)

    with pytest.raises(ValueError, match="staging_authorization_not_verified"):
        engine.execute(
            LocalTextMutationRequest("operation-1", preflight, "hello\n", _binding()),
        )

    assert _state_tree_snapshot(state) == before
    assert not (root / "docs" / "note.txt").exists()
    assert len(calls) == 1
    assert authority.requests == []
    assert not lock_attempted


@pytest.mark.skipif(os.name != "nt", reason="Windows fail-closed contract")
def test_windows_backend_fails_closed_before_reservation(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    state = root / ".jarvis-transactions"
    state.mkdir()
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
    )

    with pytest.raises(ValueError, match="backend_not_handle_safe"):
        LocalTextTransactionEngine(
            preflight_adapter=adapter,
            transaction_roots={"workspace": state},
            staging_authorization_verifier=lambda _request, _current: True,
            effect_start_claim_verifier=lambda _context, _current: True,
            historical_claim_lookup=lambda _request, _current: None,
            historical_claim_verifier=lambda _context, _current: True,
            authorization_lease_provider=lambda _request, _current: None,
            trusted_transaction_clock=lambda: NOW,
        )

    assert list(state.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX nofollow journal bootstrap")
def test_preplanted_journal_symlink_is_rejected_without_target_write(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    state = root / ".jarvis-transactions"
    state.mkdir(mode=0o700)
    state.chmod(0o700)
    outside = tmp_path / "outside.db"
    outside.write_bytes(b"untouched")
    (state / "journal.sqlite3").symlink_to(outside)
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
    )

    with pytest.raises(ValueError, match="journal_file_not_safe"):
        LocalTextTransactionEngine(
            preflight_adapter=adapter,
            transaction_roots={"workspace": state},
            staging_authorization_verifier=lambda _request, _current: True,
            effect_start_claim_verifier=lambda _context, _current: True,
            historical_claim_lookup=lambda _request, _current: None,
            historical_claim_verifier=lambda _context, _current: True,
            authorization_lease_provider=lambda _request, _current: None,
            trusted_transaction_clock=lambda: NOW,
        )

    assert outside.read_bytes() == b"untouched"


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership boundary")
@pytest.mark.parametrize("unsafe_mode", [0o770, 0o777])
def test_posix_shared_writable_root_fails_before_journal(tmp_path: Path, unsafe_mode: int) -> None:
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    state = root / ".jarvis-transactions"
    state.mkdir(mode=0o700)
    root.chmod(unsafe_mode)
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
    )

    with pytest.raises(ValueError, match="directory_not_exclusive"):
        LocalTextTransactionEngine(
            preflight_adapter=adapter,
            transaction_roots={"workspace": state},
            staging_authorization_verifier=lambda _request, _current: True,
            effect_start_claim_verifier=lambda _context, _current: True,
            historical_claim_lookup=lambda _request, _current: None,
            historical_claim_verifier=lambda _context, _current: True,
            authorization_lease_provider=lambda _request, _current: None,
            trusted_transaction_clock=lambda: NOW,
        )

    assert list(state.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership boundary")
def test_posix_nonsticky_world_writable_root_anchor_fails_closed(tmp_path: Path) -> None:
    anchor = tmp_path / "anchor"
    anchor.mkdir(mode=0o700)
    root = anchor / "root"
    root.mkdir(mode=0o700)
    state = root / ".jarvis-transactions"
    state.mkdir(mode=0o700)
    anchor.chmod(0o777)
    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=lambda _request, _current: True,
    )

    with pytest.raises(ValueError, match="root_anchor_not_exclusive"):
        LocalTextTransactionEngine(
            preflight_adapter=adapter,
            transaction_roots={"workspace": state},
            staging_authorization_verifier=lambda _request, _current: True,
            effect_start_claim_verifier=lambda _context, _current: True,
            historical_claim_lookup=lambda _request, _current: None,
            historical_claim_verifier=lambda _context, _current: True,
            authorization_lease_provider=lambda _request, _current: None,
            trusted_transaction_clock=lambda: NOW,
        )

    assert list(state.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_create_is_exactly_once_and_content_free_journal(tmp_path: Path) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    authority.clock.step = timedelta(microseconds=5_000)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="secret value\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest("operation-create", preflight, "secret value\n", _binding())

    first = engine.execute(request)
    authority.clock.current = NOW + timedelta(hours=1)
    second = engine.recover(
        root_alias="workspace",
        operation_id="operation-create",
    )

    assert first == second
    assert (root / "docs" / "note.txt").read_bytes() == b"secret value\n"
    assert len(authority.requests) == 1
    assert _timestamp(first.committed_at) >= _timestamp(authority.leases[0].context.claimed_at)
    assert all("secret value" not in metadata for _phase, metadata in _journal_rows(state))


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
@pytest.mark.parametrize("operation", ["create_text", "replace_text"])
def test_posix_fresh_effect_start_rejection_has_zero_effect_and_historical_recovery(
    tmp_path: Path,
    operation: str,
) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    target = root / "docs" / "note.txt"
    before = b"before\n"
    if operation == "replace_text":
        target.write_bytes(before)
    preflight = _preflight(
        adapter,
        operation=operation,
        relative_path="docs/note.txt",
        desired_text="after\n",
        expected_current_sha256=(_digest(before) if operation == "replace_text" else None),
    )
    authority.effect_start_allowed = False

    with pytest.raises(ValueError, match="effect_start_claim_not_verified"):
        engine.execute(
            LocalTextMutationRequest("operation-effect-start", preflight, "after\n", _binding()),
        )

    assert _journal_rows(state)[-1][0] == "claimed"
    if operation == "replace_text":
        assert target.read_bytes() == before
    else:
        assert not target.exists()
    assert len(authority.effect_starts) == 1

    authority.clock.current = NOW + timedelta(hours=1)
    recovered = engine.recover(
        root_alias="workspace",
        operation_id="operation-effect-start",
    )

    assert target.read_bytes() == b"after\n"
    assert recovered.mutation_status == "applied"
    assert len(authority.effect_starts) == 1


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_fresh_rollback_effect_start_rejection_is_recovered_historically(
    tmp_path: Path,
) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    target = root / "docs" / "note.txt"
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="created\n",
        expected_current_sha256=None,
    )
    receipt = engine.execute(
        LocalTextMutationRequest("operation-create", preflight, "created\n", _binding()),
    )
    authority.effect_start_allowed = False

    with pytest.raises(ValueError, match="effect_start_claim_not_verified"):
        engine.rollback(
            LocalTextRollbackRequest("operation-rollback", receipt, _binding("rollback")),
        )

    assert _journal_rows(state)[-1][0] == "rollback_claimed"
    assert target.read_bytes() == b"created\n"
    assert len(authority.effect_starts) == 2

    authority.clock.current = NOW + timedelta(hours=1)
    recovered = engine.recover_rollback(
        root_alias="workspace",
        operation_id="operation-create",
    )

    assert not target.exists()
    assert recovered.operation_id == "operation-rollback"
    assert len(authority.effect_starts) == 2


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
@pytest.mark.parametrize(
    "seam",
    [
        "after_stage_durable",
        "after_claim",
        "after_rename_before_directory_flush",
        "after_directory_flush_before_applied",
        "after_applied_before_receipt",
    ],
)
def test_posix_retry_or_recovery_at_crash_boundaries(tmp_path: Path, seam: str) -> None:
    fired = False

    def inject(observed: str) -> None:
        nonlocal fired
        if observed == seam and not fired:
            fired = True
            raise InjectedTransactionFailure(seam)

    root, _state, adapter, engine, authority, _calls = _harness(tmp_path, failure_injector=inject)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="recover me\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest("operation-recover", preflight, "recover me\n", _binding())
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(request)
    engine._failure_injector = None

    if seam == "after_stage_durable":
        receipt = engine.recover(root_alias="workspace", operation_id="operation-recover")
    else:
        authority.clock.current = NOW + timedelta(minutes=30)
        receipt = engine.recover(
            root_alias="workspace",
            operation_id="operation-recover",
        )

    assert receipt.desired_content_sha256 == _digest(b"recover me\n")
    assert (root / "docs" / "note.txt").read_bytes() == b"recover me\n"
    assert len(authority.requests) == 1
    if seam != "after_stage_durable":
        assert authority.historical


@pytest.mark.skipif(os.name == "nt", reason="POSIX durable recovery backend")
def test_posix_preclaim_recovery_rejects_before_recreating_missing_lock(
    tmp_path: Path,
) -> None:
    def stop_after_stage(seam: str) -> None:
        if seam == "after_stage_durable":
            raise InjectedTransactionFailure(seam)

    root, state, adapter, engine, authority, _calls = _harness(
        tmp_path, failure_injector=stop_after_stage
    )
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="preclaim\n",
        expected_current_sha256=None,
    )
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(
            LocalTextMutationRequest("operation-preclaim", preflight, "preclaim\n", _binding())
        )
    lock_name = _digest(b"workspace:text:workspace/docs/note.txt") + ".lock"
    (state / lock_name).unlink()
    engine._failure_injector = None
    engine._staging_authorization_verifier = lambda _request, _current: False
    before = _state_tree_snapshot(state)

    with pytest.raises(ValueError, match="staging_authorization_not_verified"):
        engine.recover(root_alias="workspace", operation_id="operation-preclaim")

    assert _state_tree_snapshot(state) == before
    assert not (state / lock_name).exists()
    assert not (root / "docs" / "note.txt").exists()
    assert authority.requests == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_replace_backup_and_distinct_grant_rollback_exact_bytes(tmp_path: Path) -> None:
    root, _state, adapter, engine, authority, calls = _harness(tmp_path)
    authority.clock.step = timedelta(microseconds=5_000)
    before = "antes\nbytes\n".encode()
    target = root / "docs" / "note.txt"
    target.write_bytes(before)
    preflight = _preflight(
        adapter,
        operation="replace_text",
        relative_path="docs/note.txt",
        desired_text="after\n",
        expected_current_sha256=_digest(before),
    )
    receipt = engine.execute(
        LocalTextMutationRequest("operation-replace", preflight, "after\n", _binding("a")),
    )

    rollback = engine.rollback(
        LocalTextRollbackRequest("operation-rollback", receipt, _binding("e")),
    )

    assert target.read_bytes() == before
    assert rollback.restored_content_sha256 == _digest(before)
    assert rollback.operation_id == "operation-rollback"
    assert rollback.mutation_operation_id == "operation-replace"
    assert [item.operation_id for item in authority.requests] == [
        "operation-replace",
        "operation-rollback",
    ]
    assert [item.purpose for item in authority.requests] == ["execute", "rollback"]
    assert authority.requests[1].mutation_receipt_fingerprint == receipt.receipt_fingerprint
    rollback_staging = calls[-1][0]
    assert rollback_staging.purpose == "rollback"
    assert rollback_staging.operation == "rollback_text"
    assert rollback_staging.operation_id == "operation-rollback"
    assert rollback_staging.before_content_sha256 == _digest(b"after\n")
    assert rollback_staging.desired_content_sha256 == _digest(before)
    assert authority.requests[1].before_content_sha256 == _digest(b"after\n")
    assert authority.requests[1].desired_content_sha256 == _digest(before)
    assert _timestamp(rollback.rolled_back_at) >= _timestamp(authority.leases[1].context.claimed_at)


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_rollback_is_scoped_to_receipt_root_when_operation_id_collides(
    tmp_path: Path,
) -> None:
    roots: dict[str, Path] = {}
    states: dict[str, Path] = {}
    for alias in ("alpha", "beta"):
        root = tmp_path / alias
        root.mkdir(mode=0o700)
        (root / "docs").mkdir(mode=0o700)
        state = root / ".jarvis-transactions"
        state.mkdir(mode=0o700)
        roots[alias] = root
        states[alias] = state
    adapter = LocalTextFilePreflightAdapter(
        roots=roots,
        verified_context_verifier=lambda _request, _current: True,
        max_bytes=4096,
    )
    authority = _Authority()
    engine = LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots=states,
        staging_authorization_verifier=lambda _request, _current: True,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=authority.claim,
        trusted_transaction_clock=authority.clock,
    )
    alpha_preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="alpha\n",
        expected_current_sha256=None,
        root_alias="alpha",
    )
    receipt = engine.execute(
        LocalTextMutationRequest("shared-operation", alpha_preflight, "alpha\n", _binding("a"))
    )

    def stop_beta_after_staging(seam: str) -> None:
        if seam == "after_stage_durable":
            raise InjectedTransactionFailure(seam)

    engine._failure_injector = stop_beta_after_staging
    beta_preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="beta\n",
        expected_current_sha256=None,
        root_alias="beta",
    )
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(
            LocalTextMutationRequest("shared-operation", beta_preflight, "beta\n", _binding("b"))
        )
    engine._failure_injector = None

    rollback = engine.rollback(
        LocalTextRollbackRequest("alpha-rollback", receipt, _binding("rollback"))
    )

    assert rollback.resource_ref == "text:alpha/docs/note.txt"
    assert not (roots["alpha"] / "docs" / "note.txt").exists()
    assert not (roots["beta"] / "docs" / "note.txt").exists()
    assert _journal_rows(states["beta"])[-1][0] == "desired_durable"


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_rollback_refuses_same_bytes_in_replacement_inode(tmp_path: Path) -> None:
    root, _state, adapter, engine, authority, _calls = _harness(tmp_path)
    target = root / "docs" / "note.txt"
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="same bytes\n",
        expected_current_sha256=None,
    )
    receipt = engine.execute(
        LocalTextMutationRequest("operation-create", preflight, "same bytes\n", _binding("a")),
    )
    replacement = root / "docs" / "replacement.txt"
    replacement.write_bytes(b"same bytes\n")
    os.replace(replacement, target)

    with pytest.raises(ValueError, match="later_edit_detected"):
        engine.rollback(
            LocalTextRollbackRequest("operation-rollback", receipt, _binding("e")),
        )

    assert target.read_bytes() == b"same bytes\n"
    assert len(authority.requests) == 1


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_rollback_verifier_rejects_before_any_transaction_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="keep\n",
        expected_current_sha256=None,
    )
    receipt = engine.execute(
        LocalTextMutationRequest("operation-create", preflight, "keep\n", _binding("a")),
    )
    before = _journal_rows(state)
    engine._staging_authorization_verifier = lambda _request, _current: False
    lookup_attempted = False

    def fail_if_operation_lookup_is_attempted(_alias: str, _operation_id: str):
        nonlocal lookup_attempted
        lookup_attempted = True
        raise AssertionError("operation lookup must follow rollback staging verification")

    monkeypatch.setattr(engine, "_load_events", fail_if_operation_lookup_is_attempted)

    with pytest.raises(ValueError, match="staging_authorization_not_verified"):
        engine.rollback(
            LocalTextRollbackRequest("operation-rollback", receipt, _binding("e")),
        )

    assert _journal_rows(state) == before
    assert (root / "docs" / "note.txt").read_bytes() == b"keep\n"
    assert len(authority.requests) == 1
    assert not lookup_attempted


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
@pytest.mark.parametrize(
    "seam",
    [
        "after_rollback_claim",
        "after_rollback_rename_before_flush",
        "after_rollback_renamed_before_directory_flush",
        "after_rollback_flush_before_applied",
        "after_rollback_applied_before_receipt",
    ],
)
def test_posix_rollback_recovery_is_idempotent_at_each_phase(tmp_path: Path, seam: str) -> None:
    fired = False

    def inject(observed: str) -> None:
        nonlocal fired
        if observed == seam and not fired:
            fired = True
            raise InjectedTransactionFailure(seam)

    root, _state, adapter, engine, authority, _calls = _harness(tmp_path)
    target = root / "docs" / "note.txt"
    target.write_bytes(b"before\n")
    preflight = _preflight(
        adapter,
        operation="replace_text",
        relative_path="docs/note.txt",
        desired_text="after\n",
        expected_current_sha256=_digest(b"before\n"),
    )
    receipt = engine.execute(
        LocalTextMutationRequest("operation-replace", preflight, "after\n", _binding("a")),
    )
    engine._failure_injector = inject
    with pytest.raises(InjectedTransactionFailure):
        engine.rollback(
            LocalTextRollbackRequest("operation-rollback", receipt, _binding("e")),
        )
    engine._failure_injector = None

    authority.clock.current = NOW + timedelta(hours=1)
    recovered = engine.recover_rollback(
        root_alias="workspace",
        operation_id="operation-replace",
    )

    assert target.read_bytes() == b"before\n"
    assert recovered.restored_content_sha256 == _digest(b"before\n")
    assert len(authority.requests) == 2
    assert authority.historical[-1][0].operation_id == "operation-rollback"


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_restart_after_claim_uses_historical_claim_not_a_second_claim(
    tmp_path: Path,
) -> None:
    def inject(observed: str) -> None:
        if observed == "after_claim":
            raise InjectedTransactionFailure(observed)

    root, state, adapter, engine, authority, _calls = _harness(tmp_path, failure_injector=inject)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="restart\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest("operation-restart", preflight, "restart\n", _binding())
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(request)
    restarted = LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots={"workspace": state},
        staging_authorization_verifier=lambda _request, _current: True,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=authority.claim,
        trusted_transaction_clock=authority.clock,
    )

    authority.clock.current = NOW + timedelta(hours=2)
    restarted.recover(
        root_alias="workspace",
        operation_id="operation-restart",
    )

    assert (root / "docs" / "note.txt").read_bytes() == b"restart\n"
    assert len(authority.requests) == 1
    assert authority.historical


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_restart_reconciles_claim_returned_before_local_claim_event(
    tmp_path: Path,
) -> None:
    def inject(observed: str) -> None:
        if observed == "after_execute_claim_before_journal":
            raise InjectedTransactionFailure(observed)

    root, state, adapter, engine, authority, _calls = _harness(tmp_path, failure_injector=inject)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="cross store\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest(
        "operation-cross-store", preflight, "cross store\n", _binding()
    )
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(request)
    assert _journal_rows(state)[-1][0] == "staged"
    restarted = LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots={"workspace": state},
        staging_authorization_verifier=lambda _request, _current: False,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=authority.claim,
        trusted_transaction_clock=authority.clock,
    )

    authority.clock.current = NOW + timedelta(days=1)
    restarted.recover(
        root_alias="workspace",
        operation_id="operation-cross-store",
    )

    assert (root / "docs" / "note.txt").read_bytes() == b"cross store\n"
    assert len(authority.requests) == 1
    assert authority.historical


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_restart_reconciles_rollback_claim_before_local_event(
    tmp_path: Path,
) -> None:
    root, state, adapter, engine, authority, _calls = _harness(tmp_path)
    target = root / "docs" / "note.txt"
    target.write_bytes(b"before\n")
    preflight = _preflight(
        adapter,
        operation="replace_text",
        relative_path="docs/note.txt",
        desired_text="after\n",
        expected_current_sha256=_digest(b"before\n"),
    )
    receipt = engine.execute(
        LocalTextMutationRequest("operation-replace", preflight, "after\n", _binding("a")),
    )

    def inject(observed: str) -> None:
        if observed == "after_rollback_claim_before_journal":
            raise InjectedTransactionFailure(observed)

    engine._failure_injector = inject
    with pytest.raises(InjectedTransactionFailure):
        engine.rollback(
            LocalTextRollbackRequest("operation-rollback", receipt, _binding("e")),
        )
    assert _journal_rows(state)[-1][0] == "rollback_reserved"
    restarted = LocalTextTransactionEngine(
        preflight_adapter=adapter,
        transaction_roots={"workspace": state},
        staging_authorization_verifier=lambda _request, _current: False,
        effect_start_claim_verifier=authority.verify_effect_start,
        historical_claim_lookup=authority.lookup_historical,
        historical_claim_verifier=authority.verify_historical,
        authorization_lease_provider=authority.claim,
        trusted_transaction_clock=authority.clock,
    )

    authority.clock.current = NOW + timedelta(days=1)
    restarted.recover_rollback(
        root_alias="workspace",
        operation_id="operation-replace",
    )

    assert target.read_bytes() == b"before\n"
    assert len(authority.requests) == 2
    assert authority.historical[-1][0].operation_id == "operation-rollback"


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_threads_retry_same_operation_with_one_claim_and_one_mutation(
    tmp_path: Path,
) -> None:
    root, _state, adapter, engine, authority, _calls = _harness(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="once\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest("operation-concurrent", preflight, "once\n", _binding())
    receipts = []
    errors = []

    def run() -> None:
        try:
            receipts.append(engine.execute(request))
        except Exception as exc:  # pragma: no cover - assertion reports the value
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(set(receipts)) == 1
    assert len(authority.requests) == 1
    assert (root / "docs" / "note.txt").read_bytes() == b"once\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX fork/openat physical backend")
def test_posix_processes_retry_same_operation_with_one_claim_and_one_mutation(
    tmp_path: Path,
) -> None:
    root, state, adapter, _engine, _authority, _calls = _harness(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="process once\n",
        expected_current_sha256=None,
    )
    context = multiprocessing.get_context("fork")
    counter = context.Value("i", 0)
    barrier = context.Barrier(4)
    results = context.Queue()
    processes = [
        context.Process(
            target=_process_execute_same_operation,
            args=(
                os.fspath(root),
                os.fspath(state),
                preflight,
                _binding(),
                counter,
                barrier,
                results,
            ),
        )
        for _ in range(4)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)

    outcomes = [results.get(timeout=2) for _ in processes]
    assert all(process.exitcode == 0 for process in processes)
    assert {status for status, _value in outcomes} == {"ok"}
    assert len({value for _status, value in outcomes}) == 1
    assert counter.value == 1
    assert (root / "docs" / "note.txt").read_bytes() == b"process once\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
@pytest.mark.parametrize(
    ("tamper", "expected_error"),
    [
        ("missing", "backup_stage_missing"),
        ("corrupt", "state_file_hash_mismatch"),
        ("substituted", "backup_stage_changed"),
    ],
)
def test_posix_replace_recovery_revalidates_backup_before_claim(
    tmp_path: Path,
    tamper: str,
    expected_error: str,
) -> None:
    def stop_after_backup(seam: str) -> None:
        if seam == "after_backup_durable":
            raise InjectedTransactionFailure(seam)

    root, state, adapter, engine, authority, _calls = _harness(
        tmp_path, failure_injector=stop_after_backup
    )
    target = root / "docs" / "note.txt"
    target.write_bytes(b"before\n")
    preflight = _preflight(
        adapter,
        operation="replace_text",
        relative_path="docs/note.txt",
        desired_text="after\n",
        expected_current_sha256=_digest(b"before\n"),
    )
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(
            LocalTextMutationRequest("operation-backup-tamper", preflight, "after\n", _binding())
        )
    backup = state / f"{_digest(b'operation-backup-tamper')}.backup"
    if tamper == "missing":
        backup.unlink()
    elif tamper == "corrupt":
        backup.write_bytes(b"corrupt\n")
    else:
        replacement = state / "replacement.backup"
        replacement.write_bytes(b"before\n")
        replacement.chmod(0o600)
        os.replace(replacement, backup)
    engine._failure_injector = None

    with pytest.raises(ValueError, match=expected_error):
        engine.recover(root_alias="workspace", operation_id="operation-backup-tamper")

    assert target.read_bytes() == b"before\n"
    assert authority.requests == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX durable journal backend")
@pytest.mark.parametrize("tamper", ["metadata", "truncate"])
def test_posix_journal_tamper_or_truncation_fails_hash_chain(
    tmp_path: Path,
    tamper: str,
) -> None:
    def stop_after_stage(seam: str) -> None:
        if seam == "after_stage_durable":
            raise InjectedTransactionFailure(seam)

    root, state, adapter, engine, authority, _calls = _harness(
        tmp_path, failure_injector=stop_after_stage
    )
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="journal\n",
        expected_current_sha256=None,
    )
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(
            LocalTextMutationRequest("operation-journal", preflight, "journal\n", _binding())
        )
    with sqlite3.connect(state / "journal.sqlite3") as connection:
        connection.execute("DROP TRIGGER local_text_transaction_events_no_update")
        connection.execute("DROP TRIGGER local_text_transaction_events_no_delete")
        if tamper == "metadata":
            connection.execute(
                "UPDATE local_text_transaction_events SET metadata_json = '{}' "
                "WHERE operation_id = ? AND sequence = 1",
                ("operation-journal",),
            )
        else:
            connection.execute(
                "DELETE FROM local_text_transaction_events WHERE operation_id = ? AND sequence = 0",
                ("operation-journal",),
            )
        connection.commit()
    engine._failure_injector = None

    with pytest.raises(ValueError, match="journal_tampered"):
        engine.recover(root_alias="workspace", operation_id="operation-journal")

    assert not (root / "docs" / "note.txt").exists()
    assert authority.requests == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX durable journal backend")
@pytest.mark.parametrize(
    "version_field",
    ["transaction_policy_version", "transaction_backend_version"],
)
def test_posix_recovery_rejects_transaction_version_mismatch_before_state_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version_field: str,
) -> None:
    def stop_after_stage(seam: str) -> None:
        if seam == "after_stage_durable":
            raise InjectedTransactionFailure(seam)

    root, _state, adapter, engine, authority, _calls = _harness(
        tmp_path, failure_injector=stop_after_stage
    )
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="versioned\n",
        expected_current_sha256=None,
    )
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(
            LocalTextMutationRequest("operation-version", preflight, "versioned\n", _binding())
        )
    events = engine._load_events("workspace", "operation-version")
    tampered_metadata = dict(events[-1].metadata)
    tampered_metadata[version_field] = "unsupported-version"
    tampered_events = [*events[:-1], replace(events[-1], metadata=tampered_metadata)]
    monkeypatch.setattr(engine, "_load_events", lambda _alias, _operation: tampered_events)
    lock_attempted = False

    def fail_if_lock_is_attempted(_alias: str, _resource_ref: str):
        nonlocal lock_attempted
        lock_attempted = True
        raise AssertionError("version validation must precede state lock")

    monkeypatch.setattr(engine, "_resource_lock", fail_if_lock_is_attempted)

    with pytest.raises(ValueError, match="version_mismatch"):
        engine.recover(root_alias="workspace", operation_id="operation-version")

    assert not lock_attempted
    assert not (root / "docs" / "note.txt").exists()
    assert authority.requests == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_partial_stage_retry_and_stale_precondition_fail_closed(
    tmp_path: Path,
) -> None:
    fired = False

    def inject(observed: str) -> None:
        nonlocal fired
        if observed == "after_partial_stage" and not fired:
            fired = True
            raise InjectedTransactionFailure(observed)

    root, _state, adapter, engine, authority, _calls = _harness(tmp_path, failure_injector=inject)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="retry\n",
        expected_current_sha256=None,
    )
    request = LocalTextMutationRequest("operation-partial", preflight, "retry\n", _binding())
    with pytest.raises(InjectedTransactionFailure):
        engine.execute(request)
    engine._failure_injector = None
    engine.execute(request)
    assert (root / "docs" / "note.txt").read_bytes() == b"retry\n"
    assert len(authority.requests) == 1

    second = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/other.txt",
        desired_text="new\n",
        expected_current_sha256=None,
    )
    (root / "docs" / "other.txt").write_bytes(b"external\n")
    with pytest.raises(ValueError, match="create_precondition_stale"):
        engine.execute(
            LocalTextMutationRequest("operation-stale", second, "new\n", _binding("f")),
        )
    assert (root / "docs" / "other.txt").read_bytes() == b"external\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_fifo_and_hardlink_swaps_fail_before_claim(tmp_path: Path) -> None:
    root, _state, adapter, engine, authority, _calls = _harness(tmp_path)
    fifo_preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/fifo.txt",
        desired_text="new\n",
        expected_current_sha256=None,
    )
    os.mkfifo(root / "docs" / "fifo.txt")
    with pytest.raises(ValueError, match="target_not_safe|create_precondition_stale"):
        engine.execute(
            LocalTextMutationRequest("operation-fifo", fifo_preflight, "new\n", _binding("f")),
        )

    target = root / "docs" / "note.txt"
    target.write_bytes(b"before\n")
    replace_preflight = _preflight(
        adapter,
        operation="replace_text",
        relative_path="docs/note.txt",
        desired_text="after\n",
        expected_current_sha256=_digest(b"before\n"),
    )
    os.link(target, root / "docs" / "other-link.txt")
    with pytest.raises(ValueError, match="target_not_safe"):
        engine.execute(
            LocalTextMutationRequest(
                "operation-hardlink", replace_preflight, "after\n", _binding("g")
            ),
        )

    assert target.read_bytes() == b"before\n"
    assert authority.requests == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_parent_swap_after_preflight_fails_snapshot_without_escape(
    tmp_path: Path,
) -> None:
    root, _state, adapter, engine, authority, _calls = _harness(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="new\n",
        expected_current_sha256=None,
    )
    detached = root / "detached-docs"
    os.replace(root / "docs", detached)
    (root / "docs").mkdir()

    with pytest.raises(ValueError, match="filesystem_snapshot_changed"):
        engine.execute(
            LocalTextMutationRequest("operation-parent-swap", preflight, "new\n", _binding("h")),
        )

    assert not (root / "docs" / "note.txt").exists()
    assert not (detached / "note.txt").exists()
    assert authority.requests == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX openat physical backend")
def test_posix_enospc_during_stage_never_claims_or_mutates_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _state, adapter, engine, authority, _calls = _harness(tmp_path)
    preflight = _preflight(
        adapter,
        operation="create_text",
        relative_path="docs/note.txt",
        desired_text="new\n",
        expected_current_sha256=None,
    )

    def no_space(*_args, **_kwargs):
        raise OSError(errno.ENOSPC, "no space")

    monkeypatch.setattr(engine, "_write_state_file", no_space)
    with pytest.raises(OSError) as error:
        engine.execute(
            LocalTextMutationRequest("operation-enospc", preflight, "new\n", _binding("i")),
        )

    assert error.value.errno == errno.ENOSPC
    assert not (root / "docs" / "note.txt").exists()
    assert authority.requests == []
