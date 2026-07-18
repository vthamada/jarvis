"""Deterministic policy for explicit, governed open-loop resume."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from shared.contracts import MissionStateContract, OpenLoopStateContract
from shared.types import MissionId


def open_loop_ref(mission_id: str, loop_summary: str) -> str:
    digest = sha256(f"{mission_id}\x00{loop_summary}".encode()).hexdigest()[:16]
    return f"open-loop://{mission_id}/{digest}"


def canonical_open_loop_states_from_mission(
    mission_state: MissionStateContract | None,
) -> list[OpenLoopStateContract]:
    if mission_state is None:
        return []
    states = list(mission_state.open_loop_states)
    summaries = {state.loop_summary for state in states}
    for summary in mission_state.open_loops:
        if summary in summaries:
            continue
        states.append(
            OpenLoopStateContract(
                open_loop_ref=open_loop_ref(str(mission_state.mission_id), summary),
                mission_id=MissionId(str(mission_state.mission_id)),
                loop_summary=summary,
            )
        )
        summaries.add(summary)
    return states


def mission_freshness(
    updated_at: str,
    generated_at: str,
) -> tuple[str, float | None]:
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        age_hours = (generated - updated).total_seconds() / 3600
    except (TypeError, ValueError):
        return "unknown", None
    if age_hours < -0.084:
        return "unknown", None
    safe_age = round(max(0.0, age_hours), 2)
    if safe_age <= 24:
        return "fresh", safe_age
    if safe_age <= 72:
        return "aging", safe_age
    return "stale", safe_age


def open_loop_resume_blockers(
    *,
    mission_state: MissionStateContract,
    loop_state: OpenLoopStateContract,
    freshness_status: str,
    has_structured_work_items: bool,
    selected_work_item_ref: str | None,
) -> list[str]:
    blockers: list[str] = []
    if loop_state.loop_status != "open":
        blockers.append(f"loop_status:{loop_state.loop_status}")
    if mission_state.mission_status.value != "active":
        blockers.append(f"mission_status:{mission_state.mission_status.value}")
    if (mission_state.objective_status or "active") != "active":
        blockers.append(f"objective_status:{mission_state.objective_status}")
    if freshness_status not in {"fresh", "aging"}:
        blockers.append(f"freshness_status:{freshness_status}")
    if mission_state.surface_identity_conflict_flags:
        blockers.append("surface_identity_conflict")
    if has_structured_work_items and not selected_work_item_ref:
        blockers.append("no_executable_work_item")
    return blockers
