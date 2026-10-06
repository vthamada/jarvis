# ruff: noqa: E402
"""Export an offline read-only mission snapshot through the Core inspection path."""

import os
from argparse import ArgumentParser
from datetime import UTC, datetime
from json import dumps
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from governance_service.service import GovernanceService
from memory_service.readonly_repository import ReadOnlySqliteMemoryRepository
from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from shared.artifact_policy import canonical_artifact_states_from_mission
from shared.surface_snapshot import SNAPSHOT_VERSION, validate_surface_snapshot


class _OfflineObservability(ObservabilityService):
    @staticmethod
    def _build_agentic_adapter():
        return None


def export_snapshot(*, memory_db: Path, mission_id: str, principal_ref: str) -> dict:
    if not mission_id or len(mission_id) > 200 or not principal_ref or len(principal_ref) > 200:
        raise ValueError("invalid_snapshot_identity")
    repository = ReadOnlySqliteMemoryRepository(memory_db)
    memory = MemoryService(repository=repository)
    with TemporaryDirectory(prefix="jarvis-surface-snapshot-") as temporary:
        runtime = Path(temporary)
        governance = GovernanceService()
        core = OrchestratorService(
            memory_service=memory, governance_service=governance,
            operational_service=OperationalService(artifact_dir=str(runtime / "artifacts")),
            observability_service=_OfflineObservability(str(runtime / "events.db")),
        )
        state = core.inspect_objective_state(
            mission_id=mission_id, session_id="offline-surface-snapshot",
            operator_identity_ref=principal_ref, canonical_user_ref="user://local_operator",
        )
        if state is None:
            raise ValueError("snapshot_mission_not_found")
        artifacts = canonical_artifact_states_from_mission(state)
        return validate_surface_snapshot({
            "schema_version": SNAPSHOT_VERSION,
            "mode": "core_snapshot", "read_only": True, "authority": "none",
            "generated_at": datetime.now(UTC).isoformat(), "principal_ref": principal_ref,
            "mission": {
                "mission_id": str(state.mission_id), "goal": state.mission_goal,
                "status": state.mission_status.value,
                "objective_ref": state.objective_ref, "objective_status": state.objective_status,
                "next_action_ref": state.next_action_ref,
            },
            "work_items": [
                {"ref": item.work_item_ref, "status": item.work_item_status}
                for item in state.work_items
            ],
            "artifacts": [
                {"ref": item.artifact_ref, "status": item.artifact_status,
                 "version": item.artifact_version,
                 "physical_status": item.physical_consistency_status or "unverified_legacy"}
                for item in artifacts if item.artifact_version is not None
            ],
            "activity": [{"name": "objective_state_inspected", "status": "read_only"}],
        })


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--memory-db", required=True, type=Path)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--principal-ref", default="operator://local_console")
    parser.add_argument(
        "--output", type=Path, help="Create a new UTF-8 snapshot file; never overwrite.",
    )
    args = parser.parse_args()
    try:
        document = export_snapshot(
            memory_db=args.memory_db, mission_id=args.mission_id, principal_ref=args.principal_ref,
        )
        encoded = dumps(document, ensure_ascii=False, allow_nan=False)
        if args.output is not None:
            descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
    except Exception:
        # Schema/path/runtime details can contain user data; never dump them.
        print(dumps({"error_code": "snapshot_unavailable", "read_only": True}))
        return 1
    print(encoded if args.output is None else dumps({"snapshot_exported": True, "read_only": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
