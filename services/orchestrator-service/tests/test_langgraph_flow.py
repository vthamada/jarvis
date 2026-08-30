from dataclasses import replace
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from evolution_lab.service import EvolutionLabService
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service import langgraph_flow
from orchestrator_service.service import OrchestratorService

from shared.adapter_permissions import SEEDED_ADAPTER_REGISTRY
from shared.contracts import (
    AdapterActionRequestContract,
    InputContract,
    ProceduralPlaybookCandidateContract,
)
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    OperationStatus,
    PermissionDecision,
    RequestId,
    SessionId,
)
from tests.unit.test_workflow_lifecycle import _activation


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def bounded_input(**values: object) -> InputContract:
    """Build an explicit bounded-autonomy fixture for executable legacy tests."""

    fields: dict[str, object] = {
        "requested_autonomy_level": "bounded_core_action",
        "max_autonomy_level": "bounded_core_action",
        "autonomy_confirmation_mode": "not_required",
    }
    fields.update(values)
    return InputContract(**fields)  # type: ignore[arg-type]


def adapter_action_request(**values: str) -> AdapterActionRequestContract:
    fields = {
        "adapter_id": "local_text_file",
        "adapter_version": "1.0.0",
        "action_kind": "prepare_external_action",
        "operation": "create_text",
        "resource_scope": "configured_text_root",
        "resource_ref": "text:notes/langgraph-grant.txt",
    }
    fields.update(values)
    return AdapterActionRequestContract(**fields)


def supervised_adapter_input(**values: object) -> InputContract:
    fields: dict[str, object] = {
        "requested_autonomy_level": "supervised_external_action",
        "max_autonomy_level": "supervised_external_action",
        "autonomy_confirmation_mode": "not_required",
        "operator_identity_ref": "operator://local/langgraph-adapter",
        "adapter_action_request": adapter_action_request(),
    }
    fields.update(values)
    return InputContract(**fields)  # type: ignore[arg-type]


class FakeCompiledGraph:
    def __init__(self, nodes: dict[str, object], edges: dict[str, str]) -> None:
        self.nodes = nodes
        self.edges = edges

    def invoke(self, initial_state):  # type: ignore[no-untyped-def]
        current = "__start__"
        state = dict(initial_state)
        while True:
            next_node = self.edges[current]
            if next_node == "__end__":
                return state
            updates = self.nodes[next_node](state)
            state.update(updates)
            current = next_node


class FakeStateGraph:
    def __init__(self, _state_type) -> None:  # type: ignore[no-untyped-def]
        self.nodes: dict[str, object] = {}
        self.edges: dict[str, str] = {}

    def add_node(self, name: str, handler) -> None:  # type: ignore[no-untyped-def]
        self.nodes[name] = handler

    def add_edge(self, start: str, end: str) -> None:
        self.edges[start] = end

    def compile(self) -> FakeCompiledGraph:
        return FakeCompiledGraph(self.nodes, self.edges)


def install_fake_langgraph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        langgraph_flow,
        "_load_langgraph",
        lambda: (FakeStateGraph, "__start__", "__end__"),
    )


@pytest.mark.parametrize(
    ("confirmation_mode", "challenge_expected"),
    [("not_required", False), ("explicit", True)],
)
def test_langgraph_issues_exact_metadata_only_adapter_grant_with_native_parity(
    monkeypatch: pytest.MonkeyPatch,
    confirmation_mode: str,
    challenge_expected: bool,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir(f"langgraph-adapter-grant-{confirmation_mode}")
    governance = GovernanceService(temp_dir / "governance.db")
    governance.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY)
    artifact_dir = temp_dir / "artifacts"
    service = OrchestratorService(
        governance_service=governance,
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(artifact_dir)),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        pytest.fail("LangGraph adapter prepare reached dispatch or execution")

    monkeypatch.setattr(service, "build_operation_dispatch", forbidden)
    monkeypatch.setattr(service.operational_service, "execute", forbidden)
    request = adapter_action_request()
    result = service.handle_input_langgraph_flow(
        supervised_adapter_input(
            request_id=RequestId(f"req-lg-adapter-{confirmation_mode}"),
            session_id=SessionId(f"sess-lg-adapter-{confirmation_mode}"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Prepare the exact governed adapter request.",
            timestamp="2026-08-29T17:30:00Z",
            autonomy_confirmation_mode=confirmation_mode,
            adapter_action_request=request,
        )
    )

    assert result.deliberative_plan.adapter_action_request == request
    assert result.deliberative_plan.autonomy_action_kind == "prepare_external_action"
    assert result.adapter_action_intent is not None
    assert result.adapter_descriptor is not None
    assert result.adapter_grant is not None
    assert result.adapter_grant.adapter_request == request
    assert result.adapter_grant.confirmation_required is challenge_expected
    assert (result.action_confirmation_challenge is not None) is challenge_expected
    if result.action_confirmation_challenge is not None:
        assert result.action_confirmation_challenge.intent_fingerprint == (
            result.adapter_grant.intent_fingerprint
        )
        assert result.action_confirmation_challenge.action_fingerprint == (
            result.adapter_grant.action_fingerprint
        )
    assert result.adapter_grant_claim is None
    assert result.action_confirmation_claim is None
    assert result.operation_dispatch is None
    assert result.operation_result is None
    assert result.artifact_results == []
    assert not artifact_dir.exists()
    event_names = {event.event_name for event in result.events}
    assert "adapter_grant_issued" in event_names
    assert "operation_dispatched" not in event_names
    assert "operation_completed" not in event_names


@pytest.mark.parametrize(
    ("case_name", "adapter_request", "autonomy_overrides", "activate_registry"),
    [
        (
            "assist-only",
            adapter_action_request(),
            {
                "requested_autonomy_level": "assist_only",
                "max_autonomy_level": "assist_only",
            },
            True,
        ),
        (
            "unknown-adapter",
            adapter_action_request(adapter_id="unknown_adapter"),
            {},
            True,
        ),
        (
            "wildcard-version",
            adapter_action_request(adapter_version="*"),
            {},
            True,
        ),
        (
            "descriptor-drift",
            adapter_action_request(operation="delete_text"),
            {},
            True,
        ),
        (
            "external-execute",
            adapter_action_request(action_kind="execute_external_action"),
            {"autonomy_confirmation_mode": "explicit"},
            True,
        ),
        ("missing-registry", adapter_action_request(), {}, False),
    ],
)
def test_langgraph_adapter_requests_fail_closed_before_challenge_or_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    case_name: str,
    adapter_request: AdapterActionRequestContract,
    autonomy_overrides: dict[str, object],
    activate_registry: bool,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir(f"langgraph-adapter-block-{case_name}")
    governance = GovernanceService(temp_dir / "governance.db")
    if activate_registry:
        governance.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY)
    service = OrchestratorService(
        governance_service=governance,
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        pytest.fail("blocked LangGraph adapter request reached runtime")

    monkeypatch.setattr(service, "build_operation_dispatch", forbidden)
    monkeypatch.setattr(service.operational_service, "execute", forbidden)
    result = service.handle_input_langgraph_flow(
        supervised_adapter_input(
            request_id=RequestId(f"req-lg-adapter-block-{case_name}"),
            session_id=SessionId(f"sess-lg-adapter-block-{case_name}"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Prepare the exact governed adapter request.",
            timestamp="2026-08-29T17:35:00Z",
            adapter_action_request=adapter_request,
            **autonomy_overrides,
        )
    )

    assert result.adapter_action_intent is None
    assert result.adapter_descriptor is None
    assert result.adapter_grant is None
    assert result.adapter_grant_claim is None
    assert result.action_confirmation_challenge is None
    assert result.action_confirmation_claim is None
    assert result.operation_dispatch is None
    assert result.operation_result is None
    assert not (temp_dir / "artifacts").exists()
    event_names = {event.event_name for event in result.events}
    assert "adapter_authorization_blocked" in event_names
    assert "adapter_grant_issued" not in event_names
    assert "operation_dispatched" not in event_names


def test_langgraph_flow_surfaces_optional_dependency_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OrchestratorService()
    monkeypatch.setattr(
        langgraph_flow,
        "_load_langgraph",
        lambda: (_ for _ in ()).throw(
            RuntimeError(
                'LangGraph is not installed. Use `python -m pip install -e ".[langgraph]"` '
                "to run the experimental orchestrator flow."
            )
        ),
    )

    with pytest.raises(RuntimeError, match="LangGraph is not installed"):
        service.handle_input_langgraph_flow(
            bounded_input(
                request_id=RequestId("req-lg-missing"),
                session_id=SessionId("sess-lg-missing"),
                channel=ChannelType.CHAT,
                input_type=InputType.TEXT,
                content="Plan the next pilot step.",
                timestamp="2026-03-19T00:00:00+00:00",
            )
        )


def test_langgraph_flow_replays_orchestrator_path_with_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)

    temp_dir = runtime_dir("langgraph-flow")
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    result = service.handle_input_langgraph_flow(
        bounded_input(
            request_id=RequestId("req-lg"),
            session_id=SessionId("sess-lg"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the internal pilot rollout.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )

    assert result.intent == "planning"
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.knowledge_result is not None
    assert result.knowledge_result.provenance_status == "complete"
    assert result.knowledge_evidence_governance is not None
    assert result.knowledge_evidence_governance.status == "evidence_ready"
    assert "Conhecimento:" in result.response_text
    assert result.operation_result is not None
    assert result.experience_record is not None
    assert result.post_task_reflection is not None
    assert result.decision_outcome_attribution is not None
    assert result.decision_outcome_attribution.attribution_status == (
        "declared_causality"
    )
    assert result.decision_outcome_attribution.causal_effect_proven is False
    assert result.decision_outcome_attribution.gain_claim_status == (
        "not_established_without_comparator"
    )
    assert any(
        event.event_name == "decision_outcome_attribution_recorded"
        for event in result.events
    )
    assert any(event.event_name == "plan_built" for event in result.events)
    memory_governance_event = next(
        event
        for event in result.events
        if event.event_name == "memory_influence_governed"
    )
    assert memory_governance_event.payload[
        "memory_influence_governance_status"
    ] == "governed"
    assert any(event.event_name == "specialist_selection_decided" for event in result.events)
    assert any(event.event_name == "specialist_contracts_composed" for event in result.events)
    assert any(event.event_name == "specialist_handoff_governed" for event in result.events)
    assert result.specialist_handoff_decision is not None
    assert result.deliberative_plan.workflow_policy_decision is not None
    workflow_policy_ref = result.deliberative_plan.workflow_policy_decision.policy_ref
    for event_name in {
        "plan_built",
        "workflow_composed",
        "workflow_governance_declared",
        "operation_dispatched",
        "operation_completed",
        "workflow_completed",
        "response_synthesized",
    }:
        event = next(event for event in result.events if event.event_name == event_name)
        assert event.payload["workflow_policy_ref"] == workflow_policy_ref
        assert event.payload["workflow_policy_application_status"] == "applied"
    continuity_event = next(
        event for event in result.events if event.event_name == "continuity_subflow_completed"
    )
    assert continuity_event.payload["runtime_mode"] == "langgraph_subflow"
    assert continuity_event.payload["subflow_name"] == "continuity_stateful"
    specialist_subflow_event = next(
        event for event in result.events if event.event_name == "specialist_subflow_completed"
    )
    assert specialist_subflow_event.payload["runtime_mode"] == "langgraph_subflow"
    assert specialist_subflow_event.payload["subflow_name"] == "specialist_handoffs"


def test_langgraph_executes_exact_confirmation_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir("langgraph-action-confirmation")
    governance = GovernanceService(temp_dir / "governance.db")
    service = OrchestratorService(
        governance_service=governance,
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts"),
            action_confirmation_verifier=(
                governance.verify_action_confirmation_claim
            ),
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    def contract(
        request_id: str,
        *,
        receipt_id: str | None = None,
        origin_request_id: str | None = None,
    ) -> InputContract:
        return bounded_input(
            request_id=RequestId(request_id),
            session_id=SessionId("sess-lg-action-confirmation"),
            mission_id=MissionId("mission-lg-action-confirmation"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the exact governed LangGraph rollout.",
            timestamp="2026-08-29T12:00:00Z",
            operator_identity_ref="operator://local/langgraph-confirmation",
            requested_autonomy_level="supervised_external_action",
            max_autonomy_level="supervised_external_action",
            autonomy_confirmation_mode="explicit",
            action_confirmation_receipt_id=receipt_id,
            action_confirmation_origin_request_id=origin_request_id,
        )

    first = service.handle_input_langgraph_flow(contract("req-lg-confirmation-1"))

    assert first.action_confirmation_challenge is not None
    assert first.operation_dispatch is None
    assert first.operation_result is None
    assert first.artifact_results == []
    assert "operation_dispatched" not in [
        event.event_name for event in first.events
    ]
    challenge = first.action_confirmation_challenge
    receipt = governance.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref="operator://local/langgraph-confirmation",
        expected_action_fingerprint=challenge.action_fingerprint,
    )

    missing_origin = service.handle_input_langgraph_flow(
        contract(
            "req-lg-confirmation-missing-origin",
            receipt_id=receipt.receipt_id,
        )
    )

    assert missing_origin.action_confirmation_claim is None
    assert missing_origin.operation_dispatch is None
    assert missing_origin.operation_result is None
    assert missing_origin.artifact_results == []
    missing_origin_blocked = next(
        event
        for event in missing_origin.events
        if event.event_name == "action_confirmation_blocked"
    )
    assert missing_origin_blocked.payload["reason"] == (
        "action_confirmation_origin_request_required"
    )
    assert list((temp_dir / "artifacts").glob("*.md")) == []

    second = service.handle_input_langgraph_flow(
        contract(
            "req-lg-confirmation-2",
            receipt_id=receipt.receipt_id,
            origin_request_id=str(challenge.origin_request_id),
        )
    )

    assert second.action_confirmation_claim is not None
    assert second.action_confirmation_challenge is None
    assert second.operation_result is not None
    assert second.operation_result.status == OperationStatus.COMPLETED
    assert len(second.artifact_results) == 1
    assert [event.event_name for event in second.events].count(
        "operation_completed"
    ) == 1

    third = service.handle_input_langgraph_flow(
        contract(
            "req-lg-confirmation-3",
            receipt_id=receipt.receipt_id,
            origin_request_id=str(challenge.origin_request_id),
        )
    )

    assert third.action_confirmation_claim is None
    assert third.action_confirmation_challenge is not None
    assert third.operation_result is None
    assert third.artifact_results == []
    assert "operation_dispatched" not in [
        event.event_name for event in third.events
    ]
    assert len(list((temp_dir / "artifacts").glob("*.md"))) == 1


def test_langgraph_assist_only_never_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir("langgraph-assist-only-no-dispatch")
    service = OrchestratorService(
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    result = service.handle_input_langgraph_flow(
        bounded_input(
            request_id=RequestId("req-lg-assist-only"),
            session_id=SessionId("sess-lg-assist-only"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the first milestone.",
            timestamp="2026-08-29T16:30:00Z",
            requested_autonomy_level="assist_only",
            max_autonomy_level="assist_only",
            autonomy_confirmation_mode="not_required",
            action_confirmation_receipt_id="receipt://cannot-expand-assist-only",
            action_confirmation_origin_request_id="req-lg-origin-assist-only",
        )
    )

    assert result.deliberative_plan.effective_autonomy_level == "assist_only"
    assert result.deliberative_plan.adapter_action_request is None
    assert result.adapter_action_intent is None
    assert result.adapter_descriptor is None
    assert result.adapter_grant is None
    assert result.adapter_grant_claim is None
    assert result.operation_dispatch is None
    assert result.operation_result is None
    assert result.action_confirmation_challenge is None
    assert result.action_confirmation_claim is None
    assert result.artifact_results == []
    assert list((temp_dir / "artifacts").glob("*.md")) == []
    event_names = [event.event_name for event in result.events]
    assert "operation_dispatched" not in event_names
    assert "operation_completed" not in event_names


def test_langgraph_blocks_external_action_before_confirmation_challenge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir("langgraph-external-adapter-unavailable")
    service = OrchestratorService(
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )
    monkeypatch.setattr(
        service,
        "_derive_autonomy_action_kind",
        lambda _plan: "execute_external_action",
    )
    execute_specialist_handoffs = service._execute_specialist_handoffs

    def execute_external_capability(*args, **kwargs):  # type: ignore[no-untyped-def]
        specialist_review, plan, events = execute_specialist_handoffs(
            *args,
            **kwargs,
        )
        plan.capability_decision_selected_mode = (
            "core_with_supervised_external_operation"
        )
        plan.capability_decision_selected_capabilities = [
            "core_reasoning",
            "supervised_external_operation",
        ]
        return specialist_review, plan, events

    monkeypatch.setattr(
        service,
        "_execute_specialist_handoffs",
        execute_external_capability,
    )

    result = service.handle_input_langgraph_flow(
        bounded_input(
            request_id=RequestId("req-lg-external-adapter-unavailable"),
            session_id=SessionId("sess-lg-external-adapter-unavailable"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the first milestone.",
            timestamp="2026-08-29T16:35:00Z",
            requested_autonomy_level="supervised_external_action",
            max_autonomy_level="supervised_external_action",
            autonomy_confirmation_mode="explicit",
            operator_identity_ref="operator://local/langgraph-external",
        )
    )

    assert result.deliberative_plan.autonomy_action_kind == (
        "execute_external_action"
    )
    assert result.deliberative_plan.capability_decision_selected_mode == (
        "core_with_supervised_external_operation"
    )
    assert result.governance_decision.decision == (
        PermissionDecision.ALLOW_WITH_CONDITIONS
    )
    assert result.operation_dispatch is None
    assert result.action_confirmation_challenge is None
    assert result.action_confirmation_claim is None
    assert result.operation_result is None
    assert list((temp_dir / "artifacts").glob("*.md")) == []
    event_names = [event.event_name for event in result.events]
    assert "operation_dispatched" not in event_names
    assert "operation_completed" not in event_names


def test_langgraph_uses_persisted_human_promoted_workflow_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir("langgraph-workflow-lifecycle")
    transition = _activation()
    governance = GovernanceService()
    memory = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}",
        workflow_lifecycle_transition_verifier=lambda candidate: (
            candidate == transition
        ),
    )
    assessment = governance.assess_workflow_lifecycle_transition(
        transition,
        release_bundle_verifier=lambda candidate: candidate == transition,
        assessed_at=transition.timestamp,
    )
    memory.record_workflow_lifecycle_transition(transition, assessment)
    service = OrchestratorService(
        governance_service=governance,
        memory_service=memory,
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    result = service.handle_input_langgraph_flow(
        bounded_input(
            request_id=RequestId("req-lg-workflow-lifecycle"),
            session_id=SessionId("sess-lg-workflow-lifecycle"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=(
                "Analyze the Python service API rollout and compare the safest "
                "bounded change."
            ),
            timestamp="2026-08-12T10:45:00Z",
        )
    )

    assert result.deliberative_plan.workflow_lifecycle_transition == transition
    assert result.deliberative_plan.route_workflow_steps == (
        transition.active_workflow_steps
    )
    assert transition.active_version_ref in result.response_text
    assert result.operation_dispatch is None
    for event_name in ("plan_built", "response_synthesized"):
        event = next(event for event in result.events if event.event_name == event_name)
        assert event.payload["workflow_lifecycle_status"] == "active_promoted"
        assert event.payload["workflow_lifecycle_transition_id"] == (
            transition.transition_id
        )
        assert event.payload["workflow_lifecycle_active_version_ref"] == (
            transition.active_version_ref
        )
        assert event.payload["workflow_lifecycle_automatic_promotion_allowed"] is False
        assert event.payload["workflow_lifecycle_automatic_rollback_allowed"] is False


def test_langgraph_full_path_governs_reviewed_playbook_without_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir("langgraph-reviewed-playbook")
    evolution = EvolutionLabService(
        database_path=str(temp_dir / "evolution.db")
    )
    candidate = ProceduralPlaybookCandidateContract(
        playbook_candidate_id="playbook-candidate://langgraph/safe-change",
        procedure_name="safe bounded LangGraph change",
        route="software_development",
        workflow_profile="software_change_workflow",
        domain="computacao_e_desenvolvimento",
        bounded_steps=[
            "collect contract evidence",
            "preserve rollback evidence",
        ],
        evidence_refs=["evidence://langgraph/safe-change/candidate"],
        proposed_tests=[
            "pytest services/orchestrator-service/tests/test_langgraph_flow.py"
        ],
        rollback_plan_ref="rollback://langgraph/safe-change/1.0.0",
        timestamp="2026-08-11T12:00:00+00:00",
    )
    proposal = evolution.create_proposal_from_procedural_playbook_candidate(
        candidate
    )
    review = evolution.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://langgraph/safe-change/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
        release_version="1.0.0",
    )
    checklist = evolution.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
    )
    gate = evolution.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    playbook = evolution.derive_reviewed_procedural_playbook(
        candidate,
        review,
        version="1.0.0",
        release_checklist=checklist,
        promotion_gate=gate,
    )
    memory = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}",
        reviewed_procedural_playbook_verifier=(
            evolution.verify_persisted_reviewed_procedural_playbook
        ),
    )
    memory.record_reviewed_procedural_playbook(playbook)
    observability = ObservabilityService(
        database_path=str(temp_dir / "observability.db")
    )
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=memory,
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=observability,
    )

    result = service.handle_input_langgraph_flow(
        bounded_input(
            request_id=RequestId("req-lg-reviewed-playbook"),
            session_id=SessionId("sess-lg-reviewed-playbook"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=(
                "Please plan the Python service API rollout and safest bounded change."
            ),
            timestamp="2026-08-11T12:01:00+00:00",
        )
    )

    signal_ref = f"{playbook.playbook_id}@{playbook.version}"
    decision = result.deliberative_plan.memory_influence_policy_decision
    assert decision is not None
    assert signal_ref in decision.selected_refs
    assert result.directive.should_execute_operation is True
    assert result.operation_dispatch is None
    assert result.operation_result is None
    assert result.experience_record is not None
    attribution = result.decision_outcome_attribution
    assert attribution is not None
    assert attribution.experience_id == result.experience_record.experience_id
    assert attribution.attribution_status == "declared_causality"
    assert signal_ref in attribution.declared_causal_refs
    assert attribution.memory_version_refs[signal_ref] == "1.0.0"
    assert attribution.memory_review_decision_refs[signal_ref] == (
        playbook.source_review_decision_id
    )
    assert attribution.causal_effect_proven is False
    assert attribution.promotion_authorized is False
    governed_event = next(
        event
        for event in result.events
        if event.event_name == "memory_influence_governed"
    )
    assert governed_event.payload["memory_influence_governance_status"] == "governed"
    for event_name in ("plan_built", "response_synthesized", "memory_recorded"):
        event = next(event for event in result.events if event.event_name == event_name)
        assert event.payload["memory_influence_version_refs"][signal_ref] == "1.0.0"
        assert event.payload["memory_influence_review_decision_refs"][signal_ref] == (
            playbook.source_review_decision_id
        )
    attribution_event = next(
        event
        for event in result.events
        if event.event_name == "decision_outcome_attribution_recorded"
    )
    assert attribution_event.payload["attribution_status"] == "declared_causality"
    assert signal_ref in attribution_event.payload["declared_causal_refs"]
    assert attribution_event.payload["causal_effect_proven"] is False

    audit = observability.audit_flow(
        ObservabilityQuery(request_id="req-lg-reviewed-playbook", limit=200)
    )
    assert signal_ref in audit.memory_influence_selected_refs
    assert audit.memory_influence_version_refs[signal_ref] == "1.0.0"
    assert audit.memory_influence_review_decision_refs[signal_ref] == (
        playbook.source_review_decision_id
    )
    assert audit.memory_influence_governance_status == "governed"
    assert audit.memory_influence_governance_blockers == []
    assert audit.memory_influence_governance_drift_flags == []
    assert audit.selected_reviewed_procedural_playbook_refs == [signal_ref]
    assert audit.decision_outcome_attribution_record_id == (
        attribution.attribution_record_id
    )
    assert audit.decision_outcome_attribution_status == "declared_causality"
    assert audit.decision_outcome_attribution_evidence_refs
    assert audit.causal_effect_proven is False
    assert audit.gain_claim_status == "not_established_without_comparator"


def test_langgraph_attributes_failed_operation_as_failed_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir("langgraph-failed-outcome-attribution")
    operational = OperationalService(
        artifact_dir=str(temp_dir / "artifacts")
    )
    original_execute = operational.execute

    def execute_as_failed(dispatch):  # type: ignore[no-untyped-def]
        execution = original_execute(dispatch)
        return replace(
            execution,
            operation_result=replace(
                execution.operation_result,
                status=OperationStatus.FAILED,
                errors=["simulated_langgraph_failure"],
            ),
        )

    monkeypatch.setattr(operational, "execute", execute_as_failed)
    service = OrchestratorService(
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=operational,
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    result = service.handle_input_langgraph_flow(
        bounded_input(
            request_id=RequestId("req-lg-failed-outcome-attribution"),
            session_id=SessionId("sess-lg-failed-outcome-attribution"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the bounded LangGraph failure simulation.",
            timestamp="2026-08-11T16:25:00+00:00",
        )
    )

    assert result.operation_result is not None
    assert result.operation_result.status == OperationStatus.FAILED
    assert result.experience_record is not None
    assert result.experience_record.outcome_status == "failed"
    assert "operation_status:failed" in result.experience_record.errors
    assert result.decision_outcome_attribution is not None
    assert result.decision_outcome_attribution.outcome_status == "failed"


def test_langgraph_rejects_duplicate_request_before_any_runtime_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_langgraph(monkeypatch)
    temp_dir = runtime_dir("langgraph-duplicate-request")
    observability = ObservabilityService(
        database_path=str(temp_dir / "observability.db")
    )
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=observability,
    )
    contract = bounded_input(
        request_id=RequestId("req-lg-duplicate-runtime"),
        session_id=SessionId("sess-lg-duplicate-runtime"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the bounded LangGraph rollout.",
        timestamp="2026-08-11T16:45:00+00:00",
    )

    first = service.handle_input_langgraph_flow(contract)
    assert first.operation_result is not None

    with pytest.raises(ValueError, match="request_id has already been processed"):
        service.handle_input_langgraph_flow(contract)

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-lg-duplicate-runtime", limit=200)
    )
    event_names = [event.event_name for event in stored_events]
    assert event_names.count("operation_dispatched") == 1
    assert event_names.count("decision_outcome_attribution_recorded") == 1
    assert "decision_outcome_attribution_failed" not in event_names
