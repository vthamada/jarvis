from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import (
    FlowAudit,
    ObservabilityQuery,
)

from apps.jarvis_console.cli import JarvisConsole


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


@dataclass(frozen=True)
class OperatorScenario:
    name: str
    prompt: str
    session_id: str
    mission_id: str | None
    expected_decision: str
    expected_route: str | None
    expected_workflow_profile: str | None
    expected_operation_status: str | None


def audit_response(console: JarvisConsole, request_id: str) -> FlowAudit:
    return console.orchestrator.observability_service.audit_flow(
        ObservabilityQuery(request_id=request_id, limit=200)
    )


def assert_core_trace_invariants(audit: FlowAudit) -> None:
    assert audit.workflow_trace_status in {"healthy", "not_applicable"}
    assert not audit.missing_required_events
    assert not audit.anomaly_flags
    assert "input_received" in audit.event_names
    assert "plan_built" in audit.event_names
    assert "response_synthesized" in audit.event_names
    assert "memory_recorded" in audit.event_names
    assert audit.workflow_profile_status in {
        "healthy",
        "maturation_recommended",
        "not_applicable",
    }
    assert audit.request_identity_status == "healthy"
    assert audit.mission_policy_status in {
        "policy_aligned",
        "mandatory_override",
        "attention_required",
    }
    assert audit.capability_decision_status == "healthy"
    assert audit.capability_effectiveness in {"effective", "insufficient"}
    assert audit.handoff_adapter_status in {"healthy", "contained", "attention_required"}
    assert audit.expanded_eval_status in {
        "candidate_ready",
        "baseline_expanding",
        "not_in_phase",
        "attention_required",
    }
    assert audit.surface_axis_status in {
        "candidate_ready",
        "coverage_partial",
        "not_in_phase",
        "attention_required",
    }
    assert audit.ecosystem_state_status in {
        "candidate_ready",
        "coverage_partial",
        "not_in_phase",
    }
    assert audit.experiment_lane_status in {
        "controlled_candidate",
        "baseline_only",
        "out_of_lane",
        "attention_required",
    }
    assert audit.mind_domain_specialist_effectiveness in {
        "effective",
        "insufficient",
        "not_applicable",
    }
    assert audit.memory_maintenance_status != "incomplete"
    assert audit.memory_maintenance_effectiveness in {"effective", "insufficient"}


def test_console_operator_route_matrix_covers_promoted_journeys() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-e2e-routes"))
    scenarios = [
        OperatorScenario(
            name="controlled_plan",
            prompt="Plan the internal pilot rollout.",
            session_id="sess-e2e-plan",
            mission_id="mission-e2e-plan",
            expected_decision="allow_with_conditions",
            expected_route="operational_readiness",
            expected_workflow_profile="operational_readiness_workflow",
            expected_operation_status="completed",
        ),
        OperatorScenario(
            name="analysis_guided_review",
            prompt="Analyze the pilot data and compare the strongest signal.",
            session_id="sess-e2e-analysis",
            mission_id="mission-e2e-analysis",
            expected_decision="allow",
            expected_route="analysis",
            expected_workflow_profile="structured_analysis_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="decision_risk_review",
            prompt=(
                "Compare the decision risk of shipping today versus delaying the "
                "pilot by one week."
            ),
            session_id="sess-e2e-risk",
            mission_id="mission-e2e-risk",
            expected_decision="defer_for_validation",
            expected_route="decision_risk",
            expected_workflow_profile="decision_risk_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="governance_boundary_review",
            prompt=(
                "Review the governance boundary for the pilot and identify which "
                "approval is required."
            ),
            session_id="sess-e2e-governance",
            mission_id="mission-e2e-governance",
            expected_decision="defer_for_validation",
            expected_route="governance",
            expected_workflow_profile="governance_boundary_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="software_shadow_review",
            prompt="Analyze the Python service API rollout and compare the safest change.",
            session_id="sess-e2e-software",
            mission_id="mission-e2e-software",
            expected_decision="allow_with_conditions",
            expected_route="software_development",
            expected_workflow_profile="software_change_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="guardrail_block",
            prompt="Delete all pilot records now.",
            session_id="sess-e2e-guardrail",
            mission_id=None,
            expected_decision="block",
            expected_route=None,
            expected_workflow_profile=None,
            expected_operation_status=None,
        ),
    ]

    for scenario in scenarios:
        response = console.ask(
            scenario.prompt,
            session_id=scenario.session_id,
            mission_id=scenario.mission_id,
        )
        audit = audit_response(console, response.request_id)

        assert response.request_id == audit.request_id
        assert response.governance_decision.decision.value == scenario.expected_decision
        assert audit.governance_decision == scenario.expected_decision
        assert audit.operation_status == scenario.expected_operation_status
        assert_core_trace_invariants(audit)
        if scenario.expected_decision in {"allow", "allow_with_conditions"}:
            assert audit.capability_effectiveness == "effective"
            assert audit.handoff_adapter_status in {"healthy", "contained"}
            assert audit.expanded_eval_status in {
                "candidate_ready",
                "baseline_expanding",
            }
        elif scenario.expected_decision == "defer_for_validation":
            assert audit.capability_effectiveness == "insufficient"
            assert audit.handoff_adapter_status == "attention_required"
            assert audit.expanded_eval_status == "attention_required"
            assert audit.promotion_readiness == "blocked"

        if scenario.expected_route is not None:
            assert response.deliberative_plan.primary_route == scenario.expected_route
            assert audit.primary_route == scenario.expected_route
            assert (
                response.deliberative_plan.route_workflow_profile
                == scenario.expected_workflow_profile
            )
            if scenario.expected_operation_status == "completed":
                assert audit.workflow_domain_route == scenario.expected_route
                assert audit.workflow_profile == scenario.expected_workflow_profile
            else:
                assert audit.workflow_domain_route is None
                assert audit.workflow_profile is None
        else:
            assert audit.workflow_domain_route is None
            assert audit.workflow_profile is None


def test_console_operator_flow_reuses_mission_memory_and_emits_memory_maintenance() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-e2e-memory"))
    session_id = "sess-e2e-memory"
    mission_id = "mission-e2e-memory"

    console.ask(
        "Plan the internal pilot rollout.",
        session_id=session_id,
        mission_id=mission_id,
    )
    followup = console.ask(
        (
            "Plan the next pilot checkpoint and preserve the previous "
            "recommendation before concluding."
        ),
        session_id=session_id,
        mission_id=mission_id,
    )
    audit = audit_response(console, followup.request_id)

    assert followup.deliberative_plan.primary_route == "operational_readiness"
    assert followup.deliberative_plan.continuity_action == "continuar"
    assert_core_trace_invariants(audit)
    assert audit.continuity_action == "continuar"
    assert audit.continuity_source == "active_mission"
    assert audit.memory_causality_status == "causal_guidance"
    assert audit.semantic_memory_source == "active_mission"
    assert audit.procedural_memory_source == "active_mission"
    assert audit.memory_maintenance_status in {
        "cross_session_recall_active",
        "compaction_active",
    }
    assert audit.memory_maintenance_effectiveness == "effective"
    assert audit.context_compaction_status in {
        "compressed_live_context",
        "seeded_live_context",
    }
    assert audit.cross_session_recall_status == "active"


def test_console_operator_battery_keeps_promoted_contracts_coherent_together() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-e2e-battery"))
    scenario_matrix = [
        (
            "Plan the internal pilot rollout.",
            "sess-battery-main",
            "mission-battery-main",
        ),
        (
            "Analyze the pilot data and compare the strongest signal.",
            "sess-battery-analysis",
            "mission-battery-analysis",
        ),
        (
            "Review the governance boundary for the pilot and identify which approval is required.",
            "sess-battery-governance",
            "mission-battery-governance",
        ),
        (
            "Analyze the Python service API rollout and compare the safest change.",
            "sess-battery-software",
            "mission-battery-software",
        ),
    ]

    audits: list[FlowAudit] = []
    response_routes: set[str] = set()
    for prompt, session_id, mission_id in scenario_matrix:
        response = console.ask(prompt, session_id=session_id, mission_id=mission_id)
        response_routes.add(response.deliberative_plan.primary_route or "none")
        audits.append(audit_response(console, response.request_id))

    assert {
        "operational_readiness",
        "analysis",
        "governance",
        "software_development",
    } <= response_routes
    assert all(audit.request_identity_status == "healthy" for audit in audits)
    assert all(audit.capability_decision_status == "healthy" for audit in audits)
    assert all(
        audit.capability_effectiveness in {"effective", "insufficient"}
        for audit in audits
    )
    assert all(
        audit.handoff_adapter_status in {"healthy", "contained", "attention_required"}
        for audit in audits
    )
    assert any(audit.operation_status == "completed" for audit in audits)
    assert any(audit.memory_maintenance_effectiveness == "effective" for audit in audits)
    assert any(
        audit.expanded_eval_status in {"candidate_ready", "baseline_expanding"}
        for audit in audits
    )
    assert any(
        audit.mind_domain_specialist_effectiveness == "effective" for audit in audits
    )
    assert any(audit.continuity_source == "fresh_request" for audit in audits)
    assert any(audit.experiment_lane_status == "attention_required" for audit in audits)
