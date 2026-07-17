"""Deterministic policy for governed work-item state and operator ordering."""

from __future__ import annotations

from dataclasses import replace

from shared.contracts import (
    WORK_ITEM_PRIORITY_LEVELS,
    MissionStateContract,
    WorkItemStateContract,
)

WORK_ITEM_TRANSITIONS = (
    "create",
    "update",
    "resume",
    "pause",
    "block",
    "complete",
    "redefine-next-action",
)

_TRANSITIONS_BY_STATUS = {
    "active": {"update", "pause", "block", "complete", "redefine-next-action"},
    "paused": {"update", "resume", "block", "complete", "redefine-next-action"},
    "blocked": {"update", "resume", "redefine-next-action"},
    "completed": set(),
}
_PRIORITY_RANK = {
    priority: rank for rank, priority in enumerate(WORK_ITEM_PRIORITY_LEVELS)
}


def canonical_work_items_from_mission(
    mission_state: MissionStateContract | None,
) -> list[WorkItemStateContract]:
    """Read structured state, lifting legacy refs only for compatibility."""

    if mission_state is None:
        return []
    if mission_state.work_items:
        return list(mission_state.work_items)
    items: list[WorkItemStateContract] = []
    for work_item_ref in mission_state.work_item_refs:
        has_transition_checkpoint = any(
            f":{work_item_ref}:" in checkpoint_ref
            and checkpoint_ref.startswith("work_item_transition:")
            for checkpoint_ref in mission_state.checkpoint_refs
        )
        if not work_item_ref.startswith("work-item://") and not has_transition_checkpoint:
            continue
        status = "active" if work_item_ref in mission_state.active_work_items else "inactive"
        for checkpoint_ref in reversed(mission_state.checkpoint_refs):
            matched = False
            for transition, candidate_status in {
                "complete": "completed",
                "block": "blocked",
                "pause": "paused",
                "create": "active",
                "resume": "active",
                "redefine-next-action": "active",
            }.items():
                if f"work_item_transition:{transition}:{work_item_ref}:" in checkpoint_ref:
                    status = candidate_status
                    matched = True
                    break
            if matched:
                break
        items.append(
            WorkItemStateContract(
                work_item_ref=work_item_ref,
                work_item_status=status,
                mission_id=mission_state.mission_id,
                blocking_state=("ready" if status == "active" else status),
            )
        )
    return items


def validate_work_item_graph(
    work_items: list[WorkItemStateContract],
    *,
    work_item_ref: str,
    dependency_refs: list[str],
) -> list[str]:
    """Return bounded graph errors for a proposed create or update."""

    errors: list[str] = []
    known_refs = {item.work_item_ref for item in work_items}
    if len(dependency_refs) != len(set(dependency_refs)):
        errors.append("duplicate_dependency_ref")
    if work_item_ref in dependency_refs:
        errors.append("self_dependency")
    unknown_refs = sorted(set(dependency_refs) - known_refs)
    errors.extend(f"unknown_dependency:{item}" for item in unknown_refs)

    graph = {item.work_item_ref: list(item.dependency_refs) for item in work_items}
    graph[work_item_ref] = list(dependency_refs)
    if _has_cycle(graph):
        errors.append("dependency_cycle")
    return errors


def validate_work_item_transition(
    *,
    current_status: str | None,
    requested_transition: str,
) -> str | None:
    if requested_transition not in WORK_ITEM_TRANSITIONS:
        return "unsupported_transition"
    if requested_transition == "create":
        return None if current_status is None else "duplicate_work_item"
    if current_status is None:
        return "missing_work_item"
    if requested_transition not in _TRANSITIONS_BY_STATUS.get(current_status, set()):
        return f"invalid_transition:{current_status}:{requested_transition}"
    return None


def unresolved_dependency_refs(
    item: WorkItemStateContract,
    work_items: list[WorkItemStateContract],
) -> list[str]:
    status_by_ref = {
        candidate.work_item_ref: candidate.work_item_status for candidate in work_items
    }
    return [
        dependency_ref
        for dependency_ref in item.dependency_refs
        if status_by_ref.get(dependency_ref) != "completed"
    ]


def refresh_work_item_blocking_states(
    work_items: list[WorkItemStateContract],
) -> list[WorkItemStateContract]:
    """Refresh derived blocking state without scheduling or executing work."""

    refreshed: list[WorkItemStateContract] = []
    for item in work_items:
        unresolved = unresolved_dependency_refs(item, work_items)
        if item.work_item_status == "completed":
            blocking_state = "completed"
        elif item.work_item_status == "paused":
            blocking_state = "paused"
        elif item.work_item_status == "blocked" or item.blocker_refs:
            blocking_state = "blocked"
        elif unresolved:
            blocking_state = "dependency_blocked"
        else:
            blocking_state = "ready"
        refreshed.append(replace(item, blocking_state=blocking_state))
    return refreshed


def order_work_items(
    work_items: list[WorkItemStateContract],
) -> list[WorkItemStateContract]:
    """Topologically order open work, then append completed history."""

    refreshed = refresh_work_item_blocking_states(work_items)
    open_items = {
        item.work_item_ref: item
        for item in refreshed
        if item.work_item_status != "completed"
    }
    completed_items = sorted(
        (item for item in refreshed if item.work_item_status == "completed"),
        key=_work_item_sort_key,
    )
    indegree = {
        item_ref: sum(
            dependency_ref in open_items
            for dependency_ref in item.dependency_refs
        )
        for item_ref, item in open_items.items()
    }
    dependents: dict[str, list[str]] = {item_ref: [] for item_ref in open_items}
    for item_ref, item in open_items.items():
        for dependency_ref in item.dependency_refs:
            if dependency_ref in dependents:
                dependents[dependency_ref].append(item_ref)

    available = sorted(
        (open_items[item_ref] for item_ref, degree in indegree.items() if degree == 0),
        key=_work_item_sort_key,
    )
    ordered: list[WorkItemStateContract] = []
    while available:
        item = available.pop(0)
        ordered.append(item)
        for dependent_ref in sorted(dependents[item.work_item_ref]):
            indegree[dependent_ref] -= 1
            if indegree[dependent_ref] == 0:
                available.append(open_items[dependent_ref])
                available.sort(key=_work_item_sort_key)

    if len(ordered) != len(open_items):
        remaining = [
            item for item_ref, item in open_items.items() if item_ref not in {
                ordered_item.work_item_ref for ordered_item in ordered
            }
        ]
        ordered.extend(sorted(remaining, key=_work_item_sort_key))
    return [*ordered, *completed_items]


def _work_item_sort_key(item: WorkItemStateContract) -> tuple[int, str]:
    return (_PRIORITY_RANK.get(item.priority_level, 99), item.work_item_ref)


def _has_cycle(graph: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency in graph and visit(dependency):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in sorted(graph))
