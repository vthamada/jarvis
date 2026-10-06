"""Actual CLI -> composed Core preparation, without host artifact execution."""

import json
import os
import sys
from datetime import UTC, datetime

import pytest

from apps.jarvis_console.cli import main
from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
from apps.jarvis_console.physical_cli import _read_desired_text
from shared.contracts import MissionStateContract, WorkItemStateContract
from shared.types import MissionId, MissionStatus


def command(tmp_path, *, action="prepare"):
    root = tmp_path / "notes"
    root.mkdir(exist_ok=True)
    return ["physical", "--runtime-dir", str(tmp_path / "runtime"),
            "--root", f"notes={root}", "--action", action, "--format", "json"]


def test_cli_prepares_exact_challenge_without_source_in_output(tmp_path, capsys):
    args = command(tmp_path)
    root = tmp_path / "notes"
    core = build_physical_orchestrator(runtime_dir=tmp_path / "runtime", roots={"notes": root})
    mission_id, work_ref = "mission://physical-cli/test", "work-item://physical-cli/test"
    core.memory_service.repository.upsert_mission_state(MissionStateContract(
        mission_id=MissionId(mission_id), mission_goal="CLI preparation",
        mission_status=MissionStatus.ACTIVE, checkpoints=[],
        updated_at=datetime.now(UTC).isoformat(),
        objective_ref="objective://physical-cli/test", objective_status="active",
        work_item_refs=[work_ref], active_work_items=[work_ref],
        work_items=[WorkItemStateContract(
            work_item_ref=work_ref, work_item_status="active", mission_id=MissionId(mission_id),
            priority_level="p1", blocking_state="ready",
        )],
    ))
    source = tmp_path / "desired.txt"
    source.write_text("private human source\n", encoding="utf-8", newline="\n")
    invocation = args + ["--mission-id", mission_id, "--work-item-ref", work_ref,
                        "--artifact-ref", "artifact://physical-cli/v1",
                        "--resource-ref", "text:notes/note.txt",
                        "--desired-file", str(source)]
    assert main(invocation) == 0
    output = capsys.readouterr().out
    assert "private human source" not in output
    metadata = json.loads(json.loads(output)["outputs"][0])
    assert metadata["challenge_id"] and metadata["action_fingerprint"]
    assert metadata["contains_content"] is False and "preview" not in metadata
    assert list(root.iterdir()) == []
    if sys.platform != "linux":
        assert metadata["durable"] is False


def test_invalid_source_is_refused_before_runtime_creation(tmp_path, capsys):
    args = command(tmp_path)
    assert main(args + ["--mission-id", "mission://x", "--work-item-ref", "work-item://x",
                        "--artifact-ref", "artifact://x", "--resource-ref", "text:notes/note.txt",
                        "--desired-file", str(tmp_path / "missing.txt")]) == 3
    assert json.loads(capsys.readouterr().err)["error_code"] == "physical_operation_refused"
    assert not (tmp_path / "runtime").exists()


def test_desired_text_reader_preserves_exact_utf8_bytes_and_newlines(tmp_path):
    source = tmp_path / "desired.txt"
    data = "ação\r\nexact input\x1a\n".encode("utf-8")
    source.write_bytes(data)
    assert _read_desired_text(source).encode("utf-8") == data
    assert source.read_bytes() == data


@pytest.mark.parametrize("enabled", [False, True])
def test_windows_execution_never_creates_runtime(tmp_path, capsys, enabled):
    if sys.platform == "linux":
        pytest.skip("actual Windows refusal test")
    args = command(tmp_path, action="execute") + [
        "--request-id", "id", "--challenge-id", "challenge", "--action-fingerprint", "fingerprint",
        "--confirmation-receipt-id", "receipt",
    ]
    assert main(args + (["--enable-execution"] if enabled else [])) == 3
    assert json.loads(capsys.readouterr().err)["status"] == "error"
    assert not (tmp_path / "runtime").exists()


@pytest.mark.parametrize("source_kind", ["hardlink", "oversized", "invalid_utf8", "directory"])
def test_invalid_desired_input_is_redacted_before_runtime_creation(tmp_path, capsys, source_kind):
    args = command(tmp_path)
    source = tmp_path / "private-source.txt"
    if source_kind == "directory":
        source.mkdir()
    elif source_kind == "hardlink":
        source.write_bytes(b"private input must not be disclosed")
        os.link(source, tmp_path / "other-source.txt")
    elif source_kind == "oversized":
        source.write_bytes(b"x" * 262_145)
    else:
        source.write_bytes(b"private input\xff")
    before = source.read_bytes() if source.is_file() else None
    result = main(args + ["--mission-id", "mission://x", "--work-item-ref", "work-item://x",
                         "--artifact-ref", "artifact://x", "--resource-ref", "text:notes/a.txt",
                         "--desired-file", str(source)])
    captured = capsys.readouterr()
    assert result == 3
    assert json.loads(captured.err)["error_code"] == "physical_operation_refused"
    assert "private input" not in captured.err and str(source) not in captured.err
    assert not (tmp_path / "runtime").exists()
    assert list((tmp_path / "notes").iterdir()) == []
    if before is not None:
        assert source.read_bytes() == before


def test_redirected_desired_file_ancestor_is_refused_without_runtime(tmp_path, capsys):
    args = command(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    source = outside / "desired.txt"
    source.write_text("private source", encoding="utf-8")
    redirect = tmp_path / "redirect"
    try:
        redirect.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS requires permission for real symlink fixture")
    assert main(args + ["--mission-id", "mission://x", "--work-item-ref", "work-item://x",
                        "--artifact-ref", "artifact://x", "--resource-ref", "text:notes/a.txt",
                        "--desired-file", str(redirect / "desired.txt")]) == 3
    assert "private source" not in capsys.readouterr().err
    assert not (tmp_path / "runtime").exists()
    assert source.read_text() == "private source"


@pytest.mark.skipif(sys.platform != "linux", reason="actual Linux special-file refusal")
def test_fifo_desired_input_is_refused_without_blocking_or_runtime(tmp_path, capsys):
    args = command(tmp_path)
    fifo = tmp_path / "source.fifo"
    os.mkfifo(fifo)
    assert main(args + ["--mission-id", "mission://x", "--work-item-ref", "work-item://x",
                        "--artifact-ref", "artifact://x", "--resource-ref", "text:notes/a.txt",
                        "--desired-file", str(fifo)]) == 3
    assert json.loads(capsys.readouterr().err)["error_code"] == "physical_operation_refused"
    assert not (tmp_path / "runtime").exists()
