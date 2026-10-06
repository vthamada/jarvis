"""Offline projections cannot carry action authority or oversized payloads."""

from copy import deepcopy

import pytest

from shared.surface_snapshot import SNAPSHOT_VERSION, validate_surface_snapshot


def valid_snapshot():
    return {
        "schema_version": SNAPSHOT_VERSION, "mode": "core_snapshot",
        "read_only": True, "authority": "none", "generated_at": "2026-10-02T12:00:00Z",
        "principal_ref": "operator://local_console",
        "mission": {"mission_id": "mission://test", "goal": "Review evidence", "status": "active",
                    "objective_ref": None, "objective_status": None, "next_action_ref": None},
        "work_items": [{"ref": "work-item://test", "status": "active"}],
        "artifacts": [{"ref": "artifact://test/v1", "status": "active", "version": 1,
                       "physical_status": "logical_only"}],
        "activity": [{"name": "objective_state_inspected", "status": "read_only"}],
    }


@pytest.mark.parametrize("change", [
    {"read_only": 1}, {"authority": "grant"}, {"mode": "live"}, {"schema_version": "old"},
    {"generated_at": "2026-10-02T12:00:00"}, {"generated_at": "2026-02-30T12:00:00Z"},
    {"generated_at": "2026-10-02 12:00:00+00:00"},
    {"principal_ref": "x" * 201}, {"grant": "allow"}, {"work_items": [None]},
    {"activity": [] * 101 + [{"name": "x", "status": "y"}] * 101},
    {"artifacts": [{"ref": "artifact://x", "status": "active", "version": True,
                    "physical_status": "verified"}]},
    {"artifacts": [{"ref": "artifact://x", "status": "active", "version": 2**53,
                    "physical_status": "verified"}]},
])
def test_malformed_snapshot_rejected(change):
    document = valid_snapshot()
    document.update(change)
    with pytest.raises(ValueError):
        validate_surface_snapshot(document)


def test_detached_and_no_authenticity_claim():
    document = valid_snapshot()
    result = validate_surface_snapshot(document)
    result["mission"]["goal"] = "Changed"
    assert document == deepcopy(valid_snapshot())
    assert result["authority"] == "none"


def test_total_size_is_bounded():
    document = valid_snapshot()
    document["activity"] = [{"name": "é" * 200, "status": "é" * 200}] * 100
    with pytest.raises(ValueError, match="snapshot_too_large"):
        validate_surface_snapshot(document)
