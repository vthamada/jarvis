"""Pure lexical validation for local-text resource-relative paths."""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath

_WINDOWS_DRIVE_PATTERN = re.compile(r"[A-Za-z]:")
_WINDOWS_FORBIDDEN_CHARS = frozenset('<>:"\\|?*')
_WINDOWS_DEVICE_NAMES = frozenset(
    {"con", "prn", "aux", "nul", "clock$", "conin$", "conout$"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
    | {f"com{index}" for index in "¹²³"}
    | {f"lpt{index}" for index in "¹²³"}
)


def require_valid_local_text_relative_path(
    relative_path: str,
    *,
    allowed_extensions: tuple[str, ...],
) -> None:
    """Validate one canonical, platform-neutral local-text relative path."""

    if (
        not isinstance(relative_path, str)
        or not relative_path
        or relative_path.startswith("/")
        or relative_path.startswith("//")
        or _WINDOWS_DRIVE_PATTERN.match(relative_path)
        or "\\" in relative_path
        or "%" in relative_path
        or not unicodedata.is_normalized("NFC", relative_path)
    ):
        raise ValueError("local_text_relative_path_invalid")
    try:
        utf8_length = len(relative_path.encode("utf-8"))
        utf16_length = len(relative_path.encode("utf-16-le")) // 2
    except UnicodeEncodeError:
        raise ValueError("local_text_relative_path_invalid") from None
    if utf8_length > 512 or utf16_length > 512:
        raise ValueError("local_text_relative_path_too_long")
    segments = relative_path.split("/")
    if any(not segment or segment in {".", ".."} for segment in segments):
        raise ValueError("local_text_relative_path_segment_invalid")
    if segments[0].casefold() == ".jarvis-transactions":
        raise ValueError("local_text_internal_namespace_reserved")
    for segment in segments:
        if len(segment.encode("utf-8")) > 255 or len(segment.encode("utf-16-le")) // 2 > 255:
            raise ValueError("local_text_relative_path_segment_too_long")
        if (
            segment != segment.strip()
            or segment.endswith((".", " "))
            or any(character in _WINDOWS_FORBIDDEN_CHARS for character in segment)
            or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in segment)
        ):
            raise ValueError("local_text_relative_path_segment_invalid")
        device_stem = segment.split(".", 1)[0].casefold()
        if device_stem in _WINDOWS_DEVICE_NAMES:
            raise ValueError("local_text_windows_device_name_forbidden")
    extension = PurePosixPath(relative_path).suffix.casefold()
    if extension not in allowed_extensions:
        raise ValueError("local_text_extension_not_allowlisted")
