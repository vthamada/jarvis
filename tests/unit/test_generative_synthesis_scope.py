"""Independent Synthesis scope audit using naturally eligible real Core inputs."""

import copy
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from threading import Event

import pytest
from knowledge_service.source_review import LocalKnowledgeReview
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import (
    GENERATIVE_ANALYSIS_MARKER,
    KnowledgeReviewBinding,
    ReviewedTextSource,
)
from shared.types import PermissionDecision

QUERY = "Compare documentation and observability pilot reports."
DRAFT = "Compare intended coverage with measured outcomes; investigate discrepancies."


class AuditPort:
    def __init__(self, hook=None, fail=False):
        self.calls = []
        self.hook = hook
        self.fail = fail

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        if self.hook:
            self.hook()
        if self.fail:
            raise RuntimeError("PRIVATE_PROVIDER_FAILURE")
        return InferenceResult(
            request_id=request.request_id,
            model=request.model,
            provider_id="fixture",
            status="completed",
            text=json.dumps(
                {"analysis": DRAFT, "assumptions": [], "limitations": [], "citations": []}
            ),
        )


def capture_input(core, contract, **kwargs):
    captured = []
    compose = core.synthesis_engine.compose_result

    def capture(value):
        captured.append(value)
        return compose(value)

    core.synthesis_engine.compose_result = capture
    response = core.handle_input(contract, **kwargs)
    assert response.governance_decision.decision == PermissionDecision.ALLOW
    return captured[-1]


@pytest.fixture(scope="module")
def captured_inputs(tmp_path_factory):
    runtime = tmp_path_factory.mktemp("generative-scope-audit")
    contract = PilotContext("scope-audit-subject", "scope-audit-session").input(
        "scope-audit-id", QUERY
    )
    contract = replace(contract, user_id=contract.canonical_user_ref)
    value = capture_input(_isolated_core(runtime / "plain"), contract)
    quote = "Documentation describes coverage; observability records measured outcomes."
    text = "Unselected body.\n" + quote + "\nUnselected body."
    raw = text.encode("utf-8")
    source = ReviewedTextSource(
        text=text,
        source_url="https://fixture.example/report",
        observed_at=datetime.now(UTC).isoformat(),
        content_sha256=hashlib.sha256(raw).hexdigest(),
        byte_count=len(raw),
        media_type="text/plain",
    )
    binding = KnowledgeReviewBinding(
        contract.canonical_user_ref, str(contract.session_id), str(contract.request_id)
    )
    review = LocalKnowledgeReview(binding)
    review.consent(binding, granted=True)
    ticket = review.propose(source, contract.content, binding=binding)
    review.review(ticket, binding=binding)
    start = text.index(quote)
    selection = review.select(ticket, binding=binding, start=start, end=start + len(quote))
    context = review.confirm(
        ticket, binding=binding, fingerprint=selection.fingerprint, revision=selection.revision
    )
    reviewed = capture_input(
        _isolated_core(runtime / "reviewed"),
        contract,
        reviewed_knowledge=context,
        knowledge_review=review,
    )
    return value, reviewed


@pytest.fixture
def value(captured_inputs):
    return copy.deepcopy(captured_inputs[0])


@pytest.fixture
def reviewed(captured_inputs):
    return copy.deepcopy(captured_inputs[1])


def configured(port, **kwargs):
    return SynthesisEngine(generative_port=port, generative_model="scope-fixture", **kwargs)


def test_real_plan_is_naturally_eligible_without_configuration_override(value):
    plan = value.deliberative_plan
    assert plan.capability_decision_selected_mode == "core_guidance_only"
    assert plan.capability_decision_selected_capabilities == ["core_reasoning"]
    assert plan.request_confirmation_mode == "bounded_autonomy"
    assert plan.autonomy_confirmation_mode == "not_required"
    assert plan.autonomy_human_confirmation_required is False
    port = AuditPort()
    native = SynthesisEngine().compose_result(value)
    result = configured(port).compose_result(value)
    assert result.generative_status == "accepted" and len(port.calls) == 1
    assert result.response_text.startswith(
        native.response_text + "\n\n" + GENERATIVE_ANALYSIS_MARKER
    )


@pytest.mark.parametrize(
    "decision", [PermissionDecision.BLOCK, PermissionDecision.DEFER_FOR_VALIDATION]
)
def test_nonallow_zero_port_and_exact_native(value, decision):
    value = replace(
        value, governance_decision=replace(value.governance_decision, decision=decision)
    )
    port = AuditPort()
    native = SynthesisEngine().compose_result(value)
    result = configured(port).compose_result(value)
    assert result.response_text == native.response_text
    assert result.generative_status == "withheld" and port.calls == []


@pytest.mark.parametrize(
    "field,mutation",
    [
        ("operation_result", object()),
        ("specialist_contributions", [object()]),
        ("extractive_context", None),
        ("intent", "sensitive_action"),
        ("objective_status", "blocked"),
    ],
)
def test_surface_scope_denials_zero_port(value, field, mutation, monkeypatch):
    # Isolate scope checking from unrelated native rendering of invalid fixture
    # objects; the native final being protected is a real Core-produced final.
    native = SynthesisEngine().compose_result(value)
    port = AuditPort()
    engine = configured(port)
    monkeypatch.setattr(engine, "_compose_native_result", lambda _: native)
    altered = replace(value, **{field: mutation})
    result = engine.compose_result(altered)
    assert result.response_text == native.response_text
    assert result.generative_status == "withheld" and port.calls == []


@pytest.mark.parametrize(
    "field,mutation",
    [
        ("capability_decision_selected_mode", "operational_execution"),
        (
            "capability_decision_selected_capabilities",
            ["core_reasoning", "execute_external_action"],
        ),
        ("adapter_action_request", object()),
        ("requires_human_validation", True),
        ("autonomy_human_confirmation_required", True),
        ("autonomy_confirmation_mode", "explicit_confirmation_required"),
        ("request_confirmation_mode", "explicit_confirmation_required"),
        ("capability_decision_authorization_status", "clarification_required"),
        ("primary_route", "clarification"),
        ("objective_status", "paused"),
    ],
)
def test_plan_scope_denials_zero_port(value, field, mutation, monkeypatch):
    native = SynthesisEngine().compose_result(value)
    port = AuditPort()
    engine = configured(port)
    monkeypatch.setattr(engine, "_compose_native_result", lambda _: native)
    altered = replace(
        value, deliberative_plan=replace(value.deliberative_plan, **{field: mutation})
    )
    result = engine.compose_result(altered)
    assert result.response_text == native.response_text
    assert result.generative_status == "withheld" and port.calls == []


@pytest.mark.parametrize(
    "field,mutation",
    [
        ("output_validation_status", "invalid"),
        ("output_validation_status", "repaired"),
        ("output_validation_errors", ["failure"]),
        ("workflow_output_status", "partial"),
        ("workflow_output_errors", ["failure"]),
    ],
)
def test_native_validation_failure_cannot_be_repaired_by_model(value, field, mutation, monkeypatch):
    native = replace(SynthesisEngine().compose_result(value), **{field: mutation})
    port = AuditPort()
    engine = configured(port)
    monkeypatch.setattr(engine, "_compose_native_result", lambda _: native)
    result = engine.compose_result(value)
    assert result.response_text == native.response_text
    assert result.generative_status == "withheld" and port.calls == []


def test_default_off_and_provider_failure_preserve_native(value):
    native = SynthesisEngine().compose_result(value)
    assert native.generative_status == "disabled"
    port = AuditPort(fail=True)
    result = configured(port).compose_result(value)
    assert result.generative_status == "rejected"
    assert result.response_text == native.response_text and len(port.calls) == 1


@pytest.mark.parametrize(
    "field,mutation", [("request_id", "different"), ("content", "different content")]
)
def test_same_extractive_object_mutation_after_dispatch_rejected(value, field, mutation):
    native = SynthesisEngine().compose_result(value)
    port = AuditPort(hook=lambda: object.__setattr__(value.extractive_context, field, mutation))
    result = configured(port).compose_result(value)
    assert result.generative_status == "rejected"
    assert result.response_text == native.response_text


def test_final_clock_cannot_cancel_after_last_check(value):
    native = SynthesisEngine().compose_result(value)
    cancel = Event()
    count = 0

    def clock():
        nonlocal count
        count += 1
        if count == 7:
            cancel.set()
        return count * 0.01

    result = configured(
        AuditPort(), generative_clock=clock, generative_cancellation=cancel
    ).compose_result(value)
    assert count >= 7
    assert result.generative_status == "rejected"
    assert result.response_text == native.response_text


def test_final_clock_cannot_change_eligible_plan(value):
    native = SynthesisEngine().compose_result(value)
    count = 0

    def clock():
        nonlocal count
        count += 1
        if count == 7:
            value.deliberative_plan.capability_decision_selected_capabilities.append(
                "execute_external_action"
            )
        return count * 0.01

    result = configured(AuditPort(), generative_clock=clock).compose_result(value)
    assert result.generative_status == "rejected"
    assert result.response_text == native.response_text


def test_final_clock_expiry_after_revalidation_preserves_original_native(reviewed):
    native = SynthesisEngine().compose_result(reviewed)
    count = 0

    def clock():
        nonlocal count
        count += 1
        return 30 if count == 7 else 0

    result = configured(AuditPort(), generative_clock=clock).compose_result(reviewed)
    assert result.generative_status == "rejected"
    assert result.generative_error_code == "timed_out"
    assert result.response_text == native.response_text


def test_reviewed_source_mutation_after_dispatch_preserves_preexisting_native(reviewed):
    native = SynthesisEngine().compose_result(reviewed)
    port = AuditPort(
        hook=lambda: object.__setattr__(reviewed.reviewed_knowledge, "quote", "tampered")
    )
    result = configured(port).compose_result(reviewed)
    assert result.generative_status == "rejected"
    assert result.response_text == native.response_text


def test_final_clock_reviewed_source_mutation_is_rejected(reviewed):
    native = SynthesisEngine().compose_result(reviewed)
    count = 0

    def clock():
        nonlocal count
        count += 1
        if count == 7:
            object.__setattr__(reviewed.reviewed_knowledge, "quote", "tampered")
        return count * 0.01

    result = configured(AuditPort(), generative_clock=clock).compose_result(reviewed)
    assert result.generative_status == "rejected"
    assert result.response_text == native.response_text
