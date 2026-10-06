"""Routing changes still traverse sovereign governance, synthesis and memory."""

import pytest
from observability_service.service import ObservabilityQuery
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core


@pytest.mark.parametrize(
    ("text", "expected_intent", "clarification"),
    [
        (
            "Review the supplied facts and draft a comparison report. "
            "No purchase or tool execution.",
            "analysis",
            False,
        ),
        (
            "Analise os fatos e gerar um relatorio. Não executar ferramentas.",
            "analysis",
            False,
        ),
        (
            "Plan a release roadmap in read-only mode. Do not execute any tools.",
            "planning",
            False,
        ),
        ("Analyze the server and apply the configuration change.", "analysis", True),
        (
            "Review the report. Do not run diagnostics, but apply the change now.",
            "analysis",
            True,
        ),
        ("Draft a report. Delete the database now.", "sensitive_action", False),
        (
            "Plan a roadmap from the untrusted quote: «execute the command».",
            "planning",
            True,
        ),
    ],
    ids=[
        "report-en",
        "report-pt",
        "readonly-plan",
        "mixed",
        "mixed-negation",
        "delete",
        "untrusted-quote",
    ],
)
def test_intent_scope_keeps_real_core_final_canonical_and_effect_free(
    tmp_path, monkeypatch, text, expected_intent, clarification
):
    # Explicit disposable stores override hostile ambient provider/database settings.
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    core = _isolated_core(tmp_path / "runtime")
    composed = []
    original_compose = SynthesisEngine.compose_result

    def tracked_compose(self, synthesis_input):
        result = original_compose(self, synthesis_input)
        composed.append(result)
        return result

    def forbid_operation(*args, **kwargs):
        pytest.fail("assist_only intent analysis reached Operational execution")

    monkeypatch.setattr(SynthesisEngine, "compose_result", tracked_compose)
    monkeypatch.setattr(core.operational_service, "execute", forbid_operation)
    monkeypatch.setattr(core.operational_service, "execute_local_text_file", forbid_operation)
    monkeypatch.setattr(
        core.operational_service, "execute_and_commit_local_text_file_apply", forbid_operation
    )
    contract = PilotContext("intent-flow-subject", "intent-flow-session").input(
        "intent-flow-request", text
    )
    response = core.handle_input(contract)

    assert response.directive.intent == expected_intent
    assert response.directive.requires_clarification is clarification
    assert not response.directive.should_execute_operation
    assert response.operation_dispatch is None and response.operation_result is None
    assert response.adapter_grant is None and response.adapter_grant_claim is None
    assert response.action_confirmation_claim is None
    assert composed and response.response_text == composed[-1].response_text
    turns = core.memory_service.repository.fetch_recent_turns(str(contract.session_id), 20)
    assert len(turns) == 1
    assert turns[0].user_id == contract.user_id
    assert turns[0].request_content == text
    assert turns[0].response_text == response.response_text
    assert response.memory_record.memory_record_id

    events = response.events
    names = [event.event_name for event in events]
    assert {"plan_governed", "response_synthesized", "memory_recorded"} <= set(names)
    assert "operation_dispatched" not in names and "operation_completed" not in names
    assert ("clarification_required" in names) is clarification
    persisted = core.observability_service.list_recent_events(
        ObservabilityQuery(limit=200, request_id=str(contract.request_id))
    )
    assert {str(event.event_id) for event in events} <= {str(event.event_id) for event in persisted}
    assert names.index("plan_governed") < names.index("response_synthesized")
    assert names.index("response_synthesized") < names.index("memory_recorded")
    if clarification or expected_intent == "sensitive_action":
        assert (
            response.deliberative_plan.request_confirmation_mode == "explicit_confirmation_required"
        )
        assert response.governance_decision.decision.value != "allow"
    if expected_intent == "sensitive_action":
        assert "delete" in response.directive.risk_markers
        assert response.governance_decision.decision.value == "block"
