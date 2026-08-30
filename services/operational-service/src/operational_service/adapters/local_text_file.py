"""Fail-closed, side-effect-free preflight for configured local text roots."""

from __future__ import annotations

import difflib
import json
import ntpath
import os
import re
import stat
import unicodedata
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

from shared.adapter_permissions import (
    LOCAL_TEXT_FILE_DESCRIPTOR,
    require_valid_adapter_action_request,
)
from shared.contracts import (
    LocalTextFilePreflightContract,
    LocalTextFilePreflightRequestContract,
    LocalTextFileRollbackPlanContract,
)
from shared.local_text_resource_ref import require_valid_local_text_relative_path

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_ROOT_ALIAS_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,63}")
_WINDOWS_DRIVE_PATTERN = re.compile(r"[A-Za-z]:")
_WINDOWS_FORBIDDEN_CHARS = frozenset('<>:"\\|?*')
_WINDOWS_DEVICE_NAMES = frozenset(
    {"con", "prn", "aux", "nul", "clock$", "conin$", "conout$"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
    | {f"com{index}" for index in "¹²³"}
    | {f"lpt{index}" for index in "¹²³"}
)
_AUTHORITY_FIELDS = (
    "execution_allowed",
    "tool_dispatch_allowed",
    "runtime_activation_allowed",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
)
_EMPTY_SHA256 = sha256(b"").hexdigest()
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
LOCAL_TEXT_PREFLIGHT_POLICY_VERSION = "1.0.0"
LOCAL_TEXT_DIFF_ALGORITHM = "unified_diff"
LOCAL_TEXT_DIFF_ALGORITHM_VERSION = "1.0.0"
LOCAL_TEXT_PREFLIGHT_MAX_TTL_SECONDS = 300
LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM = "lstat_identity_chain"
LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM_VERSION = "1.0.0"
LOCAL_TEXT_ADAPTER_BACKEND_VERSION = "1.0.0"


def _digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return _digest_bytes(payload.encode("utf-8"))


def build_local_text_file_rollback_fingerprint(
    plan: LocalTextFileRollbackPlanContract,
) -> str:
    """Recompute the canonical content-free rollback binding."""

    return _canonical_digest(
        {key: value for key, value in asdict(plan).items() if key != "rollback_fingerprint"}
    )


def validate_local_text_file_rollback_fingerprint(
    plan: LocalTextFileRollbackPlanContract,
) -> bool:
    return bool(_SHA256_PATTERN.fullmatch(plan.rollback_fingerprint)) and compare_digest(
        plan.rollback_fingerprint,
        build_local_text_file_rollback_fingerprint(plan),
    )


def build_local_text_file_preflight_fingerprint(
    preflight: LocalTextFilePreflightContract,
) -> str:
    """Recompute the canonical path-free preflight binding."""

    return _canonical_digest(
        {
            key: value
            for key, value in asdict(preflight).items()
            if key not in {"preflight_fingerprint", "unified_diff"}
        }
    )


def validate_local_text_file_preflight_fingerprint(
    preflight: LocalTextFilePreflightContract,
) -> bool:
    return bool(_SHA256_PATTERN.fullmatch(preflight.preflight_fingerprint)) and compare_digest(
        preflight.preflight_fingerprint,
        build_local_text_file_preflight_fingerprint(preflight),
    )


def require_valid_local_text_file_preflight(
    preflight: LocalTextFilePreflightContract,
    *,
    now: datetime | None = None,
    allowed_extensions: tuple[str, ...] = (".md", ".txt"),
) -> None:
    """Validate integrity, authority, expiry, and exact internal bindings."""

    for value in (
        preflight.grant_fingerprint,
        preflight.action_fingerprint,
        preflight.intent_fingerprint,
        preflight.descriptor_fingerprint,
        preflight.registry_fingerprint,
        preflight.before_content_sha256,
        preflight.desired_content_sha256,
        preflight.diff_sha256,
        preflight.root_config_fingerprint,
        preflight.filesystem_snapshot_fingerprint,
    ):
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("local_text_preflight_sha256_invalid")
    require_valid_adapter_action_request(
        preflight.adapter_request,
        descriptor=LOCAL_TEXT_FILE_DESCRIPTOR,
    )
    _validate_local_text_relative_path(
        preflight.relative_path,
        allowed_extensions=allowed_extensions,
    )
    if _ROOT_ALIAS_PATTERN.fullmatch(preflight.root_alias) is None:
        raise ValueError("local_text_preflight_root_alias_invalid")
    if preflight.descriptor_fingerprint != LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint:
        raise ValueError("local_text_preflight_descriptor_drift")
    if (
        preflight.operation != preflight.adapter_request.operation
        or preflight.resource_ref != preflight.adapter_request.resource_ref
        or preflight.resource_ref != f"text:{preflight.root_alias}/{preflight.relative_path}"
        or not preflight.relative_path
        or preflight.relative_path.startswith("/")
        or "\\" in preflight.relative_path
    ):
        raise ValueError("local_text_preflight_resource_binding_invalid")
    if preflight.operation == "create_text":
        if (
            preflight.before_exists
            or preflight.expected_current_sha256 is not None
            or preflight.before_content_sha256 != _EMPTY_SHA256
            or preflight.before_size_bytes != 0
        ):
            raise ValueError("local_text_preflight_create_state_invalid")
    elif preflight.operation == "replace_text":
        if (
            not preflight.before_exists
            or preflight.expected_current_sha256 != preflight.before_content_sha256
        ):
            raise ValueError("local_text_preflight_replace_state_invalid")
    else:
        raise ValueError("local_text_preflight_operation_invalid")
    expected_change_status = (
        "no_change"
        if preflight.before_exists
        and preflight.before_content_sha256 == preflight.desired_content_sha256
        else "change"
    )
    if preflight.change_status != expected_change_status:
        raise ValueError("local_text_preflight_change_status_invalid")
    if _digest_bytes(preflight.unified_diff.encode("utf-8")) != preflight.diff_sha256:
        raise ValueError("local_text_preflight_diff_hash_invalid")
    if (
        preflight.preflight_policy_version != LOCAL_TEXT_PREFLIGHT_POLICY_VERSION
        or preflight.diff_algorithm != LOCAL_TEXT_DIFF_ALGORITHM
        or preflight.diff_algorithm_version != LOCAL_TEXT_DIFF_ALGORITHM_VERSION
        or preflight.filesystem_snapshot_algorithm != LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM
        or preflight.filesystem_snapshot_algorithm_version
        != LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM_VERSION
        or preflight.adapter_backend_version != LOCAL_TEXT_ADAPTER_BACKEND_VERSION
    ):
        raise ValueError("local_text_preflight_algorithm_or_policy_invalid")
    prepared = LocalTextFilePreflightAdapter._parse_canonical_time(
        preflight.prepared_at,
        "local_text_prepared_at_invalid",
    )
    expires = LocalTextFilePreflightAdapter._parse_canonical_time(
        preflight.expires_at,
        "local_text_expires_at_invalid",
    )
    authorization_expires = LocalTextFilePreflightAdapter._parse_canonical_time(
        preflight.authorization_expires_at,
        "local_text_authorization_expires_at_invalid",
    )
    ttl = (expires - prepared).total_seconds()
    if ttl <= 0 or ttl > LOCAL_TEXT_PREFLIGHT_MAX_TTL_SECONDS or expires > authorization_expires:
        raise ValueError("local_text_preflight_window_invalid")
    if now is not None:
        if now.tzinfo is None:
            raise ValueError("local_text_now_not_timezone_aware")
        current = now.astimezone(timezone.utc)
        if current < prepared or current >= expires or current >= authorization_expires:
            raise ValueError("local_text_preflight_expired_or_inactive")
    rollback = preflight.rollback_plan
    expected_rollback_strategy = (
        "delete_created_file"
        if preflight.operation == "create_text"
        else "restore_previous_content"
    )
    if (
        rollback.strategy != expected_rollback_strategy
        or rollback.operation != preflight.operation
        or rollback.resource_ref != preflight.resource_ref
        or rollback.root_config_fingerprint != preflight.root_config_fingerprint
        or rollback.before_content_sha256 != preflight.before_content_sha256
        or rollback.desired_content_sha256 != preflight.desired_content_sha256
        or rollback.preflight_policy_version != preflight.preflight_policy_version
        or rollback.precondition_content_sha256 != preflight.desired_content_sha256
        or rollback.restore_content_sha256
        != (preflight.before_content_sha256 if preflight.before_exists else None)
        or not rollback.manual_execution_required
        or not rollback.read_only
        or not rollback.immutable
        or not validate_local_text_file_rollback_fingerprint(rollback)
    ):
        raise ValueError("local_text_preflight_rollback_binding_invalid")
    if (
        not preflight.read_only
        or not preflight.immutable
        or preflight.encoding != "utf-8"
        or not preflight.execution_grant_required
        or preflight.preflight_grant_reusable_for_execution
        or preflight.persistence_allowed
        or preflight.telemetry_allowed
        or not preflight.contains_sensitive_diff
        or any(getattr(preflight, field) for field in _AUTHORITY_FIELDS)
        or any(getattr(rollback, field) for field in _AUTHORITY_FIELDS)
    ):
        raise ValueError("local_text_preflight_authority_or_sensitivity_invalid")
    if not validate_local_text_file_preflight_fingerprint(preflight):
        raise ValueError("local_text_preflight_fingerprint_invalid")


def validate_local_text_file_preflight(
    preflight: LocalTextFilePreflightContract,
    *,
    now: datetime | None = None,
    allowed_extensions: tuple[str, ...] = (".md", ".txt"),
) -> list[str]:
    try:
        require_valid_local_text_file_preflight(
            preflight,
            now=now,
            allowed_extensions=allowed_extensions,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []


def _is_reparse_or_link(observation: os.stat_result) -> bool:
    attributes = int(getattr(observation, "st_file_attributes", 0))
    return stat.S_ISLNK(observation.st_mode) or bool(attributes & _REPARSE_POINT)


def _require_windows_safe_directory_attributes(attributes: int) -> None:
    if not attributes & 0x00000010 or attributes & 0x00000400:
        raise ValueError("local_text_directory_not_safe")


def _require_windows_contained_path(observed: str, expected: str, error: str) -> None:
    if observed != expected:
        raise ValueError(error)


def _read_windows_handle(read_file: object, handle: int, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining:
        requested = min(65_536, remaining)
        buffer = ctypes.create_string_buffer(requested)
        read_count = wintypes.DWORD()
        if not read_file(  # type: ignore[operator]
            handle,
            buffer,
            requested,
            ctypes.byref(read_count),
            None,
        ):
            raise ValueError("local_text_target_read_failed")
        if read_count.value == 0:
            break
        chunks.append(buffer.raw[: read_count.value])
        remaining -= read_count.value
    content = b"".join(chunks)
    if len(content) > max_bytes:
        raise ValueError("local_text_current_content_too_large")
    return content


def _validate_local_text_relative_path(
    relative_path: str,
    *,
    allowed_extensions: tuple[str, ...],
) -> None:
    require_valid_local_text_relative_path(
        relative_path,
        allowed_extensions=allowed_extensions,
    )


@dataclass(frozen=True)
class _NodeObservation:
    label: str
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int
    links: int
    file_attributes: int

    @classmethod
    def from_stat(cls, label: str, value: os.stat_result) -> _NodeObservation:
        return cls(
            label=label,
            device=int(value.st_dev),
            inode=int(value.st_ino),
            mode=int(value.st_mode),
            size=int(value.st_size),
            modified_ns=int(value.st_mtime_ns),
            changed_ns=int(value.st_ctime_ns),
            links=int(value.st_nlink),
            file_attributes=int(getattr(value, "st_file_attributes", 0)),
        )


class LocalTextFilePreflightAdapter:
    """Inspect one exact local text action without creating or modifying anything."""

    def __init__(
        self,
        *,
        roots: Mapping[str, str | os.PathLike[str]],
        verified_context_verifier: Callable[
            [LocalTextFilePreflightRequestContract, datetime], bool
        ],
        allowed_extensions: tuple[str, ...] = (".md", ".txt"),
        max_bytes: int = 1_048_576,
    ) -> None:
        if not roots:
            raise ValueError("local_text_roots_empty")
        configured_roots: dict[str, Path] = {}
        for alias, configured_path in roots.items():
            if _ROOT_ALIAS_PATTERN.fullmatch(alias) is None:
                raise ValueError("local_text_root_alias_invalid")
            raw_path = os.fspath(configured_path)
            self._validate_configured_root_lexically(raw_path)
            root = Path(raw_path)
            if not root.is_absolute():
                raise ValueError("local_text_root_not_absolute")
            configured_roots[alias] = root
        normalized_extensions = tuple(
            sorted({self._normalize_extension(value) for value in allowed_extensions})
        )
        if not normalized_extensions:
            raise ValueError("local_text_extension_allowlist_empty")
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ValueError("local_text_max_bytes_invalid")
        if not callable(verified_context_verifier):
            raise ValueError("local_text_verified_context_verifier_required")
        self._roots = MappingProxyType(configured_roots)
        self._allowed_extensions = normalized_extensions
        self._max_bytes = max_bytes
        self._verified_context_verifier = verified_context_verifier

    @staticmethod
    def _validate_configured_root_lexically(raw_path: str) -> None:
        if (
            not isinstance(raw_path, str)
            or not raw_path
            or "\x00" in raw_path
            or "%" in raw_path
            or raw_path != raw_path.strip()
            or not unicodedata.is_normalized("NFC", raw_path)
            or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in raw_path)
        ):
            raise ValueError("local_text_root_path_invalid")
        normalized_slashes = raw_path.replace("\\", "/")
        lowered = normalized_slashes.casefold()
        if (
            normalized_slashes.startswith("//")
            or lowered.startswith("//?/")
            or lowered.startswith("//./")
        ):
            raise ValueError("local_text_root_nonlocal_path_forbidden")
        windows_drive, windows_tail = ntpath.splitdrive(raw_path)
        if windows_drive:
            if not re.fullmatch(r"[A-Za-z]:", windows_drive) or not windows_tail.startswith(
                ("\\", "/")
            ):
                raise ValueError("local_text_root_drive_relative_forbidden")
            if windows_tail.replace("\\", "/") == "/":
                raise ValueError("local_text_filesystem_root_forbidden")
        elif _WINDOWS_DRIVE_PATTERN.match(raw_path):
            raise ValueError("local_text_root_drive_relative_forbidden")
        if raw_path.replace("\\", "/") == "/":
            raise ValueError("local_text_filesystem_root_forbidden")
        path_tail = windows_tail.replace("\\", "/") if windows_drive else normalized_slashes
        if "//" in path_tail:
            raise ValueError("local_text_root_repeated_separator_forbidden")
        root_segments = path_tail.split("/")
        for segment in root_segments:
            if not segment:
                continue
            if (
                segment in {".", ".."}
                or segment != segment.rstrip(". ")
                or segment.split(".", 1)[0].casefold() in _WINDOWS_DEVICE_NAMES
            ):
                raise ValueError("local_text_root_path_invalid")

    @staticmethod
    def _normalize_extension(value: str) -> str:
        if (
            not isinstance(value, str)
            or not value.startswith(".")
            or len(value) < 2
            or value != value.strip()
            or value != value.casefold()
            or any(character in _WINDOWS_FORBIDDEN_CHARS for character in value)
            or "/" in value
        ):
            raise ValueError("local_text_extension_invalid")
        return value

    @staticmethod
    def _require_opaque_binding(value: str, error: str) -> None:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 512
            or value != value.strip()
            or not unicodedata.is_normalized("NFC", value)
            or "\\" in value
            or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value)
        ):
            raise ValueError(error)

    @staticmethod
    def _require_sha256(value: str, error: str) -> None:
        if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(error)

    def _validate_request_bindings(self, request: LocalTextFilePreflightRequestContract) -> None:
        self._require_opaque_binding(request.grant_id, "local_text_grant_id_invalid")
        self._require_opaque_binding(request.subject_ref, "local_text_subject_ref_invalid")
        for value, error in (
            (request.grant_fingerprint, "local_text_grant_fingerprint_invalid"),
            (request.action_fingerprint, "local_text_action_fingerprint_invalid"),
            (request.intent_fingerprint, "local_text_intent_fingerprint_invalid"),
            (request.descriptor_fingerprint, "local_text_descriptor_fingerprint_invalid"),
            (request.registry_fingerprint, "local_text_registry_fingerprint_invalid"),
        ):
            self._require_sha256(value, error)
        self._require_sha256(
            request.expected_root_config_fingerprint,
            "local_text_expected_root_config_fingerprint_invalid",
        )
        if request.descriptor_fingerprint != LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint:
            raise ValueError("local_text_descriptor_fingerprint_drift")
        if (
            request.persistence_allowed
            or request.telemetry_allowed
            or not request.contains_sensitive_content
        ):
            raise ValueError("local_text_request_sensitivity_flags_invalid")
        if request.preflight_policy_version != LOCAL_TEXT_PREFLIGHT_POLICY_VERSION:
            raise ValueError("local_text_preflight_policy_version_invalid")
        if (
            request.diff_algorithm != LOCAL_TEXT_DIFF_ALGORITHM
            or request.diff_algorithm_version != LOCAL_TEXT_DIFF_ALGORITHM_VERSION
        ):
            raise ValueError("local_text_diff_algorithm_invalid")
        _, expires = self._validate_window(request.prepared_at, request.expires_at)
        authorization_expires = self._parse_canonical_time(
            request.authorization_expires_at,
            "local_text_authorization_expires_at_invalid",
        )
        if expires > authorization_expires:
            raise ValueError("local_text_preflight_exceeds_authorization_expiry")
        require_valid_adapter_action_request(
            request.adapter_request,
            descriptor=LOCAL_TEXT_FILE_DESCRIPTOR,
        )
        operation = request.adapter_request.operation
        if operation == "create_text":
            if request.expected_current_sha256 is not None:
                raise ValueError("local_text_create_expected_hash_forbidden")
        elif operation == "replace_text":
            if request.expected_current_sha256 is None:
                raise ValueError("local_text_replace_expected_hash_required")
            self._require_sha256(
                request.expected_current_sha256,
                "local_text_expected_hash_invalid",
            )
        else:
            raise ValueError("local_text_operation_invalid")

    @staticmethod
    def _parse_canonical_time(value: str, error: str) -> datetime:
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError(error)
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(error) from None
        return parsed

    @classmethod
    def _validate_window(cls, prepared_at: str, expires_at: str) -> tuple[datetime, datetime]:
        prepared = cls._parse_canonical_time(prepared_at, "local_text_prepared_at_invalid")
        expires = cls._parse_canonical_time(expires_at, "local_text_expires_at_invalid")
        ttl_seconds = (expires - prepared).total_seconds()
        if ttl_seconds <= 0 or ttl_seconds > LOCAL_TEXT_PREFLIGHT_MAX_TTL_SECONDS:
            raise ValueError("local_text_preflight_window_invalid")
        return prepared, expires

    def _parse_resource_ref(self, resource_ref: str) -> tuple[str, str, tuple[str, ...]]:
        if not resource_ref.startswith("text:"):
            raise ValueError("local_text_resource_scheme_invalid")
        payload = resource_ref[len("text:") :]
        if "/" not in payload:
            raise ValueError("local_text_resource_ref_invalid")
        root_alias, relative_path = payload.split("/", 1)
        if _ROOT_ALIAS_PATTERN.fullmatch(root_alias) is None or root_alias not in self._roots:
            raise ValueError("local_text_root_alias_not_configured")
        self._validate_relative_path(relative_path)
        canonical_ref = f"text:{root_alias}/{relative_path}"
        if canonical_ref != resource_ref:
            raise ValueError("local_text_resource_ref_not_canonical")
        return root_alias, relative_path, tuple(relative_path.split("/"))

    def _validate_relative_path(self, relative_path: str) -> None:
        _validate_local_text_relative_path(
            relative_path,
            allowed_extensions=self._allowed_extensions,
        )

    @staticmethod
    def _lstat(path: Path, error: str) -> os.stat_result:
        try:
            return os.lstat(path)
        except OSError:
            raise ValueError(error) from None

    @staticmethod
    def _lstat_optional(path: Path) -> os.stat_result | None:
        try:
            return os.lstat(path)
        except FileNotFoundError:
            return None
        except OSError:
            raise ValueError("local_text_target_stat_failed") from None

    def _observe_directories(
        self,
        root: Path,
        parent_segments: tuple[str, ...],
    ) -> tuple[_NodeObservation, ...]:
        paths: list[tuple[str, Path]] = [("root", root)]
        current = root
        for index, segment in enumerate(parent_segments, start=1):
            current = current / segment
            paths.append((f"parent:{index}", current))
        observations: list[_NodeObservation] = []
        for label, path in paths:
            observed = self._lstat(path, "local_text_directory_missing_or_unreadable")
            if not stat.S_ISDIR(observed.st_mode) or _is_reparse_or_link(observed):
                raise ValueError("local_text_directory_not_safe")
            observations.append(_NodeObservation.from_stat(label, observed))
        return tuple(observations)

    def _root_config_fingerprint(self) -> str:
        roots: list[dict[str, object]] = []
        for alias, root in sorted(self._roots.items()):
            observed = self._lstat(root, "local_text_root_missing_or_unreadable")
            if not stat.S_ISDIR(observed.st_mode) or _is_reparse_or_link(observed):
                raise ValueError("local_text_root_not_safe")
            roots.append(
                {
                    "alias": alias,
                    "identity": {
                        "device": int(observed.st_dev),
                        "inode": int(observed.st_ino),
                        "mode": int(observed.st_mode),
                        "file_attributes": int(getattr(observed, "st_file_attributes", 0)),
                    },
                }
            )
        return _canonical_digest(
            {
                "roots": roots,
                "allowed_extensions": self._allowed_extensions,
                "max_bytes": self._max_bytes,
                "adapter_descriptor_fingerprint": (
                    LOCAL_TEXT_FILE_DESCRIPTOR.descriptor_fingerprint
                ),
                "preflight_policy_version": LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
                "diff_algorithm": LOCAL_TEXT_DIFF_ALGORITHM,
                "diff_algorithm_version": LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
                "filesystem_snapshot_algorithm": (LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM),
                "filesystem_snapshot_algorithm_version": (
                    LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM_VERSION
                ),
                "adapter_backend_version": LOCAL_TEXT_ADAPTER_BACKEND_VERSION,
            }
        )

    def root_config_fingerprint(self) -> str:
        """Return a path-free CAS fingerprint for the operator-controlled configuration."""

        return self._root_config_fingerprint()

    @staticmethod
    def _require_regular_single_link_target(observed: os.stat_result) -> None:
        if (
            not stat.S_ISREG(observed.st_mode)
            or _is_reparse_or_link(observed)
            or int(observed.st_nlink) != 1
        ):
            raise ValueError("local_text_target_not_safe_regular_file")

    def _read_stable_text(
        self,
        target: Path,
        initial: os.stat_result,
        *,
        root: Path,
        parent_segments: tuple[str, ...],
        target_name: str,
    ) -> tuple[bytes, _NodeObservation]:
        if int(initial.st_size) > self._max_bytes:
            raise ValueError("local_text_current_content_too_large")
        if os.name == "nt":
            return self._read_stable_text_windows(
                target,
                initial,
                root=root,
                parent_segments=parent_segments,
            )
        no_follow = int(getattr(os, "O_NOFOLLOW", 0))
        non_block = int(getattr(os, "O_NONBLOCK", 0))
        directory_flag = int(getattr(os, "O_DIRECTORY", 0))
        if not no_follow or not directory_flag:
            raise ValueError("local_text_replace_backend_missing_safe_open_flags")
        directory_flags = os.O_RDONLY | no_follow | non_block | directory_flag
        directory_descriptor: int | None = None
        descriptor: int | None = None
        try:
            try:
                directory_descriptor = os.open(root, directory_flags)
                root_handle = os.fstat(directory_descriptor)
                root_path = self._lstat(root, "local_text_root_missing_or_unreadable")
                if _NodeObservation.from_stat("root", root_handle) != _NodeObservation.from_stat(
                    "root", root_path
                ):
                    raise ValueError("local_text_root_changed_during_preflight")
                for segment in parent_segments:
                    next_descriptor = os.open(
                        segment,
                        directory_flags,
                        dir_fd=directory_descriptor,
                    )
                    next_observed = os.fstat(next_descriptor)
                    if not stat.S_ISDIR(next_observed.st_mode) or _is_reparse_or_link(
                        next_observed
                    ):
                        os.close(next_descriptor)
                        raise ValueError("local_text_directory_not_safe")
                    os.close(directory_descriptor)
                    directory_descriptor = next_descriptor
                descriptor = os.open(
                    target_name,
                    os.O_RDONLY | no_follow | non_block,
                    dir_fd=directory_descriptor,
                )
            except OSError:
                raise ValueError("local_text_target_open_failed") from None
            if descriptor is None:
                raise ValueError("local_text_target_open_failed")
            opened = os.fstat(descriptor)
            self._require_regular_single_link_target(opened)
            if _NodeObservation.from_stat("target", opened) != _NodeObservation.from_stat(
                "target", initial
            ):
                raise ValueError("local_text_target_changed_during_preflight")
            chunks: list[bytes] = []
            remaining = self._max_bytes + 1
            while remaining:
                chunk = os.read(descriptor, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
            if len(content) > self._max_bytes:
                raise ValueError("local_text_current_content_too_large")
            after_read = os.fstat(descriptor)
            if _NodeObservation.from_stat("target", after_read) != _NodeObservation.from_stat(
                "target", opened
            ):
                raise ValueError("local_text_target_changed_during_preflight")
            return content, _NodeObservation.from_stat("target", after_read)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if directory_descriptor is not None:
                os.close(directory_descriptor)

    def _read_stable_text_windows(
        self,
        target: Path,
        initial: os.stat_result,
        *,
        root: Path,
        parent_segments: tuple[str, ...],
    ) -> tuple[bytes, _NodeObservation]:
        class _ByHandleFileInformation(ctypes.Structure):
            _fields_ = (
                ("file_attributes", wintypes.DWORD),
                ("creation_time", wintypes.FILETIME),
                ("last_access_time", wintypes.FILETIME),
                ("last_write_time", wintypes.FILETIME),
                ("volume_serial_number", wintypes.DWORD),
                ("file_size_high", wintypes.DWORD),
                ("file_size_low", wintypes.DWORD),
                ("number_of_links", wintypes.DWORD),
                ("file_index_high", wintypes.DWORD),
                ("file_index_low", wintypes.DWORD),
            )

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        get_information = kernel32.GetFileInformationByHandle
        get_information.argtypes = (wintypes.HANDLE, ctypes.POINTER(_ByHandleFileInformation))
        get_information.restype = wintypes.BOOL
        get_final_path = kernel32.GetFinalPathNameByHandleW
        get_final_path.argtypes = (
            wintypes.HANDLE,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        )
        get_final_path.restype = wintypes.DWORD
        read_file = kernel32.ReadFile
        read_file.argtypes = (
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        )
        read_file.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL

        generic_read = 0x80000000
        file_read_attributes = 0x0080
        file_share_read = 0x00000001
        open_existing = 3
        open_reparse_point = 0x00200000
        backup_semantics = 0x02000000
        directory_attribute = 0x00000010
        reparse_attribute = 0x00000400
        invalid_handle = ctypes.c_void_p(-1).value
        handles: list[int] = []

        def open_handle(path: Path, *, directory: bool) -> int:
            flags = open_reparse_point | (backup_semantics if directory else 0)
            access = file_read_attributes if directory else generic_read
            handle = create_file(
                str(path),
                access,
                file_share_read,
                None,
                open_existing,
                flags,
                None,
            )
            if handle == invalid_handle:
                raise ValueError("local_text_target_open_failed")
            handles.append(handle)
            return handle

        def information(handle: int) -> _ByHandleFileInformation:
            value = _ByHandleFileInformation()
            if not get_information(handle, ctypes.byref(value)):
                raise ValueError("local_text_target_handle_inspection_failed")
            return value

        def identity(
            value: _ByHandleFileInformation,
        ) -> tuple[int, int, int, int, int, int, int]:
            file_index = (int(value.file_index_high) << 32) | int(value.file_index_low)
            size = (int(value.file_size_high) << 32) | int(value.file_size_low)
            return (
                int(value.volume_serial_number),
                file_index,
                int(value.number_of_links),
                int(value.file_attributes),
                size,
                int(value.last_write_time.dwHighDateTime),
                int(value.last_write_time.dwLowDateTime),
            )

        def final_path(handle: int) -> str:
            required = get_final_path(handle, None, 0, 0)
            if not required:
                raise ValueError("local_text_handle_final_path_failed")
            buffer = ctypes.create_unicode_buffer(required + 1)
            written = get_final_path(handle, buffer, len(buffer), 0)
            if not written or written >= len(buffer):
                raise ValueError("local_text_handle_final_path_failed")
            value = buffer.value.replace("/", "\\")
            if value.casefold().startswith("\\\\?\\unc\\"):
                raise ValueError("local_text_handle_nonlocal_path_forbidden")
            if value.startswith("\\\\?\\"):
                value = value[4:]
            if not re.match(r"^[A-Za-z]:\\", value):
                raise ValueError("local_text_handle_nonlocal_path_forbidden")
            return ntpath.normpath(value).casefold()

        try:
            current = root
            directory_paths = [root]
            for segment in parent_segments:
                current = current / segment
                directory_paths.append(current)
            root_final_path: str | None = None
            for index, directory_path in enumerate(directory_paths):
                directory_handle = open_handle(directory_path, directory=True)
                directory_info = information(directory_handle)
                attributes = int(directory_info.file_attributes)
                _require_windows_safe_directory_attributes(attributes)
                path_info = self._lstat(
                    directory_path,
                    "local_text_directory_missing_or_unreadable",
                )
                file_index = (int(directory_info.file_index_high) << 32) | int(
                    directory_info.file_index_low
                )
                if int(path_info.st_ino) != file_index:
                    raise ValueError("local_text_directory_changed_during_preflight")
                observed_final_path = final_path(directory_handle)
                if index == 0:
                    root_final_path = observed_final_path
                else:
                    if root_final_path is None:
                        raise ValueError("local_text_root_final_path_missing")
                    expected_directory = ntpath.normpath(
                        ntpath.join(root_final_path, *parent_segments[:index])
                    ).casefold()
                    _require_windows_contained_path(
                        observed_final_path,
                        expected_directory,
                        "local_text_directory_escaped_root",
                    )

            target_handle = open_handle(target, directory=False)
            before_info = information(target_handle)
            target_attributes = int(before_info.file_attributes)
            if (
                target_attributes & (directory_attribute | reparse_attribute)
                or int(before_info.number_of_links) != 1
            ):
                raise ValueError("local_text_target_not_safe_regular_file")
            file_index = (int(before_info.file_index_high) << 32) | int(before_info.file_index_low)
            file_size = (int(before_info.file_size_high) << 32) | int(before_info.file_size_low)
            if int(initial.st_ino) != file_index or int(initial.st_size) != file_size:
                raise ValueError("local_text_target_changed_during_preflight")
            if root_final_path is None:
                raise ValueError("local_text_root_final_path_missing")
            expected_target = ntpath.normpath(
                ntpath.join(root_final_path, *parent_segments, target.name)
            ).casefold()
            _require_windows_contained_path(
                final_path(target_handle),
                expected_target,
                "local_text_target_escaped_root",
            )
            if file_size > self._max_bytes:
                raise ValueError("local_text_current_content_too_large")

            content = _read_windows_handle(read_file, target_handle, self._max_bytes)
            after_info = information(target_handle)
            if identity(after_info) != identity(before_info):
                raise ValueError("local_text_target_changed_during_preflight")
            _require_windows_contained_path(
                final_path(target_handle),
                expected_target,
                "local_text_target_escaped_root",
            )
            return content, _NodeObservation.from_stat("target", initial)
        finally:
            for handle in reversed(handles):
                close_handle(handle)

    def _encode_desired(self, desired_text: str) -> bytes:
        if not isinstance(desired_text, str):
            raise ValueError("local_text_desired_text_invalid")
        if not unicodedata.is_normalized("NFC", desired_text) or any(
            (
                character not in {"\n", "\t"}
                and unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            )
            for character in desired_text
        ):
            raise ValueError("local_text_desired_text_invalid")
        try:
            encoded = desired_text.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            raise ValueError("local_text_desired_encoding_invalid") from None
        if len(encoded) > self._max_bytes:
            raise ValueError("local_text_desired_content_too_large")
        return encoded

    def _decode_current(self, current: bytes) -> str:
        if b"\x00" in current:
            raise ValueError("local_text_current_content_invalid")
        try:
            decoded = current.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise ValueError("local_text_current_encoding_invalid") from None
        if not unicodedata.is_normalized("NFC", decoded) or any(
            (
                character not in {"\n", "\t"}
                and unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            )
            for character in decoded
        ):
            raise ValueError("local_text_current_content_invalid")
        return decoded

    @staticmethod
    def _build_diff(relative_path: str, before: str, desired: str) -> str:
        lines: list[str] = []
        for line in difflib.unified_diff(
            before.splitlines(keepends=True),
            desired.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
            lineterm="\n",
        ):
            lines.append(line)
            if not line.endswith("\n"):
                lines.append("\n\\ No newline at end of file\n")
        return "".join(lines)

    def _require_safe_create_absence(
        self,
        *,
        root: Path,
        parent_segments: tuple[str, ...],
        target: Path,
        target_name: str,
    ) -> None:
        if os.name == "nt":
            self._require_safe_create_absence_windows(
                root=root,
                parent_segments=parent_segments,
                target=target,
            )
            return
        no_follow = int(getattr(os, "O_NOFOLLOW", 0))
        non_block = int(getattr(os, "O_NONBLOCK", 0))
        directory_flag = int(getattr(os, "O_DIRECTORY", 0))
        if not no_follow or not directory_flag:
            raise ValueError("local_text_create_backend_missing_safe_open_flags")
        flags = os.O_RDONLY | no_follow | non_block | directory_flag
        directory_descriptor: int | None = None
        try:
            try:
                directory_descriptor = os.open(root, flags)
                root_path = self._lstat(root, "local_text_root_missing_or_unreadable")
                if _NodeObservation.from_stat(
                    "root", os.fstat(directory_descriptor)
                ) != _NodeObservation.from_stat("root", root_path):
                    raise ValueError("local_text_root_changed_during_preflight")
                for segment in parent_segments:
                    next_descriptor = os.open(
                        segment,
                        flags,
                        dir_fd=directory_descriptor,
                    )
                    next_observed = os.fstat(next_descriptor)
                    if not stat.S_ISDIR(next_observed.st_mode) or _is_reparse_or_link(
                        next_observed
                    ):
                        os.close(next_descriptor)
                        raise ValueError("local_text_directory_not_safe")
                    os.close(directory_descriptor)
                    directory_descriptor = next_descriptor
            except OSError:
                raise ValueError("local_text_parent_open_failed") from None
            if directory_descriptor is None:
                raise ValueError("local_text_parent_open_failed")
            try:
                with os.scandir(directory_descriptor) as entries:
                    if any(entry.name.casefold() == target_name.casefold() for entry in entries):
                        raise ValueError("local_text_create_casefold_collision")
            except ValueError:
                raise
            except OSError:
                raise ValueError("local_text_parent_scan_failed") from None
        finally:
            if directory_descriptor is not None:
                os.close(directory_descriptor)

    def _require_safe_create_absence_windows(
        self,
        *,
        root: Path,
        parent_segments: tuple[str, ...],
        target: Path,
    ) -> None:
        class _CaseSensitiveInformation(ctypes.Structure):
            _fields_ = (("flags", wintypes.ULONG),)

        class _ByHandleFileInformation(ctypes.Structure):
            _fields_ = (
                ("file_attributes", wintypes.DWORD),
                ("creation_time", wintypes.FILETIME),
                ("last_access_time", wintypes.FILETIME),
                ("last_write_time", wintypes.FILETIME),
                ("volume_serial_number", wintypes.DWORD),
                ("file_size_high", wintypes.DWORD),
                ("file_size_low", wintypes.DWORD),
                ("number_of_links", wintypes.DWORD),
                ("file_index_high", wintypes.DWORD),
                ("file_index_low", wintypes.DWORD),
            )

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        get_final_path = kernel32.GetFinalPathNameByHandleW
        get_final_path.argtypes = (
            wintypes.HANDLE,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        )
        get_final_path.restype = wintypes.DWORD
        get_information = kernel32.GetFileInformationByHandle
        get_information.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(_ByHandleFileInformation),
        )
        get_information.restype = wintypes.BOOL
        get_information_ex = kernel32.GetFileInformationByHandleEx
        get_information_ex.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        )
        get_information_ex.restype = wintypes.BOOL
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        invalid_handle = ctypes.c_void_p(-1).value
        handles: list[int] = []

        def open_directory(path: Path) -> int:
            handle = create_file(
                str(path),
                0x0080,
                0x00000001,
                None,
                3,
                0x00200000 | 0x02000000,
                None,
            )
            if handle == invalid_handle:
                raise ValueError("local_text_parent_open_failed")
            handles.append(handle)
            return handle

        def final_path(handle: int) -> str:
            required = get_final_path(handle, None, 0, 0)
            if not required:
                raise ValueError("local_text_handle_final_path_failed")
            buffer = ctypes.create_unicode_buffer(required + 1)
            written = get_final_path(handle, buffer, len(buffer), 0)
            if not written or written >= len(buffer):
                raise ValueError("local_text_handle_final_path_failed")
            value = buffer.value.replace("/", "\\")
            if value.casefold().startswith("\\\\?\\unc\\"):
                raise ValueError("local_text_handle_nonlocal_path_forbidden")
            if value.startswith("\\\\?\\"):
                value = value[4:]
            if not re.match(r"^[A-Za-z]:\\", value):
                raise ValueError("local_text_handle_nonlocal_path_forbidden")
            return ntpath.normpath(value).casefold()

        try:
            current = root
            directory_paths = [root]
            for segment in parent_segments:
                current = current / segment
                directory_paths.append(current)
            root_final: str | None = None
            parent_handle: int | None = None
            for index, directory_path in enumerate(directory_paths):
                parent_handle = open_directory(directory_path)
                directory_info = _ByHandleFileInformation()
                if not get_information(parent_handle, ctypes.byref(directory_info)):
                    raise ValueError("local_text_directory_handle_inspection_failed")
                attributes = int(directory_info.file_attributes)
                _require_windows_safe_directory_attributes(attributes)
                observed_final = final_path(parent_handle)
                if index == 0:
                    root_final = observed_final
                else:
                    if root_final is None:
                        raise ValueError("local_text_root_final_path_missing")
                    expected = ntpath.normpath(
                        ntpath.join(root_final, *parent_segments[:index])
                    ).casefold()
                    _require_windows_contained_path(
                        observed_final,
                        expected,
                        "local_text_directory_escaped_root",
                    )
            if parent_handle is None:
                raise ValueError("local_text_parent_open_failed")
            case_info = _CaseSensitiveInformation()
            if not get_information_ex(
                parent_handle,
                23,
                ctypes.byref(case_info),
                ctypes.sizeof(case_info),
            ):
                raise ValueError("local_text_parent_case_policy_unavailable")
            if int(case_info.flags) & 1:
                raise ValueError("local_text_case_sensitive_parent_forbidden")
            if self._lstat_optional(target) is not None:
                raise ValueError("local_text_create_casefold_collision")
            if root_final is None:
                raise ValueError("local_text_root_final_path_missing")
            _require_windows_contained_path(
                final_path(parent_handle),
                ntpath.normpath(ntpath.join(root_final, *parent_segments)).casefold(),
                "local_text_directory_escaped_root",
            )
        finally:
            for handle in reversed(handles):
                close_handle(handle)

    @staticmethod
    def _build_rollback_fingerprint(plan: LocalTextFileRollbackPlanContract) -> str:
        return build_local_text_file_rollback_fingerprint(plan)

    def preflight(
        self,
        request: LocalTextFilePreflightRequestContract,
        *,
        now: datetime | None = None,
    ) -> LocalTextFilePreflightContract:
        """Return an exact immutable preparation; never write or create filesystem entries."""

        self._validate_request_bindings(request)
        prepared_at, expires_at = self._validate_window(request.prepared_at, request.expires_at)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("local_text_now_not_timezone_aware")
        current = current.astimezone(timezone.utc)
        if current < prepared_at or current >= expires_at:
            raise ValueError("local_text_preflight_window_inactive")
        desired_bytes = self._encode_desired(request.desired_text)
        try:
            verified = self._verified_context_verifier(request, current)
        except Exception:
            raise ValueError("local_text_preflight_context_not_verified") from None
        if verified is not True:
            raise ValueError("local_text_preflight_context_not_verified")
        root_config_fingerprint = self._root_config_fingerprint()
        if root_config_fingerprint != request.expected_root_config_fingerprint:
            raise ValueError("local_text_root_config_fingerprint_mismatch")
        root_alias, relative_path, segments = self._parse_resource_ref(
            request.adapter_request.resource_ref
        )
        root = self._roots[root_alias]
        target = root.joinpath(*segments)
        initial_directories = self._observe_directories(root, segments[:-1])
        operation = request.adapter_request.operation

        initial_target = self._lstat_optional(target)
        if operation == "create_text":
            if initial_target is not None:
                raise ValueError("local_text_create_target_exists")
            self._require_safe_create_absence(
                root=root,
                parent_segments=segments[:-1],
                target=target,
                target_name=target.name,
            )
            before_exists = False
            before_bytes = b""
            before_text = ""
            target_observation: _NodeObservation | None = None
        else:
            if initial_target is None:
                raise ValueError("local_text_replace_target_missing")
            self._require_regular_single_link_target(initial_target)
            before_bytes, target_observation = self._read_stable_text(
                target,
                initial_target,
                root=root,
                parent_segments=segments[:-1],
                target_name=segments[-1],
            )
            before_text = self._decode_current(before_bytes)
            before_exists = True
            before_hash = _digest_bytes(before_bytes)
            if before_hash != request.expected_current_sha256:
                raise ValueError("local_text_expected_current_hash_mismatch")

        final_directories = self._observe_directories(root, segments[:-1])
        if final_directories != initial_directories:
            raise ValueError("local_text_directory_changed_during_preflight")
        final_target = self._lstat_optional(target)
        if operation == "create_text":
            if final_target is not None:
                raise ValueError("local_text_create_target_changed_during_preflight")
        else:
            if final_target is None:
                raise ValueError("local_text_target_changed_during_preflight")
            self._require_regular_single_link_target(final_target)
            if _NodeObservation.from_stat("target", final_target) != target_observation:
                raise ValueError("local_text_target_changed_during_preflight")
        if self._root_config_fingerprint() != root_config_fingerprint:
            raise ValueError("local_text_root_config_changed_during_preflight")

        before_content_sha256 = _digest_bytes(before_bytes) if before_exists else _EMPTY_SHA256
        desired_content_sha256 = _digest_bytes(desired_bytes)
        unified_diff = self._build_diff(relative_path, before_text, request.desired_text)
        diff_sha256 = _digest_bytes(unified_diff.encode("utf-8"))
        snapshot_payload = {
            "directories": [asdict(item) for item in final_directories],
            "target": asdict(target_observation) if target_observation is not None else None,
            "target_absent": not before_exists,
        }
        filesystem_snapshot_fingerprint = _canonical_digest(snapshot_payload)
        rollback_strategy = (
            "delete_created_file" if operation == "create_text" else "restore_previous_content"
        )
        rollback_plan = LocalTextFileRollbackPlanContract(
            strategy=rollback_strategy,
            operation=operation,
            resource_ref=request.adapter_request.resource_ref,
            root_config_fingerprint=root_config_fingerprint,
            before_content_sha256=before_content_sha256,
            desired_content_sha256=desired_content_sha256,
            preflight_policy_version=request.preflight_policy_version,
            precondition_content_sha256=desired_content_sha256,
            restore_content_sha256=before_content_sha256 if before_exists else None,
            rollback_fingerprint="0" * 64,
        )
        rollback_plan = replace(
            rollback_plan,
            rollback_fingerprint=self._build_rollback_fingerprint(rollback_plan),
        )
        result = LocalTextFilePreflightContract(
            grant_id=request.grant_id,
            grant_fingerprint=request.grant_fingerprint,
            action_fingerprint=request.action_fingerprint,
            intent_fingerprint=request.intent_fingerprint,
            descriptor_fingerprint=request.descriptor_fingerprint,
            registry_fingerprint=request.registry_fingerprint,
            subject_ref=request.subject_ref,
            adapter_request=request.adapter_request,
            operation=operation,
            resource_ref=request.adapter_request.resource_ref,
            root_alias=root_alias,
            relative_path=relative_path,
            expected_current_sha256=request.expected_current_sha256,
            before_exists=before_exists,
            before_content_sha256=before_content_sha256,
            desired_content_sha256=desired_content_sha256,
            before_size_bytes=len(before_bytes),
            desired_size_bytes=len(desired_bytes),
            unified_diff=unified_diff,
            diff_sha256=diff_sha256,
            root_config_fingerprint=root_config_fingerprint,
            filesystem_snapshot_fingerprint=filesystem_snapshot_fingerprint,
            rollback_plan=rollback_plan,
            preflight_fingerprint="0" * 64,
            preflight_policy_version=request.preflight_policy_version,
            diff_algorithm=request.diff_algorithm,
            diff_algorithm_version=request.diff_algorithm_version,
            prepared_at=request.prepared_at,
            expires_at=request.expires_at,
            authorization_expires_at=request.authorization_expires_at,
            filesystem_snapshot_algorithm=LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM,
            filesystem_snapshot_algorithm_version=(
                LOCAL_TEXT_FILESYSTEM_SNAPSHOT_ALGORITHM_VERSION
            ),
            adapter_backend_version=LOCAL_TEXT_ADAPTER_BACKEND_VERSION,
            change_status=(
                "no_change" if before_exists and before_bytes == desired_bytes else "change"
            ),
        )
        result = replace(
            result,
            preflight_fingerprint=build_local_text_file_preflight_fingerprint(result),
        )
        if any(getattr(result, field) for field in _AUTHORITY_FIELDS):
            raise ValueError("local_text_preflight_authority_flag_true")
        require_valid_local_text_file_preflight(
            result,
            now=current,
            allowed_extensions=self._allowed_extensions,
        )
        return result
