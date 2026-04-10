from tools.evolution_from_pilot import _evaluation_from_dict, render_text


def test_evaluation_from_dict_preserves_adaptive_intervention_policy_status() -> None:
    evaluation = _evaluation_from_dict(
        {
            "request_id": "req-1",
            "session_id": "sess-1",
            "mission_id": None,
            "governance_decision": "allow_with_conditions",
            "operation_status": "completed",
            "total_events": 7,
            "duration_seconds": 1.8,
            "missing_required_events": [],
            "anomaly_flags": [],
            "adaptive_intervention_status": "healthy",
            "adaptive_intervention_effectiveness": "effective",
            "adaptive_intervention_policy_status": "policy_aligned",
        }
    )

    assert evaluation.adaptive_intervention_status == "healthy"
    assert evaluation.adaptive_intervention_effectiveness == "effective"
    assert evaluation.adaptive_intervention_policy_status == "policy_aligned"


def test_render_text_reports_adaptive_intervention_policy_assessment() -> None:
    rendered = render_text(
        {
            "recent_trace_proposals": [],
            "comparison_decisions": [
                {
                    "scenario_id": "scenario-a",
                    "decision": {"decision": "sandbox_candidate", "rollback_plan_ref": "sandbox://rollback/a"},
                    "baseline_workflow_profile_assessment": "baseline_saudavel",
                    "candidate_workflow_profile_assessment": "baseline_saudavel",
                    "baseline_workflow_output_assessment": "baseline_saudavel",
                    "candidate_workflow_output_assessment": "baseline_saudavel",
                    "baseline_metacognitive_guidance_assessment": "healthy",
                    "candidate_metacognitive_guidance_assessment": "healthy",
                    "baseline_mind_disagreement_assessment": "not_applicable",
                    "candidate_mind_disagreement_assessment": "not_applicable",
                    "baseline_memory_causality_assessment": "causal_guidance",
                    "candidate_memory_causality_assessment": "causal_guidance",
                    "baseline_adaptive_intervention_policy_assessment": "policy_aligned",
                    "candidate_adaptive_intervention_policy_assessment": "review_recommended",
                    "baseline_memory_lifecycle_assessment": "retained",
                    "candidate_memory_lifecycle_assessment": "retained",
                    "baseline_memory_corpus_assessment": "stable",
                    "candidate_memory_corpus_assessment": "stable",
                    "baseline_workflow_checkpoint_assessment": "healthy",
                    "candidate_workflow_checkpoint_assessment": "healthy",
                    "baseline_workflow_resume_assessment": "resume_available",
                    "candidate_workflow_resume_assessment": "resume_available",
                    "baseline_procedural_artifact_assessment": "reusable",
                    "candidate_procedural_artifact_assessment": "reusable",
                    "baseline_mind_domain_specialist_assessment": "aligned",
                    "candidate_mind_domain_specialist_assessment": "aligned",
                    "baseline_mind_domain_specialist_chain_assessment": "aligned",
                    "candidate_mind_domain_specialist_chain_assessment": "aligned",
                    "baseline_cognitive_recomposition_assessment": "not_applicable",
                    "candidate_cognitive_recomposition_assessment": "not_applicable",
                }
            ],
        }
    )

    assert "adaptive_intervention_policy=policy_aligned->review_recommended" in rendered
