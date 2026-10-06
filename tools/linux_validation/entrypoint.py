"""Run a bounded source archive on a native, temporary Linux filesystem."""

import json
import os
import platform
import stat
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

PHYSICAL_TESTS = (
    "tests/unit/test_physical_bootstrap.py",
    "tests/unit/test_physical_operations_console.py",
    "tests/integration/test_physical_cli.py",
    "tests/integration/test_physical_operations_console_integration.py",
    "tests/unit/test_mb219_physical_effect_boundary.py",
    "tests/unit/test_mb219_scope_lock.py",
    "tests/unit/test_mb219_kernel_modes.py",
    "tests/integration/test_mb219_physical_boundary.py",
    "tests/integration/test_mb219_scope_process_boundary.py",
    "tests/integration/test_mb219_storage_faults.py",
    "services/operational-service/tests/test_local_text_transaction.py",
    "services/operational-service/tests/test_local_text_transaction_wiring.py",
    "services/operational-service/tests/test_local_text_transaction_receipt_proof.py",
    "services/operational-service/tests/test_local_text_transaction_hard_crash.py",
    "services/operational-service/tests/test_local_text_governance_transaction_integration.py",
    "services/orchestrator-service/tests/test_artifact_physical_saga_real_integration.py",
    "tests/unit/test_persistent_physical_scenario.py",
)
PERSISTENT_STAGES = {"prepare", "confirm", "crash", "recover", "rollback", "verify", "suite"}


def persistent_storage_info(root: Path) -> dict[str, object]:
    """Refuse ephemeral filesystems; host runner verifies named-volume ownership."""
    if root != Path("/validation") or not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("invalid_persistent_validation_mount")
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        fields = line.split()
        if len(fields) < 10 or fields[4] != "/validation" or "-" not in fields:
            continue
        separator = fields.index("-")
        filesystem = fields[separator + 1]
        if filesystem in {"tmpfs", "ramfs", "overlay"}:
            raise ValueError("persistent_validation_filesystem_refused")
        # No host paths or raw mountinfo in output.
        return {"storage_mode": "mounted_non_ephemeral_filesystem", "filesystem": filesystem}
    raise ValueError("persistent_validation_mount_missing")


def initialize_persistent_volume(root: Path) -> None:
    if root != Path("/validation"):
        raise ValueError("invalid_persistent_validation_mount")
    if root.lstat().st_uid != os.geteuid() or any(root.iterdir()):
        raise ValueError("persistent_validation_volume_not_fresh")
    root.chmod(0o700)  # Only the new, empty, runner-owned volume.


def extract_sources(stream, destination: Path) -> None:
    total = 0
    count = 0
    with tarfile.open(fileobj=stream, mode="r|*") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            count += 1
            total += member.size
            if (
                not member.isfile()
                or name.is_absolute()
                or ".." in name.parts
                or any("\\" in part or ":" in part for part in name.parts)
                or count > 10_000
                or not 0 <= member.size <= 20_000_000
                or total > 200_000_000
            ):
                raise ValueError("invalid_source_archive")
            target = destination.joinpath(*name.parts)
            if target.exists():
                raise ValueError("duplicate_source_path")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("invalid_source_archive")
            with source, target.open("xb") as output:
                while data := source.read(65_536):
                    output.write(data)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    persistent_stage = mode.removeprefix("persistent-") if mode.startswith("persistent-") else None
    if (
        sys.platform != "linux"
        or len(sys.argv) != 2
        or (mode not in {"physical", "standard", "release"}
            and persistent_stage not in PERSISTENT_STAGES)
    ):
        return 2
    print(
        json.dumps(
            {
                "platform": sys.platform,
                "machine": platform.machine(),
                "python": platform.python_version(),
                "mode": mode,
                "configuration": "temporary_linux_source_archive",
                "execution_proof": "pending_validation",
            }
        )
    )
    with TemporaryDirectory(prefix="jarvis-linux-validation-") as temporary:
        root = Path(temporary)
        try:
            extract_sources(sys.stdin.buffer, root)
        except (OSError, ValueError, tarfile.TarError):
            print("invalid_source_archive", file=sys.stderr)
            return 2
        # Resolve only the trusted image interpreter, not caller-controlled paths.
        python = str(Path(sys.executable).resolve(strict=True))
        if persistent_stage is not None:
            try:
                print(json.dumps(persistent_storage_info(Path("/validation"))), flush=True)
                if persistent_stage == "prepare":
                    initialize_persistent_volume(Path("/validation"))
            except (OSError, ValueError, IndexError):
                print("persistent_validation_mount_refused", file=sys.stderr)
                return 2
            command = (
                [python, "-m", "pytest", "-ra", "--basetemp", "/validation/pytest-fixtures",
                 *PHYSICAL_TESTS]
                if persistent_stage == "suite"
                else [python, "-m", "tools.linux_validation.persistent_scenario", persistent_stage]
            )
        elif mode == "physical":
            command = [python, "-m", "pytest", "-ra", *PHYSICAL_TESTS]
        else:
            command = [python, "tools/engineering_gate.py", "--mode", mode]
        return subprocess.run(command, cwd=root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
