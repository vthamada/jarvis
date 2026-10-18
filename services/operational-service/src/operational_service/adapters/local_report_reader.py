"""Read host-selected reports as untrusted data, never as instructions or grants.

Construction is entirely lexical: no stat, content read, or content hash is made
before Core authorizes execution. The first successful read pins the observed
file; this is NOT advance content selection or consent. Later reads refuse drift.
Cancellation/deadlines are cooperative checks around a bounded OS read, not an
OS-level I/O watchdog. This adapter itself does not authorize its caller.
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from threading import Event, Lock
from types import MappingProxyType
from typing import Mapping

from operational_service.adapters.local_text_file import (
    LocalTextFilePreflightAdapter,
    _NodeObservation,
)

_RESOURCE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}", re.ASCII)
_ERROR_CODES = frozenset({
    "invalid_configuration", "invalid_resource_id", "unknown_resource", "cancelled",
    "expired", "report_unavailable", "report_rejected", "report_drift", "report_too_large",
    "report_encoding_invalid",
})


class LocalReportReadError(ValueError):
    """A content-free refusal; paths, report text and OS exceptions stay private."""

    def __init__(self, code: str) -> None:
        self.code = code if code in _ERROR_CODES else "report_rejected"
        super().__init__(self.code)


class _ReportReadBackend(LocalTextFilePreflightAdapter):
    """Reuse only the existing read-only POSIX/Windows handle implementation.

    No preflight, writer, authority verifier, or shared contract is invoked.
    The inherited handle reader needs only this byte bound and its pure helpers.
    """

    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes


@dataclass(frozen=True)
class _PinnedReport:
    file_state: _NodeObservation
    directory_identities: tuple[tuple[int, int, int, int], ...]
    content_sha256: str


def _directory_identities(
    observations: tuple[_NodeObservation, ...],
) -> tuple[tuple[int, int, int, int], ...]:
    # Sibling edits can change ancestor timestamps without rebinding the file.
    # Check every directory identity, mode and reparse attributes, not its mtime.
    # The target file itself still uses the complete before/handle/after state.
    return tuple((item.device, item.inode, item.mode, item.file_attributes)
                 for item in observations)


class LocalReportReader:
    """A copied immutable allowlist, not a general filesystem capability."""

    def __init__(self, resources: Mapping[str, Path], *, max_bytes: int = 8192) -> None:
        if (isinstance(max_bytes, bool) or not isinstance(max_bytes, int)
                or not 1 <= max_bytes <= 8192 or not isinstance(resources, Mapping)
                or not resources):
            raise LocalReportReadError("invalid_configuration")
        configured: dict[str, Path] = {}
        for resource_id, path in resources.items():
            if (not isinstance(resource_id, str) or _RESOURCE_ID.fullmatch(resource_id) is None
                    or not isinstance(path, Path) or not path.is_absolute()):
                raise LocalReportReadError("invalid_configuration")
            valid = True
            try:
                LocalTextFilePreflightAdapter._validate_configured_root_lexically(str(path))
            except (TypeError, ValueError):
                valid = False
            # Reject Windows alternate data streams and nonportable path aliases.
            if not valid or any(":" in part for part in path.parts[1:]):
                raise LocalReportReadError("invalid_configuration")
            configured[resource_id] = path
        self._resources = MappingProxyType(configured)
        self._resource_ids = tuple(sorted(configured))
        self._max_bytes = max_bytes
        self._configuration_fingerprint = sha256(json.dumps(
            {"resources": [(key, str(configured[key])) for key in self._resource_ids],
             "max_bytes": max_bytes},
            ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        ).encode("ascii")).hexdigest()
        self._backend = _ReportReadBackend(max_bytes)
        self._pins: dict[str, _PinnedReport] = {}
        self._lock = Lock()

    @property
    def resource_ids(self) -> tuple[str, ...]:
        return self._resource_ids

    @property
    def configuration_fingerprint(self) -> str:
        return self._configuration_fingerprint

    @staticmethod
    def _check_control(cancellation: Event | None, deadline_monotonic: float | None) -> None:
        if cancellation is not None:
            if not isinstance(cancellation, Event) or cancellation.is_set() is not False:
                raise LocalReportReadError("cancelled")
        if deadline_monotonic is not None:
            if (isinstance(deadline_monotonic, bool)
                    or not isinstance(deadline_monotonic, (int, float))
                    or not math.isfinite(deadline_monotonic)
                    or time.monotonic() >= deadline_monotonic):
                raise LocalReportReadError("expired")

    def read(
        self,
        resource_id: str,
        *,
        cancellation: Event | None = None,
        deadline_monotonic: float | None = None,
    ) -> str:
        """Return a whole stable UTF-8 report or refuse; never return partial data."""
        if not isinstance(resource_id, str) or _RESOURCE_ID.fullmatch(resource_id) is None:
            raise LocalReportReadError("invalid_resource_id")
        if resource_id not in self._resources:
            raise LocalReportReadError("unknown_resource")
        try:
            self._check_control(cancellation, deadline_monotonic)
            with self._lock:
                return self._read(resource_id, cancellation, deadline_monotonic)
        except LocalReportReadError as exc:
            code = exc.code
        except UnicodeError:
            code = "report_encoding_invalid"
        except OSError:
            code = "report_unavailable"
        except ValueError as exc:
            reason = str(exc)
            code = ("report_too_large" if "too_large" in reason else
                    "report_drift" if "changed" in reason else "report_rejected")
        except Exception:
            code = "report_rejected"
        # Raise outside the handler so even __context__ does not expose OS paths.
        raise LocalReportReadError(code) from None

    def _read(
        self, resource_id: str, cancellation: Event | None, deadline_monotonic: float | None,
    ) -> str:
        self._check_control(cancellation, deadline_monotonic)
        path = self._resources[resource_id]
        root = Path(path.anchor)
        parent_segments = tuple(path.parts[1:-1])
        before_directories = self._backend._observe_directories(root, parent_segments)
        initial = self._backend._lstat(path, "local_report_missing")
        self._backend._require_regular_single_link_target(initial)
        if initial.st_size > self._max_bytes:
            raise LocalReportReadError("report_too_large")
        initial_state = _NodeObservation.from_stat("target", initial)
        pinned = self._pins.get(resource_id)
        if pinned is not None and (
            initial_state != pinned.file_state
            or _directory_identities(before_directories) != pinned.directory_identities
        ):
            raise LocalReportReadError("report_drift")
        self._check_control(cancellation, deadline_monotonic)
        raw, read_state = self._backend._read_stable_text(
            path, initial, root=root, parent_segments=parent_segments, target_name=path.name,
        )
        self._check_control(cancellation, deadline_monotonic)
        after_directories = self._backend._observe_directories(root, parent_segments)
        final = self._backend._lstat(path, "local_report_missing")
        self._backend._require_regular_single_link_target(final)
        if (_directory_identities(before_directories) != _directory_identities(after_directories)
                or initial_state != read_state
                or initial_state != _NodeObservation.from_stat("target", final)
                or len(raw) != initial.st_size):
            raise LocalReportReadError("report_drift")
        text = raw.decode("utf-8", errors="strict")
        current = _PinnedReport(
            file_state=initial_state,
            directory_identities=_directory_identities(after_directories),
            content_sha256=sha256(raw).hexdigest(),
        )
        if pinned is not None and current != pinned:
            raise LocalReportReadError("report_drift")
        self._check_control(cancellation, deadline_monotonic)
        self._pins[resource_id] = current
        return text
