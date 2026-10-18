"""Real Windows base/venv process handles and synthetic exclusive capture, no ML SDK."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from apps.jarvis_voice_lab import worker_lifecycle as lifecycle
from apps.jarvis_voice_lab.lab import _stop, worker_environment

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows process handle integration")

CHILD = r'''
import ctypes
import importlib.util
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

spec = importlib.util.spec_from_file_location("private_lifecycle", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
request = json.loads(sys.stdin.buffer.read(16384))
module.acknowledge_worker(request)
# A synthetic file, never a physical microphone, reference voice, provider, or SDK.
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel.CreateFileW.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL
handle = kernel.CreateFileW(str(Path.cwd() / "capture-synthetic.wav"),
                            0xC0000000, 0, None, 1, 0x80, None)
if not handle or handle == ctypes.c_void_p(-1).value:
    raise SystemExit(2)
try:
    (Path.cwd() / "capture-ready.tmp").write_bytes(b"ready")
    if sys.argv[2] == "linger":
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
finally:
    kernel.CloseHandle(handle)
print(json.dumps({"status": "completed"}))
'''


@pytest.mark.parametrize("python_source", ["active", "base"])
@pytest.mark.parametrize("mode", ["normal", "linger"])
def test_real_worker_exit_precedes_synthetic_capture_cleanup(tmp_path, python_source, mode):
    executable = Path(sys.executable if python_source == "active" else sys._base_executable)
    script = tmp_path / "synthetic_worker.py"
    script.write_text(CHILD, encoding="utf-8")
    for name in ("home", "tmp", "cache"):
        (tmp_path / name).mkdir()
    binding = lifecycle.new_binding("a" * 32)
    request = dict(run_id="a" * 32, output_directory=str(tmp_path), worker_lifecycle=binding)
    payload = json.dumps(request).encode("ascii")
    helper = Path(lifecycle.__file__).absolute()
    process, owner, first = None, None, True
    status_path = tmp_path / "worker-status.tmp"
    with status_path.open("xb") as status:
        try:
            process = subprocess.Popen(
                [str(executable), "-I", str(script), str(helper), mode],
                cwd=tmp_path, stdin=subprocess.PIPE, stdout=status, stderr=subprocess.DEVNULL,
                env=worker_environment(executable, tmp_path),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            owner = lifecycle.OwnedWorkerSupervisor(
                process=process, directory=tmp_path, binding=binding,
                expected_image=lifecycle.expected_worker_image(executable),
            )
            deadline = time.monotonic() + 7
            while time.monotonic() < deadline:
                owner.poll_handshake()
                if (tmp_path / "capture-ready.tmp").exists():
                    break
                try:
                    process.communicate(input=payload if first else None, timeout=0.02)
                    first = False
                    if mode == "normal":
                        break
                except subprocess.TimeoutExpired:
                    first = False
            assert owner.handle is not None, "worker did not complete the private handshake"
            assert (tmp_path / "capture-ready.tmp").exists()
            if mode == "linger":
                # The launcher is not evidence of the worker's exit. Keep the real
                # attested handle while exercising the legacy Popen stop topology.
                _stop(process)
                owner.confirm_exit(terminate=True)
            else:
                process.communicate(input=payload if first else None, timeout=3)
                owner.confirm_exit()
            assert owner.exit_confirmed
            assert owner.api.exited(owner.handle)
            # One attempt only, after the kernel has signalled the owned worker.
            (tmp_path / "capture-synthetic.wav").unlink()
        finally:
            if owner is not None:
                if owner.handle is not None and not owner.exit_confirmed:
                    owner.confirm_exit(terminate=True)
                owner.close()
            if process is not None:
                _stop(process)
    if mode == "normal":
        assert json.loads(status_path.read_bytes()) == {"status": "completed"}
    assert not (tmp_path / "capture-synthetic.wav").exists()
