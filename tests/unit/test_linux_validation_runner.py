"""Runner unit contracts; these tests do not claim Docker/Linux backend proof."""

import io
import shlex
import stat
import subprocess
import tarfile
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.linux_validation.entrypoint import PHYSICAL_TESTS, extract_sources
from tools.run_linux_validation import docker_run_command, main, source_archive


def test_linux_image_has_pinned_synthetic_tls_test_tool_matching_dev_only_metadata():
    """Static image contract, not evidence of a rebuilt or executed Linux image."""
    root = Path(__file__).resolve().parents[2]
    dockerfile = (root / "tools/linux_validation/Dockerfile").read_text(encoding="utf-8")
    install_lines = [line for line in dockerfile.splitlines() if line.startswith("RUN ")]
    assert len(install_lines) == 1
    command = shlex.split(install_lines[0])
    assert command[:5] == ["RUN", "python", "-m", "pip", "install"]
    assert "--no-cache-dir" in command
    assert {item for item in command[5:] if not item.startswith("--")} == {
        "pytest==9.0.2",
        "ruff==0.15.7",
        "cryptography==46.0.7",
    }
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "cryptography>=46" in metadata["optional-dependencies"]["dev"]
    assert not any(item.lower().startswith("cryptography") for item in metadata["dependencies"])


def test_standard_entrypoint_keeps_full_gate_using_image_development_tools(monkeypatch):
    """Fake subprocess checks routing only, never claims native Linux validation."""
    import tools.linux_validation.entrypoint as entrypoint

    calls = []
    monkeypatch.setattr(entrypoint.sys, "platform", "linux")
    monkeypatch.setattr(entrypoint.sys, "argv", ["entrypoint", "standard"])
    monkeypatch.setattr(entrypoint.sys, "stdin", SimpleNamespace(buffer=io.BytesIO()))
    monkeypatch.setattr(entrypoint, "extract_sources", lambda stream, root: None)

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(entrypoint.subprocess, "run", run)
    assert entrypoint.main() == 0
    python = str(Path(entrypoint.sys.executable).resolve(strict=True))
    assert calls == [[python, "tools/engineering_gate.py", "--mode", "standard"]]


def test_physical_entrypoint_reports_skip_reasons_and_test_counts(monkeypatch):
    """Command seam only; a fake subprocess is not Linux execution evidence."""
    import tools.linux_validation.entrypoint as entrypoint

    calls = []
    monkeypatch.setattr(entrypoint.sys, "platform", "linux")
    monkeypatch.setattr(entrypoint.sys, "argv", ["entrypoint", "physical"])
    monkeypatch.setattr(entrypoint.sys, "stdin", SimpleNamespace(buffer=io.BytesIO()))
    monkeypatch.setattr(entrypoint, "extract_sources", lambda stream, root: None)

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(entrypoint.subprocess, "run", run)
    assert entrypoint.main() == 0
    python = str(Path(entrypoint.sys.executable).resolve(strict=True))
    assert calls == [[python, "-m", "pytest", "-ra", *PHYSICAL_TESTS]]
    assert "-q" not in calls[0]  # pyproject already supplies one quiet flag.


def test_physical_runner_includes_mb219_boundary_and_exact_receipt_proofs():
    required = {
        "tests/unit/test_mb219_physical_effect_boundary.py",
        "tests/unit/test_mb219_scope_lock.py",
        "tests/unit/test_mb219_kernel_modes.py",
        "tests/integration/test_mb219_physical_boundary.py",
        "services/operational-service/tests/test_local_text_transaction_receipt_proof.py",
        "services/operational-service/tests/test_local_text_transaction_wiring.py",
    }
    assert required <= set(PHYSICAL_TESTS)
    assert len(PHYSICAL_TESTS) == len(set(PHYSICAL_TESTS))


def test_archive_excludes_runtime_git_environment_and_hidden_files(tmp_path):
    for name in ("tests", ".git", ".jarvis_runtime", ".venv"):
        (tmp_path / name).mkdir()
    (tmp_path / "tests" / "test_safe.py").write_text("pass", encoding="utf-8")
    (tmp_path / "tests" / ".env.private.json").write_text("private", encoding="utf-8")
    for name in (".env", ".git/config", ".jarvis_runtime/memory.db", ".venv/private.py"):
        (tmp_path / name).write_text("private", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    data = source_archive(tmp_path)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        assert set(archive.getnames()) == {"tests/test_safe.py", "pyproject.toml"}
    assert b"private" not in data
    output = tmp_path / "output"
    output.mkdir()
    extract_sources(io.BytesIO(data), output)
    assert (output / "tests" / "test_safe.py").read_text() == "pass"


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../outside.py", tarfile.REGTYPE),
        ("/outside.py", tarfile.REGTYPE),
        ("link", tarfile.SYMTYPE),
        ("link", tarfile.LNKTYPE),
        ("..\\outside.py", tarfile.REGTYPE),
        ("D:/outside.py", tarfile.REGTYPE),
        ("\\outside.py", tarfile.REGTYPE),
    ],
)
def test_extractor_refuses_redirect_or_escape(tmp_path, name, kind):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        entry = tarfile.TarInfo(name)
        entry.type = kind
        entry.linkname = "../../human-file"
        archive.addfile(entry)
    with pytest.raises(ValueError, match="invalid_source_archive"):
        extract_sources(io.BytesIO(stream.getvalue()), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_container_command_has_no_host_mount_network_or_privileged_mode():
    command = docker_run_command("physical")
    assert "--rm" in command and "--read-only" in command
    assert command[command.index("--network") + 1] == "none"
    assert "--mount" not in command and "-v" not in command and "--privileged" not in command
    assert "no-new-privileges" in command and "/tmp:rw,exec,nosuid,size=2g" in command
    with pytest.raises(ValueError):
        docker_run_command("arbitrary-command")


def test_unavailable_backend_cannot_build_or_run(monkeypatch, capsys):
    calls = []

    def unavailable(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1, stdout="", stderr="private diagnostics")

    monkeypatch.setattr("tools.run_linux_validation.subprocess.run", unavailable)
    monkeypatch.setattr("sys.argv", ["runner", "--build"])
    assert main() == 3
    assert len(calls) == 1 and calls[0][1] == "version"
    assert capsys.readouterr().out == "linux_docker_backend_unavailable\n"


def test_archive_excludes_usual_sensitive_data_names_but_not_source_modules(tmp_path):
    source = tmp_path / "services"
    source.mkdir()
    for name in ("auth.json", "credentials-local.yaml", "secrets.toml", "token.txt", "tokens.csv"):
        (source / name).write_text("private-token", encoding="utf-8")
    (source / "auth.py").write_text("# source only", encoding="utf-8")
    # Contents are not scanned: benign filenames can still contain personal
    # data. This test deliberately prevents an absolute secret-exclusion claim.
    (source / "fixture.json").write_text('{"human_note": "review before transfer"}')
    data = source_archive(tmp_path)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        assert set(archive.getnames()) == {"services/auth.py", "services/fixture.json"}
    assert b"private-token" not in data


def test_reparse_directory_is_refused_before_traversal(tmp_path, monkeypatch):
    source = tmp_path / "services"
    source.mkdir()
    redirected = source / "junction"
    redirected.mkdir()
    original_lstat = Path.lstat
    original_iterdir = Path.iterdir

    def observed(path, *args, **kwargs):
        if path == redirected:
            return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_file_attributes=0x400)
        return original_lstat(path, *args, **kwargs)

    def must_not_traverse(path):
        if path == redirected:
            pytest.fail("reparse directory traversed")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "lstat", observed)
    monkeypatch.setattr(Path, "iterdir", must_not_traverse)
    with pytest.raises(ValueError, match="redirected_source_path"):
        source_archive(tmp_path)


def test_file_size_limit_is_checked_before_open(tmp_path, monkeypatch):
    source = tmp_path / "tests"
    source.mkdir()
    oversized = source / "test_big.py"
    oversized.write_text("pass")
    original_lstat = Path.lstat
    original_open = Path.open

    def observed(path, *args, **kwargs):
        if path == oversized:
            actual = original_lstat(path, *args, **kwargs)
            return SimpleNamespace(
                st_mode=actual.st_mode,
                st_nlink=actual.st_nlink,
                st_size=20_000_001,
                st_file_attributes=0,
            )
        return original_lstat(path, *args, **kwargs)

    def must_not_open(path, *args, **kwargs):
        if path == oversized:
            pytest.fail("oversized source opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", observed)
    monkeypatch.setattr(Path, "open", must_not_open)
    with pytest.raises(ValueError, match="source_archive_limit"):
        source_archive(tmp_path)


@pytest.mark.parametrize("failure", ["interrupt", "timeout"])
def test_run_interruption_attempts_cleanup_only_its_unique_container(monkeypatch, capsys, failure):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1] == "version":
            return SimpleNamespace(returncode=0, stdout="linux")
        if command[1:3] == ["image", "inspect"]:
            return SimpleNamespace(returncode=0, stdout="sha256:test-image")
        if command[1] == "run":
            if failure == "interrupt":
                raise KeyboardInterrupt
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        assert command[1:3] == ["rm", "--force"]
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("tools.run_linux_validation.subprocess.run", fake_run)
    monkeypatch.setattr("tools.run_linux_validation.source_archive", lambda root: b"test-sources")
    monkeypatch.setattr("sys.argv", ["runner"])
    assert main() == (130 if failure == "interrupt" else 3)
    run_command, run_kwargs = calls[2]
    cleanup_command, cleanup_kwargs = calls[3]
    name = run_command[run_command.index("--name") + 1]
    assert name.startswith("jarvis-linux-validation-")
    assert cleanup_command == ["docker", "rm", "--force", name]
    assert run_kwargs["timeout"] == 1800 and cleanup_kwargs["timeout"] == 15
    assert len(calls) == 4
    assert "test-sources" not in capsys.readouterr().out


def test_unowned_container_name_is_refused():
    with pytest.raises(ValueError, match="invalid_validation_container_name"):
        docker_run_command("physical", container_name="human-container")


def test_archive_reads_with_explicit_bound(tmp_path, monkeypatch):
    source_dir = tmp_path / "tests"
    source_dir.mkdir()
    source = source_dir / "test_safe.py"
    source.write_text("pass")
    original_open = Path.open
    requested_limits = []

    class BoundedReader:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def fileno(self):
            return self.handle.fileno()

        def read(self, limit):
            requested_limits.append(limit)
            return self.handle.read(limit)

    def bounded_open(path, *args, **kwargs):
        handle = original_open(path, *args, **kwargs)
        return BoundedReader(handle) if path == source else handle

    monkeypatch.setattr(Path, "open", bounded_open)
    monkeypatch.setattr("tools.run_linux_validation.MAX_FILE_BYTES", 8)
    monkeypatch.setattr("tools.run_linux_validation.MAX_TOTAL_BYTES", 6)
    source_archive(tmp_path)
    assert requested_limits == [7]


def test_cleanup_timeout_is_reported_without_touching_other_resources(monkeypatch, capsys):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[1] == "version":
            return SimpleNamespace(returncode=0, stdout="linux")
        if command[1:3] == ["image", "inspect"]:
            return SimpleNamespace(returncode=0, stdout="sha256:test-image")
        if command[1] == "run":
            return SimpleNamespace(returncode=0)
        assert command[1:3] == ["rm", "--force"]
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr("tools.run_linux_validation.subprocess.run", fake_run)
    monkeypatch.setattr("tools.run_linux_validation.source_archive", lambda root: b"sources")
    monkeypatch.setattr("sys.argv", ["runner"])
    assert main() == 0
    assert len(calls) == 4
    assert "validation_container_cleanup_unconfirmed" in capsys.readouterr().out
