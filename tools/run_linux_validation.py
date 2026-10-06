"""Explicit Docker Linux validation without mounting the host workspace."""

import argparse
import io
import os
import stat
import subprocess
import tarfile
from hashlib import sha256
from json import loads
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "jarvis-linux-validation:py311-v1"
SOURCE_DIRS = (
    "apps",
    "docs",
    "engines",
    "evals",
    "evolution",
    "governance",
    "infra",
    "knowledge",
    "memory",
    "observability",
    "services",
    "shared",
    "tests",
    "tools",
)
SOURCE_FILES = (
    "AGENTS.md",
    "HANDOFF.md",
    "CHANGELOG.md",
    "README.md",
    "documento_mestre_jarvis.md",
    "conftest.py",
    "pyproject.toml",
    "package.json",
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
)
SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".sql",
    ".csv",
    ".txt",
    ".html",
    ".css",
    ".mjs",
    ".js",
    ".sh",
    ".ps1",
    ".bash",
}
MAX_FILE_BYTES = 20_000_000
MAX_TOTAL_BYTES = 200_000_000
MAX_SOURCE_FILES = 10_000
RUN_TIMEOUT_SECONDS = 1_800
PERSISTENT_STAGES = ("prepare", "confirm", "crash", "recover", "rollback", "verify", "suite")
VOLUME_OWNER_LABEL = "io.jarvis.validation.owner"
VOLUME_PURPOSE_LABEL = "io.jarvis.validation.purpose"
SENSITIVE_DATA_NAMES = {"auth", "credentials", "secret", "secrets", "token", "tokens"}
DATA_SUFFIXES = {".json", ".toml", ".yml", ".yaml", ".txt", ".csv"}


def _source_info(path: Path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("redirected_source_path")
    return info


def _excluded(path: Path) -> bool:
    if path.name.startswith(".") or path.name in {"__pycache__", "node_modules"}:
        return True
    # A practical denylist, not a secret scanner or a guarantee about contents.
    prefix = path.stem.casefold().replace("-", ".").replace("_", ".").split(".")[0]
    return path.suffix.casefold() in DATA_SUFFIXES and prefix in SENSITIVE_DATA_NAMES


def _source_paths(root: Path):
    _source_info(root)
    for name in SOURCE_FILES:
        path = root / name
        if path.exists() or path.is_symlink():
            yield path
    visited = 0
    for name in SOURCE_DIRS:
        directory = root / name
        if not directory.exists() and not directory.is_symlink():
            continue
        stack = [directory]
        while stack:
            path = stack.pop()
            visited += 1
            if visited > 30_000:
                raise ValueError("source_archive_limit")
            if _excluded(path):
                continue
            info = _source_info(path)  # Before descending into a junction/reparse point.
            if stat.S_ISDIR(info.st_mode):
                stack.extend(sorted(path.iterdir(), reverse=True))
            else:
                yield path


def source_archive(root: Path) -> bytes:
    buffer = io.BytesIO()
    total = 0
    count = 0
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for path in _source_paths(root):
            relative = path.relative_to(root)
            if _excluded(path) and relative.as_posix() not in SOURCE_FILES:
                continue
            info = _source_info(path)
            if not stat.S_ISREG(info.st_mode) or (
                relative.as_posix() not in SOURCE_FILES
                and path.suffix not in SUFFIXES
                and path.name != "_jarvis-console"
            ):
                continue
            if info.st_nlink != 1:
                raise ValueError("invalid_source_file")
            if (
                info.st_size > MAX_FILE_BYTES
                or total + info.st_size > MAX_TOTAL_BYTES
                or count >= MAX_SOURCE_FILES
            ):
                raise ValueError("source_archive_limit")
            with path.open("rb") as source:
                opened = os.fstat(source.fileno())
                if (
                    (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
                    or opened.st_size != info.st_size
                    or opened.st_mtime_ns != info.st_mtime_ns
                    or not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                ):
                    raise ValueError("unstable_source_file")
                data = source.read(min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total) + 1)
                after = os.fstat(source.fileno())
            named = _source_info(path)
            if (
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                != (
                    opened.st_dev,
                    opened.st_ino,
                    opened.st_size,
                    opened.st_mtime_ns,
                    opened.st_ctime_ns,
                )
                or after.st_nlink != 1
                or len(data) != info.st_size
                or (named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns, named.st_ctime_ns)
                != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            ):
                raise ValueError("unstable_source_file")
            total += len(data)
            count += 1
            if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("source_archive_limit")
            member = tarfile.TarInfo(relative.as_posix())
            member.size = len(data)
            member.mode = 0o755 if info.st_mode & 0o111 else 0o644
            archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


def _validation_volume_name(name: str) -> bool:
    suffix = name.removeprefix("jarvis-linux-validation-storage-")
    return (
        name.startswith("jarvis-linux-validation-storage-")
        and len(suffix) == 32
        and all(char in "0123456789abcdef" for char in suffix)
    )


def docker_run_command(
    mode: str, *, container_name: str | None = None, volume_name: str | None = None,
) -> list[str]:
    persistent = mode in {f"persistent-{stage}" for stage in PERSISTENT_STAGES}
    if not persistent and mode not in {"physical", "standard", "release"}:
        raise ValueError("invalid_validation_mode")
    if (persistent and (volume_name is None or not _validation_volume_name(volume_name))) or (
        not persistent and volume_name is not None
    ):
        raise ValueError("invalid_validation_volume")
    name = container_name or f"jarvis-linux-validation-{uuid4().hex}"
    if (
        not name.startswith("jarvis-linux-validation-")
        or len(name.removeprefix("jarvis-linux-validation-")) != 32
        or any(
            char not in "0123456789abcdef" for char in name.removeprefix("jarvis-linux-validation-")
        )
    ):
        raise ValueError("invalid_validation_container_name")
    command = [
        "docker",
        "run",
        "--name",
        name,
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "2g",
        "--cpus",
        "2",
        "--pids-limit",
        "256",
        "--tmpfs",
        "/tmp:rw,exec,nosuid,size=2g",
    ]
    if persistent:
        # Only a runner-created named volume; never accept a bind or host path.
        command.extend([
            "--mount", f"type=volume,src={volume_name},dst=/validation,volume-nocopy",
        ])
    return [*command, IMAGE, mode]


def _owned_volume(name: str, nonce: str) -> bool:
    if not _validation_volume_name(name) or not name.endswith(nonce):
        return False
    result = subprocess.run(
        ["docker", "volume", "inspect", name], capture_output=True, text=True,
        timeout=30, check=False,
    )
    if result.returncode:
        return False
    try:
        values = loads(result.stdout)
        if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], dict):
            return False
        value = values[0]
        return (
            value.get("Name") == name and value.get("Driver") == "local"
            and value.get("Scope") == "local" and value.get("Options") in (None, {})
            and value.get("Labels") == {
                VOLUME_OWNER_LABEL: nonce, VOLUME_PURPOSE_LABEL: "persistent-physical",
            }
        )
    except (ValueError, TypeError):
        return False


def _run_owned_container(command: list[str], payload: bytes) -> int:
    name = command[command.index("--name") + 1]
    print(f"validation_container={name}", flush=True)
    result = None
    try:
        result = subprocess.run(
            command, input=payload, timeout=RUN_TIMEOUT_SECONDS, check=False,
        ).returncode
        return result
    finally:
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "--force", name], check=False, timeout=15,
                capture_output=True, text=True,
            )
            if cleanup.returncode and "no such container" not in cleanup.stderr.casefold():
                print("validation_container_cleanup_unconfirmed", flush=True)
                if result is not None:
                    raise ValueError("validation_container_cleanup_unconfirmed")
        except (OSError, subprocess.TimeoutExpired):
            print("validation_container_cleanup_unconfirmed", flush=True)
            if result is not None:
                raise ValueError("validation_container_cleanup_unconfirmed") from None


def run_persistent_validation(payload: bytes, image_id: str) -> int:
    # A tag can change between containers. Pin the inspected image for the campaign.
    if not image_id.startswith("sha256:") or len(image_id) != 71 or any(
        char not in "0123456789abcdef" for char in image_id[7:]
    ):
        raise ValueError("invalid_validation_image_identity")
    nonce = uuid4().hex
    volume = f"jarvis-linux-validation-storage-{nonce}"
    existing = subprocess.run(
        ["docker", "volume", "inspect", volume], capture_output=True, text=True,
        timeout=30, check=False,
    )
    # Refuse both an existing resource and an inconclusive daemon error.
    if existing.returncode != 1 or "no such volume" not in existing.stderr.casefold():
        raise ValueError("validation_volume_not_fresh")
    created = subprocess.run(
        ["docker", "volume", "create", "--driver", "local", "--label",
         f"{VOLUME_OWNER_LABEL}={nonce}", "--label",
         f"{VOLUME_PURPOSE_LABEL}=persistent-physical", volume],
        capture_output=True, text=True, timeout=30, check=False,
    )
    print(f"validation_volume={volume}", flush=True)
    if created.returncode or created.stdout.strip() != volume or not _owned_volume(volume, nonce):
        print("validation_volume_ownership_unconfirmed_preserved", flush=True)
        return 3
    print(f"validation_source_sha256={sha256(payload).hexdigest()}", flush=True)
    try:
        for stage in PERSISTENT_STAGES:
            if not _owned_volume(volume, nonce):
                print("validation_volume_ownership_changed_preserved", flush=True)
                return 3
            command = docker_run_command(f"persistent-{stage}", volume_name=volume)
            command[-2] = image_id
            result = _run_owned_container(command, payload)
            expected = 86 if stage == "crash" else 0
            print(f"validation_stage={stage} exit={result} expected={expected}", flush=True)
            if result != expected:
                print("validation_volume_preserved_after_failure", flush=True)
                return result if result > 0 else 3
    except BaseException:
        # Preserve failed/interrupted journals, not a blanket Docker cleanup.
        print("validation_volume_preserved_after_failure", flush=True)
        raise
    if not _owned_volume(volume, nonce):
        print("validation_volume_ownership_changed_preserved", flush=True)
        return 3
    removed = subprocess.run(
        ["docker", "volume", "rm", volume], capture_output=True, text=True,
        timeout=30, check=False,
    )
    if removed.returncode:
        print("validation_volume_cleanup_unconfirmed", flush=True)
        return 3
    print("validation_volume_removed_synthetic_test_data_only", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["physical", "standard", "release", "persistent"], default="physical",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Download/build development image explicitly.",
    )
    args = parser.parse_args()
    try:
        check = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Os}}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if check.returncode or check.stdout.strip() != "linux":
            print("linux_docker_backend_unavailable")
            return 3
        if args.build:
            result = subprocess.run(
                ["docker", "build", "--tag", IMAGE, str(ROOT / "tools" / "linux_validation")],
                check=False,
                timeout=600,
            )
            if result.returncode:
                return result.returncode
        identity = subprocess.run(
            ["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if identity.returncode:
            print("linux_validation_image_missing_use_explicit_build")
            return 3
        print(f"validation_image={identity.stdout.strip()}", flush=True)
        payload = source_archive(ROOT)
        if args.mode == "persistent":
            return run_persistent_validation(payload, identity.stdout.strip())
        name = f"jarvis-linux-validation-{uuid4().hex}"
        print(f"validation_container={name}", flush=True)
        try:
            return subprocess.run(
                docker_run_command(args.mode, container_name=name),
                input=payload,
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            ).returncode
        finally:
            # Only this invocation's unique container; never enumerate/delete
            # other containers, images, caches, volumes or host files.
            try:
                subprocess.run(
                    ["docker", "rm", "--force", name],
                    check=False,
                    timeout=15,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.TimeoutExpired):
                print("validation_container_cleanup_unconfirmed", flush=True)
    except KeyboardInterrupt:
        print("linux_validation_interrupted")
        return 130
    except (OSError, ValueError, tarfile.TarError, subprocess.TimeoutExpired):
        print("linux_validation_unavailable")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
