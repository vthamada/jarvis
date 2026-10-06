"""Explicit private SIWC storage: Windows DPAPI, POSIX owner-only files.

No default path, environment credential import, plaintext Windows fallback or
automatic initialization. This is trusted-host storage, not an adversarial
descriptor sandbox or an authentication/authorization registry for JARVIS.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import stat
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from threading import Lock, get_ident

from inference_service.siwc_contracts import SiwcCredentials, SiwcError, valid_host_id

_MAX_BYTES = 262_144
_WINDOWS_MAGIC = b"jarvis-siwc-dpapi-v1\n"
_POSIX_MAGIC = b"jarvis-siwc-private-v1\n"


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SiwcError("siwc_storage_invalid")
        result[key] = value
    return result


def _nonfinite(value):
    raise SiwcError("siwc_storage_invalid")


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    if os.name != "nt":
        raise SiwcError("siwc_storage_protection_unavailable")

    class Blob(ctypes.Structure):
        _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source, output = Blob(len(data), buffer), Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    routine = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    routine.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    routine.restype = ctypes.c_int
    # Current-user protection, no UI and no machine-wide protection flag.
    if not routine(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise SiwcError("siwc_storage_protection_failed")
    try:
        if not 1 <= output.size <= _MAX_BYTES:
            raise SiwcError("siwc_storage_invalid")
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(ctypes.cast(output.data, ctypes.c_void_p))


class SiwcCredentialStore:
    def __init__(self, directory: Path, *, authorized: bool = False):
        if type(authorized) is not bool or not isinstance(directory, Path):
            raise SiwcError("siwc_storage_input_invalid")
        self.directory = directory
        self.authorized = authorized
        self._mutex = Lock()
        self._lock_owner = None

    def __repr__(self):
        return "SiwcCredentialStore(explicit_private_storage=True)"

    def _directory(self, *, create: bool = False):
        if not self.authorized:
            raise SiwcError("siwc_storage_not_authorized")
        path = self.directory
        if (not path.is_absolute() or path == Path(path.anchor) or ".." in path.parts
                or str(path).startswith(("\\\\", "//"))
                or any(":" in part for part in path.parts[1:])
                or any("onedrive" in part.casefold() for part in path.parts)):
            raise SiwcError("siwc_storage_path_refused")
        try:
            for component in reversed(path.parents):
                info = component.lstat()
                if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                        or getattr(info, "st_file_attributes", 0) & 0x400):
                    raise SiwcError("siwc_storage_path_refused")
                if (component / ".git").exists():
                    raise SiwcError("siwc_storage_path_refused")
            if not path.exists():
                if not create:
                    raise SiwcError("siwc_storage_uninitialized")
                try:
                    path.mkdir(mode=0o700)
                except FileExistsError:
                    pass
            info = path.lstat()
            if (path / ".git").exists():
                raise SiwcError("siwc_storage_path_refused")
            if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400):
                raise SiwcError("siwc_storage_path_refused")
            if os.name == "posix" and (info.st_uid != os.geteuid()
                                       or stat.S_IMODE(info.st_mode) & 0o077):
                raise SiwcError("siwc_storage_permissions_refused")
        except OSError:
            raise SiwcError("siwc_storage_unavailable") from None

    def _path(self, name: str, *, missing: bool = False) -> Path:
        self._directory()
        path = self.directory / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            if missing:
                return path
            raise SiwcError("siwc_storage_record_missing") from None
        except OSError:
            raise SiwcError("siwc_storage_unavailable") from None
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & 0x400
                or not 1 <= info.st_size <= _MAX_BYTES):
            raise SiwcError("siwc_storage_path_refused")
        if os.name == "posix" and (info.st_uid != os.geteuid()
                                   or stat.S_IMODE(info.st_mode) != 0o600):
            raise SiwcError("siwc_storage_permissions_refused")
        return path

    def initialize(self) -> str:
        """Create only this explicit directory, lock and stable host record."""
        self._directory(create=True)
        # Do not initialize an unrelated populated directory as an auth store.
        try:
            if not (self.directory / "host.sealed").exists() and any(
                child.name != ".session.lock" for child in self.directory.iterdir()
            ):
                raise SiwcError("siwc_storage_path_refused")
        except OSError:
            raise SiwcError("siwc_storage_unavailable") from None
        lock_path = self._path(".session.lock", missing=True)
        if not lock_path.exists():
            try:
                fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    os.write(fd, b"0")
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except FileExistsError:
                pass
            except OSError:
                raise SiwcError("siwc_storage_unavailable") from None
        with self.locked():
            if self._path("host.sealed", missing=True).exists():
                return self._host()
            host = "urn:uuid:" + str(uuid.uuid4())
            self._write("host.sealed", {"schema_version": "jarvis-siwc-host-v1", "host_id": host})
            return host

    @contextmanager
    def locked(self):
        """Cross-process nonblocking OS lock; process death releases it.

        Keep this context across load -> refresh -> persist to serialize token
        rotation. No stale lock-file removal and no automatic retry.
        """
        path = self._path(".session.lock")
        fd, held = None, False
        if not self._mutex.acquire(blocking=False):
            raise SiwcError("siwc_storage_busy")
        try:
            fd = os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            elif os.name == "posix":
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                raise SiwcError("siwc_storage_protection_unavailable")
            held = True
            self._lock_owner = get_ident()
            yield self
        except OSError:
            raise SiwcError("siwc_storage_busy") from None
        finally:
            self._lock_owner = None
            if fd is not None:
                if held:
                    try:
                        if os.name == "nt":
                            os.lseek(fd, 0, os.SEEK_SET)
                            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
                try:
                    os.close(fd)
                except OSError:
                    raise SiwcError("siwc_storage_unavailable") from None
                finally:
                    self._mutex.release()
            else:
                self._mutex.release()

    def _read(self, name: str) -> dict:
        path = self._path(name)
        try:
            with path.open("rb") as source:
                data = source.read(_MAX_BYTES + 1)
            if not 1 <= len(data) <= _MAX_BYTES:
                raise SiwcError("siwc_storage_invalid")
            if os.name == "nt" and data.startswith(_WINDOWS_MAGIC):
                data = _dpapi(data[len(_WINDOWS_MAGIC):], decrypt=True)
            elif os.name == "posix" and data.startswith(_POSIX_MAGIC):
                data = data[len(_POSIX_MAGIC):]
            else:
                raise SiwcError("siwc_storage_protection_refused")
            value = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_object,
                               parse_constant=_nonfinite)
            if type(value) is not dict:
                raise SiwcError("siwc_storage_invalid")
            return value
        except SiwcError:
            raise
        except Exception:
            raise SiwcError("siwc_storage_invalid") from None

    def _write(self, name: str, value: dict):
        target = self._path(name, missing=True)
        stage = self.directory / (".stage-" + uuid.uuid4().hex)
        fd = None
        created_stage = False
        try:
            raw = json.dumps(
                value, ensure_ascii=True, allow_nan=False, sort_keys=True,
            ).encode("ascii")
            if not 1 <= len(raw) <= 131_072:
                raise SiwcError("siwc_storage_invalid")
            if os.name == "nt":
                encoded = _WINDOWS_MAGIC + _dpapi(raw, decrypt=False)
            elif os.name == "posix":
                encoded = _POSIX_MAGIC + raw
            else:
                raise SiwcError("siwc_storage_protection_unavailable")
            fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created_stage = True
            with os.fdopen(fd, "wb") as output:
                fd = None
                output.write(encoded)
                output.flush()
                os.fsync(output.fileno())
            self._path(name, missing=True)
            os.replace(stage, target)
            if os.name == "posix":
                directory_fd = os.open(self.directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except SiwcError:
            raise
        except Exception:
            raise SiwcError("siwc_storage_write_failed") from None
        finally:
            if fd is not None:
                os.close(fd)
            try:
                if created_stage:
                    stage.unlink(missing_ok=True)
            except OSError:
                pass

    def _host(self) -> str:
        value = self._read("host.sealed")
        if (set(value) != {"schema_version", "host_id"}
                or value["schema_version"] != "jarvis-siwc-host-v1"
                or not valid_host_id(value["host_id"])):
            raise SiwcError("siwc_storage_invalid")
        return value["host_id"]

    def host_id(self) -> str:
        with self.locked():
            return self._host()

    @staticmethod
    def _name(client_id: str, subject: str) -> str:
        from inference_service.siwc_contracts import VerifiedIdentity

        VerifiedIdentity(client_id, subject)
        digest = hashlib.sha256(json.dumps([client_id, subject]).encode()).hexdigest()
        return "account-" + digest + ".sealed"

    def save_locked(self, credentials: SiwcCredentials):
        """Trusted caller must hold locked() across the full token replacement."""
        if self._lock_owner != get_ident():
            raise SiwcError("siwc_storage_lock_required")
        if type(credentials) is not SiwcCredentials or credentials.host_id != self._host():
            raise SiwcError("siwc_storage_binding_mismatch")
        self._write(self._name(credentials.client_id, credentials.subject), {
            "schema_version": "jarvis-siwc-credentials-v1", **asdict(credentials),
        })

    def load_locked(self, *, client_id: str, subject: str) -> SiwcCredentials:
        if self._lock_owner != get_ident():
            raise SiwcError("siwc_storage_lock_required")
        value = self._read(self._name(client_id, subject))
        if value.pop("schema_version", None) != "jarvis-siwc-credentials-v1":
            raise SiwcError("siwc_storage_invalid")
        try:
            if type(value.get("scopes")) is not list:
                raise SiwcError("siwc_storage_invalid")
            value["scopes"] = tuple(value["scopes"])
            credentials = SiwcCredentials(**value)
        except Exception:
            raise SiwcError("siwc_storage_invalid") from None
        if (credentials.client_id != client_id or credentials.subject != subject
                or credentials.host_id != self._host()):
            raise SiwcError("siwc_storage_binding_mismatch")
        return credentials

    def save(self, credentials: SiwcCredentials):
        with self.locked():
            self.save_locked(credentials)

    def load(self, *, client_id: str, subject: str) -> SiwcCredentials:
        with self.locked():
            return self.load_locked(client_id=client_id, subject=subject)

    @classmethod
    def profile_ref(cls, credentials: SiwcCredentials) -> str:
        if type(credentials) is not SiwcCredentials:
            raise SiwcError("siwc_storage_input_invalid")
        return "profile-" + cls._name(credentials.client_id, credentials.subject)[8:-7]

    def load_profile(self, profile_ref: str) -> SiwcCredentials:
        if (type(profile_ref) is not str
                or re.fullmatch(r"profile-[0-9a-f]{64}", profile_ref) is None):
            raise SiwcError("siwc_storage_input_invalid")
        with self.locked():
            value = self._read("account-" + profile_ref[8:] + ".sealed")
            client, subject = value.get("client_id"), value.get("subject")
            # Validate the content-to-filename binding before exposing anything.
            if self._name(client, subject) != "account-" + profile_ref[8:] + ".sealed":
                raise SiwcError("siwc_storage_binding_mismatch")
            return self.load_locked(client_id=client, subject=subject)

    def profiles(self) -> tuple[str, ...]:
        """Opaque references only; no account identifiers, email or credentials."""
        with self.locked():
            try:
                names = []
                for index, child in enumerate(self.directory.iterdir()):
                    if index >= 256:
                        raise SiwcError("siwc_storage_limit_exceeded")
                    if re.fullmatch(r"account-[0-9a-f]{64}\.sealed", child.name):
                        names.append(child.name)
                if len(names) > 32:
                    raise SiwcError("siwc_storage_limit_exceeded")
                refs = []
                for name in sorted(names):
                    value = self._read(name)
                    client, subject = value.get("client_id"), value.get("subject")
                    if self._name(client, subject) != name:
                        raise SiwcError("siwc_storage_binding_mismatch")
                    credentials = self.load_locked(client_id=client, subject=subject)
                    refs.append(self.profile_ref(credentials))
                return tuple(refs)
            except OSError:
                raise SiwcError("siwc_storage_unavailable") from None
