# ruff: noqa: E501
"""Local evolution lab for sandbox-only comparison workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
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
class FlowEvaluationInput:
    """Operational flow evaluation used to seed sandbox proposals and comparisons."""

    request_id: str
    session_id: str | None
    mission_id: str | None
    governance_decision: str | None
    operation_status: str | None
    total_events: int
    duration_seconds: float
    missing_required_events: list[str]
    anomaly_flags: list[str]
    continuity_action: str | None = None
    continuity_source: str | None = None
    continuity_runtime_mode: str | None = None
    registry_domains: list[str] = field(default_factory=list)
    shadow_specialists: list[str] = field(default_factory=list)
    domain_alignment_status: str | None = None
    memory_alignment_status: str | None = None
    specialist_sovereignty_status: str | None = None
    continuity_trace_status: str | None = None
    missing_continuity_signals: list[str] = field(default_factory=list)
    continuity_anomaly_flags: list[str] = field(default_factory=list)


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

    def create_proposal_from_flow_evaluation(
        self,
        evaluation: FlowEvaluationInput,
        *,
        target_scope: str,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Create a sandbox proposal from a pilot or runtime flow evaluation."""

        hypothesis = (
            "Flow anomalies should be reduced without relaxing governance or traceability."
            if evaluation.anomaly_flags or evaluation.missing_required_events
            else "Healthy flows may support a safer candidate path under the same controls."
        )
        expected_gain = (
            "Reduce missing trace events and operational anomalies in the observed flow."
            if evaluation.anomaly_flags or evaluation.missing_required_events
            else "Preserve flow health while improving execution quality."
        )
        source_signals = [
            f"observability://request/{evaluation.request_id}",
            f"governance://decision/{evaluation.governance_decision or 'unknown'}",
        ]
        if evaluation.session_id:
            source_signals.append(f"observability://session/{evaluation.session_id}")
        if evaluation.mission_id:
            source_signals.append(f"observability://mission/{evaluation.mission_id}")
        if evaluation.continuity_action:
            source_signals.append(f"continuity://action/{evaluation.continuity_action}")
        if evaluation.continuity_runtime_mode:
            source_signals.append(
                f"continuity://runtime/{evaluation.continuity_runtime_mode}"
            )
        for domain in evaluation.registry_domains:
            source_signals.append(f"domain://registry/{domain}")
        for specialist in evaluation.shadow_specialists:
            source_signals.append(f"specialist://shadow/{specialist}")
        if evaluation.continuity_trace_status:
            source_signals.append(
                f"continuity://trace-status/{evaluation.continuity_trace_status}"
            )
        return self.create_proposal(
            proposal_type="flow_evaluation_refinement",
            target_scope=target_scope,
            hypothesis=hypothesis,
            expected_gain=expected_gain,
            baseline_refs=[f"trace://{evaluation.request_id}"],
            source_signals=source_signals,
            risk_hint=self._risk_hint_from_flow(evaluation),
            proposed_tests=["python tools/go_live_internal_checklist.py --profile controlled"],
            strategy_name=strategy_name,
        )

    def compare_flow_evaluations(
        self,
        proposal: EvolutionProposalContract,
        *,
        baseline_label: str,
        candidate_label: str,
        baseline: FlowEvaluationInput,
        candidate: FlowEvaluationInput,
        governance_refs: list[str],
        notes: list[str],
        strategy_name: str | None = None,
    ) -> EvolutionComparisonResult:
        """Compare two observed flow evaluations under the sandbox policy."""

        return self.compare_candidate(
            proposal,
            ComparisonInput(
                baseline_label=baseline_label,
                candidate_label=candidate_label,
                baseline_metrics=self._metrics_from_flow_evaluation(baseline),
                candidate_metrics=self._metrics_from_flow_evaluation(candidate),
                governance_refs=governance_refs,
                notes=notes,
                strategy_name=strategy_name,
            ),
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
    def _metrics_from_flow_evaluation(evaluation: FlowEvaluationInput) -> dict[str, float]:
        missing_penalty = float(len(evaluation.missing_required_events))
        anomaly_penalty = float(len(evaluation.anomaly_flags))
        continuity_missing_penalty = float(len(evaluation.missing_continuity_signals))
        continuity_anomaly_penalty = float(len(evaluation.continuity_anomaly_flags))
        successful_operation = evaluation.operation_status == "completed"
        healthy_governance = evaluation.governance_decision in {
            "allow",
            "allow_with_conditions",
            "block",
            "defer_for_validation",
        }
        return {
            "success": 1.0 if successful_operation or healthy_governance else 0.0,
            "stability": max(
                0.0,
                1.0 - (anomaly_penalty * 0.25) - (continuity_anomaly_penalty * 0.15),
            ),
            "trace_completeness": max(0.0, 1.0 - (missing_penalty * 0.15)),
            "continuity_health": max(
                0.0,
                1.0
                - (continuity_missing_penalty * 0.2)
                - (continuity_anomaly_penalty * 0.25),
            ),
            "domain_alignment": EvolutionLabService._status_score(
                evaluation.domain_alignment_status
            ),
            "memory_alignment": EvolutionLabService._status_score(
                evaluation.memory_alignment_status
            ),
            "specialist_sovereignty": EvolutionLabService._status_score(
                evaluation.specialist_sovereignty_status
            ),
            "shadow_coverage": 1.0 if evaluation.shadow_specialists else 0.0,
            "runtime_statefulness": (
                1.0 if evaluation.continuity_runtime_mode == "langgraph_subflow" else 0.5
            ),
            "throughput": float(evaluation.total_events),
            "latency": max(0.0, 1.0 - min(evaluation.duration_seconds / 30.0, 1.0)),
            "risk": anomaly_penalty
            + (missing_penalty * 0.5)
            + (continuity_missing_penalty * 0.35)
            + (continuity_anomaly_penalty * 0.5),
        }

    @staticmethod
    def _status_score(status: str | None) -> float:
        weights = {
            "healthy": 1.0,
            "partial": 0.6,
            "incomplete": 0.2,
            "attention_required": 0.0,
        }
        return weights.get(status, 0.0)

    @staticmethod
    def _risk_hint_from_flow(evaluation: FlowEvaluationInput) -> str:
        if evaluation.anomaly_flags or evaluation.continuity_anomaly_flags:
            return "moderate"
        if evaluation.missing_required_events or evaluation.missing_continuity_signals:
            return "low_to_moderate"
        return "low"

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
