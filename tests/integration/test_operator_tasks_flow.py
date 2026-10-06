"""Product controls and real sovereign Core failures, not model-intelligence evidence."""

import json
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.operator_tasks import TASKS, History, OperatorTaskRunner, Registration, core_pilot
from evals.operator_tasks.fixture_port import FixtureTaskPort
from evals.operator_tasks.runner import Binding, ExecutionRequest


def test_three_public_task_products_execute_and_export_only_metrics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = OperatorTaskRunner(Registration(FixtureTaskPort(), "fixture", "fixture-v1", "subject"))
    measures = []
    for task in TASKS:
        history = (
            History("subject", "first", "second", "correction-receipt", "correction-rev2")
            if task.product_kind == "resumption"
            else None
        )
        measures.append(
            runner.run(
                task.case_id, run_id="private-run-id", session_ref="second", history=history
            ).export()
        )
    assert all(item["success"] for item in measures)
    assert all(item["evidence_mode"] == "fixture" for item in measures)
    assert all(item["promotion_allowed"] is False for item in measures)
    assert all(item["improvement_claim"] is False for item in measures)
    assert all(item["requires_human_review"] is True for item in measures)
    assert all(item["input_units"] is None and item["output_units"] is None for item in measures)
    exported = json.dumps(measures)
    for content in ("private-run-id", "proposal.csv", "Correction revision", "Thursday", "receipt"):
        assert content not in exported
    assert not list(tmp_path.iterdir())


def test_latest_correction_changes_product_score_in_full_execution():
    class Stale:
        def execute(self, request):
            result = FixtureTaskPort().execute(request)
            raw = json.loads(result.payload)
            raw["product"]["facts"]["quantity"] = 40
            raw["product"]["facts"]["delivery_day"] = "Wednesday"
            raw["product"]["total"] = 780
            return replace(result, payload=json.dumps(raw).encode())

    runner = OperatorTaskRunner(Registration(Stale(), "fixture", "stale-v1", "subject"))
    result = runner.run(
        "corrected-resumption",
        run_id="run",
        session_ref="second",
        history=History("subject", "first", "second", "correction", "correction-rev2"),
    )
    assert not result.success and result.rework_required
    assert set(result.failed_criteria) == {"latest_facts", "arithmetic"}


def test_real_core_canonical_path_is_measured_without_fabricated_product_success(
    tmp_path, monkeypatch
):
    from apps.jarvis_console import voice_pilot

    built = []
    build = voice_pilot._isolated_core

    def track(runtime):
        assert runtime.parent == Path(core_pilot.tempfile.gettempdir()).resolve()
        built.append(runtime)
        return build(runtime)

    monkeypatch.setattr(voice_pilot, "_isolated_core", track)
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.chdir(tmp_path)
    report = core_pilot.run_core_operator_tasks(authorized=True)
    assert len(built) == 3 and all(not runtime.exists() for runtime in built)
    assert not list(tmp_path.iterdir())
    assert report["evidence_mode"] == "core_local"
    assert report["core_turn_count"] == report["canonical_final_count"] == 5
    assert report["core_event_count"] > 0
    assert sum(report["governance_decisions"].values()) == 5
    assert all(not item["success"] for item in report["measurements"])
    assert {item["outcome"] for item in report["measurements"]} <= {
        "needs_decision",
        "invalid_output",
    }
    for flag in (
        "operator_authenticated",
        "external_model_used",
        "production_memory_opened",
        "operation_dispatched",
        "promotion_allowed",
        "improvement_claim",
        "useful_continuity_demonstrated",
    ):
        assert report[flag] is False
    for source in TASKS[0].sources:
        assert source.text not in json.dumps(report)


def test_core_pilot_requires_opt_in_before_import_or_runtime(monkeypatch):
    monkeypatch.setattr(core_pilot, "TemporaryDirectory", lambda **_: pytest.fail("runtime opened"))
    with pytest.raises(ValueError, match="opt_in_required"):
        core_pilot.run_core_operator_tasks()


def test_workspace_temp_base_refused_before_core(monkeypatch):
    workspace = Path(core_pilot.__file__).resolve().parents[2]
    monkeypatch.setattr(core_pilot.tempfile, "gettempdir", lambda: str(workspace / "temp"))
    monkeypatch.setattr(core_pilot, "TemporaryDirectory", lambda **_: pytest.fail("runtime opened"))
    with pytest.raises(ValueError, match="temp_base_refused"):
        core_pilot.run_core_operator_tasks(authorized=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("subject_ref", "other"),
        ("revision", "foreign"),
        ("task_version", "old-version"),
        ("task_digest", "forged"),
        ("request_id", ""),
        ("session_ref", ""),
    ],
)
def test_direct_core_port_refuses_binding_drift_before_core(field, value):
    task = TASKS[0]
    binding = Binding(
        "run",
        "request",
        task.case_id,
        task.version,
        task.digest,
        "core-control-v1",
        "operator-task-subject",
        "session",
    )
    request = ExecutionRequest(
        replace(binding, **{field: value}),
        task.brief,
        task.sources,
        time.monotonic() + 30,
        None,
    )
    core = SimpleNamespace(handle_input=lambda _: pytest.fail("drift reached Core"))
    with pytest.raises(ValueError, match="core_binding_refused"):
        core_pilot.IsolatedOperatorCorePort(core).execute(request)
