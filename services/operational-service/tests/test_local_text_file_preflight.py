from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import operational_service.adapters.local_text_file as local_text_module
import pytest
from operational_service.adapters import (
    LocalTextFilePreflightAdapter,
    build_local_text_file_preflight_fingerprint,
    build_local_text_file_rollback_fingerprint,
    validate_local_text_file_preflight,
    validate_local_text_file_preflight_fingerprint,
    validate_local_text_file_rollback_fingerprint,
)
from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_ADAPTER_BACKEND_VERSION,
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM,
    LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)

from shared.adapter_permissions import LOCAL_TEXT_FILE_DESCRIPTOR, SEEDED_ADAPTER_REGISTRY
from shared.contracts import (
    AdapterActionRequestContract,
    LocalTextFilePreflightRequestContract,
)
from shared.schemas import LOCAL_TEXT_FILE_PREFLIGHT_REQUEST_SCHEMA

NOW = datetime(2026, 8, 29, 12, 1, tzinfo=timezone.utc)
PREPARED_AT = "2026-08-29T12:00:00Z"
EXPIRES_AT = "2026-08-29T12:05:00Z"
AUTHORIZATION_EXPIRES_AT = "2026-08-29T12:10:00Z"


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def adapter_for(root: Path, *, verifier=None, max_bytes: int = 4096):
    observed: list[datetime] = []

    def default_verifier(
        request: LocalTextFilePreflightRequestContract,
        current: datetime,
    ) -> bool:
        assert request.descriptor_fingerprint == LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint
        observed.append(current)
        return True

    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": root},
        verified_context_verifier=verifier or default_verifier,
        max_bytes=max_bytes,
    )
    return adapter, observed


def request_for(
    adapter: LocalTextFilePreflightAdapter,
    *,
    operation: str = "create_text",
    relative_path: str = "docs/note.txt",
    desired_text: str = "Olá\n",
    expected_current_sha256: str | None = None,
    **changes: object,
) -> LocalTextFilePreflightRequestContract:
    values: dict[str, object] = {
        "grant_id": "adapter-grant://test/1",
        "grant_fingerprint": "1" * 64,
        "action_fingerprint": "2" * 64,
        "intent_fingerprint": "3" * 64,
        "descriptor_fingerprint": LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint,
        "registry_fingerprint": SEEDED_ADAPTER_REGISTRY.registry_fingerprint,
        "subject_ref": "operator://local/tester",
        "adapter_request": AdapterActionRequestContract(
            adapter_id="local_text_file",
            adapter_version="1.0.0",
            action_kind="prepare_external_action",
            operation=operation,
            resource_scope="configured_text_root",
            resource_ref=f"text:workspace/{relative_path}",
        ),
        "desired_text": desired_text,
        "expected_root_config_fingerprint": adapter.root_config_fingerprint(),
        "preflight_policy_version": LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
        "diff_algorithm": LOCAL_TEXT_DIFF_ALGORITHM,
        "diff_algorithm_version": LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
        "prepared_at": PREPARED_AT,
        "expires_at": EXPIRES_AT,
        "authorization_expires_at": AUTHORIZATION_EXPIRES_AT,
        "expected_current_sha256": expected_current_sha256,
    }
    values.update(changes)
    return LocalTextFilePreflightRequestContract(**values)


def tree_snapshot(root: Path) -> list[tuple[str, bool, bytes | None]]:
    snapshot: list[tuple[str, bool, bytes | None]] = []
    for entry in sorted(root.rglob("*")):
        snapshot.append(
            (
                entry.relative_to(root).as_posix(),
                entry.is_dir(),
                entry.read_bytes() if entry.is_file() else None,
            )
        )
    return snapshot


def test_create_preflight_is_deterministic_sensitive_metadata_with_zero_write(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    adapter, observed = adapter_for(tmp_path)
    request = request_for(adapter)
    before = tree_snapshot(tmp_path)

    first = adapter.preflight(request, now=NOW)
    second = adapter.preflight(request, now=NOW)

    assert first == second
    assert tree_snapshot(tmp_path) == before
    assert not (tmp_path / "docs" / "note.txt").exists()
    assert observed == [NOW, NOW]
    assert first.before_exists is False
    assert first.before_content_sha256 == digest(b"")
    assert first.desired_content_sha256 == digest("Olá\n".encode())
    assert first.unified_diff == ("--- a/docs/note.txt\n+++ b/docs/note.txt\n@@ -0,0 +1 @@\n+Olá\n")
    assert first.rollback_plan.strategy == "delete_created_file"
    assert first.rollback_plan.restore_content_sha256 is None
    assert first.execution_grant_required is True
    assert first.preflight_grant_reusable_for_execution is False
    assert first.persistence_allowed is False
    assert first.telemetry_allowed is False
    assert first.contains_sensitive_diff is True
    assert first.filesystem_snapshot_algorithm == LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM
    assert (
        first.filesystem_snapshot_algorithm_version
        == LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM_VERSION
    )
    assert first.adapter_backend_version == LOCAL_TEXT_ADAPTER_BACKEND_VERSION
    assert validate_local_text_file_preflight(first, now=NOW) == []
    serialized = json.dumps(asdict(first), ensure_ascii=False, sort_keys=True)
    assert str(tmp_path) not in serialized


def test_create_preflight_never_calls_directory_or_temporary_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path)
    request = request_for(adapter)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("creation_primitive_called")

    monkeypatch.setattr(os, "mkdir", forbidden)
    monkeypatch.setattr(tempfile, "mkstemp", forbidden)
    monkeypatch.setattr(tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", forbidden)

    result = adapter.preflight(request, now=NOW)
    assert result.operation == "create_text"
    assert not (tmp_path / "docs" / "note.txt").exists()


@pytest.mark.parametrize("operation", ["create_text", "replace_text"])
@pytest.mark.parametrize(
    "relative_path",
    [
        ".jarvis-transactions/secret.txt",
        ".JARVIS-TRANSACTIONS/secret.txt",
    ],
)
def test_internal_transaction_namespace_is_reserved_before_filesystem_access(
    tmp_path: Path,
    operation: str,
    relative_path: str,
) -> None:
    adapter, _ = adapter_for(tmp_path)
    request = request_for(
        adapter,
        operation=operation,
        relative_path=relative_path,
        expected_current_sha256=("a" * 64 if operation == "replace_text" else None),
    )
    before = tree_snapshot(tmp_path)

    with pytest.raises(ValueError, match="internal_namespace_reserved"):
        adapter.preflight(request, now=NOW)

    assert tree_snapshot(tmp_path) == before


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-containment seam")
def test_windows_create_reparse_attributes_block_before_second_target_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path)
    request = request_for(adapter)
    real_optional = adapter._lstat_optional
    target_stat_calls = 0

    def counted_optional(path: Path):
        nonlocal target_stat_calls
        target_stat_calls += 1
        return real_optional(path)

    def simulated_reparse(_attributes: int) -> None:
        raise ValueError("local_text_directory_not_safe")

    monkeypatch.setattr(adapter, "_lstat_optional", counted_optional)
    monkeypatch.setattr(
        local_text_module,
        "_require_windows_safe_directory_attributes",
        simulated_reparse,
    )
    with pytest.raises(ValueError, match="directory_not_safe"):
        adapter.preflight(request, now=NOW)
    assert target_stat_calls == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-containment seam")
def test_windows_replace_target_escape_blocks_before_readfile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.txt"
    target.write_bytes(b"before\n")
    adapter, _ = adapter_for(tmp_path)
    request = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256=digest(b"before\n"),
    )
    real_containment = local_text_module._require_windows_contained_path

    def escape_at_target(observed: str, expected: str, error: str) -> None:
        if error == "local_text_target_escaped_root":
            raise ValueError(error)
        real_containment(observed, expected, error)

    def forbidden_read(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("ReadFile_called_before_containment")

    monkeypatch.setattr(
        local_text_module,
        "_require_windows_contained_path",
        escape_at_target,
    )
    monkeypatch.setattr(local_text_module, "_read_windows_handle", forbidden_read)
    with pytest.raises(ValueError, match="target_escaped_root"):
        adapter.preflight(request, now=NOW)
    assert target.read_bytes() == b"before\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-containment seam")
def test_windows_replace_rechecks_containment_after_bounded_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.txt"
    target.write_bytes(b"before\n")
    adapter, _ = adapter_for(tmp_path)
    request = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256=digest(b"before\n"),
    )
    real_containment = local_text_module._require_windows_contained_path
    target_checks = 0

    def escape_after_read(observed: str, expected: str, error: str) -> None:
        nonlocal target_checks
        if error == "local_text_target_escaped_root":
            target_checks += 1
            if target_checks == 2:
                raise ValueError(error)
        real_containment(observed, expected, error)

    monkeypatch.setattr(
        local_text_module,
        "_require_windows_contained_path",
        escape_after_read,
    )
    monkeypatch.setattr(
        local_text_module,
        "_read_windows_handle",
        lambda _reader, _handle, _limit: b"before\n",
    )
    with pytest.raises(ValueError, match="target_escaped_root"):
        adapter.preflight(request, now=NOW)
    assert target_checks == 2


def test_diff_golden_preserves_no_final_newline_and_non_ascii(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path)
    result = adapter.preflight(
        request_for(adapter, desired_text="ação"),
        now=NOW,
    )
    assert result.unified_diff == (
        "--- a/docs/note.txt\n"
        "+++ b/docs/note.txt\n"
        "@@ -0,0 +1 @@\n"
        "+ação\n"
        "\\ No newline at end of file\n"
    )
    assert result.diff_sha256 == digest(result.unified_diff.encode("utf-8"))


def test_replace_preflight_uses_exact_before_hash_and_never_writes(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.txt"
    target.write_text("antes\n", encoding="utf-8", newline="")
    adapter, _ = adapter_for(tmp_path)
    before_hash = digest(b"antes\n")
    request = request_for(
        adapter,
        operation="replace_text",
        desired_text="depois\n",
        expected_current_sha256=before_hash,
    )
    before_tree = tree_snapshot(tmp_path)

    result = adapter.preflight(request, now=NOW)

    assert tree_snapshot(tmp_path) == before_tree
    assert target.read_bytes() == b"antes\n"
    assert result.before_exists is True
    assert result.before_content_sha256 == before_hash
    assert result.rollback_plan.strategy == "restore_previous_content"
    assert result.rollback_plan.restore_content_sha256 == before_hash
    assert result.unified_diff == (
        "--- a/docs/note.txt\n+++ b/docs/note.txt\n@@ -1 +1 @@\n-antes\n+depois\n"
    )


def test_replace_same_content_is_non_authorizing_no_change(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.txt"
    target.write_bytes(b"same\n")
    adapter, _ = adapter_for(tmp_path)
    result = adapter.preflight(
        request_for(
            adapter,
            operation="replace_text",
            desired_text="same\n",
            expected_current_sha256=digest(b"same\n"),
        ),
        now=NOW,
    )
    assert result.change_status == "no_change"
    assert result.unified_diff == ""
    assert result.execution_allowed is False


@pytest.mark.parametrize(
    "relative_path",
    (
        "/absolute.txt",
        "C:/drive.txt",
        "C:drive.txt",
        "//server/share.txt",
        r"folder\backslash.txt",
        "../escape.txt",
        "folder/./dot.txt",
        "folder//empty.txt",
        "name.txt:stream",
        "name%2ftest.txt",
        "wild*.txt",
        "trail./name.txt",
        "trail /name.txt",
        "CON.txt",
        "CLOCK$.txt",
        "CONIN$.txt",
        "COM¹.txt",
        "e\u0301.txt",
        "control\u0001.txt",
        "format\u202etxt.md",
        "binary.exe",
    ),
)
def test_windows_lexical_corpus_fails_closed_without_filesystem_changes(
    tmp_path: Path,
    relative_path: str,
) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path)
    before = tree_snapshot(tmp_path)
    request = request_for(adapter, relative_path=relative_path)
    with pytest.raises(ValueError):
        adapter.preflight(request, now=NOW)
    assert tree_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "desired_text",
    (
        "nul\x00",
        "bom\ufeff",
        "decomposed e\u0301",
        "carriage\rreturn",
        "surrogate\ud800",
    ),
)
def test_invalid_desired_encoding_or_normalization_fails_closed(
    tmp_path: Path,
    desired_text: str,
) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path)
    request = request_for(adapter, desired_text=desired_text)
    with pytest.raises(ValueError):
        adapter.preflight(request, now=NOW)
    assert not (tmp_path / "docs" / "note.txt").exists()


def test_verifier_is_required_and_runs_with_actual_now_before_any_io(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    calls: list[datetime] = []

    def deny(_request: LocalTextFilePreflightRequestContract, current: datetime) -> bool:
        calls.append(current)
        return False

    adapter = LocalTextFilePreflightAdapter(
        roots={"workspace": missing_root},
        verified_context_verifier=deny,
    )
    request = LocalTextFilePreflightRequestContract(
        grant_id="adapter-grant://test/1",
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
            operation="create_text",
            resource_scope="configured_text_root",
            resource_ref="text:workspace/docs/note.txt",
        ),
        desired_text="safe\n",
        expected_root_config_fingerprint="4" * 64,
        preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
        diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
        diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
        prepared_at=PREPARED_AT,
        expires_at=EXPIRES_AT,
        authorization_expires_at=AUTHORIZATION_EXPIRES_AT,
    )
    with pytest.raises(ValueError, match="context_not_verified"):
        adapter.preflight(request, now=NOW)
    assert calls == [NOW]


def test_expired_or_over_authorization_window_blocks_before_verifier(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    calls: list[datetime] = []

    def verifier(_request: LocalTextFilePreflightRequestContract, current: datetime) -> bool:
        calls.append(current)
        return True

    adapter, _ = adapter_for(tmp_path, verifier=verifier)
    request = request_for(
        adapter,
        expires_at="2026-08-29T12:04:00Z",
        authorization_expires_at="2026-08-29T12:03:00Z",
    )
    with pytest.raises(ValueError, match="exceeds_authorization"):
        adapter.preflight(request, now=NOW)
    assert calls == []


def test_root_config_cas_parent_and_target_rules_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    adapter, _ = adapter_for(root)
    (root / "docs").mkdir()
    request = request_for(adapter, expected_root_config_fingerprint="f" * 64)
    with pytest.raises(ValueError, match="root_config_fingerprint_mismatch"):
        adapter.preflight(request, now=NOW)

    adapter, _ = adapter_for(root)
    request = request_for(adapter, relative_path="missing/note.txt")
    with pytest.raises(ValueError, match="directory_missing"):
        adapter.preflight(request, now=NOW)

    existing = root / "docs" / "Note.TXT"
    existing.write_text("collision", encoding="utf-8")
    adapter, _ = adapter_for(root)
    request = request_for(adapter, relative_path="docs/note.txt")
    with pytest.raises(ValueError, match="target_exists|casefold_collision"):
        adapter.preflight(request, now=NOW)


def test_replace_rejects_hash_mismatch_nonregular_symlink_and_hardlink(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.txt"
    target.write_bytes(b"current\n")
    adapter, _ = adapter_for(tmp_path)
    mismatch = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256="f" * 64,
    )
    with pytest.raises(ValueError, match="expected_current_hash_mismatch"):
        adapter.preflight(mismatch, now=NOW)

    target.unlink()
    target.mkdir()
    adapter, _ = adapter_for(tmp_path)
    directory_request = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256=digest(b"current\n"),
    )
    with pytest.raises(ValueError, match="not_safe_regular_file"):
        adapter.preflight(directory_request, now=NOW)

    target.rmdir()
    target.write_bytes(b"current\n")
    hardlink = tmp_path / "docs" / "other.txt"
    os.link(target, hardlink)
    adapter, _ = adapter_for(tmp_path)
    hardlink_request = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256=digest(b"current\n"),
    )
    with pytest.raises(ValueError, match="not_safe_regular_file"):
        adapter.preflight(hardlink_request, now=NOW)


def test_replace_rejects_symlink_target_before_read(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside\n")
    target = tmp_path / "docs" / "note.txt"
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows host")
    adapter, _ = adapter_for(tmp_path)
    request = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256=digest(b"outside\n"),
    )
    with pytest.raises(ValueError, match="not_safe_regular_file"):
        adapter.preflight(request, now=NOW)
    assert outside.read_bytes() == b"outside\n"


@pytest.mark.skipif(os.name == "nt", reason="FIFO is a POSIX filesystem primitive")
def test_posix_fifo_is_rejected_before_os_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.txt"
    os.mkfifo(target)
    adapter, _ = adapter_for(tmp_path)
    request = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256=digest(b""),
    )

    def forbidden_read(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("os.read_called_for_fifo")

    monkeypatch.setattr(os, "read", forbidden_read)
    with pytest.raises(ValueError, match="not_safe_regular_file"):
        adapter.preflight(request, now=NOW)


@pytest.mark.skipif(os.name == "nt", reason="openat parent swap is POSIX-specific")
def test_posix_parent_swap_to_symlink_blocks_before_os_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    parent = root / "docs"
    parent.mkdir(parents=True)
    target = parent / "note.txt"
    target.write_bytes(b"inside\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "note.txt").write_bytes(b"outside\n")
    adapter, _ = adapter_for(root)
    initial = os.lstat(target)
    parent.rename(root / "docs-old")
    parent.symlink_to(outside, target_is_directory=True)

    def forbidden_read(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("os.read_called_after_parent_swap")

    monkeypatch.setattr(os, "read", forbidden_read)
    with pytest.raises(ValueError, match="target_open_failed|directory_not_safe"):
        adapter._read_stable_text(
            target,
            initial,
            root=root,
            parent_segments=("docs",),
            target_name="note.txt",
        )


@pytest.mark.parametrize("current", (b"bad\xff", b"bom\xef\xbb\xbf", b"nul\x00"))
def test_replace_rejects_invalid_current_text(tmp_path: Path, current: bytes) -> None:
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "note.txt"
    target.write_bytes(current)
    adapter, _ = adapter_for(tmp_path)
    request = request_for(
        adapter,
        operation="replace_text",
        expected_current_sha256=digest(current),
    )
    with pytest.raises(ValueError, match="current_(encoding|content)_invalid"):
        adapter.preflight(request, now=NOW)
    assert target.read_bytes() == current


def test_size_limits_and_create_contract_rules(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path, max_bytes=4)
    with pytest.raises(ValueError, match="desired_content_too_large"):
        adapter.preflight(request_for(adapter, desired_text="ááá"), now=NOW)
    with pytest.raises(ValueError, match="expected_hash_forbidden"):
        adapter.preflight(
            request_for(adapter, expected_current_sha256=digest(b"")),
            now=NOW,
        )


def test_fingerprint_validators_detect_nested_and_top_level_tamper(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path)
    result = adapter.preflight(request_for(adapter), now=NOW)
    assert validate_local_text_file_preflight_fingerprint(result)
    assert validate_local_text_file_rollback_fingerprint(result.rollback_plan)
    assert result.preflight_fingerprint == build_local_text_file_preflight_fingerprint(result)
    assert result.rollback_plan.rollback_fingerprint == build_local_text_file_rollback_fingerprint(
        result.rollback_plan
    )

    tampered = replace(result, desired_content_sha256="f" * 64)
    assert not validate_local_text_file_preflight_fingerprint(tampered)
    assert validate_local_text_file_preflight(tampered, now=NOW)
    tampered_rollback = replace(result.rollback_plan, resource_ref="text:workspace/other.txt")
    assert not validate_local_text_file_rollback_fingerprint(tampered_rollback)
    sensitive_diff_tamper = replace(result, unified_diff="sensitive tamper")
    assert validate_local_text_file_preflight_fingerprint(sensitive_diff_tamper)
    assert validate_local_text_file_preflight(sensitive_diff_tamper, now=NOW) == [
        "local_text_preflight_diff_hash_invalid"
    ]

    reserved_request = replace(
        result.adapter_request,
        resource_ref="text:workspace/CON.txt",
    )
    reserved_rollback = replace(
        result.rollback_plan,
        resource_ref="text:workspace/CON.txt",
        rollback_fingerprint="0" * 64,
    )
    reserved_rollback = replace(
        reserved_rollback,
        rollback_fingerprint=build_local_text_file_rollback_fingerprint(reserved_rollback),
    )
    reserved_result = replace(
        result,
        adapter_request=reserved_request,
        resource_ref="text:workspace/CON.txt",
        relative_path="CON.txt",
        rollback_plan=reserved_rollback,
        preflight_fingerprint="0" * 64,
    )
    reserved_result = replace(
        reserved_result,
        preflight_fingerprint=build_local_text_file_preflight_fingerprint(reserved_result),
    )
    assert (
        "windows_device_name_forbidden"
        in validate_local_text_file_preflight(
            reserved_result,
            now=NOW,
        )[0]
    )


def test_request_sensitivity_descriptor_and_schema_bindings_are_fail_closed(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    adapter, _ = adapter_for(tmp_path)
    required = set(LOCAL_TEXT_FILE_PREFLIGHT_REQUEST_SCHEMA.required_fields)
    assert {"descriptor_fingerprint", "registry_fingerprint"} <= required
    base = request_for(adapter)
    for tampered in (
        replace(base, descriptor_fingerprint="f" * 64),
        replace(base, persistence_allowed=True),
        replace(base, telemetry_allowed=True),
        replace(base, contains_sensitive_content=False),
    ):
        with pytest.raises(ValueError):
            adapter.preflight(tampered, now=NOW)


@pytest.mark.parametrize(
    "root_value",
    (
        "/",
        "C:\\",
        "C:relative",
        r"\\server\share\root",
        r"\\?\C:\root",
        r"\\.\C:\root",
        " C:\\root",
        "C:\\root\\..\\escape",
        "C:\\root\\\\nested",
        "C:\\CON\\nested",
        "C:\\e\u0301",
    ),
)
def test_configured_root_lexical_rejections_happen_before_io(root_value: str) -> None:
    with pytest.raises(ValueError):
        LocalTextFilePreflightAdapter(
            roots={"workspace": root_value},
            verified_context_verifier=lambda _request, _now: True,
        )


def test_unc_and_device_roots_are_rejected_before_lstat_or_scandir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("filesystem_io_before_root_lexical_validation")

    monkeypatch.setattr(os, "lstat", forbidden)
    monkeypatch.setattr(os, "scandir", forbidden)
    for root_value in (r"\\server\share\root", r"\\?\C:\root", r"\\.\C:\root"):
        with pytest.raises(ValueError):
            LocalTextFilePreflightAdapter(
                roots={"workspace": root_value},
                verified_context_verifier=lambda _request, _now: True,
            )
