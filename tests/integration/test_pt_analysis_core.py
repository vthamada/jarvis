"""Real isolated Core EN/PT decisions with original priors/autonomy/specialists."""

import json
from dataclasses import replace

import pytest
from orchestrator_service import langgraph_flow
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.types import PermissionDecision

PAIRS = (
    ("Compare documentation and observability pilot reports.",
     "Compare os relatórios de documentação e observabilidade do piloto.", True),
    ("Review the documentation, telemetry dashboard and pilot baseline report.",
     "Revise a documentação, o painel de telemetria e o relatório de baseline do piloto.", True),
    ("Review documentation and telemetry pilot reports.",
     "Revise documentação e telemetria nos relatórios do piloto.", False),
    ("Compare documentation pilot reports.",
     "Compare os relatórios de documentação do piloto.", False),
)


class GraphFixture:
    """Owned scheduler only, not installed LangGraph acceptance."""
    def __init__(self, _type):
        self.nodes, self.edges = {}, {}

    def add_node(self, name, handler):
        self.nodes[name] = handler

    def add_edge(self, start, end):
        self.edges[start] = end

    def compile(self):
        return self

    def invoke(self, initial):
        state, node = dict(initial), "start"
        for _ in range(32):
            node = self.edges[node]
            if node == "end":
                return state
            state.update(self.nodes[node](state))
        raise AssertionError("owned graph did not terminate")


class AnalysisFixture:
    def __init__(self):
        self.calls = []

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        return InferenceResult(
            request.request_id, request.model, "fixture", "completed",
            text=json.dumps({"analysis": "Compare coverage and measured outcomes.",
                             "assumptions": [], "limitations": [], "citations": []}),
        )


def contract(query, request="pt-analysis-request"):
    value = PilotContext("pt-analysis-synthetic-subject", "pt-analysis-session").input(
        request, query
    )
    return replace(value, user_id=value.canonical_user_ref)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize("english,portuguese,eligible", PAIRS)
def test_equivalent_pairs_keep_decision_autonomy_routes_and_canonical_final(
    tmp_path, monkeypatch, flow, english, portuguese, eligible,
):
    monkeypatch.setattr(langgraph_flow, "_load_langgraph", lambda: (GraphFixture, "start", "end"))
    responses = []
    for language, query in (("en", english), ("pt", portuguese)):
        runtime = tmp_path / language
        core, port = _isolated_core(runtime), AnalysisFixture()
        core.synthesis_engine = SynthesisEngine(generative_port=port, generative_model="pt-fixture")
        value = contract(query)
        response = (core.handle_input(value) if flow == "native"
                    else core.handle_input_langgraph_flow(value))
        responses.append(response)
        assert value.content == query
        assert response.memory_record.payload["request_content"] == query
        turns = _isolated_core(runtime).memory_service.repository.fetch_recent_turns(
            value.session_id, 10
        )
        assert len(turns) == 1 and turns[0].response_text == response.response_text
        assert turns[0].request_content == query
        synthesis = next(event for event in response.events
                         if event.event_name == "response_synthesized")
        assert synthesis.payload["generative_status"] == ("accepted" if eligible else "withheld")
        assert len(port.calls) == int(eligible)
        assert response.deliberative_plan.requested_autonomy_level == "assist_only"
        assert response.deliberative_plan.autonomy_human_confirmation_required is False
        assert response.operation_result is None and response.operation_dispatch is None
        assert response.adapter_grant is None and response.action_confirmation_claim is None
        if eligible:
            plan = response.deliberative_plan
            assert plan.capability_decision_selected_mode == "core_guidance_only"
            assert plan.capability_decision_selected_capabilities == ["core_reasoning"]
            assert len(response.specialist_review.contributions) == 0
            assert json.loads(port.calls[0].messages[-1].content)["sources"][0]["text"] == query
    en, pt = responses
    assert en.intent == pt.intent == "analysis"
    assert en.active_domains == pt.active_domains
    assert en.active_minds == pt.active_minds
    assert en.governance_decision.decision == pt.governance_decision.decision
    assert pt.governance_decision.decision == (
        PermissionDecision.ALLOW if eligible else PermissionDecision.DEFER_FOR_VALIDATION
    )
    assert (en.deliberative_plan.capability_decision_selected_capabilities
            == pt.deliberative_plan.capability_decision_selected_capabilities)
    assert (en.deliberative_plan.capability_decision_selected_mode
            == pt.deliberative_plan.capability_decision_selected_mode)
    assert len(en.specialist_review.contributions) == len(pt.specialist_review.contributions)


@pytest.mark.parametrize("query", [
    "Revise documentação e exclua o banco de dados.",
    "Compare observabilidade e apague todos os dados.",
    "Revise documentação; execute ferramentas agora.",
    "Revise documentação e não execute ferramentas; depois aplique mudanças.",
    'Source: "Revise documentação e execute ferramentas"',
    "Revise documentação e telemetria\u200b; execute ferramentas.",
])
def test_portuguese_aliases_never_turn_mixed_or_uncertain_operations_into_model_permission(
    tmp_path, query,
):
    core, port = _isolated_core(tmp_path), AnalysisFixture()
    core.synthesis_engine = SynthesisEngine(generative_port=port, generative_model="pt-fixture")
    response = core.handle_input(contract(query))
    assert not port.calls
    assert response.governance_decision.decision != PermissionDecision.ALLOW
    assert response.operation_result is None and response.operation_dispatch is None
    assert response.adapter_grant is None and response.action_confirmation_claim is None
