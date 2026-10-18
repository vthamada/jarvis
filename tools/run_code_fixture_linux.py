"""Opt-in physical Linux proof for four fixed fixtures, never arbitrary code.

This is not a generic sandbox, code-generation engine, patch executor, provider
or grant. Docker must already have the exact image; no download or host mount
is permitted. Child output is bounded and never published by the public API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

IMAGE = "sha256:06227a71f8091cae6663926523eeab05c4b5f976ffcc8a293854b38a1d00c7ac"
OWNER_LABEL = "io.jarvis.codefixture.owner"
PURPOSE_LABEL = "io.jarvis.codefixture.purpose"
PURPOSE = "code-fixture"
PROTOCOL = "jarvis-code-fixture-result-v1"
TMPFS_OPTIONS = "rw,nosuid,nodev,noexec,size=8m,mode=1777"
MAX_OUTPUT_BYTES = 4096
_HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
SCENARIOS = ("baseline", "candidate", "isolation", "timeout")
_PROGRAMS = {
    "baseline": "def add(a, b):\n    return a - b\n",
    "candidate": "def add(a, b):\n    return a + b\n",
    "isolation": (
        "import os\n"
        "checks = [os.getuid() == 65534]\n"
        "with open('/proc/self/mountinfo') as stream:\n"
        "    roots = [line.split() for line in stream if line.split()[4] == '/']\n"
        "checks.append(len(roots) == 1 and 'ro' in roots[0][5].split(','))\n"
        "with open('/proc/net/route') as stream:\n"
        "    routes = [line.split() for line in list(stream)[1:] if line.strip()]\n"
        "checks.append(all(route[0] == 'lo' for route in routes))\n"
        "with open('/proc/net/ipv6_route') as stream:\n"
        "    routes6 = [line.split() for line in stream if line.strip()]\n"
        "checks.append(all(route[-1] == 'lo' for route in routes6))\n"
        "checks.append(not os.path.lexists('/host/jarvis-code-fixture-host-marker'))\n"
    ),
    "timeout": "import time\nwhile True:\n    time.sleep(1)\n",
}
_IMAGE_FORMAT = (
    '{"id":{{json .Id}},"os":{{json .Os}},'
    '"architecture":{{json .Architecture}},"volumes":{{json (index .Config "Volumes")}}}'
)
_CONTAINER_FORMAT = (
    '{"id":{{json .Id}},"image":{{json .Image}},"name":{{json .Name}},'
    '"owner":{{json (index .Config.Labels "' + OWNER_LABEL + '")}},'
    '"purpose":{{json (index .Config.Labels "' + PURPOSE_LABEL + '")}},'
    '"running":{{json .State.Running}},"started_at":{{json .State.StartedAt}},'
    '"user":{{json .Config.User}},"read_only":{{json .HostConfig.ReadonlyRootfs}},'
    '"network":{{json .HostConfig.NetworkMode}},"mounts":{{json .Mounts}},'
    '"binds":{{json (index .HostConfig "Binds")}},"cap_drop":{{json .HostConfig.CapDrop}},'
    '"security_opt":{{json .HostConfig.SecurityOpt}},'
    '"pids_limit":{{json .HostConfig.PidsLimit}},"memory":{{json .HostConfig.Memory}},'
    '"nano_cpus":{{json .HostConfig.NanoCpus}},'
    '"privileged":{{json .HostConfig.Privileged}},"tmpfs":{{json .HostConfig.Tmpfs}},'
    '"entrypoint":{{json .Config.Entrypoint}},"cmd":{{json .Config.Cmd}},'
    '"working_dir":{{json .Config.WorkingDir}}}'
)
_OWNERSHIP_FORMAT = (
    '{"id":{{json .Id}},"image":{{json .Image}},"name":{{json .Name}},'
    '"owner":{{json (index .Config.Labels "' + OWNER_LABEL + '")}},'
    '"purpose":{{json (index .Config.Labels "' + PURPOSE_LABEL + '")}},'
    '"running":{{json .State.Running}}}'
)


@dataclass(frozen=True, slots=True)
class CommandResult:
    """`started` includes an uncertain spawn attempt, not verified execution."""

    returncode: int | None
    stdout: bytes
    stderr: bytes
    reason: str | None
    started: bool


def _cancellation(cancelled):
    if cancelled is None:
        return None
    try:
        value = cancelled()
        if type(value) is not bool:
            return "invalid_cancel_callback"
        return "cancelled" if value else None
    except KeyboardInterrupt:
        return "cancelled"
    except Exception:
        return "invalid_cancel_callback"


def _run_command(argv, *, timeout_seconds, cancelled=None):
    """Bound each pipe independently while polling deadline and cancellation."""
    reason = _cancellation(cancelled)
    if reason:
        return CommandResult(None, b"", b"", reason, False)
    try:
        process = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=False, bufsize=0, close_fds=True,
        )
    except KeyboardInterrupt:
        # Popen may be interrupted after spawning, before returning its handle.
        # The orchestrator must inspect the owned name instead of asserting
        # nothing was created. Only Docker StartedAt proves actual execution.
        return CommandResult(None, b"", b"", "cancelled", True)
    except OSError:
        return CommandResult(None, b"", b"", "unavailable", False)
    buffers = [bytearray(), bytearray()]
    exceeded = threading.Event()
    read_failed = threading.Event()
    readers = []

    def read_pipe(stream, output):
        try:
            while True:
                block = stream.read(1024)
                if not block:
                    return
                room = MAX_OUTPUT_BYTES - len(output)
                output.extend(block[:room])
                if len(block) > room:
                    exceeded.set()
                    return
        except (OSError, ValueError):
            read_failed.set()

    try:
        deadline = time.monotonic() + timeout_seconds
        readers = [threading.Thread(target=read_pipe, args=(stream, output), daemon=True)
                   for stream, output in zip((process.stdout, process.stderr), buffers)]
        for reader in readers:
            reader.start()
        while True:
            if exceeded.is_set():
                reason = "output_limit"
                break
            if read_failed.is_set():
                reason = "process_io_failed"
                break
            reason = _cancellation(cancelled)
            if reason:
                break
            if process.poll() is not None and all(not reader.is_alive() for reader in readers):
                break
            if time.monotonic() >= deadline:
                reason = "timeout"
                break
            time.sleep(0.01)
    except KeyboardInterrupt:
        reason = "cancelled"
    except Exception:
        reason = "process_io_failed"
    finally:
        try:
            if reason is not None or process.poll() is None:
                process.kill()
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt):
            reason = "process_cleanup_unconfirmed"
        for reader in readers:
            if reader.ident is not None:
                try:
                    reader.join(timeout=0.2)
                except KeyboardInterrupt:
                    reason = "process_cleanup_unconfirmed"
        if any(reader.is_alive() for reader in readers):
            reason = "process_cleanup_unconfirmed"
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except (OSError, ValueError, KeyboardInterrupt):
                reason = "process_cleanup_unconfirmed"
    if exceeded.is_set() and reason is None:
        reason = "output_limit"
    return CommandResult(process.returncode, bytes(buffers[0]), bytes(buffers[1]), reason, True)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError()
        result[key] = value
    return result


def _json(result):
    if result.reason is not None or result.returncode != 0 or len(result.stdout) > MAX_OUTPUT_BYTES:
        return None
    try:
        value = json.loads(result.stdout.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        return value if type(value) is dict else None
    except (ValueError, UnicodeError, RecursionError):
        return None


def fixture_sha256(scenario):
    if type(scenario) is not str or scenario not in SCENARIOS:
        raise ValueError("invalid_fixture_scenario")
    return hashlib.sha256(_PROGRAMS[scenario].encode("utf-8")).hexdigest()


def _script(scenario):
    # Only values from the literal allowlist reach Python's compile operation.
    program = _PROGRAMS[scenario]
    return (
        "import hashlib,json,sys\n"
        f"program={program!r}\nscenario={scenario!r}\n"
        "namespace={}\nexec(compile(program,'fixed_fixture','exec'),namespace)\n"
        "if scenario in ('baseline','candidate'):\n"
        "    add=namespace['add']\n"
        "    checks=[add(2,3)==5,add(-2,5)==3,add(0,4)==4]\n"
        "else:\n    checks=namespace['checks']\n"
        f"report={{'protocol':{PROTOCOL!r},'scenario':scenario,"
        "'fixture_sha256':hashlib.sha256(program.encode()).hexdigest(),"
        "'test_count':len(checks),'passed_count':sum(checks),"
        "'failed_count':len(checks)-sum(checks)}\n"
        "print(json.dumps(report,sort_keys=True,separators=(',',':')),flush=True)\n"
        "sys.exit(0 if all(checks) else 1)\n"
    )


def _create_command(name, owner, scenario):
    return [
        "docker", "create", "--pull", "never", "--name", name,
        "--label", OWNER_LABEL + "=" + owner, "--label", PURPOSE_LABEL + "=" + PURPOSE,
        "--network", "none", "--read-only", "--user", "65534:65534",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "32", "--memory", "256m", "--cpus", "1",
        "--tmpfs", "/work:" + TMPFS_OPTIONS, "--workdir", "/work",
        "--entrypoint", "python", IMAGE, "-I", "-B", "-c", _script(scenario),
    ]


def _inspect(target, *, timeout_seconds=3, cancelled=None):
    return _json(_run_command(
        ["docker", "container", "inspect", "--format", _CONTAINER_FORMAT, target],
        timeout_seconds=timeout_seconds, cancelled=cancelled,
    ))


def _inspect_owned(target):
    """Cleanup authority only; unavailable configuration never becomes proof."""
    return _json(_run_command(
        ["docker", "container", "inspect", "--format", _OWNERSHIP_FORMAT, target],
        timeout_seconds=3,
    ))


def _owned(value, name, owner, identity):
    return (type(value) is dict and type(value.get("id")) is str
            and _HEX.fullmatch(value["id"]) is not None
            and (identity is None or value["id"] == identity)
            and value.get("name") == "/" + name and value.get("owner") == owner
            and value.get("purpose") == PURPOSE and value.get("image") == IMAGE
            and type(value.get("running")) is bool)


def _isolated(value, scenario):
    mounts = value.get("mounts")
    return (value.get("user") == "65534:65534" and value.get("read_only") is True
            and value.get("network") == "none" and value.get("privileged") is False
            and value.get("binds") in (None, []) and value.get("cap_drop") == ["ALL"]
            and value.get("security_opt") == ["no-new-privileges"]
            and type(value.get("pids_limit")) is int and value["pids_limit"] == 32
            and type(value.get("memory")) is int and value["memory"] == 256 * 1024 * 1024
            and type(value.get("nano_cpus")) is int and value["nano_cpus"] == 1000000000
            and value.get("tmpfs") == {"/work": TMPFS_OPTIONS}
            and value.get("entrypoint") == ["python"]
            and value.get("cmd") == ["-I", "-B", "-c", _script(scenario)]
            and value.get("working_dir") == "/work"
            and type(mounts) is list and len(mounts) <= 1
            and all(type(mount) is dict and mount.get("Type") == "tmpfs"
                    and mount.get("Destination") == "/work" for mount in mounts))


def _started(value):
    stamp = value.get("started_at")
    if type(stamp) is not str or len(stamp) > 64:
        return False
    try:
        parsed = datetime.fromisoformat(stamp)
        return parsed.tzinfo is not None and parsed.year >= 2000
    except ValueError:
        return False


def _cleanup(name, owner, identity, scenario):
    # Ignore cancellation only for bounded cleanup, never for another workload.
    value = _inspect(identity or name)
    fully_observed = value is not None
    if value is None:
        # A configuration template may fail on an absent Docker field. It must
        # not obstruct cleanup of a separately verified owned container, nor
        # grant any claim about execution/isolation in the fallback path.
        value = _inspect_owned(identity or name)
    if not _owned(value, name, owner, identity):
        return False, False, False
    identity = value["id"]
    started = fully_observed and _started(value) and _isolated(value, scenario)
    was_running = value["running"]
    if value["running"]:
        stopped = _run_command(["docker", "stop", "--time", "1", identity], timeout_seconds=3)
        if stopped.reason is not None or stopped.returncode != 0:
            return False, started, was_running
    removed = _run_command(["docker", "rm", identity], timeout_seconds=3)
    if removed.reason is not None or removed.returncode != 0:
        return False, started, was_running
    absent = _run_command([
        "docker", "container", "ls", "--all", "--no-trunc", "--filter", "id=" + identity,
        "--format", "{{.ID}}",
    ], timeout_seconds=3)
    return (absent.reason is None and absent.returncode == 0
            and absent.stdout.strip() == b""), started, was_running


def _report(scenario, status, reason, *, cleanup=True, started=False, counts=(0, 0, 0)):
    return {
        "schema_version": "jarvis-code-fixture-proof-v1", "status": status, "reason": reason,
        "evidence_mode": "controlled_linux_fixture" if status == "passed" else "not_demonstrated",
        "scenario": scenario if type(scenario) is str and scenario in SCENARIOS else None,
        "test_count": counts[0], "passed_count": counts[1], "failed_count": counts[2],
        "fixture_sha256": fixture_sha256(scenario)
        if type(scenario) is str and scenario in SCENARIOS else None,
        "image_sha256": IMAGE, "cleanup_verified": cleanup, "execution_started": started,
        "authority": "none", "capability_promoted": False,
    }


def _expected(result, scenario):
    # Baseline intentionally returns exit1. Parse only after checking that
    # explicit expected code, never convert arbitrary child failures to proof.
    expected = (3, 0, 3) if scenario == "baseline" else (
        (5, 5, 0) if scenario == "isolation" else (3, 3, 0))
    if (result.reason is not None or result.stderr
            or result.returncode != (1 if scenario == "baseline" else 0)):
        return None
    value = _json(CommandResult(0, result.stdout, b"", None, result.started))
    fields = {"protocol", "scenario", "fixture_sha256", "test_count", "passed_count",
              "failed_count"}
    if (value is None or set(value) != fields or value["protocol"] != PROTOCOL
            or value["scenario"] != scenario or value["fixture_sha256"] != fixture_sha256(scenario)
            or any(type(value[key]) is not int
                   for key in ("test_count", "passed_count", "failed_count"))
            or tuple(value[key] for key in ("test_count", "passed_count", "failed_count"))
            != expected):
        return None
    return expected


def run_code_fixture_linux(*, authorized=False, scenario="candidate", timeout_seconds=10,
                           cancelled=None):
    """Run only an authorized literal fixture; return content-free evidence."""
    if type(authorized) is not bool:
        return _report(scenario, "refused", "invalid_options")
    if not authorized:
        return _report(scenario, "refused", "authorization_required")
    if (type(scenario) is not str or scenario not in SCENARIOS
            or type(timeout_seconds) not in (int, float)
            or cancelled is not None and not callable(cancelled)):
        return _report(scenario, "refused", "invalid_options")
    try:
        timeout_seconds = float(timeout_seconds)
    except (ValueError, OverflowError):
        return _report(scenario, "refused", "invalid_options")
    if not math.isfinite(timeout_seconds) or not 0.1 <= timeout_seconds <= 30:
        return _report(scenario, "refused", "invalid_options")
    reason = _cancellation(cancelled)
    if reason:
        return _report(scenario, "refused", reason)
    preflight = _run_command(["docker", "image", "inspect", "--format", _IMAGE_FORMAT, IMAGE],
                             timeout_seconds=min(timeout_seconds, 5), cancelled=cancelled)
    image = _json(preflight)
    if image is None:
        return _report(scenario, "unavailable", preflight.reason or "image_unavailable")
    if (image != {"id": IMAGE, "os": "linux", "architecture": "amd64", "volumes": None}
            and image != {"id": IMAGE, "os": "linux", "architecture": "amd64", "volumes": {}}):
        return _report(scenario, "refused", "image_identity_mismatch")
    reason = _cancellation(cancelled)
    if reason:
        return _report(scenario, "refused", reason)
    name, owner = "jarvis-code-fixture-" + uuid4().hex, uuid4().hex
    identity = None
    created = result = None
    failure = None
    clean, started, was_running = False, False, False
    try:
        created = _run_command(_create_command(name, owner, scenario),
                               timeout_seconds=min(timeout_seconds, 5), cancelled=cancelled)
        if created.started and created.reason is None and created.returncode == 0:
            try:
                proposed = created.stdout.decode("ascii").strip()
                identity = proposed if _HEX.fullmatch(proposed) else None
            except UnicodeError:
                pass
        if identity is None:
            failure = created.reason or "container_create_failed"
        else:
            value = _inspect(identity, timeout_seconds=min(timeout_seconds, 3), cancelled=cancelled)
            if not _owned(value, name, owner, identity) or not _isolated(value, scenario):
                failure = "container_configuration_refused"
            else:
                result = _run_command(["docker", "start", "--attach", identity],
                                      timeout_seconds=min(timeout_seconds, 1)
                                      if scenario == "timeout" else timeout_seconds,
                                      cancelled=cancelled)
    except KeyboardInterrupt:
        failure = "cancelled"
    except Exception:
        failure = "runner_failed"
    finally:
        # A create command interrupted before returning has uncertain outcome.
        # Inspect the unique name and only touch a fully verified owned ID.
        try:
            if created is None or created.started:
                clean, started, was_running = _cleanup(name, owner, identity, scenario)
            else:
                clean = True
        except (Exception, KeyboardInterrupt):
            clean, started, was_running = False, False, False
    if not clean:
        return _report(scenario, "failed", "cleanup_unconfirmed", cleanup=False, started=started)
    if failure is not None:
        return _report(scenario, "failed", failure, started=started)
    if scenario == "timeout":
        if result.reason == "timeout" and started and was_running:
            return _report(scenario, "passed", "expected_timeout", started=True)
        return _report(scenario, "failed", "expected_timeout_not_observed",
                       started=started)
    if not started or was_running:
        return _report(scenario, "failed", "execution_state_unconfirmed", started=started)
    counts = _expected(result, scenario)
    if counts is None:
        return _report(scenario, "failed", result.reason or "fixture_protocol_refused",
                       started=started)
    return _report(scenario, "passed", "expected_fixture_outcome", started=started, counts=counts)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("invalid_arguments")


def main(argv=None):
    parser = _Parser(description="Run an explicitly authorized, fixed Linux fixture.",
                     allow_abbrev=False)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--scenario", choices=SCENARIOS, default="candidate")
    parser.add_argument("--timeout-seconds", type=float, default=10)
    try:
        args = parser.parse_args(argv)
    except ValueError:
        print(json.dumps(_report(None, "refused", "invalid_arguments"), sort_keys=True))
        return 3
    try:
        result = run_code_fixture_linux(authorized=args.authorized, scenario=args.scenario,
                                       timeout_seconds=args.timeout_seconds)
    except KeyboardInterrupt:
        result = _report(args.scenario, "refused", "cancelled", cleanup=False)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" and result["cleanup_verified"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
