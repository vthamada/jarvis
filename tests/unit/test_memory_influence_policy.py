from dataclasses import replace

from governance_service.service import GovernanceService
from memory_service.service import MemoryService

from shared.contract_validation import validate_contract_instance
from shared.contracts import MemoryInfluenceSignalContract
from shared.memory_influence_policy import (
    evaluate_memory_influence_policy,
    semantic_memory_freshness_status,
)
from shared.schemas import (
    MEMORY_INFLUENCE_GOVERNANCE_ASSESSMENT_SCHEMA,
    MEMORY_INFLUENCE_POLICY_DECISION_SCHEMA,
    MEMORY_INFLUENCE_SIGNAL_SCHEMA,
)


def _signal(
    source_kind: str,
    *,
    summary: str | None = None,
) -> MemoryInfluenceSignalContract:
    review_status = {
        "reviewed_learning": "approved",
        "reflection": "candidate",
        "procedural": "stable",
        "semantic": "stable",
    }[source_kind]
    return MemoryInfluenceSignalContract(
        signal_ref=f"memory-influence://{source_kind}/1",
        source_kind=source_kind,
        summary=summary or f"{source_kind} directive",
        evidence_refs=[f"evidence://memory-influence/{source_kind}/1"],
        conflict_group=(
            "learning_guidance"
            if source_kind in {"reviewed_learning", "reflection"}
            else f"{source_kind}_context"
        ),
        directive=summary or f"{source_kind} directive",
        route="strategy",
        workflow_profile="strategic_direction_workflow",
        domain="estrategia_e_pensamento_sistemico",
        lifecycle_status="reviewed" if source_kind == "reviewed_learning" else "retained",
        review_status=review_status,
        observed_at=(
            "2026-07-16T21:00:00Z" if source_kind == "semantic" else None
        ),
        freshness_status="current" if source_kind == "semantic" else None,
        relevance_score=0.8 if source_kind == "semantic" else None,
        relevance_reason=(
            "route_workflow_domain_match" if source_kind == "semantic" else None
        ),
    )


def _evaluate(signals):  # type: ignore[no-untyped-def]
    return evaluate_memory_influence_policy(
        decision_id="memory-influence-decision://test/1",
        signals=signals,
        route="strategy",
        workflow_profile="strategic_direction_workflow",
        domain="estrategia_e_pensamento_sistemico",
        generated_at="2026-07-16T22:00:00Z",
    )


def test_memory_influence_policy_prioritizes_reviewed_guidance_and_audits_conflict() -> None:
    reviewed = _signal("reviewed_learning", summary="use reviewed milestone framing")
    reflection = _signal("reflection", summary="skip milestone framing")
    procedural = _signal("procedural")
    semantic = _signal("semantic")

    decision = _evaluate([reflection, semantic, reviewed, procedural])

    assert decision.decision_status == "applied_with_conflict_resolution"
    assert decision.priority_order == [
        "reviewed_learning",
        "procedural",
        "semantic",
        "reflection",
    ]
    assert decision.selected_refs == [
        reviewed.signal_ref,
        procedural.signal_ref,
        semantic.signal_ref,
    ]
    assert decision.ignored_refs == [reflection.signal_ref]
    assert decision.conflict_refs == [reviewed.signal_ref, reflection.signal_ref]
    assert decision.non_use_reasons[reflection.signal_ref] == (
        f"conflict_with_higher_priority:{reviewed.signal_ref}"
    )
    assert decision.memory_write_allowed is False
    assert decision.automatic_promotion_allowed is False
    assert decision.core_mutation_allowed is False
    assert validate_contract_instance(
        reviewed,
        schema=MEMORY_INFLUENCE_SIGNAL_SCHEMA,
    ).status == "coherent"
    assert validate_contract_instance(
        decision,
        schema=MEMORY_INFLUENCE_POLICY_DECISION_SCHEMA,
    ).status == "coherent"


def test_memory_influence_policy_records_scope_evidence_and_authority_non_use() -> None:
    semantic = _signal("semantic")
    no_evidence = replace(
        _signal("procedural"),
        evidence_refs=[],
    )
    wrong_scope = replace(
        _signal("reflection"),
        route="analysis",
    )
    authority_claim = replace(
        _signal("reviewed_learning"),
        automatic_promotion_allowed=True,
    )

    decision = _evaluate(
        [semantic, no_evidence, wrong_scope, authority_claim]
    )

    assert decision.decision_status == "applied"
    assert decision.selected_refs == [semantic.signal_ref]
    assert decision.non_use_reasons[no_evidence.signal_ref] == "evidence_required"
    assert decision.non_use_reasons[wrong_scope.signal_ref] == "scope_mismatch:route"
    assert decision.non_use_reasons[authority_claim.signal_ref] == (
        "authority_claim_not_allowed"
    )

    no_signals = _evaluate([])
    assert no_signals.decision_status == "not_applicable"
    assert validate_contract_instance(
        no_signals,
        schema=MEMORY_INFLUENCE_POLICY_DECISION_SCHEMA,
    ).status == "coherent"


def test_memory_service_delegates_to_same_policy_without_persistence(tmp_path) -> None:
    service = MemoryService(
        database_url=f"sqlite:///{(tmp_path / 'memory.db').as_posix()}"
    )
    signal = _signal("semantic")

    decision = service.evaluate_influence_policy(
        decision_id="memory-influence-decision://memory-service/1",
        signals=[signal],
        route="strategy",
        workflow_profile="strategic_direction_workflow",
        domain="estrategia_e_pensamento_sistemico",
        generated_at="2026-07-16T22:10:00Z",
    )

    assert decision.decision_status == "applied"
    assert decision.selected_refs == [signal.signal_ref]
    assert service.repository.fetch_recent_turns("policy-test", limit=10) == []


def test_governance_blocks_forged_memory_influence_authority() -> None:
    decision = _evaluate([_signal("semantic")])
    governance = GovernanceService()

    governed = governance.assess_memory_influence_policy(
        decision,
        assessed_at="2026-07-16T22:20:00Z",
    )
    blocked = governance.assess_memory_influence_policy(
        replace(decision, memory_write_allowed=True),
        assessed_at="2026-07-16T22:20:01Z",
    )

    assert governed.assessment_status == "governed"
    assert governed.causal_use_allowed is True
    assert governed.decision_mutation_allowed is False
    assert blocked.assessment_status == "blocked"
    assert blocked.causal_use_allowed is False
    assert "memory_influence_authority_claim_not_allowed" in blocked.blockers
    assert validate_contract_instance(
        governed,
        schema=MEMORY_INFLUENCE_GOVERNANCE_ASSESSMENT_SCHEMA,
    ).status == "coherent"


def test_semantic_memory_freshness_is_derived_from_canonical_timestamps() -> None:
    generated_at = "2026-07-18T12:00:00Z"

    assert (
        semantic_memory_freshness_status(
            "2026-07-18T11:00:00Z",
            generated_at,
        )
        == "current"
    )
    assert (
        semantic_memory_freshness_status(
            "2026-06-28T12:00:00Z",
            generated_at,
        )
        == "aging"
    )
    assert (
        semantic_memory_freshness_status(
            "2026-05-01T12:00:00Z",
            generated_at,
        )
        == "stale"
    )
    assert semantic_memory_freshness_status("invalid", generated_at) == "unknown"


def test_memory_influence_policy_rejects_stale_or_forged_semantic_freshness() -> None:
    stale = replace(
        _signal("semantic"),
        observed_at="2026-05-01T12:00:00Z",
        freshness_status="stale",
    )
    forged = replace(
        _signal("semantic"),
        signal_ref="memory-influence://semantic/forged",
        observed_at="2026-05-01T12:00:00Z",
        freshness_status="current",
    )

    stale_decision = _evaluate([stale])
    forged_decision = _evaluate([forged])

    assert stale_decision.decision_status == "blocked_no_eligible_signal"
    assert stale_decision.freshness_statuses[stale.signal_ref] == "stale"
    assert stale_decision.non_use_reasons[stale.signal_ref] == (
        "freshness_not_eligible:stale"
    )
    assert forged_decision.decision_status == "blocked_no_eligible_signal"
    assert forged_decision.freshness_statuses[forged.signal_ref] == "stale"
    assert forged_decision.non_use_reasons[forged.signal_ref] == (
        "semantic_freshness_claim_mismatch:current:stale"
    )


def test_memory_influence_policy_rejects_semantic_write_authority() -> None:
    writable = replace(
        _signal("semantic"),
        signal_ref="memory-influence://semantic/writable",
        read_only=False,
        memory_write_allowed=True,
    )

    decision = _evaluate([writable])

    assert decision.decision_status == "blocked_no_eligible_signal"
    assert decision.selected_refs == []
    assert decision.non_use_reasons[writable.signal_ref] == (
        "authority_claim_not_allowed"
    )


def test_memory_influence_policy_resolves_semantic_conflict_by_relevance() -> None:
    lower = replace(
        _signal("semantic", summary="reuse the older strategic frame"),
        signal_ref="memory-influence://semantic/a-lower",
        relevance_score=0.6,
        relevance_reason="related_mission_similarity",
    )
    higher = replace(
        _signal("semantic", summary="continue the active strategic frame"),
        signal_ref="memory-influence://semantic/z-higher",
        relevance_score=0.95,
        relevance_reason="active_mission_id_match",
    )

    decision = _evaluate([lower, higher])

    assert decision.decision_status == "applied_with_conflict_resolution"
    assert decision.selected_refs == [higher.signal_ref]
    assert decision.ignored_refs == [lower.signal_ref]
    assert decision.conflict_refs == [higher.signal_ref, lower.signal_ref]
    assert decision.relevance_scores == {
        lower.signal_ref: 0.6,
        higher.signal_ref: 0.95,
    }
    assert decision.non_use_reasons[lower.signal_ref] == (
        f"conflict_with_higher_priority:{higher.signal_ref}"
    )
