"""Opt-in composition validates roots before any runtime or journal creation."""

import os
import stat
import sys
from hashlib import sha256
from types import SimpleNamespace

import pytest

from apps.jarvis_console.physical_bootstrap import (
    _exclusive_runtime_anchor,
    build_physical_orchestrator,
    validate_physical_configuration,
)


def test_prepare_only_builds_real_services_and_no_target_effect(tmp_path, monkeypatch):
    root = tmp_path / "notes"
    root.mkdir()
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    core = build_physical_orchestrator(runtime_dir=runtime, roots={"notes": root})
    assert core.operational_service._local_text_file_transaction_engine is None
    assert core.observability_service.agentic_adapter is None
    assert list(root.iterdir()) == []
    assert core.governance_service.load_active_adapter_registry()
    assert core.governance_service.load_active_adapter_execution_registry()
    assert core.governance_service.load_active_local_text_file_rollback_registry()
    build_physical_orchestrator(runtime_dir=runtime, roots={"notes": root})
    assert list(root.iterdir()) == []


@pytest.mark.skipif(sys.platform == "linux", reason="non-Linux backend refusal")
def test_windows_execute_is_refused_before_runtime_write(tmp_path):
    root = tmp_path / "notes"
    root.mkdir()
    runtime = tmp_path / "runtime"
    with pytest.raises(ValueError, match="physical_execution_backend_unavailable"):
        build_physical_orchestrator(
            runtime_dir=runtime, roots={"notes": root}, enable_execution=True,
        )
    assert not runtime.exists()
    assert not list(root.iterdir())


def test_invalid_alias_and_overlaps_do_not_create_runtime(tmp_path):
    root = tmp_path / "notes"
    root.mkdir()
    runtime = tmp_path / "runtime"
    for roots, candidate_runtime in [
        ({"Notes": root}, runtime), ({"notes": root}, root / "runtime"),
        ({"notes": root, "other": root}, runtime),
    ]:
        with pytest.raises(ValueError):
            validate_physical_configuration(candidate_runtime, roots, enable_execution=False)
    assert not runtime.exists()


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal"])
def test_redirected_ledger_refused_before_any_database_write(tmp_path, suffix):
    root = tmp_path / "notes"
    root.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    outside = tmp_path / "human-data"
    outside.write_bytes(b"untouched-human-data")
    os.link(outside, runtime / ("governance.db" + suffix))
    before = sha256(outside.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="multiply_linked_physical_file"):
        build_physical_orchestrator(runtime_dir=runtime, roots={"notes": root})
    assert sha256(outside.read_bytes()).hexdigest() == before
    assert not (runtime / "memory.db").exists()
    assert not (runtime / "observability.db").exists()


def test_symlink_ancestor_refused_before_runtime_write(tmp_path):
    root = tmp_path / "notes"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    redirected = tmp_path / "redirected"
    try:
        redirected.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("OS requires permission for real symlink fixture")
    with pytest.raises(ValueError, match="redirected_physical_path"):
        build_physical_orchestrator(runtime_dir=redirected / "runtime", roots={"notes": root})
    assert list(target.iterdir()) == []


@pytest.mark.skipif(sys.platform != "linux", reason="actual Linux authority composition")
def test_linux_composition_shares_exact_attestation_authority(tmp_path):
    root = tmp_path / "notes"
    root.mkdir(mode=0o755)
    (root / ".jarvis-transactions").mkdir(mode=0o700)
    core = build_physical_orchestrator(
        runtime_dir=tmp_path / "runtime", roots={"notes": root}, enable_execution=True,
    )
    engine = core.operational_service._local_text_file_transaction_engine
    assert engine._physical_attestation_lease_provider.__self__ is (
        core._artifact_physical_attestation_authority
    )
    assert engine._canonical_physical_effect_scope_provider.__self__ is core.memory_service
    # Opt-in initializes the journal schema, not an artifact effect.
    assert (root / ".jarvis-transactions" / "journal.sqlite3").is_file()
    assert not (root / "note.txt").exists()


@pytest.mark.parametrize("mode,owner,child,accepted", [
    (0o755, 1000, 1000, True), (0o755, 0, 1000, True),
    (0o777, 1000, 1000, False), (0o1777, 0, 1000, True),
    (0o1777, 0, 2000, False), (0o755, 2000, 1000, False),
])
def test_runtime_anchor_policy(mode, owner, child, accepted):
    # Pure policy evidence, not a fake Linux filesystem/execution proof.
    info = SimpleNamespace(st_mode=stat.S_IFDIR | mode, st_uid=owner)
    assert _exclusive_runtime_anchor(info, child_owner=child, user_id=1000) is accepted


@pytest.mark.skipif(sys.platform != "linux", reason="real Linux permission evidence")
def test_linux_runtime_under_shared_nonsticky_parent_refused_before_write(tmp_path):
    root = tmp_path / "notes"
    root.mkdir()
    parent = tmp_path / "shared"
    parent.mkdir()
    parent.chmod(0o777)
    try:
        with pytest.raises(ValueError, match="unsafe_physical_runtime_anchor"):
            build_physical_orchestrator(runtime_dir=parent / "runtime", roots={"notes": root})
        assert list(parent.iterdir()) == []
    finally:
        parent.chmod(0o700)
