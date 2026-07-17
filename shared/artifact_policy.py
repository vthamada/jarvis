"""Deterministic policy for canonical artifact versions and lineage."""

from __future__ import annotations

import re

from shared.contracts import ArtifactLifecycleStateContract, MissionStateContract

ARTIFACT_TRANSITIONS = ("register", "activate", "archive", "replace", "rollback")

_TRANSITIONS_BY_STATUS = {
    "active": {"archive", "replace"},
    "archived": {"activate"},
    "superseded": {"rollback"},
    "rolled_back": set(),
}
_VERSION_SUFFIX = re.compile(r"(?:^|/)v(?P<version>[1-9][0-9]*)$")


def canonical_artifact_states_from_mission(
    mission_state: MissionStateContract | None,
) -> list[ArtifactLifecycleStateContract]:
    """Read canonical versions, lifting legacy refs without mutating memory."""

    if mission_state is None:
        return []
    states = list(mission_state.artifact_states)
    structured_refs = {state.artifact_ref for state in states}
    for artifact_ref in mission_state.artifact_refs:
        if artifact_ref in structured_refs:
            continue
        status = (
            "active" if artifact_ref in mission_state.active_artifact_refs else "archived"
        )
        transition = None
        checkpoint_refs: list[str] = []
        for checkpoint_ref in reversed(mission_state.checkpoint_refs):
            if f":{artifact_ref}:" not in checkpoint_ref:
                continue
            for candidate_transition, candidate_status in {
                "archive": "archived",
                "register": "active",
                "activate": "active",
                "replace": "superseded",
                "rollback": "active",
            }.items():
                marker = f"artifact_lifecycle_transition:{candidate_transition}:{artifact_ref}:"
                if marker in checkpoint_ref:
                    transition = candidate_transition
                    status = candidate_status
                    checkpoint_refs = [checkpoint_ref]
                    break
            if transition:
                break
        states.append(
            ArtifactLifecycleStateContract(
                artifact_ref=artifact_ref,
                artifact_status=status,
                mission_id=mission_state.mission_id,
                transition=transition,
                artifact_version=artifact_version_from_ref(artifact_ref),
                owner_mission_id=mission_state.mission_id,
                objective_ref=mission_state.objective_ref,
                lineage_root_ref=artifact_ref,
                checkpoint_refs=checkpoint_refs,
            )
        )
        structured_refs.add(artifact_ref)
    return states


def artifact_version_from_ref(artifact_ref: str) -> int | None:
    match = _VERSION_SUFFIX.search(artifact_ref)
    return int(match.group("version")) if match else None


def validate_artifact_transition(
    *,
    current_status: str | None,
    requested_transition: str,
) -> str | None:
    if requested_transition not in ARTIFACT_TRANSITIONS:
        return "unsupported_transition"
    if requested_transition == "register":
        return None if current_status is None else "duplicate_artifact"
    if current_status is None:
        return "missing_artifact"
    if requested_transition not in _TRANSITIONS_BY_STATUS.get(current_status, set()):
        return f"invalid_transition:{current_status}:{requested_transition}"
    return None


def validate_artifact_version(
    *,
    requested_transition: str,
    requested_version: int | None,
    current_version: int | None,
) -> str | None:
    if requested_transition in {"register", "replace"}:
        if requested_version is None or requested_version < 1:
            return "positive_version_required"
        if requested_transition == "replace":
            if current_version is None:
                return "current_version_unknown"
            if requested_version != current_version + 1:
                return "replacement_version_must_increment_by_one"
        return None
    if requested_version is not None:
        return "version_metadata_is_immutable"
    return None


def validate_artifact_lineage(
    artifact_states: list[ArtifactLifecycleStateContract],
    *,
    artifact_ref: str,
    replacement_artifact_ref: str | None,
) -> list[str]:
    errors: list[str] = []
    refs = {state.artifact_ref for state in artifact_states}
    if replacement_artifact_ref is None:
        return errors
    if replacement_artifact_ref == artifact_ref:
        errors.append("replacement_must_be_distinct")
    if replacement_artifact_ref in refs:
        errors.append("replacement_artifact_already_exists")
    return errors


def order_artifact_states(
    artifact_states: list[ArtifactLifecycleStateContract],
) -> list[ArtifactLifecycleStateContract]:
    return sorted(
        artifact_states,
        key=lambda item: (
            item.lineage_root_ref or item.artifact_ref,
            item.artifact_version if item.artifact_version is not None else 2**31,
            item.artifact_ref,
        ),
    )
