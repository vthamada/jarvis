"""Canonical SQLite readback, no repair and no inferred execution receipts."""

import json
import sqlite3
import time
from dataclasses import asdict, replace
from threading import Event

import pytest

from apps.jarvis_console.voice_pilot import _isolated_core
from evals.operator_tasks.canonical_mission_port import CanonicalMissionTaskPort
from evals.operator_tasks.corpus import Source
from evals.operator_tasks.runner import Binding, ExecutionRequest
from shared.model_inference import InferenceResult


def request():
    return ExecutionRequest(
        Binding("trial", "request-one", "example", "operator-missions-v1", "d" * 64,
                "revision-one", "mission-subject", "mission-session"),
        "Compare documentation and observability pilot reports.",
        (Source("public-report", "Documentation is current; observability is pending."),),
        time.monotonic() + 90, None,
    )


def test_missing_opt_in_never_constructs_core_or_writes_runtime(tmp_path):
    control = CanonicalMissionTaskPort(
        tmp_path, core_factory=lambda _: pytest.fail("unapproved Core construction"),
    )
    with pytest.raises(ValueError):
        control.execute(request())
    assert not tuple(tmp_path.iterdir())


def test_native_output_is_exact_stored_final_not_rewritten_as_json(tmp_path):
    control = CanonicalMissionTaskPort(tmp_path, authorized=True)
    selected = request()
    result = control.execute(selected)
    assert result.status == "completed" and result.binding == selected.binding
    with sqlite3.connect(next(tmp_path.iterdir()) / "memory.db") as db:
        rows = db.execute("SELECT response_text FROM interaction_turns").fetchall()
    assert len(rows) == 1 and result.payload == rows[0][0].encode("utf-8")
    assert control.snapshot()["canonical_finals_verified"] == 1
    assert control.snapshot()["answer_repair"] is False


def test_repeated_binding_does_not_reuse_runtime_or_enter_core_again(tmp_path):
    control = CanonicalMissionTaskPort(tmp_path, authorized=True)
    selected = request()
    control.execute(selected)
    with pytest.raises(FileExistsError):
        control.execute(selected)
    assert control.snapshot()["core_turns"] == 1


def test_event_drift_prevents_publishing_an_unverified_canonical_answer(tmp_path):
    def corrupting_factory(runtime):
        core = _isolated_core(runtime)
        handle = core.handle_input

        def corrupt(contract):
            response = handle(contract)
            with sqlite3.connect(runtime / "events.db") as db:
                db.execute("DELETE FROM internal_events WHERE event_name='memory_recorded'")
            return response

        core.handle_input = corrupt
        return core

    control = CanonicalMissionTaskPort(tmp_path, authorized=True, core_factory=corrupting_factory)
    result = control.execute(request())
    assert result.status == "error" and result.payload == b""
    assert control.snapshot()["canonical_finals_verified"] == 0


def test_model_product_is_projected_only_from_accepted_persisted_analysis(tmp_path):
    selected = request()
    product = json.dumps({"binding": asdict(selected.binding), "status": "completed",
                          "product": {"draft": True, "facts": {"status": "pending"}}})

    class Model:
        provider_id = "fixture"
        evidence_mode = "fixture"

        def infer(self, query, **_options):
            return InferenceResult(
                query.request_id, query.model, "fixture", "completed",
                text=json.dumps({"analysis": product, "assumptions": [], "limitations": [],
                                 "citations": []}), evidence_mode="fixture",
            )

    control = CanonicalMissionTaskPort(
        tmp_path, authorized=True, inference_port=Model(), model="test-model",
    )
    result = control.execute(selected)
    assert result.status == "completed" and result.payload == product.encode("utf-8")
    assert control.snapshot()["canonical_finals_verified"] == 1
    assert control.snapshot()["projection"] == "canonical_unverified_analysis"
    with sqlite3.connect(next(tmp_path.iterdir()) / "memory.db") as db:
        final = db.execute("SELECT response_text FROM interaction_turns").fetchone()[0]
    assert "Analysis: " in final and final != product


def test_rejected_generation_never_becomes_a_fabricated_product(tmp_path):
    class Model:
        def infer(self, query, **_options):
            return InferenceResult(query.request_id, query.model, "fixture", "completed",
                                   text="INVALID_CANDIDATE_SENTINEL", evidence_mode="fixture")

    control = CanonicalMissionTaskPort(
        tmp_path, authorized=True, inference_port=Model(), model="test-model",
    )
    result = control.execute(request())
    assert result.status == "incomplete" and result.payload == b""
    assert control.snapshot()["last_outcome"] == "generative_not_accepted"


def test_keyboard_interrupt_propagates_instead_of_starting_later_missions(tmp_path):
    def factory(runtime):
        core = _isolated_core(runtime)

        def interrupted(_contract):
            raise KeyboardInterrupt()

        core.handle_input = interrupted
        return core

    control = CanonicalMissionTaskPort(tmp_path, authorized=True, core_factory=factory)
    with pytest.raises(KeyboardInterrupt):
        control.execute(request())
    assert control.snapshot()["core_turns"] == 0


@pytest.mark.parametrize("stop", ["cancelled", "deadline"])
def test_revocation_during_factory_never_dispatches_core(tmp_path, stop):
    clock, token, calls = [0.0], Event(), []

    def factory(runtime):
        core = _isolated_core(runtime)
        core.handle_input = lambda _contract: calls.append(True)
        if stop == "cancelled":
            token.set()
        else:
            clock[0] = 31.0
        return core

    control = CanonicalMissionTaskPort(
        tmp_path, authorized=True, core_factory=factory, clock=lambda: clock[0],
        cancellation=token,
    )
    result = control.execute(replace(request(), deadline=30.0))
    assert not calls
    assert result.status == "incomplete" and result.payload == b""
    assert control.snapshot()["core_turns"] == 0
