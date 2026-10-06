"""Real SQLite cross-connection scope fences, not physical Linux evidence."""

import sqlite3
import threading
from contextlib import nullcontext

import pytest
from test_mb219_physical_effect_boundary import MISSION, _dispatched

from shared.types import MissionStatus


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
@pytest.mark.parametrize("abort_scope", [False, True])
def test_memory_scope_fences_pause_from_other_connection_until_effect_scope_exits(
    tmp_path, purpose, abort_scope
):
    service, plan, authorizer_kwargs = _dispatched(tmp_path, purpose)
    update_attempted = threading.Event()
    update_finished = threading.Event()
    errors = []

    def pause_from_other_connection():
        try:
            with sqlite3.connect(service.repository.database_path, timeout=3) as connection:
                # Trace fires at the actual statement, not merely thread start.
                connection.set_trace_callback(
                    lambda sql: update_attempted.set() if sql.startswith("UPDATE") else None
                )
                connection.execute(
                    "UPDATE mission_states SET mission_status = ? WHERE mission_id = ?",
                    (MissionStatus.PAUSED.value, str(MISSION)),
                )
                connection.commit()
        except Exception as exc:
            errors.append(exc)
        finally:
            update_finished.set()

    writer = threading.Thread(target=pause_from_other_connection)
    expectation = pytest.raises(RuntimeError, match="injected scope interruption") if (
        abort_scope
    ) else nullcontext()
    try:
        with expectation:
            with service.artifact_physical_effect_scope(plan):
                writer.start()
                assert update_attempted.wait(timeout=2)
                assert not update_finished.wait(timeout=0.2)
                mission = service.get_mission_state(str(MISSION))
                assert mission.mission_status is MissionStatus.ACTIVE
                if abort_scope:
                    raise RuntimeError("injected scope interruption")
    finally:
        if writer.ident is not None:
            writer.join(timeout=4)
    assert not writer.is_alive()
    assert update_finished.is_set() and errors == []
    assert service.get_mission_state(str(MISSION)).mission_status is MissionStatus.PAUSED
    assert not service.authorize_artifact_physical_effect(
        plan, resource_ref=plan.resource_ref, **authorizer_kwargs
    )
    assert service.authorize_artifact_physical_effect(
        plan, resource_ref=plan.resource_ref, effect_mode="historical_recovery",
        **authorizer_kwargs,
    )
    with pytest.raises(ValueError, match="first_effect_not_authorized"):
        with service.artifact_physical_effect_scope(plan):
            pytest.fail("paused mission entered fresh effect scope")
    assert not (tmp_path / "mb219.txt").exists()


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_denied_memory_scope_releases_database_lock_without_promoting_authority(tmp_path, purpose):
    service, plan, _kwargs = _dispatched(tmp_path, purpose)
    mission = service.get_mission_state(str(MISSION))
    mission.mission_status = MissionStatus.PAUSED
    service.repository.upsert_mission_state(mission)
    before = service.get_artifact_physical_saga(plan.saga_id)
    with pytest.raises(ValueError, match="first_effect_not_authorized"):
        with service.artifact_physical_effect_scope(plan):
            pytest.fail("denied scope yielded")
    # A real independent connection can write after the failed entry; no stale
    # BEGIN IMMEDIATE transaction survives the authorization exception.
    with sqlite3.connect(service.repository.database_path, timeout=0.2) as connection:
        connection.execute(
            "UPDATE mission_states SET mission_status = ? WHERE mission_id = ?",
            (MissionStatus.ACTIVE.value, str(MISSION)),
        )
        connection.commit()
    with service.artifact_physical_effect_scope(plan):
        assert service.get_artifact_physical_saga(plan.saga_id) == before
    assert service.get_artifact_physical_lineage(str(MISSION), plan.lineage_root_ref) is None
