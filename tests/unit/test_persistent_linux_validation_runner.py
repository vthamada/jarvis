"""Declared Docker command seams, not persistent-storage execution evidence."""

import json
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import run_linux_validation as runner
from tools.linux_validation import entrypoint

IMAGE = "sha256:" + "a" * 64
VOLUME = "jarvis-linux-validation-storage-" + "b" * 32


def docker_seam(
    monkeypatch, *, failure=None, drift=False, cleanup_failure=False,
    container_cleanup_failure=False,
):
    calls = []
    state = {"volume": None, "inspects": 0}

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1:3] == ["volume", "inspect"]:
            state["inspects"] += 1
            if state["volume"] is None:
                return SimpleNamespace(
                    returncode=1, stdout="", stderr="get synthetic: no such volume",
                )
            name = state["volume"]
            labels = {
                runner.VOLUME_OWNER_LABEL: name.rsplit("-", 1)[1],
                runner.VOLUME_PURPOSE_LABEL: "persistent-physical",
            }
            if drift and state["inspects"] >= 3:
                labels[runner.VOLUME_OWNER_LABEL] = "foreign"
            value = {"Name": name, "Driver": "local", "Scope": "local",
                     "Options": None, "Labels": labels}
            return SimpleNamespace(returncode=0, stdout=json.dumps([value]))
        if command[1:3] == ["volume", "create"]:
            state["volume"] = command[-1]
            return SimpleNamespace(returncode=0, stdout=command[-1])
        if command[1] == "run":
            stage = command[-1].removeprefix("persistent-")
            if failure == "interrupt":
                raise KeyboardInterrupt
            if failure == "timeout":
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            code = 86 if stage == "crash" else 0
            if failure == stage:
                code = 0 if stage == "crash" else 7
            return SimpleNamespace(returncode=code)
        if command[1:3] == ["rm", "--force"]:
            return SimpleNamespace(
                returncode=1 if container_cleanup_failure else 0, stderr="private diagnostic",
            )
        assert command == ["docker", "volume", "rm", state["volume"]]
        return SimpleNamespace(returncode=1 if cleanup_failure else 0, stdout="")

    monkeypatch.setattr(runner.subprocess, "run", run)
    return calls, state


def test_persistent_campaign_pins_image_sources_and_removes_only_owned_volume(monkeypatch, capsys):
    calls, state = docker_seam(monkeypatch)
    assert runner.run_persistent_validation(b"synthetic-sources", IMAGE) == 0
    runs = [item for item in calls if item[0][1] == "run"]
    assert [command[-1] for command, _ in runs] == [
        f"persistent-{stage}" for stage in runner.PERSISTENT_STAGES
    ]
    assert len({command[command.index("--name") + 1] for command, _ in runs}) == len(runs)
    for command, kwargs in runs:
        assert command[-2] == IMAGE and kwargs["input"] == b"synthetic-sources"
        assert command[command.index("--mount") + 1] == (
            f"type=volume,src={state['volume']},dst=/validation,volume-nocopy"
        )
        assert command[command.index("--network") + 1] == "none"
        assert "--read-only" in command and "ALL" in command and "--privileged" not in command
        assert "-v" not in command and "type=bind" not in " ".join(command)
    assert calls[-1][0] == ["docker", "volume", "rm", state["volume"]]
    output = capsys.readouterr().out
    assert "validation_source_sha256=" in output and "synthetic-sources" not in output
    assert "validation_volume_removed_synthetic_test_data_only" in output


@pytest.mark.parametrize("stage", runner.PERSISTENT_STAGES)
def test_failed_or_missing_expected_crash_preserves_volume(monkeypatch, capsys, stage):
    calls, _ = docker_seam(monkeypatch, failure=stage)
    assert runner.run_persistent_validation(b"sources", IMAGE) != 0
    assert not any(command[1:3] == ["volume", "rm"] for command, _ in calls)
    assert "validation_volume_preserved_after_failure" in capsys.readouterr().out
    assert calls[-1][0][1:3] == ["rm", "--force"]


@pytest.mark.parametrize("failure", ["interrupt", "timeout"])
def test_interrupted_campaign_reaps_own_container_but_preserves_volume(monkeypatch, failure):
    calls, _ = docker_seam(monkeypatch, failure=failure)
    with pytest.raises(KeyboardInterrupt if failure == "interrupt" else subprocess.TimeoutExpired):
        runner.run_persistent_validation(b"sources", IMAGE)
    assert calls[-1][0][1:3] == ["rm", "--force"]
    assert not any(command[1:3] == ["volume", "rm"] for command, _ in calls)


def test_volume_ownership_drift_prevents_deletion(monkeypatch, capsys):
    calls, _ = docker_seam(monkeypatch, drift=True)
    assert runner.run_persistent_validation(b"sources", IMAGE) == 3
    assert not any(command[1:3] == ["volume", "rm"] for command, _ in calls)
    assert "validation_volume_ownership_changed_preserved" in capsys.readouterr().out


def test_failed_volume_cleanup_cannot_be_reported_as_complete(monkeypatch, capsys):
    docker_seam(monkeypatch, cleanup_failure=True)
    assert runner.run_persistent_validation(b"sources", IMAGE) == 3
    assert "validation_volume_cleanup_unconfirmed" in capsys.readouterr().out


@pytest.mark.parametrize("image", ["latest", "sha256:test", "sha256:" + "z" * 64])
def test_invalid_image_refused_before_docker(monkeypatch, image):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("Docker accessed"))
    with pytest.raises(ValueError, match="image_identity"):
        runner.run_persistent_validation(b"sources", image)


@pytest.mark.parametrize("error", [None, "permission denied", "backend unavailable"])
def test_existing_or_inconclusive_volume_never_reused(monkeypatch, error):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0 if error is None else 1, stderr=error or "")

    monkeypatch.setattr(runner.subprocess, "run", run)
    with pytest.raises(ValueError, match="not_fresh"):
        runner.run_persistent_validation(b"sources", IMAGE)
    assert len(calls) == 1


@pytest.mark.parametrize("volume", [None, "human-data", "C:/Users/data", "../escape",
                                    VOLUME + ",type=bind", VOLUME.upper()])
def test_persistent_command_rejects_foreign_or_host_volume(volume):
    with pytest.raises(ValueError, match="validation_volume"):
        runner.docker_run_command("persistent-prepare", volume_name=volume)
    with pytest.raises(ValueError):
        runner.docker_run_command("physical", volume_name=VOLUME)


@pytest.mark.parametrize("change", [
    {"Driver": "remote"}, {"Scope": "global"}, {"Options": {"device": "/human"}},
    {"Name": "human-data"}, {"Labels": {}},
])
def test_volume_inspection_refuses_driver_options_or_binding_drift(monkeypatch, change):
    value = {"Name": VOLUME, "Driver": "local", "Scope": "local", "Options": {},
             "Labels": {runner.VOLUME_OWNER_LABEL: "b" * 32,
                        runner.VOLUME_PURPOSE_LABEL: "persistent-physical"}}
    value.update(change)
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=json.dumps([value]),
    ))
    assert not runner._owned_volume(VOLUME, "b" * 32)


@pytest.mark.parametrize("filesystem", ["ext4", "tmpfs", "ramfs", "overlay", "missing"])
def test_mount_metadata_distinguishes_disk_from_ephemeral_storage(monkeypatch, filesystem):
    monkeypatch.setattr(Path, "lstat", lambda _: SimpleNamespace(st_mode=stat.S_IFDIR | 0o700))
    mountinfo = (
        f"100 99 8:16 /volume /validation rw - {filesystem} /dev/synthetic rw\n"
        if filesystem != "missing" else "100 99 0:1 / /tmp rw - tmpfs tmpfs rw\n"
    )
    monkeypatch.setattr(Path, "read_text", lambda _: mountinfo)
    if filesystem == "ext4":
        assert entrypoint.persistent_storage_info(Path("/validation")) == {
            "storage_mode": "mounted_non_ephemeral_filesystem", "filesystem": "ext4",
        }
    else:
        with pytest.raises(ValueError, match="persistent_validation"):
            entrypoint.persistent_storage_info(Path("/validation"))


@pytest.mark.parametrize("stage", runner.PERSISTENT_STAGES)
def test_entrypoint_uses_only_fixed_persistent_commands(monkeypatch, stage):
    import io

    calls = []
    monkeypatch.setattr(entrypoint.sys, "platform", "linux")
    monkeypatch.setattr(entrypoint.sys, "argv", ["entrypoint", f"persistent-{stage}"])
    monkeypatch.setattr(entrypoint.sys, "stdin", SimpleNamespace(buffer=io.BytesIO()))
    monkeypatch.setattr(entrypoint, "extract_sources", lambda *a: None)
    monkeypatch.setattr(entrypoint, "persistent_storage_info", lambda root: {})
    monkeypatch.setattr(entrypoint, "initialize_persistent_volume", lambda root: None)
    monkeypatch.setattr(entrypoint.subprocess, "run", lambda command, **kw: (
        calls.append((command, kw)), SimpleNamespace(returncode=0),
    )[1])
    assert entrypoint.main() == 0
    command = calls[0][0]
    if stage == "suite":
        assert command[1:6] == ["-m", "pytest", "-ra", "--basetemp", "/validation/pytest-fixtures"]
        assert command[6:] == list(entrypoint.PHYSICAL_TESTS)
    else:
        assert command[1:] == ["-m", "tools.linux_validation.persistent_scenario", stage]


@pytest.mark.parametrize("existing,owner", [(True, 0), (False, 1), (False, 0)])
def test_only_empty_owned_fixed_volume_gets_private_permissions(monkeypatch, existing, owner):
    changed = []
    monkeypatch.setattr(entrypoint.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(Path, "lstat", lambda _: SimpleNamespace(st_uid=owner))
    monkeypatch.setattr(Path, "iterdir", lambda _: iter([Path("private")] if existing else []))
    monkeypatch.setattr(Path, "chmod", lambda root, mode: changed.append((root, mode)))
    if existing or owner != 0:
        with pytest.raises(ValueError, match="not_fresh"):
            entrypoint.initialize_persistent_volume(Path("/validation"))
        assert not changed
    else:
        entrypoint.initialize_persistent_volume(Path("/validation"))
        assert changed == [(Path("/validation"), 0o700)]
    with pytest.raises(ValueError, match="mount"):
        entrypoint.initialize_persistent_volume(Path("/human"))


def test_unconfirmed_container_cleanup_preserves_volume_without_private_diagnostics(
    monkeypatch, capsys,
):
    calls, _ = docker_seam(monkeypatch, container_cleanup_failure=True)
    with pytest.raises(ValueError, match="container_cleanup_unconfirmed"):
        runner.run_persistent_validation(b"sources", IMAGE)
    assert not any(command[1:3] == ["volume", "rm"] for command, _ in calls)
    output = capsys.readouterr().out
    assert "validation_volume_preserved_after_failure" in output
    assert "private diagnostic" not in output
