"""Real Core evidence is deliberately separate from the evaluator's fixture scores."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console import empirical_pilot
from evolution.empirical_runner import CORPUS_DIGEST, CORPUS_VERSION, EvaluationRequest


def request() -> EvaluationRequest:
    prompt = "Return only the integer result of 17 + 25."
    digest = hashlib.sha256(json.dumps(prompt, separators=(",", ":")).encode()).hexdigest()
    return EvaluationRequest(
        "a" * 64,
        empirical_pilot.RUN_ID,
        "baseline",
        empirical_pilot.CONTROL_REVISION,
        "train-add",
        "repeat",
        0,
        CORPUS_VERSION,
        CORPUS_DIGEST,
        digest,
        prompt,
        30.0,
        "core_local",
    )


def test_real_pipeline_executes_twelve_turns_in_two_isolated_core_stores(tmp_path, monkeypatch):
    cores, inputs, final_texts = [], [], []
    build = empirical_pilot._isolated_core
    compose = SynthesisEngine.compose_result

    def tracked_build(runtime):
        core = build(runtime)
        original = core.handle_input

        def handle(contract):
            inputs.append(contract)
            response = original(contract)
            turns = core.memory_service.repository.fetch_recent_turns(contract.session_id, 20)
            assert turns[-1].request_content == contract.content
            assert turns[-1].response_text == response.response_text
            return response

        core.handle_input = handle
        cores.append((core, runtime))
        return core

    def tracked_compose(self, synthesis_input):
        result = compose(self, synthesis_input)
        final_texts.append(result.response_text)
        return result

    monkeypatch.setattr(empirical_pilot, "_isolated_core", tracked_build)
    monkeypatch.setattr(SynthesisEngine, "compose_result", tracked_compose)
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.chdir(tmp_path)
    result = empirical_pilot.run_empirical_core_pilot()
    assert result["report"]["status"] == "completed"
    assert result["report"]["expected_measurements"] == 12
    assert result["report"]["completed_measurements"] == 12
    assert result["report"]["promotion_allowed"] is False
    assert result["claim"] == "pipeline_only_no_improvement_claim"
    assert result["external_model_used"] is False
    assert result["runtime_capability_promoted"] is False
    assert result["production_memory_opened"] is False
    assert len(cores) == 2 and cores[0][0] is not cores[1][0]
    assert cores[0][1] != cores[1][1]
    assert len(inputs) == len(final_texts) == 12
    assert all(not runtime.exists() for _, runtime in cores)
    assert not list(tmp_path.iterdir())
    assert {contract.session_id for contract in inputs} == {
        "session://empirical-core-control-baseline",
        "session://empirical-core-control-candidate",
    }
    assert all(contract.max_autonomy_level == "assist_only" for contract in inputs)
    assert all(contract.surface_capability_scope == [] for contract in inputs)
    assert all(contract.adapter_action_request is None for contract in inputs)
    assert all(contract.action_confirmation_receipt_id is None for contract in inputs)
    assert all(arm["core_turn_count"] == 6 for arm in result["arms"])
    assert all(arm["canonical_memory_record_count"] == 6 for arm in result["arms"])
    assert all(arm["operation_dispatched"] is False for arm in result["arms"])
    assert all(arm["core_event_count"] > 0 for arm in result["arms"])
    assert all(sum(arm["governance_decisions"].values()) == 6 for arm in result["arms"])
    exported = json.dumps(result)
    assert "Return only" not in exported
    assert all(text not in exported for text in final_texts)
    assert all(arm["evidence_mode"] == "core_local" for arm in result["arms"])


@pytest.mark.parametrize(
    "change",
    [
        {"evidence_mode": "fixture"},
        {"arm_id": "candidate"},
        {"arm_revision": "promoted"},
        {"run_id": "foreign"},
        {"deadline": -1},
        {"deadline": float("nan")},
        {"request_id": "bad"},
        {"prompt": ""},
        {"prompt": "\x00"},
        {"corpus_digest": "foreign"},
        {"input_digest": "foreign"},
    ],
)
def test_invalid_evaluation_request_never_enters_core(change):
    class NeverCore:
        def handle_input(self, contract):
            pytest.fail("invalid empirical request reached Core")

    port = empirical_pilot.IsolatedEmpiricalCorePort(NeverCore(), "baseline", clock=lambda: 0.0)
    with pytest.raises(ValueError):
        port.evaluate(replace(request(), **change))
    assert port.metadata()["core_turn_count"] == 0


def test_real_core_failure_yields_invalid_report_and_cleans_runtime(tmp_path, monkeypatch):
    built = []
    build = empirical_pilot._isolated_core

    def failing_build(runtime):
        core = build(runtime)

        def fail(contract):
            raise RuntimeError("private failure must not be exported")

        if runtime.name == "candidate":
            core.handle_input = fail
        built.append(runtime)
        return core

    monkeypatch.setattr(empirical_pilot, "_isolated_core", failing_build)
    monkeypatch.chdir(tmp_path)
    result = empirical_pilot.run_empirical_core_pilot()
    assert result["report"]["status"] == "invalid"
    assert result["report"]["completed_measurements"] == 1
    assert result["report"]["promotion_allowed"] is False
    assert "private failure" not in json.dumps(result)
    assert all(not runtime.exists() for runtime in built)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("change", ["request", "session", "dispatch"])
def test_core_final_binding_or_dispatch_is_refused(tmp_path, change):
    core = empirical_pilot._isolated_core(tmp_path / "runtime")
    handle = core.handle_input

    def tampered(contract):
        response = handle(contract)
        if change == "request":
            response.request_id = "foreign"
        elif change == "session":
            response.session_id = "foreign"
        else:
            response.operation_dispatch = object()
        return response

    core.handle_input = tampered
    port = empirical_pilot.IsolatedEmpiricalCorePort(core, "baseline", clock=lambda: 0.0)
    with pytest.raises(ValueError, match="empirical_core_final_refused"):
        port.evaluate(request())
    assert port.metadata()["core_turn_count"] == 0
