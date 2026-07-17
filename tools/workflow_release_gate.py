"""Compose the governed workflow release gate without authorizing promotion."""

from __future__ import annotations

from dataclasses import dataclass

from evolution_lab.service import EvolutionLabService

from shared.contracts import (
    EvolutionProposalContract,
    EvolutionReviewDecisionContract,
    PromotionGateDecisionContract,
    SandboxToReleaseChecklistContract,
    WorkflowProfileVersionContract,
    WorkflowRollbackPlanContract,
    WorkflowVariantEvalRunContract,
)


@dataclass(frozen=True)
class WorkflowReleaseGateResult:
    """Checklist plus machine gate; final human promotion stays separate."""

    checklist: SandboxToReleaseChecklistContract
    gate_decision: PromotionGateDecisionContract


def evaluate_workflow_release_gate(
    *,
    service: EvolutionLabService,
    proposal: EvolutionProposalContract,
    review_decision: EvolutionReviewDecisionContract,
    candidate: WorkflowProfileVersionContract,
    workflow_eval: WorkflowVariantEvalRunContract | None,
    rollback_plan: WorkflowRollbackPlanContract | None,
    completed_external_gates: list[str],
) -> WorkflowReleaseGateResult:
    """Evaluate all workflow evidence and keep promotion unauthorized."""

    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review_decision,
        workflow_candidate=candidate,
        workflow_variant_eval=workflow_eval,
        workflow_rollback_plan=rollback_plan,
    )
    gate = service.evaluate_promotion_gate(
        checklist,
        completed_gates=completed_external_gates,
    )
    return WorkflowReleaseGateResult(
        checklist=checklist,
        gate_decision=gate,
    )
