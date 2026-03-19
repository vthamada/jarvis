from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from evolution_lab.service import ComparisonInput, EvolutionLabService


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
