"""Real canonical mission -> Core inspection -> offline surface, without source writes."""

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from shutil import which
from subprocess import run

import pytest
from memory_service.readonly_repository import ReadOnlySqliteMemoryRepository
from memory_service.service import MemoryService

from apps.jarvis_console.snapshot import export_snapshot, main
from shared.contracts import (
    ArtifactLifecycleStateContract,
    MissionStateContract,
    WorkItemStateContract,
)
from shared.types import MissionId, MissionStatus


def create_memory(path):
    service = MemoryService(database_url=f"sqlite:///{path.as_posix()}")
    mission_id = MissionId("mission://snapshot-test")
    service.repository.upsert_mission_state(MissionStateContract(
        mission_id=mission_id, mission_goal="Objetivo real do Core",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[], updated_at="2026-10-02T12:00:00Z", objective_status="active",
        work_items=[WorkItemStateContract(
            "work-item://snapshot-test", "active", mission_id, priority_level="p1",
        )],
        artifact_states=[ArtifactLifecycleStateContract(
            "artifact://snapshot-test/v1", "active", mission_id, artifact_version=1,
            physical_consistency_status="logical_only",
        )],
    ))
    return service


def test_export_uses_canonical_memory_without_changing_db(tmp_path, monkeypatch):
    database = tmp_path / "memory.db"
    create_memory(database)
    before = sha256(database.read_bytes()).hexdigest()
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    projection = export_snapshot(
        memory_db=database, mission_id="mission://snapshot-test", principal_ref="operator://local_console",
    )
    assert projection["mission"]["goal"] == "Objetivo real do Core"
    # JSON overlay cannot manufacture a normalized physical version.
    assert projection["artifacts"][0]["physical_status"] == "unverified_legacy"
    assert projection["activity"][0]["name"] == "objective_state_inspected"
    assert projection["authority"] == "none"
    assert sha256(database.read_bytes()).hexdigest() == before
    assert [p.name for p in tmp_path.iterdir()] == ["memory.db"]


def test_readonly_repository_does_not_create_missing_database(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(ValueError, match="existing_memory_database_required"):
        ReadOnlySqliteMemoryRepository(missing)
    assert not missing.exists()


def test_wal_database_refused_without_creating_sidecars(tmp_path):
    database = tmp_path / "wal.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE fixture(value TEXT)")
        connection.execute("PRAGMA journal_mode=WAL")
    connection.close()
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="quiescent_delete_mode_database_required"):
        ReadOnlySqliteMemoryRepository(database)
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_readonly_rechecks_wal_before_each_connect(tmp_path):
    database = tmp_path / "memory.db"
    create_memory(database)
    readonly = ReadOnlySqliteMemoryRepository(database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    connection.close()
    with pytest.raises(ValueError, match="quiescent_delete_mode_database_required"):
        readonly.fetch_mission_state("mission://snapshot-test")


def test_readonly_sqlite_refuses_mutation_and_migration(tmp_path):
    database = tmp_path / "memory.db"
    service = create_memory(database)
    readonly = ReadOnlySqliteMemoryRepository(database)
    before = sha256(database.read_bytes()).hexdigest()
    with pytest.raises(sqlite3.OperationalError):
        readonly.upsert_mission_state(service.get_mission_state("mission://snapshot-test"))
    assert sha256(database.read_bytes()).hexdigest() == before


def test_export_missing_mission_and_legacy_schema_fail_closed(tmp_path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE legacy(value TEXT)")
    before = sha256(database.read_bytes()).hexdigest()
    with pytest.raises(sqlite3.OperationalError):
        export_snapshot(memory_db=database, mission_id="mission://absent", principal_ref="operator://x")
    assert sha256(database.read_bytes()).hexdigest() == before


def test_cli_exports_real_snapshot_and_sanitizes_failure(tmp_path, monkeypatch, capsys):
    database = tmp_path / "memory.db"
    create_memory(database)
    monkeypatch.setattr("sys.argv", ["snapshot", "--memory-db", str(database),
                                    "--mission-id", "mission://snapshot-test"])
    assert main() == 0
    document = json.loads(capsys.readouterr().out)
    assert document["mission"]["goal"] == "Objetivo real do Core"
    monkeypatch.setattr("sys.argv", ["snapshot", "--memory-db", str(database),
                                    "--mission-id", "mission://missing"])
    assert main() == 1
    assert json.loads(capsys.readouterr().out) == {
        "error_code": "snapshot_unavailable", "read_only": True,
    }


def test_cli_writes_utf8_file_but_never_overwrites(tmp_path, monkeypatch, capsys):
    database = tmp_path / "memory.db"
    create_memory(database)
    output = tmp_path / "snapshot.json"
    monkeypatch.setattr("sys.argv", ["snapshot", "--memory-db", str(database),
                                    "--mission-id", "mission://snapshot-test",
                                    "--output", str(output)])
    assert main() == 0
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["mission"]["goal"] == "Objetivo real do Core"
    assert json.loads(capsys.readouterr().out)["snapshot_exported"] is True
    before = output.read_bytes()
    assert main() == 1
    assert output.read_bytes() == before
    assert json.loads(capsys.readouterr().out)["error_code"] == "snapshot_unavailable"


@pytest.mark.skipif(which("node") is None, reason="separate Web Node verification required")
def test_real_core_export_reaches_web_readonly_controller(tmp_path):
    database = tmp_path / "memory.db"
    create_memory(database)
    document = export_snapshot(
        memory_db=database, mission_id="mission://snapshot-test", principal_ref="operator://test",
    )
    script = """
        import { createController } from './apps/jarvis_web/controller.mjs';
        let text = ''; for await (const chunk of process.stdin) text += chunk;
        const controller = createController();
        const before = controller.getSnapshot();
        const accepted = await controller.importSnapshotFile({
          size: Buffer.byteLength(text, 'utf8'), text: async () => text
        });
        const after = controller.getSnapshot();
        process.stdout.write(JSON.stringify({accepted,
          snapshot: after.importedSnapshot, requestStatus: after.requestStatus,
          sameIdentity: before.principalId === after.principalId,
          sameConversation: JSON.stringify(before.messages) === JSON.stringify(after.messages)
        }));
        controller.dispose();
    """
    process = run(
        [which("node"), "--input-type=module", "-e", script],
        input=json.dumps(document), text=True, encoding="utf-8", capture_output=True,
        cwd=Path(__file__).resolve().parents[2], timeout=15, check=True,
    )
    result = json.loads(process.stdout)
    assert result["accepted"] is True
    assert result["snapshot"]["mission"]["goal"] == "Objetivo real do Core"
    assert result["sameIdentity"] is True and result["sameConversation"] is True
    assert result["requestStatus"] == "idle"
