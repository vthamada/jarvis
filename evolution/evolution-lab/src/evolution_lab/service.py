# ruff: noqa: E501
"""Local evolution lab for sandbox-only comparison workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from pathlib import Path
from uuid import uuid4

from evolution_lab.repository import EvolutionLabRepository
from shared.contracts import EvolutionDecisionContract, EvolutionProposalContract
from shared.types import EvolutionDecisionId, EvolutionProposalId

DEFAULT_EVOLUTION_STRATEGY = "manual_variants"
SUPPORTED_EVOLUTION_STRATEGIES = (
    "manual_variants",
    "mipro_like_search",
    "textgrad_like_refinement",
)


@dataclass(frozen=True)
class ComparisonInput:
    """Input payload for comparing a candidate against the current baseline."""

    baseline_label: str
    candidate_label: str
    baseline_metrics: dict[str, float]
    candidate_metrics: dict[str, float]
    governance_refs: list[str]
    notes: list[str]
    strategy_name: str | None = None


@dataclass(frozen=True)
class EvolutionComparisonResult:
    """Structured output for a sandbox comparison."""

    proposal: EvolutionProposalContract
    decision: EvolutionDecisionContract
    metric_deltas: dict[str, float]


class EvolutionLabService:
    """Persist proposals and compare candidates without automatic promotion."""

    name = "evolution-lab"

    def __init__(self, database_path: str | None = None) -> None:
        runtime_path = database_path or getenv("JARVIS_EVOLUTION_DB")
        resolved = (
            Path(runtime_path) if runtime_path else Path.cwd() / ".jarvis_runtime" / "evolution.db"
        )
        self.repository = EvolutionLabRepository(resolved)

    def create_proposal(
        self,
        *,
        proposal_type: str,
        target_scope: str,
        hypothesis: str,
        expected_gain: str,
        baseline_refs: list[str],
        source_signals: list[str] | None = None,
        risk_hint: str | None = None,
        proposed_tests: list[str] | None = None,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Register a sandbox proposal for later comparison."""

        chosen_strategy = self.resolve_strategy_name(strategy_name)
        strategy_signal = f"strategy://{chosen_strategy}"
        signals = list(source_signals or [])
        if strategy_signal not in signals:
            signals.append(strategy_signal)

        proposal = EvolutionProposalContract(
            evolution_proposal_id=EvolutionProposalId(f"evo-proposal-{uuid4().hex[:8]}"),
            proposal_type=proposal_type,
            target_scope=target_scope,
            hypothesis=hypothesis,
            expected_gain=expected_gain,
            timestamp=self.now(),
            source_signals=signals,
            baseline_refs=baseline_refs,
            risk_hint=risk_hint,
            requires_sandbox=True,
            proposed_tests=proposed_tests or [],
            promotion_constraints=[
                "manual_review_required",
                "no_automatic_promotion",
                "rollback_plan_mandatory",
                f"preferred_strategy={chosen_strategy}",
            ],
        )
        self.repository.record_proposal(proposal)
        return proposal

    def compare_candidate(
        self,
        proposal: EvolutionProposalContract,
        comparison: ComparisonInput,
    ) -> EvolutionComparisonResult:
        """Compare a candidate against the baseline and keep the outcome sandbox-only."""

        chosen_strategy = self.resolve_strategy_name(comparison.strategy_name)
        metric_deltas = {
            key: round(
                comparison.candidate_metrics.get(key, 0.0)
                - comparison.baseline_metrics.get(key, 0.0),
                4,
            )
            for key in sorted(set(comparison.baseline_metrics) | set(comparison.candidate_metrics))
        }
        stability_score = round(comparison.candidate_metrics.get("stability", 0.0), 4)
        risk_score = round(comparison.candidate_metrics.get("risk", 0.0), 4)
        improved = sum(1 for value in metric_deltas.values() if value > 0)
        degraded = sum(1 for value in metric_deltas.values() if value < 0)
        decision_name = (
            "sandbox_candidate"
            if improved >= degraded
            and risk_score <= comparison.baseline_metrics.get("risk", risk_score)
            else "hold_baseline"
        )
        summary = (
            f"baseline={comparison.baseline_label}; candidate={comparison.candidate_label}; "
            f"strategy={chosen_strategy}; improved_metrics={improved}; degraded_metrics={degraded}; "
            f"stability={stability_score}; risk={risk_score}"
        )
        decision = EvolutionDecisionContract(
            evolution_decision_id=EvolutionDecisionId(f"evo-decision-{uuid4().hex[:8]}"),
            evolution_proposal_id=proposal.evolution_proposal_id,
            decision=decision_name,
            comparison_summary=summary,
            timestamp=self.now(),
            promoted_to=None,
            rollback_plan_ref=f"sandbox://rollback/{comparison.baseline_label}",
            governance_refs=comparison.governance_refs,
            stability_score=stability_score,
            risk_score=risk_score,
            notes=comparison.notes
            + [f"strategy={chosen_strategy}", f"metric_deltas={metric_deltas}"],
        )
        self.repository.record_decision(decision)
        return EvolutionComparisonResult(
            proposal=proposal,
            decision=decision,
            metric_deltas=metric_deltas,
        )

    def list_recent_proposals(self, limit: int = 20) -> list[EvolutionProposalContract]:
        """Return recently registered sandbox proposals."""

        return self.repository.list_proposals(limit=limit)

    def list_recent_decisions(self, limit: int = 20) -> list[EvolutionDecisionContract]:
        """Return recent evolution decisions for local review."""

        return self.repository.list_decisions(limit=limit)

    def preferred_strategy(self) -> str:
        """Return the current sandbox-first evolution strategy."""

        return DEFAULT_EVOLUTION_STRATEGY

    def list_supported_strategies(self) -> list[str]:
        """Expose the supported evolution strategies for local review."""

        return list(SUPPORTED_EVOLUTION_STRATEGIES)

    def resolve_strategy_name(self, strategy_name: str | None) -> str:
        """Normalize strategy selection to the supported sandbox set."""

        if strategy_name in SUPPORTED_EVOLUTION_STRATEGIES:
            return str(strategy_name)
        return self.preferred_strategy()

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
