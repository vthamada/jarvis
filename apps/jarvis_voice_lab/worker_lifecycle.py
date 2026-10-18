"""Private Windows worker identity handshake; no SDK, process scans, or public metadata."""

from __future__ import annotations

import ctypes
import json
import os
import re
import secrets
import stat
import time
from ctypes import wintypes
from pathlib import Path

SCHEMA = "jarvis-owned-worker-v1"
READY = "worker-identity.tmp"
ACK = "worker-identity-ack.tmp"
MAX_BYTES = 2048
HANDSHAKE_SECONDS = 8.0
EXIT_SECONDS = 5.0


class WorkerExitUnconfirmed(RuntimeError):
    """The caller must retain its private runtime/capture, never claim cleanup succeeded."""

    artifacts_retained = True

    def __init__(self):
        super().__init__("local_asr_worker_exit_unconfirmed")


def _local_absolute_path(value):
    """Reject network/device/root-relative spellings before filesystem metadata IO."""
    raw = os.fspath(value)
    if (type(raw) is not str or not 1 <= len(raw) <= 4096
            or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in raw)
            or raw.startswith(("\\", "//"))):
        raise ValueError("worker_private_path_refused")
    path = Path(raw)
    if (not path.is_absolute()
            or (os.name == "nt" and re.match(r"^[A-Za-z]:[/\\]", raw) is None)):
        raise ValueError("worker_private_path_refused")
    return path


def _plain(path, *, directory=False):
    path = _local_absolute_path(path)
    for component in (path, *path.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("worker_private_path_refused")
    info = path.stat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("worker_private_directory_required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("worker_private_file_required")
    return path


def _identity(info):
    return info.st_dev, info.st_ino


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("worker_duplicate_field")
        result[key] = value
    return result


def _read(path, expected=None):
    try:
        _plain(path)
    except FileNotFoundError:
        return None, expected
    before = path.stat()
    identity = _identity(before)
    if before.st_size > MAX_BYTES or (expected is not None and identity != expected):
        raise ValueError("worker_private_metadata_refused")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (_identity(opened) != identity or opened.st_nlink != 1
                or not stat.S_ISREG(opened.st_mode)):
            raise ValueError("worker_private_metadata_replaced")
        raw = os.read(descriptor, MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("worker_private_metadata_limit")
        if _identity(path.stat()) != identity:
            raise ValueError("worker_private_metadata_replaced")
    finally:
        os.close(descriptor)
    if b"\n" not in raw:
        return None, identity  # Writer has not finished the bounded record yet.
    if raw.count(b"\n") != 1 or not raw.endswith(b"\n"):
        raise ValueError("worker_private_metadata_invalid")
    return json.loads(raw.decode("ascii"), object_pairs_hook=_unique), identity


def _write(path, document):
    raw = json.dumps(document, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"
    if len(raw) > MAX_BYTES:
        raise ValueError("worker_private_metadata_limit")
    _plain(path.parent, directory=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("worker_private_metadata_refused")
        if os.write(descriptor, raw) != len(raw):
            raise ValueError("worker_private_metadata_short_write")
    finally:
        os.close(descriptor)


def _binding(value):
    if (type(value) is not dict or set(value) != {"schema_version", "run_id", "nonce"}
            or value["schema_version"] != SCHEMA
            or type(value["run_id"]) is not str
            or re.fullmatch(r"[a-f0-9]{32}", value["run_id"]) is None
            or type(value["nonce"]) is not str
            or re.fullmatch(r"[a-f0-9]{64}", value["nonce"]) is None):
        raise ValueError("worker_identity_binding_refused")
    return dict(value)


def _normalized(path):
    return os.path.normcase(os.path.abspath(path))


class WindowsProcessApi:
    """Only exact process handles; never enumerate processes or terminate by PID/name."""

    def __init__(self):
        if os.name != "nt":
            raise ValueError("windows_worker_lifecycle_required")
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "GetCurrentProcess": ([], wintypes.HANDLE),
            "GetProcessId": ([wintypes.HANDLE], wintypes.DWORD),
            "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
            "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            "TerminateProcess": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "GetProcessTimes": ([wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)],
                                wintypes.BOOL),
            "QueryFullProcessImageNameW": ([wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                            ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        self.ntquery = ctypes.WinDLL("ntdll").NtQueryInformationProcess
        self.ntquery.argtypes = [wintypes.HANDLE, wintypes.ULONG, wintypes.LPVOID,
                                wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
        self.ntquery.restype = wintypes.LONG

    def current(self):
        return self.kernel.GetCurrentProcess()

    def created(self, handle):
        values = [wintypes.FILETIME() for _ in range(4)]
        if not self.kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in values)):
            raise ValueError("worker_creation_time_unavailable")
        return values[0].dwHighDateTime << 32 | values[0].dwLowDateTime

    def image(self, handle):
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if not self.kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            raise ValueError("worker_image_unavailable")
        return _normalized(buffer.value)

    def parent(self, handle):
        class BasicInformation(ctypes.Structure):
            _fields_ = [("reserved1", ctypes.c_void_p), ("peb", ctypes.c_void_p),
                        ("reserved2", ctypes.c_void_p * 2), ("pid", ctypes.c_size_t),
                        ("parent_pid", ctypes.c_size_t)]

        value, length = BasicInformation(), wintypes.ULONG()
        if self.ntquery(handle, 0, ctypes.byref(value), ctypes.sizeof(value),
                        ctypes.byref(length)) != 0 or length.value != ctypes.sizeof(value):
            raise ValueError("worker_parent_unavailable")
        return value.parent_pid

    def open(self, pid):
        handle = self.kernel.OpenProcess(0x1000 | 0x100000 | 0x0001, False, pid)
        if not handle:
            raise ValueError("worker_handle_unavailable")
        return handle

    def pid(self, handle):
        return self.kernel.GetProcessId(handle)

    def exited(self, handle, seconds=0):
        result = self.kernel.WaitForSingleObject(handle, max(0, int(seconds * 1000)))
        if result not in {0, 258}:
            raise ValueError("worker_wait_unavailable")
        return result == 0

    def terminate(self, handle):
        if not self.kernel.TerminateProcess(handle, 73):
            raise ValueError("worker_termination_unavailable")

    def close(self, handle):
        self.kernel.CloseHandle(handle)


def expected_worker_image(executable):
    selected = _plain(executable)
    configuration = selected.parent.parent / "pyvenv.cfg"
    if not configuration.exists() and not configuration.is_symlink():
        return _normalized(selected)
    configuration = _plain(configuration)
    if not 1 <= configuration.stat().st_size <= 16384:
        raise ValueError("worker_venv_configuration_refused")
    homes = []
    for line in configuration.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "home":
            homes.append(value.strip())
    if len(homes) != 1:
        raise ValueError("worker_venv_configuration_refused")
    try:
        home = _local_absolute_path(homes[0])
    except (TypeError, ValueError):
        raise ValueError("worker_venv_configuration_refused") from None
    return _normalized(_plain(home / "python.exe"))


class OwnedWorkerSupervisor:
    """Acknowledge only after retaining a handle bound to this launch and private nonce."""

    def __init__(self, *, process, directory, binding, expected_image, api=None):
        self.process = process
        self.directory = _plain(directory, directory=True)
        self.binding = _binding(binding)
        self.expected_image = _normalized(expected_image)
        self.api = api if api is not None else WindowsProcessApi()
        self.handle = None
        self.ready_identity = None
        self.exit_confirmed = False
        self.launcher_created = self.api.created(int(process._handle))

    def poll_handshake(self, *, acknowledge=True):
        if self.handle is not None:
            return True
        ready, self.ready_identity = _read(self.directory / READY, self.ready_identity)
        if ready is None:
            return False
        fields = {"schema_version", "run_id", "nonce", "pid", "ppid", "creation_time"}
        if (type(ready) is not dict or set(ready) != fields
                or any(ready.get(key) != value for key, value in self.binding.items())
                or any(type(ready[key]) is not int or not 0 < ready[key] < 2**32
                       for key in ("pid", "ppid"))
                or type(ready["creation_time"]) is not int
                or not 0 < ready["creation_time"] < 2**64):
            raise ValueError("worker_identity_refused")
        same_process = ready["pid"] == self.process.pid
        expected_parent = os.getpid() if same_process else self.process.pid
        if ready["ppid"] != expected_parent:
            raise ValueError("worker_parent_binding_refused")
        handle = self.api.open(ready["pid"])
        try:
            if (self.api.pid(handle) != ready["pid"]
                    or self.api.parent(handle) != expected_parent
                    or self.api.created(handle) != ready["creation_time"]
                    or self.api.created(handle) < self.launcher_created
                    or self.api.image(handle) != self.expected_image
                    or self.api.exited(handle)):
                raise ValueError("worker_handle_identity_refused")
            self.handle = handle
        except BaseException:
            self.api.close(handle)
            raise
        # Keep the validated handle even when ACK creation fails: it remains safely stoppable.
        if acknowledge:
            _write(self.directory / ACK, ready)
        return True

    def confirm_exit(self, *, terminate=False, timeout_seconds=EXIT_SECONDS):
        if self.exit_confirmed:
            return
        try:
            if self.handle is None:
                self.poll_handshake(acknowledge=False)
            if self.handle is None:
                raise WorkerExitUnconfirmed()
            if terminate and not self.api.exited(self.handle):
                try:
                    self.api.terminate(self.handle)
                except Exception:
                    # Exit can win the race after the zero-time wait. A failed
                    # termination is never proof: only a signalled, already
                    # attested handle can authorize cleanup in this case.
                    if not self.api.exited(self.handle, timeout_seconds):
                        raise WorkerExitUnconfirmed() from None
                    self.exit_confirmed = True
                    return
            if not self.api.exited(self.handle, timeout_seconds):
                raise WorkerExitUnconfirmed()
            self.exit_confirmed = True
        except Exception:
            raise WorkerExitUnconfirmed() from None

    def close(self):
        if self.handle is not None:
            self.api.close(self.handle)
            self.handle = None


def new_binding(run_id):
    return _binding(dict(schema_version=SCHEMA, run_id=run_id, nonce=secrets.token_hex(32)))


def acknowledge_worker(request, *, api=None, clock=time.monotonic, pause=time.sleep):
    """Called before SDK imports; absence of a validated supervisor ACK forbids SDK work."""
    binding = _binding(request["worker_lifecycle"])
    if request.get("run_id") != binding["run_id"]:
        raise ValueError("worker_run_binding_refused")
    directory = _plain(Path.cwd(), directory=True)
    if _normalized(request["output_directory"]) != _normalized(directory):
        raise ValueError("worker_directory_binding_refused")
    api = api if api is not None else WindowsProcessApi()
    ready = dict(binding, pid=os.getpid(), ppid=os.getppid(),
                 creation_time=api.created(api.current()))
    _write(directory / READY, ready)
    deadline, identity = clock() + HANDSHAKE_SECONDS, None
    while clock() < deadline:
        acknowledgment, identity = _read(directory / ACK, identity)
        if acknowledgment is not None:
            if (type(acknowledgment) is not dict or acknowledgment != ready
                    or any(type(acknowledgment[key]) is not type(value)
                           for key, value in ready.items())
                    or api.created(api.current()) != ready["creation_time"]):
                raise ValueError("worker_acknowledgment_refused")
            return
        pause(min(0.01, max(0.0, deadline - clock())))
    raise ValueError("worker_acknowledgment_expired")
