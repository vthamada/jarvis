"""Injected Docker command seams; these tests are not physical Linux proof."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

import pytest

from tools import run_code_fixture_linux as runner


def test_authorization_is_required_before_any_docker_command(monkeypatch):
    monkeypatch.setattr(runner, "_run_command", lambda *a, **k: pytest.fail("unexpected process"))
    result = runner.run_code_fixture_linux()
    assert result["status"] == "refused" and result["reason"] == "authorization_required"
    assert result["evidence_mode"] == "not_demonstrated"


@pytest.mark.parametrize("kwargs", [
    {"authorized": 1}, {"scenario": "private-source"}, {"timeout_seconds": True},
    {"timeout_seconds": float("nan")}, {"timeout_seconds": 0},
    {"timeout_seconds": 31}, {"timeout_seconds": 10**1000}, {"cancelled": True},
])
def test_invalid_options_are_refused_without_echo_or_docker(monkeypatch, kwargs):
    monkeypatch.setattr(runner, "_run_command", lambda *a, **k: pytest.fail("unexpected process"))
    options = {"authorized": True, **kwargs}
    result = runner.run_code_fixture_linux(**options)
    assert result["status"] == "refused"
    assert "private-source" not in json.dumps(result)


def _result(stdout=b"", rc=0, reason=None):
    return runner.CommandResult(rc, stdout, b"", reason, True)


def _docker(monkeypatch, *, scenario="candidate", mutate=None, run_result=None):
    calls = []
    state = {"exists": False, "started": False, "running": False}
    identity = "1" * 64

    def command(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[1:3] == ["image", "inspect"]:
            return _result(json.dumps({"id": runner.IMAGE, "os": "linux",
                                      "architecture": "amd64", "volumes": None}).encode())
        if argv[1] == "create":
            state["exists"] = True
            state["name"] = argv[argv.index("--name") + 1]
            labels = [argv[i + 1] for i, value in enumerate(argv) if value == "--label"]
            state["owner"] = next(item.split("=", 1)[1] for item in labels
                                  if item.startswith(runner.OWNER_LABEL + "="))
            return _result((identity + "\n").encode())
        if argv[1:3] == ["container", "inspect"]:
            if not state["exists"]:
                return _result(b"", 1)
            value = {"id": identity, "image": runner.IMAGE,
                     "name": "/" + state["name"], "owner": state["owner"],
                     "purpose": runner.PURPOSE, "running": state["running"],
                     "started_at": "2026-10-13T00:00:00Z" if state["started"]
                     else "0001-01-01T00:00:00Z",
                     "user": "65534:65534", "read_only": True, "network": "none",
                     "mounts": [], "binds": None, "cap_drop": ["ALL"],
                     "security_opt": ["no-new-privileges"], "pids_limit": 32,
                     "memory": 256 * 1024 * 1024, "nano_cpus": 1000000000,
                     "privileged": False, "tmpfs": {"/work": runner.TMPFS_OPTIONS},
                     "entrypoint": ["python"], "cmd": ["-I", "-B", "-c", runner._script(scenario)],
                     "working_dir": "/work"}
            if mutate:
                mutate(value)
            return _result(json.dumps(value).encode())
        if argv[1] == "start":
            state["started"] = True
            state["running"] = scenario == "timeout"
            if run_result:
                return run_result
            failed = 3 if scenario == "baseline" else 0
            count = 5 if scenario == "isolation" else 3
            report = {"protocol": runner.PROTOCOL, "scenario": scenario,
                      "fixture_sha256": runner.fixture_sha256(scenario),
                      "test_count": count, "passed_count": count - failed,
                      "failed_count": failed}
            return _result(json.dumps(report).encode(), 1 if failed else 0)
        if argv[1] == "stop":
            state["running"] = False
            return _result()
        if argv[1] == "rm":
            state["exists"] = False
            return _result(identity.encode())
        if argv[1:3] == ["container", "ls"]:
            return _result(identity.encode() if state["exists"] else b"")
        pytest.fail("unexpected Docker command")

    monkeypatch.setattr(runner, "_run_command", command)
    return calls


@pytest.mark.parametrize("scenario,count,failed", [
    ("candidate", 3, 0), ("baseline", 3, 3), ("isolation", 5, 0),
])
def test_expected_fixed_fixture_and_cleanup_protocol(monkeypatch, scenario, count, failed):
    calls = _docker(monkeypatch, scenario=scenario)
    result = runner.run_code_fixture_linux(authorized=True, scenario=scenario)
    assert result["status"] == "passed" and result["cleanup_verified"]
    assert result["test_count"] == count and result["failed_count"] == failed
    argv = next(argv for argv, _ in calls if argv[1] == "create")
    assert argv[argv.index("--pull") + 1] == "never"
    assert argv[argv.index("--network") + 1] == "none"
    assert argv[argv.index("--user") + 1] == "65534:65534"
    assert "--read-only" in argv and "--privileged" not in argv
    assert "--mount" not in argv and "--volume" not in argv and "-v" not in argv
    assert "--env" not in argv and "-e" not in argv
    assert argv[argv.index(runner.IMAGE) + 1:][:3] == ["-I", "-B", "-c"]
    assert "def add" not in json.dumps(result)
    assert "stdout" not in result and "stderr" not in result
    assert all(argv[-1] == "1" * 64 for argv, _ in calls if argv[1] in {"stop", "rm"})


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(owner="foreign"), lambda v: v.update(image="sha256:" + "a" * 64),
    lambda v: v.update(id="2" * 64), lambda v: v.update(purpose="foreign"),
])
def test_wrong_ownership_never_stops_or_removes(monkeypatch, mutation):
    calls = _docker(monkeypatch, mutate=mutation)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and not result["cleanup_verified"]
    assert not any(argv[1] in {"stop", "rm", "start"} for argv, _ in calls)


def test_host_mount_refused_but_owned_container_is_cleaned(monkeypatch):
    calls = _docker(monkeypatch, mutate=lambda v: v.update(
        mounts=[{"Type": "bind", "Source": "C:/private", "Destination": "/host"}]))
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["cleanup_verified"]
    assert not any(argv[1] == "start" for argv, _ in calls)
    assert "C:/private" not in json.dumps(result)


@pytest.mark.parametrize("report", [b"private-secret", b"{}", b'[{"private":"secret"}]'])
def test_malformed_child_protocol_is_never_success_or_exposed(monkeypatch, report):
    _docker(monkeypatch, run_result=_result(report))
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["cleanup_verified"]
    assert "private-secret" not in json.dumps(result)


def test_fixed_timeout_expected_only_with_verified_cleanup(monkeypatch):
    _docker(monkeypatch, scenario="timeout", run_result=_result(reason="timeout"))
    result = runner.run_code_fixture_linux(authorized=True, scenario="timeout")
    assert result["status"] == "passed" and result["reason"] == "expected_timeout"
    assert result["cleanup_verified"] and result["test_count"] == 0


def test_timed_out_attach_to_exited_container_is_not_timeout_proof(monkeypatch):
    _docker(monkeypatch, scenario="timeout", run_result=_result(reason="timeout"),
            mutate=lambda v: v.update(running=False))
    result = runner.run_code_fixture_linux(authorized=True, scenario="timeout")
    assert result["status"] == "failed" and result["cleanup_verified"]
    assert result["reason"] == "expected_timeout_not_observed"


def test_normal_protocol_requires_real_started_state(monkeypatch):
    _docker(monkeypatch, mutate=lambda v: v.update(started_at="0001-01-01T00:00:00Z"))
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["cleanup_verified"]
    assert result["reason"] == "execution_state_unconfirmed"


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(entrypoint=["sh"]), lambda v: v.update(cmd=["private-secret"]),
    lambda v: v.update(working_dir="/host"),
])
def test_command_drift_is_refused_before_start_and_cleaned(monkeypatch, mutation):
    calls = _docker(monkeypatch, mutate=mutation)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["cleanup_verified"]
    assert not any(argv[1] == "start" for argv, _ in calls)
    assert "private-secret" not in json.dumps(result)


@pytest.mark.parametrize("interrupt_at", ["create", "inspect", "start"])
def test_keyboard_interrupt_after_creation_performs_owned_cleanup(monkeypatch, interrupt_at):
    calls = _docker(monkeypatch)
    base = runner._run_command
    interrupted = False

    def command(argv, **kwargs):
        nonlocal interrupted
        result = base(argv, **kwargs)
        operation = "inspect" if argv[1:3] == ["container", "inspect"] else argv[1]
        if operation == interrupt_at and not interrupted:
            interrupted = True
            raise KeyboardInterrupt()
        return result

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["reason"] == "cancelled"
    assert result["cleanup_verified"]
    assert len([argv for argv, _ in calls if argv[1] == "rm"]) == 1


def test_cleanup_interrupt_reports_unconfirmed_without_second_destructive_attempt(monkeypatch):
    calls = _docker(monkeypatch)
    base = runner._run_command
    inspections = 0

    def command(argv, **kwargs):
        nonlocal inspections
        if argv[1:3] == ["container", "inspect"]:
            inspections += 1
            if inspections == 2:
                raise KeyboardInterrupt()
        return base(argv, **kwargs)

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["reason"] == "cleanup_unconfirmed"
    assert not result["cleanup_verified"]
    assert not any(argv[1] == "rm" for argv, _ in calls)


def test_unavailable_image_is_not_pulled_or_launched(monkeypatch):
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        return _result(rc=1)

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "unavailable"
    assert len(calls) == 1 and calls[0][1:3] == ["image", "inspect"]


def test_optional_docker_fields_use_index_without_relaxing_required_fields():
    assert '{{json (index .Config "Volumes")}}' in runner._IMAGE_FORMAT
    assert '{{json (index .HostConfig "Binds")}}' in runner._CONTAINER_FORMAT
    assert "{{json .Id}}" in runner._IMAGE_FORMAT
    assert "{{json .State.Running}}" in runner._CONTAINER_FORMAT


def test_declared_image_volumes_are_refused_before_create(monkeypatch):
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        return _result(json.dumps({"id": runner.IMAGE, "os": "linux", "architecture": "amd64",
                                  "volumes": {"/private": {}}}).encode())

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "refused" and result["reason"] == "image_identity_mismatch"
    assert len(calls) == 1 and calls[0][1:3] == ["image", "inspect"]


def test_failed_full_inspect_uses_owned_cleanup_without_execution_promotion(monkeypatch):
    calls = _docker(monkeypatch)
    base = runner._run_command

    def command(argv, **kwargs):
        if argv[1:3] == ["container", "inspect"] and argv[-2] == runner._CONTAINER_FORMAT:
            return _result(rc=1)
        return base(argv, **kwargs)

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["cleanup_verified"]
    assert result["execution_started"] is False
    assert result["evidence_mode"] == "not_demonstrated"
    assert not any(argv[1] == "start" for argv, _ in calls)
    assert len([argv for argv, _ in calls if argv[1] == "rm"]) == 1


def test_fallback_with_invalid_ownership_preserves_container(monkeypatch):
    calls = _docker(monkeypatch, mutate=lambda value: value.update(owner="foreign"))
    base = runner._run_command

    def command(argv, **kwargs):
        if argv[1:3] == ["container", "inspect"] and argv[-2] == runner._CONTAINER_FORMAT:
            return _result(rc=1)
        return base(argv, **kwargs)

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and not result["cleanup_verified"]
    assert result["reason"] == "cleanup_unconfirmed"
    assert not any(argv[1] in {"start", "stop", "rm"} for argv, _ in calls)


def test_cancel_before_execution_does_not_invoke_docker(monkeypatch):
    monkeypatch.setattr(runner, "_run_command", lambda *a, **k: pytest.fail("unexpected process"))
    result = runner.run_code_fixture_linux(authorized=True, cancelled=lambda: True)
    assert result["status"] == "refused" and result["reason"] == "cancelled"


def test_bounded_output_does_not_use_communicate(monkeypatch):
    process = SimpleNamespace(stdout=io.BytesIO(b"x" * 4097), stderr=io.BytesIO(b""),
                              poll=lambda: 0, wait=lambda timeout: 0,
                              kill=lambda: None, returncode=0)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **k: process)
    result = runner._run_command(["docker", "version"], timeout_seconds=1)
    assert result.reason == "output_limit" and len(result.stdout) <= 4096


def test_os_error_does_not_expose_path_or_details(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("private-path-and-secret")

    monkeypatch.setattr(runner.subprocess, "Popen", unavailable)
    result = runner._run_command(["docker", "version"], timeout_seconds=1)
    assert result.reason == "unavailable" and result.stdout == result.stderr == b""


def test_process_keyboard_interrupt_always_kills_waits_and_closes(monkeypatch):
    events = []
    process = SimpleNamespace(stdout=io.BytesIO(b""), stderr=io.BytesIO(b""), returncode=None)

    def poll():
        raise KeyboardInterrupt()

    def kill():
        events.append("kill")
        process.returncode = -9

    def wait(timeout):
        events.append("wait")
        return process.returncode

    process.poll, process.kill, process.wait = poll, kill, wait
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **k: process)
    result = runner._run_command(["docker", "version"], timeout_seconds=1)
    assert result.reason == "cancelled" and events == ["kill", "wait"]
    assert process.stdout.closed and process.stderr.closed


def test_popen_interrupt_reports_uncertain_launch_not_proven_absence(monkeypatch):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(runner.subprocess, "Popen", interrupted)
    result = runner._run_command(["docker", "version"], timeout_seconds=1)
    assert result.reason == "cancelled" and result.started is True
    assert result.stdout == result.stderr == b""


def test_uncertain_create_spawn_is_cleaned_by_verified_owned_name(monkeypatch):
    calls = _docker(monkeypatch)
    base = runner._run_command

    def command(argv, **kwargs):
        result = base(argv, **kwargs)
        if argv[1] == "create":
            return runner.CommandResult(None, b"", b"", "cancelled", True)
        return result

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["reason"] == "cancelled"
    assert result["cleanup_verified"] and not result["execution_started"]
    assert not any(argv[1] == "start" for argv, _ in calls)
    assert len([argv for argv, _ in calls if argv[1] == "rm"]) == 1


def test_uncertain_create_absence_cannot_be_reported_as_cleanup_proof(monkeypatch):
    calls = _docker(monkeypatch)
    base = runner._run_command

    def command(argv, **kwargs):
        if argv[1] == "create":
            return runner.CommandResult(None, b"", b"", "cancelled", True)
        return base(argv, **kwargs)

    monkeypatch.setattr(runner, "_run_command", command)
    result = runner.run_code_fixture_linux(authorized=True)
    assert result["status"] == "failed" and result["reason"] == "cleanup_unconfirmed"
    assert not result["cleanup_verified"] and not result["execution_started"]
    assert not any(argv[1] in {"start", "stop", "rm"} for argv, _ in calls)


def test_cli_fixed_error_does_not_echo_arguments(capsys):
    assert runner.main(["--source", "private-secret"]) == 3
    output = capsys.readouterr()
    assert "private-secret" not in output.out + output.err
    assert json.loads(output.out)["reason"] == "invalid_arguments"
