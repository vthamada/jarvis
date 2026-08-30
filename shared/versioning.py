"""Shared validation for canonical numeric semantic versions."""

from __future__ import annotations

from re import fullmatch

_CANONICAL_SEMVER_PATTERN = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"


def parse_canonical_semver(value: object) -> tuple[int, int, int] | None:
    """Parse ASCII ``major.minor.patch`` without non-canonical leading zeros."""

    if not isinstance(value, str):
        return None
    match = fullmatch(_CANONICAL_SEMVER_PATTERN, value)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)
