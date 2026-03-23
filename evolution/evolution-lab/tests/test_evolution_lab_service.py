from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from evolution_lab.service import ComparisonInput, EvolutionLabService, FlowEvaluationInput


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_evolution_lab_service_name() -> None:
    assert EvolutionLabService.name == "evolution-lab"


def test_evolution_lab_defaults_to_manual_variants_strategy() -> None:
    temp_dir = runtime_dir("evolution-lab-default-strategy")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    assert service.preferred_strategy() == "manual_variants"
    assert service.resolve_strategy_name(None) == "manual_variants"
    assert service.resolve_strategy_name("unknown") == "manual_variants"
    assert "manual_variants" in service.list_supported_strategies()


def test_evolution_lab_persists_proposals_and_sandbox_candidate_decision() -> None:
    temp_dir = runtime_dir("evolution-lab")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="workflow_refinement",
        target_scope="orchestrator-service",
        hypothesis="Candidate sequencing should improve stability without increasing risk.",
        expected_gain="Higher stability for the same low-risk profile.",
        baseline_refs=["baseline://orchestrator/current"],
        source_signals=["observability://flows/req-1"],
        proposed_tests=["pytest -q"],
    )

    comparison = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="current",
            candidate_label="candidate-a",
            baseline_metrics={"stability": 0.72, "risk": 0.2, "throughput": 0.5},
            candidate_metrics={"stability": 0.81, "risk": 0.18, "throughput": 0.56},
            governance_refs=["policy://sandbox/manual-review"],
            notes=["candidate kept sandbox-only"],
        ),
    )

    assert comparison.decision.decision == "sandbox_candidate"
    assert comparison.decision.promoted_to is None
    assert comparison.metric_deltas["stability"] > 0
    assert "strategy://manual_variants" in proposal.source_signals
    assert "preferred_strategy=manual_variants" in proposal.promotion_constraints
    assert "strategy=manual_variants" in comparison.decision.notes
    assert service.list_recent_proposals(limit=1)[0].target_scope == "orchestrator-service"
    assert service.list_recent_decisions(limit=1)[0].decision == "sandbox_candidate"


def test_evolution_lab_holds_baseline_when_risk_increases() -> None:
    temp_dir = runtime_dir("evolution-lab-hold")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="prompt_refinement",
        target_scope="synthesis-engine",
        hypothesis="A more aggressive style could improve throughput.",
        expected_gain="Faster synthesis.",
        baseline_refs=["baseline://synthesis/current"],
        strategy_name="textgrad_like_refinement",
    )

    comparison = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="current",
            candidate_label="candidate-risky",
            baseline_metrics={"stability": 0.8, "risk": 0.1},
            candidate_metrics={"stability": 0.78, "risk": 0.3},
            governance_refs=["policy://sandbox/manual-review"],
            notes=["candidate rejected for higher risk"],
            strategy_name="textgrad_like_refinement",
        ),
    )

    assert comparison.decision.decision == "hold_baseline"
    assert comparison.decision.rollback_plan_ref == "sandbox://rollback/current"
    assert "strategy://textgrad_like_refinement" in proposal.source_signals
    assert "strategy=textgrad_like_refinement" in comparison.decision.notes


def test_evolution_lab_creates_proposal_from_flow_evaluation() -> None:
    temp_dir = runtime_dir("evolution-lab-flow-proposal")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_flow_evaluation(
        FlowEvaluationInput(
            request_id="req-flow",
            session_id="sess-flow",
            mission_id="mission-flow",
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=8,
            duration_seconds=2.4,
            missing_required_events=["memory_recovered"],
            anomaly_flags=["operation_missing_completion"],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="langgraph_subflow",
            continuity_trace_status="attention_required",
            missing_continuity_signals=["memory_continuity_mode"],
            continuity_anomaly_flags=["retomar_missing_target_mission"],
        ),
        target_scope="orchestrator-service",
    )

    assert proposal.proposal_type == "flow_evaluation_refinement"
    assert "observability://request/req-flow" in proposal.source_signals
    assert "continuity://action/retomar" in proposal.source_signals
    assert "continuity://runtime/langgraph_subflow" in proposal.source_signals
    assert proposal.risk_hint == "moderate"


def test_evolution_lab_compares_flow_evaluations() -> None:
    temp_dir = runtime_dir("evolution-lab-flow-comparison")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="flow_evaluation_refinement",
        target_scope="orchestrator-service",
        hypothesis="Candidate path should improve trace health.",
        expected_gain="Fewer anomalies.",
        baseline_refs=["trace://req-a"],
    )

    comparison = service.compare_flow_evaluations(
        proposal,
        baseline_label="baseline",
        candidate_label="candidate",
        baseline=FlowEvaluationInput(
            request_id="req-a",
            session_id="sess-a",
            mission_id=None,
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=7,
            duration_seconds=3.2,
            missing_required_events=["memory_recovered"],
            anomaly_flags=["operation_missing_completion"],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="baseline_linear",
            continuity_trace_status="attention_required",
            missing_continuity_signals=["memory_continuity_mode"],
            continuity_anomaly_flags=["retomar_missing_target_mission"],
        ),
        candidate=FlowEvaluationInput(
            request_id="req-b",
            session_id="sess-b",
            mission_id=None,
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=8,
            duration_seconds=2.1,
            missing_required_events=[],
            anomaly_flags=[],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="langgraph_subflow",
            continuity_trace_status="healthy",
        ),
        governance_refs=["policy://sandbox/manual-review"],
        notes=["pilot comparison"],
    )

    assert comparison.decision.decision == "sandbox_candidate"
    assert comparison.metric_deltas["risk"] < 0
    assert comparison.metric_deltas["continuity_health"] > 0
    assert comparison.metric_deltas["runtime_statefulness"] > 0
