from tools.internal_pilot_support import PilotExecutionResult
from tools.verify_active_cut_baseline import build_payload, render_markdown


def make_pilot_result(  # type: ignore[no-untyped-def]
    *,
    scenario_id: str,
    workflow_domain_route: str | None,
    expected_route: str | None,
    route_matches_expectation: bool | None,
    expected_workflow_profile: str | None,
    workflow_profile_matches_expectation: bool | None,
    memory_causality_status: str = "causal_guidance",
    metacognitive_guidance_status: str = "healthy",
    mind_disagreement_status: str = "not_applicable",
    mind_validation_checkpoint_status: str = "not_applicable",
    memory_lifecycle_status: str = "retained",
    memory_review_status: str = "stable",
    memory_corpus_status: str = "stable",
    memory_retention_pressure: str | None = "low",
    cognitive_recomposition_applied: bool = False,
    cognitive_recomposition_reason: str | None = None,
    cognitive_recomposition_trigger: str | None = None,
    dominant_tension: str | None = "equilibrar profundidade analitica com conclusao util",
    primary_mind: str | None = "analise_estruturada",
    primary_route: str | None = None,
    arbitration_source: str | None = "mind_registry",
    primary_domain_driver: str | None = "dados_estatistica_e_inteligencia_analitica",
    mind_domain_specialist_status: str = "aligned",
    mind_domain_specialist_chain_status: str = "aligned",
    mind_domain_specialist_chain: str | None = None,
    specialist_subflow_status: str = "healthy",
    specialist_subflow_runtime_mode: str | None = "native_pipeline",
    mission_runtime_state_status: str = "healthy",
    semantic_memory_source: str | None = "active_mission",
    procedural_memory_source: str | None = "active_mission",
    semantic_memory_effects: list[str] | None = None,
    procedural_memory_effects: list[str] | None = None,
    semantic_memory_lifecycle: str | None = "retained",
    procedural_memory_lifecycle: str | None = "retained",
    coverage_tags: list[str] | None = None,
) -> PilotExecutionResult:
    return PilotExecutionResult(
        scenario_id=scenario_id,
        path_name="baseline",
        request_id=f"req-{scenario_id}",
        session_id=f"sess-{scenario_id}",
        mission_id=f"mission-{scenario_id}",
        intent="planning",
        governance_decision="allow_with_conditions",
        expected_decision="allow_with_conditions",
        decision_matches_expectation=True,
        operation_status=None,
        expected_operation=False,
        operation_matches_expectation=True,
        continuity_action="continuar",
        continuity_source="active_mission",
        continuity_runtime_mode="baseline_linear",
        specialist_subflow_status=specialist_subflow_status,
        specialist_subflow_runtime_mode=specialist_subflow_runtime_mode,
        mission_runtime_state_status=mission_runtime_state_status,
        workflow_domain_route=workflow_domain_route,
        registry_domains=[workflow_domain_route] if workflow_domain_route else [],
        shadow_specialists=[],
        domain_alignment_status="healthy",
        mind_alignment_status="healthy",
        identity_alignment_status="healthy",
        memory_alignment_status="healthy",
        specialist_sovereignty_status="healthy",
        axis_gate_status="healthy",
        workflow_trace_status="healthy",
        workflow_profile_status="healthy",
        metacognitive_guidance_status=metacognitive_guidance_status,
        mind_disagreement_status=mind_disagreement_status,
        mind_validation_checkpoint_status=mind_validation_checkpoint_status,
        memory_causality_status=memory_causality_status,
        primary_mind=primary_mind,
        primary_route=primary_route or workflow_domain_route,
        dominant_tension=dominant_tension,
        arbitration_source=arbitration_source,
        primary_domain_driver=primary_domain_driver,
        mind_domain_specialist_status=mind_domain_specialist_status,
        mind_domain_specialist_chain_status=mind_domain_specialist_chain_status,
        mind_domain_specialist_chain=(
            mind_domain_specialist_chain
            if mind_domain_specialist_chain is not None
            else (
                f"{primary_mind or 'none'} -> {primary_domain_driver or 'none'} -> "
                f"{(primary_route or workflow_domain_route) or 'none'} -> "
                "specialists[structured_analysis_specialist]"
            )
        ),
        cognitive_recomposition_applied=cognitive_recomposition_applied,
        cognitive_recomposition_reason=cognitive_recomposition_reason,
        cognitive_recomposition_trigger=cognitive_recomposition_trigger,
        semantic_memory_source=semantic_memory_source,
        procedural_memory_source=procedural_memory_source,
        semantic_memory_focus=[],
        procedural_memory_hint=None,
        semantic_memory_effects=semantic_memory_effects or ["framing", "continuity"],
        procedural_memory_effects=procedural_memory_effects or ["next_action", "continuity"],
        semantic_memory_lifecycle=semantic_memory_lifecycle,
        procedural_memory_lifecycle=procedural_memory_lifecycle,
        memory_lifecycle_status=memory_lifecycle_status,
        memory_review_status=memory_review_status,
        memory_corpus_status=memory_corpus_status,
        memory_retention_pressure=memory_retention_pressure,
        semantic_memory_specialists=[],
        procedural_memory_specialists=[],
        expected_continuity_action=None,
        continuity_matches_expectation=None,
        continuity_trace_status="healthy",
        missing_continuity_signals=[],
        continuity_anomaly_flags=[],
        trace_status="healthy",
        anomaly_flags=[],
        missing_required_events=[],
        total_events=12,
        duration_seconds=1.0,
        active_domains=[],
        specialist_hints=[],
        response_preview="preview",
        expected_route=expected_route,
        route_matches_expectation=route_matches_expectation,
        expected_workflow_profile=expected_workflow_profile,
        workflow_profile_matches_expectation=workflow_profile_matches_expectation,
        coverage_tags=coverage_tags or [],
    )


def test_verify_active_cut_baseline_reports_release_ready() -> None:
    payload = build_payload(
        pilot_results=[
            make_pilot_result(
                scenario_id="analysis-guided",
                workflow_domain_route="analysis",
                expected_route="analysis",
                route_matches_expectation=True,
                expected_workflow_profile="structured_analysis_workflow",
                workflow_profile_matches_expectation=True,
                coverage_tags=[
                    "mind_disagreement",
                    "dominant_tension",
                    "mind_domain_specialist",
                    "specialist_subflow",
                    "mission_runtime_state",
                ],
                mind_disagreement_status="validation_required",
                mind_validation_checkpoint_status="healthy",
            ),
            make_pilot_result(
                scenario_id="decision-risk",
                workflow_domain_route="decision_risk",
                expected_route="decision_risk",
                route_matches_expectation=True,
                expected_workflow_profile="decision_risk_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="governance",
                workflow_domain_route="governance",
                expected_route="governance",
                route_matches_expectation=True,
                expected_workflow_profile="governance_boundary_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="operational",
                workflow_domain_route="operational_readiness",
                expected_route="operational_readiness",
                route_matches_expectation=True,
                expected_workflow_profile="operational_readiness_workflow",
                workflow_profile_matches_expectation=True,
                coverage_tags=[
                    "memory_causality",
                    "memory_corpus",
                    "specialist_subflow",
                    "mission_runtime_state",
                ],
                memory_corpus_status="monitor",
                memory_retention_pressure="moderate",
            ),
            make_pilot_result(
                scenario_id="software",
                workflow_domain_route="software_development",
                expected_route="software_development",
                route_matches_expectation=True,
                expected_workflow_profile="software_change_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="strategy",
                workflow_domain_route="strategy",
                expected_route="strategy",
                route_matches_expectation=True,
                expected_workflow_profile="strategic_direction_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="recomposition",
                workflow_domain_route=None,
                expected_route=None,
                route_matches_expectation=None,
                expected_workflow_profile=None,
                workflow_profile_matches_expectation=None,
                cognitive_recomposition_applied=True,
                cognitive_recomposition_reason=(
                    "primary domain driver has no matching guided specialist route"
                ),
                cognitive_recomposition_trigger="specialist_route_impasse",
                coverage_tags=["cognitive_recomposition", "mission_runtime_state"],
            ),
        ]
    )

    assert payload["decision"] == "baseline_release_ready"
    assert payload["summary"]["active_routes_missing_workflows"] == 0
    assert payload["summary"]["promoted_routes_missing_consumer_contract"] == 0
    assert payload["summary"]["promoted_routes_missing_specialist_contract"] == 0
    assert payload["summary"]["benchmark_now_candidates"] == 3
    assert payload["summary"]["promotion_trigger_rules"] >= 5
    assert payload["summary"]["promoted_routes_missing_pilot_coverage"] == 0
    assert payload["summary"]["promoted_workflow_profiles_missing_pilot_coverage"] == 0
    assert payload["summary"]["memory_causality_ready_scenarios"] == 1
    assert payload["summary"]["mind_disagreement_ready_scenarios"] == 1
    assert payload["summary"]["mind_domain_specialist_ready_scenarios"] == 1
    assert payload["summary"]["memory_corpus_ready_scenarios"] == 1
    assert payload["summary"]["dominant_tension_ready_scenarios"] == 1
    assert payload["summary"]["specialist_subflow_ready_scenarios"] == 2
    assert payload["summary"]["mission_runtime_state_ready_scenarios"] == 3
    assert payload["summary"]["cognitive_recomposition_ready_scenarios"] == 1


def test_verify_active_cut_baseline_markdown_mentions_notes() -> None:
    payload = build_payload(
        pilot_results=[
            make_pilot_result(
                scenario_id="analysis-guided",
                workflow_domain_route="analysis",
                expected_route="analysis",
                route_matches_expectation=True,
                expected_workflow_profile="structured_analysis_workflow",
                workflow_profile_matches_expectation=True,
                coverage_tags=[
                    "memory_causality",
                    "memory_corpus",
                    "specialist_subflow",
                    "mission_runtime_state",
                ],
                memory_corpus_status="monitor",
                memory_retention_pressure="moderate",
            ),
            make_pilot_result(
                scenario_id="recomposition",
                workflow_domain_route=None,
                expected_route=None,
                route_matches_expectation=None,
                expected_workflow_profile=None,
                workflow_profile_matches_expectation=None,
                cognitive_recomposition_applied=True,
                cognitive_recomposition_reason=(
                    "primary domain driver has no matching guided specialist route"
                ),
                cognitive_recomposition_trigger="specialist_route_impasse",
                coverage_tags=["cognitive_recomposition"],
            ),
        ]
    )

    rendered = render_markdown(payload)

    assert "Active V2 Cut Release Baseline" in rendered
    assert "benchmark_now candidates" in rendered
    assert "consumer contract" in rendered
    assert "targeted pilot route matches" in rendered
    assert "memory causality scenarios ready" in rendered
    assert "mind disagreement scenarios ready" in rendered
    assert "mind-domain-specialist scenarios ready" in rendered
    assert "memory corpus scenarios ready" in rendered
    assert "dominant tension scenarios ready" in rendered
    assert "specialist subflow scenarios ready" in rendered
    assert "mission runtime state scenarios ready" in rendered


def test_verify_active_cut_baseline_requires_deliberate_cognitive_coverage() -> None:
    payload = build_payload(
        pilot_results=[
            make_pilot_result(
                scenario_id="analysis-guided",
                workflow_domain_route="analysis",
                expected_route="analysis",
                route_matches_expectation=True,
                expected_workflow_profile="structured_analysis_workflow",
                workflow_profile_matches_expectation=True,
                coverage_tags=["mind_disagreement"],
            ),
            make_pilot_result(
                scenario_id="decision-risk",
                workflow_domain_route="decision_risk",
                expected_route="decision_risk",
                route_matches_expectation=True,
                expected_workflow_profile="decision_risk_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="governance",
                workflow_domain_route="governance",
                expected_route="governance",
                route_matches_expectation=True,
                expected_workflow_profile="governance_boundary_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="operational",
                workflow_domain_route="operational_readiness",
                expected_route="operational_readiness",
                route_matches_expectation=True,
                expected_workflow_profile="operational_readiness_workflow",
                workflow_profile_matches_expectation=True,
                coverage_tags=["memory_causality"],
            ),
            make_pilot_result(
                scenario_id="software",
                workflow_domain_route="software_development",
                expected_route="software_development",
                route_matches_expectation=True,
                expected_workflow_profile="software_change_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="strategy",
                workflow_domain_route="strategy",
                expected_route="strategy",
                route_matches_expectation=True,
                expected_workflow_profile="strategic_direction_workflow",
                workflow_profile_matches_expectation=True,
            ),
            make_pilot_result(
                scenario_id="recomposition",
                workflow_domain_route=None,
                expected_route=None,
                route_matches_expectation=None,
                expected_workflow_profile=None,
                workflow_profile_matches_expectation=None,
                cognitive_recomposition_applied=True,
                cognitive_recomposition_reason=(
                    "primary domain driver has no matching guided specialist route"
                ),
                cognitive_recomposition_trigger="specialist_route_impasse",
                coverage_tags=["cognitive_recomposition"],
                dominant_tension=None,
                arbitration_source=None,
                primary_domain_driver=None,
            ),
        ]
    )

    assert payload["decision"] == "baseline_requires_iteration"
    assert payload["summary"]["mind_disagreement_ready_scenarios"] == 0
    assert payload["summary"]["mind_domain_specialist_ready_scenarios"] == 0
    assert payload["summary"]["memory_corpus_ready_scenarios"] == 0
    assert payload["summary"]["dominant_tension_ready_scenarios"] == 0
