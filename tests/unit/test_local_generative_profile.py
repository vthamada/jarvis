"""Explicit lazy configuration, budget, cancellation and composition fences."""

from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest

from apps.jarvis_api.generative_profile import GenerativeProfile
from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult

PROFILE = "profile-" + "a" * 64
MODEL = "test-model"


def options(tmp_path, **overrides):
    return dict(authorized=True, model=MODEL, credential_dir=tmp_path,
                profile_ref=PROFILE, **overrides)


def request(**overrides):
    values = dict(request_id="test-request", model=MODEL,
                  messages=(InferenceMessage("user", "Private request text"),),
                  timeout_seconds=20.0, max_output_chars=512)
    values.update(overrides)
    return InferenceRequest(**values)


class Port:
    provider_id = "responses_plan"
    evidence_mode = "injected_transport"

    def __init__(self, hook=None):
        self.calls, self.hook = [], hook

    def infer(self, req, *, cancellation=None):
        self.calls.append((req, cancellation))
        result = InferenceResult(req.request_id, req.model, self.provider_id,
                                 "completed", text="bounded output",
                                 evidence_mode=self.evidence_mode)
        return self.hook(req, cancellation, result) if self.hook else result


@pytest.mark.parametrize("field,value", [
    ("authorized", False), ("authorized", 1), ("authorized", None),
    ("model", ""), ("model", "x" * 161), ("model", "model id"),
    ("model", "á"), ("model", "x\n"), ("model", ["test-model"]),
    ("profile_ref", "profile-" + "A" * 64), ("profile_ref", "profile-" + "a" * 63),
    ("profile_ref", "a" * 64), ("profile_ref", None),
    ("credential_dir", "C:/credentials"), ("credential_dir", Path("relative")),
    ("timeout_seconds", 0), ("timeout_seconds", -1), ("timeout_seconds", 20.001),
    ("timeout_seconds", float("nan")), ("timeout_seconds", float("inf")),
    ("timeout_seconds", True), ("timeout_seconds", "20"),
    ("port_factory", 7), ("clock", None),
])
def test_constructor_refuses_invalid_options_without_factory(tmp_path, field, value):
    values = options(tmp_path)
    values[field] = value
    with pytest.raises(ValueError, match="^invalid_local_generative_profile$"):
        GenerativeProfile(**values)


def test_authorization_defaults_off(tmp_path):
    values = options(tmp_path)
    del values["authorized"]
    with pytest.raises(ValueError, match="^invalid_local_generative_profile$"):
        GenerativeProfile(**values)


def test_constructor_and_port_are_inert_and_repr_is_opaque(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("inert configuration performed IO or called clock/factory")
    for operation in ("exists", "open", "stat", "mkdir", "read_text"):
        monkeypatch.setattr(Path, operation, forbidden)
    profile = GenerativeProfile(**options(tmp_path, port_factory=forbidden, clock=forbidden))
    port = profile.port_for(Event())
    assert profile.model == MODEL and profile.timeout_seconds == 20
    assert profile.provider_id == port.provider_id == "responses_plan"
    assert profile.evidence_mode == port.evidence_mode == "injected_transport"
    assert "lazy=True" in repr(profile) and "lazy=True" in repr(port)
    for value in (str(tmp_path), PROFILE, MODEL):
        assert value not in repr(profile) + repr(port)


def test_default_factory_is_lazy_not_called_before_infer(tmp_path, monkeypatch):
    from apps.jarvis_console import generative_analysis_cli
    called = []
    monkeypatch.setattr(generative_analysis_cli, "_session_factory",
                        lambda *args: called.append(args))
    profile = GenerativeProfile(**options(tmp_path))
    token = Event()
    port = profile.port_for(token)
    assert not called and profile.evidence_mode == port.evidence_mode == "live"
    token.set()
    result = port.infer(request())
    assert not called and result.status == "cancelled" and not result.text


def test_factory_only_once_inside_infer(tmp_path):
    backend, calls = Port(), []
    def factory(*args):
        calls.append(args)
        return backend
    profile = GenerativeProfile(**options(tmp_path, port_factory=factory))
    cancellation = Event()
    port = profile.port_for(cancellation)
    assert not calls
    result = port.infer(request())
    assert calls == [(tmp_path, PROFILE, MODEL)] and len(backend.calls) == 1
    assert backend.calls[0][1] is cancellation
    assert result.status == "completed" and result.evidence_mode == "injected_transport"
    assert "Private request text" not in repr(port) + repr(profile)


@pytest.mark.parametrize("cancellation", [None, False, "cancel", object()])
def test_port_requires_event(tmp_path, cancellation):
    profile = GenerativeProfile(**options(tmp_path))
    with pytest.raises(ValueError, match="^invalid_local_generative_profile$"):
        profile.port_for(cancellation)


def test_wrong_model_does_not_construct_factory(tmp_path):
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: pytest.fail()))
    result = profile.port_for(Event()).infer(request(model="other-model"))
    assert result.status == "failed" and result.error_code == "model_mismatch"
    assert result.text == "" and result.model == "other-model"


@pytest.mark.parametrize("field,value", [
    ("authorized", False), ("model", "other-model"), ("profile_ref", "profile-" + "b" * 64),
    ("credential_dir", Path("relative")), ("timeout_seconds", 21),
    ("factory", lambda *args: None), ("clock", lambda: 0), ("evidence_mode", "live"),
])
def test_configuration_forgery_before_infer_is_fenced(tmp_path, field, value):
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: pytest.fail()))
    port = profile.port_for(Event())
    object.__setattr__(profile._options, field, value)
    result = port.infer(request())
    assert result.error_code == "profile_changed" and not result.text
    with pytest.raises(ValueError, match="^invalid_local_generative_profile$"):
        profile.port_for(Event())


@pytest.mark.parametrize("stage", ["factory", "inference"])
def test_configuration_changed_during_work_is_fenced(tmp_path, stage):
    backend = Port()
    def mutate():
        object.__setattr__(profile._options, "model", "other-model")
    def factory(*args):
        if stage == "factory":
            mutate()
        return backend
    def infer_hook(req, cancellation, result):
        mutate()
        return result
    if stage == "inference":
        backend.hook = infer_hook
    profile = GenerativeProfile(**options(tmp_path, port_factory=factory))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "profile_changed" and not result.text
    assert len(backend.calls) == (1 if stage == "inference" else 0)


@pytest.mark.parametrize("field,value", [
    ("request_id", "other-request"), ("model", "other-model"),
    ("provider_id", "wrong-provider"), ("evidence_mode", "live"),
    ("text", "x" * 513), ("input_tokens", 1_000_000_001),
])
def test_result_binding_and_limits(tmp_path, field, value):
    backend = Port(lambda req, token, result: replace(result, **{field: value}))
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: backend))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "binding_mismatch" and not result.text
    assert result.evidence_mode == "injected_transport" and len(backend.calls) == 1


@pytest.mark.parametrize("field,value", [("provider_id", "other"), ("evidence_mode", "live")])
def test_port_binding_refused_before_infer(tmp_path, field, value):
    backend = Port()
    setattr(backend, field, value)
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: backend))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "binding_mismatch" and not backend.calls
    assert result.evidence_mode == "injected_transport"


@pytest.mark.parametrize("stage", ["before", "factory", "infer"])
@pytest.mark.parametrize("which", ["service", "consumer"])
def test_cancellation_at_each_boundary(tmp_path, stage, which):
    service, consumer = Event(), Event()
    selected = service if which == "service" else consumer
    backend = Port()
    def factory(*args):
        if stage == "factory":
            selected.set()
        return backend
    def hook(req, token, result):
        selected.set()
        assert token.is_set()
        return result
    if stage == "infer":
        backend.hook = hook
    if stage == "before":
        selected.set()
    profile = GenerativeProfile(**options(tmp_path, port_factory=factory))
    result = profile.port_for(service).infer(request(), cancellation=consumer)
    assert result.status == "cancelled" and result.error_code == "cancelled" and not result.text
    assert len(backend.calls) == (1 if stage == "infer" else 0)


@pytest.mark.parametrize("invalid", [False, "cancel", object()])
def test_invalid_consumer_cancellation(tmp_path, invalid):
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: pytest.fail()))
    result = profile.port_for(Event()).infer(request(), cancellation=invalid)
    assert result.error_code == "invalid_cancellation" and not result.text


@pytest.mark.parametrize("budget", [0.01, 5, 20])
def test_factory_time_is_subtracted_from_inference_budget(tmp_path, budget):
    current = [0.0]
    backend = Port()
    def factory(*args):
        current[0] += budget / 2
        return backend
    profile = GenerativeProfile(**options(tmp_path, timeout_seconds=budget,
                                         port_factory=factory, clock=lambda: current[0]))
    result = profile.port_for(Event()).infer(request(timeout_seconds=120))
    assert result.status == "completed"
    assert backend.calls[0][0].timeout_seconds == pytest.approx(budget / 2)


@pytest.mark.parametrize("stage", ["factory", "infer"])
def test_total_timeout_discards_late_content_and_never_retries(tmp_path, stage):
    current = [0.0]
    backend = Port()
    def factory(*args):
        if stage == "factory":
            current[0] = 20.0
        return backend
    def hook(req, token, result):
        current[0] = 20.0
        return result
    if stage == "infer":
        backend.hook = hook
    profile = GenerativeProfile(**options(tmp_path, port_factory=factory,
                                         clock=lambda: current[0]))
    result = profile.port_for(Event()).infer(request())
    assert result.status == "timed_out" and result.error_code == "timeout" and not result.text
    assert len(backend.calls) == (1 if stage == "infer" else 0)


@pytest.mark.parametrize("values", [
    [float("nan")], [True], [float("inf")], [1e308], [1, 0], [0, 0, -1],
])
def test_invalid_clock_values_and_rollback(tmp_path, values):
    clocks = iter(values)
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: Port(),
                                         clock=lambda: next(clocks)))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "invalid_clock" and not result.text


@pytest.mark.parametrize("stage", ["original", "forwarded", "message"])
def test_request_mutation_during_inference_is_fenced(tmp_path, stage):
    initial = request()
    def hook(req, token, result):
        if stage == "original":
            object.__setattr__(initial, "instructions", "changed")
        elif stage == "forwarded":
            object.__setattr__(req, "timeout_seconds", 120)
        else:
            object.__setattr__(req.messages[0], "content", "changed")
        return result
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: Port(hook)))
    result = profile.port_for(Event()).infer(initial)
    assert result.error_code == "request_changed" and not result.text


@pytest.mark.parametrize("mutation", ["type", "model", "message", "timeout"])
def test_invalid_and_forged_request_before_factory(tmp_path, mutation):
    initial = request()
    if mutation == "type":
        initial = object()
    elif mutation == "model":
        object.__setattr__(initial, "model", "bad model")
    elif mutation == "message":
        object.__setattr__(initial.messages[0], "content", "")
    else:
        object.__setattr__(initial, "timeout_seconds", float("nan"))
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: pytest.fail()))
    with pytest.raises(ValueError, match="^invalid_local_inference_request$"):
        profile.port_for(Event()).infer(initial)


@pytest.mark.parametrize("status", ["failed", "timed_out", "cancelled"])
def test_failed_result_is_opaque(tmp_path, status):
    backend = Port(lambda req, token, result: InferenceResult(
        req.request_id, req.model, "responses_plan", status,
        error_code="sensitive_provider_detail", evidence_mode="injected_transport"))
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: backend))
    result = profile.port_for(Event()).infer(request())
    assert result.status == status and not result.text
    assert result.error_code != "sensitive_provider_detail"


@pytest.mark.parametrize("stage", ["factory", "infer"])
def test_exception_text_is_not_retained_or_reflected(tmp_path, stage):
    backend = Port()
    def fail(*args, **kwargs):
        raise RuntimeError("secret token private content")
    if stage == "infer":
        backend.hook = fail
    profile = GenerativeProfile(**options(tmp_path, port_factory=(
        fail if stage == "factory" else lambda *args: backend)))
    port = profile.port_for(Event())
    result = port.infer(request())
    assert result.error_code == "inference_unavailable" and not result.text
    assert "secret" not in repr(result) + repr(port) + repr(profile)


def test_request_budget_smaller_than_profile_is_preserved(tmp_path):
    backend = Port()
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: backend,
                                         clock=lambda: 0))
    result = profile.port_for(Event()).infer(request(timeout_seconds=3))
    assert result.status == "completed" and backend.calls[0][0].timeout_seconds == 3


def test_default_factory_cannot_upgrade_injected_result_to_live(tmp_path, monkeypatch):
    from apps.jarvis_console import generative_analysis_cli
    backend = Port()
    backend.evidence_mode = "live"
    backend.hook = lambda req, token, result: replace(result, evidence_mode="injected_transport")
    monkeypatch.setattr(generative_analysis_cli, "_session_factory", lambda *args: backend)
    profile = GenerativeProfile(**options(tmp_path))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "binding_mismatch" and not result.text
    assert result.evidence_mode == "live"  # selected expectation, never accepted evidence


@pytest.mark.parametrize("mutation", ["provider_id", "evidence_mode"])
def test_backend_binding_changed_during_inference_is_refused(tmp_path, mutation):
    backend = Port()
    def hook(req, token, result):
        setattr(backend, mutation, "other" if mutation == "provider_id" else "live")
        return result
    backend.hook = hook
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: backend))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "binding_mismatch" and not result.text


def test_invalid_utf8_result_has_no_retained_content(tmp_path):
    backend = Port(lambda req, token, result: replace(result, text="\ud800"))
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: backend))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "inference_unavailable" and not result.text


@pytest.mark.parametrize("field,value", [("request_id", "other-request"),
                                        ("messages", (InferenceMessage("user", "changed"),))])
def test_forwarded_request_identifiers_and_messages_cannot_change(tmp_path, field, value):
    def hook(req, token, result):
        object.__setattr__(req, field, value)
        return result
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: Port(hook)))
    result = profile.port_for(Event()).infer(request())
    assert result.error_code == "request_changed" and not result.text


def test_replaced_options_snapshot_is_refused(tmp_path):
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: pytest.fail()))
    port = profile.port_for(Event())
    profile._options = replace(profile._options, profile_ref="profile-" + "b" * 64)
    result = port.infer(request())
    assert result.error_code == "profile_changed" and not result.text


@pytest.mark.parametrize("result", [None, {}, object()])
def test_noncontract_result_is_refused(tmp_path, result):
    backend = Port(lambda *args: result)
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: backend))
    outcome = profile.port_for(Event()).infer(request())
    assert outcome.error_code == "invalid_result" and not outcome.text


def test_backend_can_cancel_the_combined_token(tmp_path):
    def hook(req, token, result):
        token.set()
        return result
    profile = GenerativeProfile(**options(tmp_path, port_factory=lambda *args: Port(hook)))
    result = profile.port_for(Event()).infer(request(), cancellation=Event())
    assert result.status == "cancelled" and result.error_code == "cancelled" and not result.text
