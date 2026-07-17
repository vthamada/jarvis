from shared.artifact_policy import (
    artifact_version_from_ref,
    canonical_artifact_states_from_mission,
    order_artifact_states,
    validate_artifact_lineage,
    validate_artifact_transition,
    validate_artifact_version,
)
from shared.contracts import ArtifactLifecycleStateContract, MissionStateContract
from shared.types import MissionId, MissionStatus


def artifact_state(
    ref: str,
    *,
    version: int,
    status: str = "active",
    root: str | None = None,
) -> ArtifactLifecycleStateContract:
    return ArtifactLifecycleStateContract(
        artifact_ref=ref,
        artifact_status=status,
        mission_id=MissionId("mission-artifact-policy"),
        artifact_version=version,
        owner_mission_id=MissionId("mission-artifact-policy"),
        work_item_ref="work-item://mission-artifact-policy/plan",
        lineage_root_ref=root or ref,
    )


def test_artifact_policy_lifts_legacy_version_without_mutation() -> None:
    mission = MissionStateContract(
        mission_id=MissionId("mission-artifact-policy"),
        mission_goal="Ship plan",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T00:00:00Z",
        artifact_refs=["artifact://mission-artifact-policy/plan/v3"],
        active_artifact_refs=["artifact://mission-artifact-policy/plan/v3"],
    )

    states = canonical_artifact_states_from_mission(mission)

    assert artifact_version_from_ref(states[0].artifact_ref) == 3
    assert states[0].artifact_status == "active"
    assert states[0].owner_mission_id == mission.mission_id
    assert mission.artifact_states == []


def test_artifact_policy_enforces_state_machine_and_immutable_versions() -> None:
    assert (
        validate_artifact_transition(
            current_status=None,
            requested_transition="register",
        )
        is None
    )
    assert (
        validate_artifact_transition(
            current_status="superseded",
            requested_transition="replace",
        )
        == "invalid_transition:superseded:replace"
    )
    assert (
        validate_artifact_version(
            requested_transition="replace",
            requested_version=3,
            current_version=1,
        )
        == "replacement_version_must_increment_by_one"
    )
    assert (
        validate_artifact_version(
            requested_transition="archive",
            requested_version=1,
            current_version=1,
        )
        == "version_metadata_is_immutable"
    )


def test_artifact_policy_rejects_duplicate_or_self_replacement() -> None:
    version_one = artifact_state("artifact://mission-artifact-policy/plan/v1", version=1)
    version_two = artifact_state(
        "artifact://mission-artifact-policy/plan/v2",
        version=2,
        root=version_one.artifact_ref,
    )

    assert validate_artifact_lineage(
        [version_one],
        artifact_ref=version_one.artifact_ref,
        replacement_artifact_ref=version_one.artifact_ref,
    ) == ["replacement_must_be_distinct", "replacement_artifact_already_exists"]
    assert validate_artifact_lineage(
        [version_one, version_two],
        artifact_ref=version_one.artifact_ref,
        replacement_artifact_ref=version_two.artifact_ref,
    ) == ["replacement_artifact_already_exists"]


def test_artifact_policy_orders_lineage_by_version() -> None:
    root = "artifact://mission-artifact-policy/plan/v1"
    version_two = artifact_state(
        "artifact://mission-artifact-policy/plan/v2", version=2, root=root
    )
    version_one = artifact_state(root, version=1)

    ordered = order_artifact_states([version_two, version_one])

    assert [item.artifact_version for item in ordered] == [1, 2]
