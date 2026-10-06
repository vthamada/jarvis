from json import loads

from tools import operational_artifacts
from tools.operational_artifacts import (
    create_baseline_snapshot,
    create_containment_drill,
    read_baseline_snapshot,
    write_baseline_snapshot,
    write_containment_drill,
)


def test_git_identity_is_explicitly_unknown_without_git_executable(monkeypatch) -> None:
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("private environment diagnostic")

    monkeypatch.setattr(operational_artifacts, "run", unavailable)
    assert operational_artifacts.git_sha() == "unknown"


def test_operational_artifacts_write_and_read_baseline_snapshot() -> None:
    snapshot = create_baseline_snapshot(
        profile="development",
        backend="sqlite",
        checks_passed=["pytest", "ruff"],
        operational_decision="go_conditional_for_controlled_production",
        pilot_status="healthy",
    )

    json_path, md_path = write_baseline_snapshot(snapshot)
    loaded = read_baseline_snapshot("development")

    assert json_path.exists()
    assert md_path.exists()
    assert loaded is not None
    assert loaded.operational_decision == snapshot.operational_decision
    assert loads(json_path.read_text(encoding="utf-8"))["backend"] == "sqlite"


def test_operational_artifacts_write_containment_drill() -> None:
    snapshot = create_baseline_snapshot(
        profile="controlled",
        backend="postgresql",
        checks_passed=["validate_baseline", "go_live_internal_checklist"],
        operational_decision="go_conditional_for_controlled_production",
        pilot_status="healthy",
    )
    drill = create_containment_drill(
        snapshot=snapshot,
        trigger_reason="go_live_internal_containment_drill",
    )

    json_path, md_path = write_containment_drill(drill)

    assert json_path.exists()
    assert md_path.exists()
    assert drill.rollback_target == snapshot.git_sha
