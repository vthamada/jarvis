"""A shared inference ceiling is enforced before either comparison arm can call."""

from dataclasses import replace
from threading import Event

import pytest

from evals.operator_tasks.inference_guard import CampaignInferenceGuard
from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult


class Port:
    provider_id = "fixture"
    evidence_mode = "fixture"

    def __init__(self, status="completed"):
        self.calls = 0
        self.status = status

    def infer(self, request, *, cancellation=None):
        self.calls += 1
        return InferenceResult(
            request.request_id, request.model, self.provider_id, self.status,
            text='{"data":"public"}' if self.status == "completed" else "",
            error_code=None if self.status == "completed" else "transport_error",
            evidence_mode=self.evidence_mode,
        )


def request():
    return InferenceRequest("request-one", "gpt-6.1-sol", (InferenceMessage("user", "Public"),))


def guard(port, **changes):
    options = dict(model="gpt-6.1-sol", provider_id="fixture", evidence_mode="fixture",
                   authorized=True, max_calls=2)
    options.update(changes)
    return CampaignInferenceGuard(lambda: port, **options)


def test_construction_and_missing_consent_never_open_provider():
    called = []
    control = CampaignInferenceGuard(
        lambda: called.append(True), model="gpt-6.1-sol", provider_id="fixture",
        evidence_mode="fixture", max_calls=2,
    )
    assert not called and control.snapshot()["attempted_model_calls"] == 0
    with pytest.raises(ValueError):
        control.infer(request())
    assert not called and control.snapshot()["attempted_model_calls"] == 0


def test_shared_quota_prevents_third_inference_without_changing_selection():
    port = Port()
    control = guard(port)
    assert control.infer(request()).status == "completed"
    assert control.infer(replace(request(), request_id="request-two")).status == "completed"
    with pytest.raises(ValueError):
        control.infer(replace(request(), request_id="request-three"))
    state = control.snapshot()
    assert state["attempted_model_calls"] == port.calls == 2
    assert state["input_tokens"] is None and state["output_tokens"] is None


def test_first_transport_failure_stops_other_arm_and_never_retries():
    port = Port("failed")
    control = guard(port)
    assert control.infer(request()).status == "failed"
    with pytest.raises(ValueError):
        control.infer(replace(request(), request_id="other-arm"))
    assert control.stopped and port.calls == 1
    assert control.snapshot()["last_error_code"] == "transport_error"


def test_provider_exception_is_content_free_and_sticky():
    def private_failure():
        raise OSError("PRIVATE_EXCEPTION_SENTINEL")

    control = CampaignInferenceGuard(
        private_failure, model="gpt-6.1-sol", provider_id="fixture",
        evidence_mode="fixture", authorized=True, max_calls=2,
    )
    with pytest.raises(ValueError) as error:
        control.infer(request())
    assert str(error.value) == "campaign_inference_refused"
    assert error.value.__context__ is None
    assert control.stopped and control.snapshot()["attempted_model_calls"] == 1


@pytest.mark.parametrize("change", [{"model": "other"}, {"provider_id": "other"},
                                    {"evidence_mode": "live"}])
def test_result_selection_drift_stops_without_publishing_text(change):
    class Drifting(Port):
        def infer(self, selected, **_options):
            return replace(super().infer(selected), **change)

    control = guard(Drifting())
    with pytest.raises(ValueError):
        control.infer(request())
    assert control.stopped


def test_cancelled_before_call_does_not_consume_quota():
    token, port = Event(), Port()
    token.set()
    control = guard(port, cancellation=token)
    with pytest.raises(ValueError):
        control.infer(request())
    assert not port.calls and control.snapshot()["attempted_model_calls"] == 0


def test_global_cancellation_reaches_transport_when_local_token_is_absent():
    token = Event()

    class Cooperative(Port):
        def infer(self, selected, *, cancellation=None):
            assert cancellation is token
            return super().infer(selected)

    assert guard(Cooperative(), cancellation=token).infer(request()).status == "completed"


def test_reentrant_call_cannot_publish_outer_result_after_campaign_stopped():
    class Reentrant(Port):
        def infer(self, selected, **_options):
            with pytest.raises(ValueError):
                control.infer(replace(request(), request_id="recursive"))
            return super().infer(selected)

    port = Reentrant()
    control = guard(port)
    with pytest.raises(ValueError):
        control.infer(request())
    assert control.stopped and port.calls == 1
    assert control.snapshot()["attempted_model_calls"] == 1
    assert control.snapshot()["completed_model_calls"] == 0


def test_late_result_is_discarded_and_stops_campaign():
    clock = [1.0]

    class Late(Port):
        def infer(self, selected, **_options):
            clock[0] += 31
            return super().infer(selected)

    control = guard(Late(), clock=lambda: clock[0])
    with pytest.raises(ValueError):
        control.infer(request())
    assert control.stopped


def test_request_mutation_is_refused_after_callback():
    class Mutating(Port):
        def infer(self, selected, **_options):
            result = super().infer(selected)
            object.__setattr__(selected, "model", "other")
            return result

    control = guard(Mutating())
    with pytest.raises(ValueError):
        control.infer(request())
    assert control.stopped


@pytest.mark.parametrize("maximum", [0, 11, True, 1.5])
def test_pilot_ceiling_cannot_be_silently_expanded(maximum):
    with pytest.raises(ValueError):
        guard(Port(), max_calls=maximum)
