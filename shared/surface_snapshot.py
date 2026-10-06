"""Versioned offline surface projection. Metadata is never action authority."""

from __future__ import annotations

import json
import re
from datetime import datetime

SNAPSHOT_VERSION = "jarvis-surface-snapshot-v1"
MAX_SNAPSHOT_BYTES = 65_536


def _object(value: object, keys: set[str]) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ValueError("invalid_snapshot_shape")
    return value


def _text(value: object, *, limit: int = 200, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError("invalid_snapshot_text")
    if any(ord(char) < 32 and char not in "\n\t\r" for char in value):
        raise ValueError("invalid_snapshot_text")


def validate_surface_snapshot(value: object) -> dict[str, object]:
    """Validate bounded shape, not identity, authenticity or capability authority."""
    document = _object(value, {
        "schema_version", "mode", "read_only", "authority", "generated_at",
        "principal_ref", "mission", "work_items", "artifacts", "activity",
    })
    if (
        document["schema_version"] != SNAPSHOT_VERSION
        or document["mode"] != "core_snapshot"
        or document["read_only"] is not True or document["authority"] != "none"
    ):
        raise ValueError("invalid_snapshot_boundary")
    _text(document["generated_at"], limit=64)
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})",
        document["generated_at"],
    ):
        raise ValueError("invalid_snapshot_timestamp")
    try:
        timestamp = datetime.fromisoformat(document["generated_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError
    except ValueError:
        raise ValueError("invalid_snapshot_timestamp") from None
    _text(document["principal_ref"])
    mission = _object(document["mission"], {
        "mission_id", "goal", "status", "objective_ref", "objective_status", "next_action_ref",
    })
    for name in ("mission_id", "status"):
        _text(mission[name])
    _text(mission["goal"], limit=1000)
    for name in ("objective_ref", "objective_status", "next_action_ref"):
        _text(mission[name], nullable=True)
    definitions = {
        "work_items": {"ref", "status"},
        "artifacts": {"ref", "status", "version", "physical_status"},
        "activity": {"name", "status"},
    }
    for name, keys in definitions.items():
        items = document[name]
        if type(items) is not list or len(items) > 100:
            raise ValueError("invalid_snapshot_collection")
        for item in items:
            _object(item, keys)
            for key in keys - {"version"}:
                _text(item[key])
            if "version" in keys and (
                type(item["version"]) is not int or not 1 <= item["version"] <= 2**53 - 1
            ):
                raise ValueError("invalid_snapshot_version")
    encoded = json.dumps(document, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot_too_large")
    # Return a detached JSON projection, not mutable caller aliases.
    return json.loads(encoded)
