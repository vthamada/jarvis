"""Strict product parsing, independent grounding and fail-closed runner boundaries."""

import json
from dataclasses import FrozenInstanceError, asdict, replace

import pytest

from evals.operator_tasks import (
    CORPUS_DIGEST,
    TASKS,
    History,
    OperatorTaskRunner,
    Registration,
    decode_product,
    score_product,
)
from evals.operator_tasks.fixture_port import FixtureTaskPort
from evals.operator_tasks.runner import Binding, ExecutionRequest, ExecutionResult


def request(case=0):
    task = TASKS[case]
    history = History("subject", "previous", "current", "receipt-v2", "correction-rev2")
    return ExecutionRequest(
        Binding(
            "run", "request", task.case_id, task.version, task.digest, "rev", "subject", "current"
        ),
        task.brief,
        task.sources,
        30.0,
        history if case == 2 else None,
    )


def envelope(case=0):
    return json.loads(FixtureTaskPort().execute(request(case)).payload)


def runner(port=None, **kwargs):
    return OperatorTaskRunner(
        Registration(port or FixtureTaskPort(), "fixture", "rev", "subject"), **kwargs
    )


def test_corpus_is_versioned_frozen_and_expected_metadata_not_in_request():
    assert len(TASKS) == 3
    assert len({task.digest for task in TASKS}) == 3
    assert all(task.version == "operator-tasks-v1" for task in TASKS)
    assert CORPUS_DIGEST == "c70a17581da807f404e92b518dd3393a8b618a5ee20d694f07ac394e5261ed46"
    assert not hasattr(request(), "expected")
    with pytest.raises(FrozenInstanceError):
        TASKS[0].brief = "candidate-selected grading"


@pytest.mark.parametrize(
    "summary", ["A concise corrected draft.", "Proposta revista para análise."]
)
def test_report_accepts_different_prose_and_span_extent(summary):
    raw = envelope()
    raw["product"]["summary"] = summary
    for citation in raw["product"]["citations"]:
        citation["start"] = 0
        citation["end"] = len(TASKS[0].sources[-1].text)
    _, product = decode_product(json.dumps(raw).encode())
    assert score_product(TASKS[0], product).success


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["facts"].update(quantity=40),
        lambda p: p.update(total=780),
        lambda p: p.update(draft=False),
        lambda p: p["citations"][0].update(source_ref="purchase-rev1"),
        lambda p: p["citations"][0].update(end=900),
        lambda p: p["citations"].append(p["citations"][0]),
        lambda p: p["citations"].pop(),
    ],
)
def test_factual_arithmetic_authority_or_grounding_errors_fail(mutation):
    raw = envelope()
    mutation(raw["product"])
    _, product = decode_product(json.dumps(raw).encode())
    assert not score_product(TASKS[0], product).success


@pytest.mark.parametrize(
    "csv_text",
    [
        "item,quantity,unit_cost,total\nkits,30,18,540\nshipping,1,60,60\n",
        "item,quantity,unit_cost,total\r\nshipping,1,60,60\r\nkits,30,18,540\r\n",
    ],
)
def test_csv_evaluates_rows_not_identical_text(csv_text):
    raw = envelope(1)
    raw["product"]["csv_text"] = csv_text
    _, product = decode_product(json.dumps(raw).encode())
    assert score_product(TASKS[1], product).success


@pytest.mark.parametrize(
    "changes",
    [
        {"filename": "../proposal.csv"},
        {"media_type": "application/octet-stream"},
        {"csv_text": "item,quantity,unit_cost,total\nkits,30,18,540\nkits,30,18,540\n"},
        {"csv_text": "item,quantity,unit_cost,total\nkits,30,18,541\nshipping,1,60,60\n"},
        {"csv_text": "item,quantity,unit_cost,total\nkits,30,18,=30*18\nshipping,1,60,60\n"},
        {"csv_text": "item,quantity,unit_cost,total\nkits,30,18,540,hidden\nshipping,1,60,60\n"},
    ],
)
def test_unsafe_or_unreviewable_artifact_is_not_success(changes):
    raw = envelope(1)
    raw["product"].update(changes)
    _, product = decode_product(json.dumps(raw).encode())
    assert "reviewable_csv" in score_product(TASKS[1], product).failed


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(score=1),
        lambda r: r.update(evaluator="candidate-selected"),
        lambda r: r.update(status="incomplete"),
        lambda r: r["product"].update(total=True),
        lambda r: r["product"]["facts"].update(quantity=True),
        lambda r: r["product"]["citations"][0].update(start=True),
        lambda r: r["product"].update(summary="\x00private"),
        lambda r: r["product"].update(summary="x" * 2049),
        lambda r: r["product"].update(kind=[]),
        lambda r: r["product"].update(facts=[]),
        lambda r: r["product"].update(draft=1),
    ],
)
def test_candidate_cannot_choose_score_or_supply_unbounded_untyped_values(mutation):
    raw = envelope()
    mutation(raw)
    with pytest.raises(ValueError):
        decode_product(json.dumps(raw).encode())


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"x" * 16385,
        b"\xff",
        b"[]",
        b'{"status":1,"status":2}',
        b'{"binding":{},"status":"completed","product":{"kind":"report","total":NaN}}',
        (b"[" * 2000) + (b"]" * 2000),
    ],
)
def test_invalid_json_or_envelope_is_refused(payload):
    with pytest.raises(ValueError):
        decode_product(payload)


@pytest.mark.parametrize("field", list(asdict(request().binding)))
def test_every_response_binding_field_is_checked(field):
    class Tampered:
        def execute(self, req):
            result = FixtureTaskPort().execute(req)
            raw = json.loads(result.payload)
            raw["binding"][field] = "foreign"
            return replace(result, payload=json.dumps(raw).encode())

    measurement = runner(Tampered()).run(TASKS[0].case_id, run_id="run", session_ref="current")
    assert measurement.outcome == "stale_or_tampered_output"


@pytest.mark.parametrize(
    "changes",
    [
        {"subject_ref": "other"},
        {"current_session_ref": "other"},
        {"prior_session_ref": "current"},
        {"correction_source_ref": "purchase-rev1"},
        {"correction_receipt": ""},
    ],
)
def test_cross_subject_wrong_session_or_stale_history_never_executes(changes):
    class Never:
        def execute(self, req):
            pytest.fail("invalid history reached candidate")

    history = replace(request(2).history, **changes)
    with pytest.raises(ValueError, match="history_binding_refused"):
        runner(Never()).run(TASKS[2].case_id, run_id="run", session_ref="current", history=history)


@pytest.mark.parametrize(
    "result_change,expected",
    [
        ({"status": "incomplete"}, "incomplete"),
        ({"status": "needs_decision"}, "needs_decision"),
        ({"input_units": True}, "binding_or_metadata_refused"),
        ({"output_units": -1}, "binding_or_metadata_refused"),
        ({"payload": b"private-not-json"}, "invalid_output"),
    ],
)
def test_port_outcomes_and_usage_do_not_become_candidate_scores(result_change, expected):
    class Changed:
        def execute(self, req):
            return replace(FixtureTaskPort().execute(req), **result_change)

    measured = runner(Changed()).run(TASKS[0].case_id, run_id="run", session_ref="current")
    assert measured.outcome == expected
    assert not measured.success
    assert "private-not-json" not in json.dumps(measured.export())


def test_returning_same_case_previous_run_is_not_accepted():
    class Replay:
        last = None

        def execute(self, req):
            if self.last is None:
                self.last = FixtureTaskPort().execute(req)
            return self.last

    run = runner(Replay())
    assert run.run(TASKS[0].case_id, run_id="run", session_ref="current").success
    assert run.run(TASKS[0].case_id, run_id="run", session_ref="current").outcome == (
        "binding_or_metadata_refused"
    )


def test_port_failure_content_is_not_exported():
    class Broken:
        def execute(self, req):
            raise RuntimeError("private path / subject / prompt")

    measured = runner(Broken()).run(TASKS[0].case_id, run_id="run", session_ref="current")
    assert measured.outcome == "port_error"
    assert "private" not in json.dumps(measured.export())


def test_late_completion_is_rejected_and_latency_measured():
    times = iter([0.0, 30.0])
    measured = runner(clock=lambda: next(times)).run(
        TASKS[0].case_id, run_id="run", session_ref="current"
    )
    assert measured.outcome == "deadline_exceeded" and measured.elapsed_ms == 30000


@pytest.mark.parametrize("timeout", [True, float("nan"), 0, 121])
def test_invalid_deadline_is_refused(timeout):
    with pytest.raises(ValueError, match="invalid_run"):
        runner().run(TASKS[0].case_id, run_id="run", session_ref="current", timeout_seconds=timeout)


def test_candidate_claimed_continuity_requires_separate_port_history_observation():
    class NoHistory:
        def execute(self, req):
            return replace(FixtureTaskPort().execute(req), history_digest="")

    measured = runner(NoHistory()).run(
        TASKS[2].case_id, run_id="run", session_ref="current", history=request(2).history
    )
    assert measured.outcome == "needs_rework"
    assert measured.failed_criteria == ("correction_continuity",)


def test_output_binding_and_port_binding_are_separate_checks():
    class WrongPort:
        def execute(self, req):
            return ExecutionResult(replace(req.binding, subject_ref="other"), "completed", b"{}")

    assert (
        runner(WrongPort()).run(TASKS[0].case_id, run_id="run", session_ref="current").outcome
        == "binding_or_metadata_refused"
    )


def test_known_fixture_cannot_be_mislabeled_as_real_model():
    with pytest.raises(ValueError, match="invalid_registration"):
        OperatorTaskRunner(Registration(FixtureTaskPort(), "model_real", "rev", "subject"))
