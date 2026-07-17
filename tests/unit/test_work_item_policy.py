from shared.contracts import MissionStateContract, WorkItemStateContract
from shared.types import MissionId, MissionStatus
from shared.work_item_policy import (
    canonical_work_items_from_mission,
    order_work_items,
    refresh_work_item_blocking_states,
    validate_work_item_graph,
    validate_work_item_transition,
)


def work_item(
    ref: str,
    *,
    status: str = "active",
    priority: str = "p2",
    dependencies: list[str] | None = None,
    blockers: list[str] | None = None,
) -> WorkItemStateContract:
    return WorkItemStateContract(
        work_item_ref=ref,
        work_item_status=status,
        mission_id=MissionId("mission-work-policy"),
        priority_level=priority,
        dependency_refs=list(dependencies or []),
        blocker_refs=list(blockers or []),
    )


def test_work_item_policy_orders_dependencies_before_higher_priority_dependents() -> None:
    foundation = work_item("work-item://foundation", priority="p2")
    release = work_item(
        "work-item://release",
        priority="p0",
        dependencies=[foundation.work_item_ref],
    )

    ordered = order_work_items([release, foundation])

    assert [item.work_item_ref for item in ordered] == [
        foundation.work_item_ref,
        release.work_item_ref,
    ]
    assert ordered[0].blocking_state == "ready"
    assert ordered[1].blocking_state == "dependency_blocked"


def test_work_item_policy_refreshes_dependent_after_completion() -> None:
    foundation = work_item("work-item://foundation", status="completed")
    release = work_item(
        "work-item://release",
        priority="p0",
        dependencies=[foundation.work_item_ref],
    )

    refreshed = refresh_work_item_blocking_states([release, foundation])

    assert next(
        item for item in refreshed if item.work_item_ref == release.work_item_ref
    ).blocking_state == "ready"


def test_work_item_policy_detects_cycle_self_unknown_and_transition_errors() -> None:
    first = work_item("work-item://first", dependencies=["work-item://second"])
    second = work_item("work-item://second")

    cycle_errors = validate_work_item_graph(
        [first, second],
        work_item_ref=second.work_item_ref,
        dependency_refs=[first.work_item_ref],
    )
    invalid_errors = validate_work_item_graph(
        [first],
        work_item_ref=first.work_item_ref,
        dependency_refs=[first.work_item_ref, "work-item://missing"],
    )

    assert cycle_errors == ["dependency_cycle"]
    assert "self_dependency" in invalid_errors
    assert "unknown_dependency:work-item://missing" in invalid_errors
    assert validate_work_item_transition(
        current_status="completed",
        requested_transition="resume",
    ) == "invalid_transition:completed:resume"


def test_work_item_policy_lifts_legacy_state_without_mutation() -> None:
    mission = MissionStateContract(
        mission_id=MissionId("mission-legacy-work-item"),
        mission_goal="Preserve old state",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T00:00:00Z",
        work_item_refs=["work-item://legacy"],
        active_work_items=["work-item://legacy"],
    )

    lifted = canonical_work_items_from_mission(mission)

    assert lifted[0].work_item_status == "active"
    assert lifted[0].priority_level == "p2"
    assert mission.work_items == []
