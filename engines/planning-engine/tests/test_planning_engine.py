from dataclasses import replace

from planning_engine.engine import AdaptiveIntervention, PlanningContext, PlanningEngine

from shared.contracts import (
    AdapterActionRequestContract,
    ReviewedProceduralPlaybookContract,
    SemanticMemoryCandidateContract,
    SpecialistContributionContract,
    WorkflowLifecycleTransitionContract,
)
from shared.domain_registry import build_active_workflow_version_registry, workflow_definition_hash
from tests.unit.test_workflow_lifecycle import _activation


def _reviewed_procedural_playbook(
    *,
    playbook_id: str = "reviewed-playbook://strategy/checkpoint",
    version: str = "1.0.0",
    route: str = "strategy",
    workflow_profile: str = "strategic_direction_workflow",
    domain: str = "estrategia_e_pensamento_sistemico",
    review_status: str = "approved",
    bounded_steps: list[str] | None = None,
) -> ReviewedProceduralPlaybookContract:
    return ReviewedProceduralPlaybookContract(
        playbook_id=playbook_id,
        version=version,
        source_candidate_id="playbook-candidate://strategy/checkpoint",
        source_review_decision_id=f"review-decision://strategy/{version}",
        evolution_proposal_id="proposal-reviewed-playbook",
        review_status=review_status,
        procedure_name="bounded strategic checkpoint",
        route=route,
        workflow_profile=workflow_profile,
        domain=domain,
        bounded_steps=bounded_steps or [
            "collect decision evidence",
            "validate the rollback checkpoint",
        ],
        allowed_usage=["planning_context"],
        evidence_refs=["evidence://strategy/checkpoint"],
        rollback_plan_ref="rollback://strategy/checkpoint",
        timestamp="2026-07-18T12:00:00Z",
    )


def test_planning_engine_name() -> None:
    assert PlanningEngine.name == "planning-engine"


def test_planning_engine_preserves_explicit_adapter_action_request() -> None:
    request = AdapterActionRequestContract(
        adapter_id="local_text_file",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        operation="create_text",
        resource_scope="configured_text_root",
        resource_ref="text://reports/adapter-plan.txt",
    )
    engine = PlanningEngine()

    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Prepare the exact governed adapter request",
            recovered_context=[],
            active_domains=["software_development"],
            active_minds=["mente_executiva"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            adapter_action_request=request,
        )
    )

    assert plan.adapter_action_request == request
    assert (
        plan.capability_decision_selected_mode
        == "core_with_supervised_external_operation"
    )
    assert "supervised_external_adapter" in (
        plan.capability_decision_selected_capabilities
    )
    assert "local_safe_operation" not in plan.capability_decision_selected_capabilities
    assert plan.capability_decision_tool_class == "supervised_external_adapter"

    refined = engine.refine_task_plan(
        plan,
        specialist_summary="adapter request remains exact",
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="structured_analysis_specialist",
                role="subordinate_adapter_review",
                focus="preserve exact adapter metadata",
                findings=[],
                recommendation="preserve the typed request",
                confidence=0.9,
            )
        ],
    )
    assert refined.adapter_action_request == request
    assert (
        refined.capability_decision_selected_mode
        == "core_with_supervised_external_operation"
    )


def test_planning_engine_never_infers_adapter_authority_from_prompt_text() -> None:
    engine = PlanningEngine()

    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query=(
                "Use the local_text_file adapter and prepare_external_action "
                "through a supervised external tool"
            ),
            recovered_context=[],
            active_domains=["software_development"],
            active_minds=["mente_executiva"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
        )
    )

    assert plan.adapter_action_request is None
    assert (
        plan.capability_decision_selected_mode
        != "core_with_supervised_external_operation"
    )
    assert "supervised_external_adapter" not in (
        plan.capability_decision_selected_capabilities
    )


def test_planning_engine_carries_the_human_promoted_workflow_definition() -> None:
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-08-12T10:00:00Z",
    )
    baseline = next(
        item
        for item in registry.versions
        if item.workflow_profile == "software_change_workflow"
    )
    steps = [*baseline.workflow_steps, "apply the promoted bounded checkpoint"]
    checkpoints = [*baseline.workflow_checkpoints, "promoted_checkpoint_applied"]
    decisions = [*baseline.workflow_decision_points, "promoted_checkpoint_gate"]
    success = [*baseline.success_criteria, "promoted checkpoint remains attributable"]
    candidate_hash = workflow_definition_hash(
        workflow_steps=steps,
        workflow_checkpoints=checkpoints,
        workflow_decision_points=decisions,
        success_criteria=success,
    )
    transition = WorkflowLifecycleTransitionContract(
        transition_id="workflow-lifecycle-transition://software-change/runtime",
        workflow_profile=baseline.workflow_profile,
        route=baseline.route,
        transition_action="activate_candidate",
        transition_status="active_promoted",
        revision=1,
        previous_transition_id=None,
        previous_transition_fingerprint=None,
        source_registry_ref=baseline.source_registry_ref,
        source_registry_fingerprint=baseline.source_registry_fingerprint,
        baseline_version_ref=baseline.workflow_version_id,
        baseline_definition_hash=baseline.definition_hash,
        candidate_version_ref="workflow-version://software_change_workflow/1.1.0",
        candidate_definition_hash=candidate_hash,
        active_version_ref="workflow-version://software_change_workflow/1.1.0",
        active_definition_hash=candidate_hash,
        active_workflow_steps=steps,
        active_workflow_checkpoints=checkpoints,
        active_workflow_decision_points=decisions,
        active_success_criteria=success,
        evolution_proposal_id="proposal://workflow/runtime",
        proposal_fingerprint="1" * 64,
        review_decision_id="review://workflow/runtime",
        review_decision_fingerprint="2" * 64,
        release_checklist_id="checklist://workflow/runtime",
        release_checklist_fingerprint="3" * 64,
        promotion_gate_id="gate://workflow/runtime",
        promotion_gate_fingerprint="4" * 64,
        workflow_eval_run_id="eval://workflow/runtime",
        workflow_eval_run_fingerprint="5" * 64,
        rollback_plan_id="rollback://workflow/runtime",
        rollback_plan_fingerprint="6" * 64,
        human_authorization_ref="human-authorization://workflow/runtime",
        operator_ref="operator://runtime-reviewer",
        evidence_refs=["evidence://workflow/eval", "evidence://workflow/release"],
        completed_test_refs=["test://workflow/release"],
        failure_refs=[],
        timestamp="2026-08-12T10:30:00Z",
    )

    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan a bounded software change",
            recovered_context=[],
            active_domains=["software_development"],
            active_minds=["mente_executiva"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            primary_route=baseline.route,
            route_workflow_profile=baseline.workflow_profile,
            route_workflow_steps=steps,
            route_workflow_checkpoints=checkpoints,
            route_workflow_decision_points=decisions,
            workflow_lifecycle_transition=transition,
        )
    )

    assert plan.workflow_lifecycle_transition == transition
    assert plan.route_workflow_steps == steps
    assert plan.route_workflow_checkpoints == checkpoints
    assert plan.route_workflow_decision_points == decisions
    assert "promoted checkpoint remains attributable" in plan.success_criteria


def test_planning_engine_preserves_every_promoted_success_criterion() -> None:
    base = _activation()
    success = [f"promoted criterion {index}" for index in range(1, 11)]
    promoted_hash = workflow_definition_hash(
        workflow_steps=base.active_workflow_steps,
        workflow_checkpoints=base.active_workflow_checkpoints,
        workflow_decision_points=base.active_workflow_decision_points,
        success_criteria=success,
    )
    transition = replace(
        base,
        active_success_criteria=success,
        active_definition_hash=promoted_hash,
        candidate_definition_hash=promoted_hash,
    )

    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan a bounded software change",
            recovered_context=[],
            active_domains=["software_development"],
            active_minds=["mente_executiva"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            primary_route=transition.route,
            route_workflow_profile=transition.workflow_profile,
            route_workflow_steps=list(transition.active_workflow_steps),
            route_workflow_checkpoints=list(
                transition.active_workflow_checkpoints
            ),
            route_workflow_decision_points=list(
                transition.active_workflow_decision_points
            ),
            workflow_lifecycle_transition=transition,
        )
    )

    assert set(success) <= set(plan.success_criteria)
    refined = engine.refine_task_plan(
        plan,
        specialist_summary="preserve the promoted release criteria",
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="structured_analysis_specialist",
                role="subordinate_release_review",
                focus="verify every promoted success criterion",
                findings=["success: specialist review remains attributable"],
                recommendation="retain the complete promoted success contract",
                confidence=0.9,
            )
        ],
    )
    assert set(success) <= set(refined.success_criteria)


def test_planning_engine_builds_structured_plan_with_continuity() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M3",
            recovered_context=[
                "context_summary=previous plan created",
                (
                    "identity_continuity_brief=objetivo=Plan milestone M3; "
                    "prioridade=definir escopo final"
                ),
                "open_loops=definir escopo final;alinhar checkpoints",
                "mission_semantic_brief=objetivo=Plan milestone M3",
                "mission_focus=strategy,planning",
            ],
            active_domains=["strategy", "productivity"],
            active_minds=["mente_executiva", "mente_estrategica"],
            knowledge_snippets=["Priorize clareza de objetivo."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            tensions=["equilibrar ambicao estrategica com a menor proxima acao segura"],
            specialist_hints=["operational_planning_specialist"],
            dominant_goal="definir um caminho executavel e seguro",
            secondary_goals=["preservar espaco para analise antes de executar"],
            identity_mode="structured_planning",
            primary_mind="mente_executiva",
            supporting_minds=["mente_estrategica", "mente_pragmatica"],
            dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
            arbitration_summary="mente_executiva lidera com apoio estrategico",
            identity_continuity_brief=(
                "objetivo=Plan milestone M3; prioridade=definir escopo final"
            ),
            open_loops=["definir escopo final", "alinhar checkpoints"],
            mission_semantic_brief="objetivo=Plan milestone M3",
            mission_focus=["strategy", "planning"],
            last_decision_frame="planning",
            mission_goal="Plan milestone M3",
            mission_recommendation="retomar o escopo final antes da proxima acao",
        )
    )
    assert plan.goal == "definir um caminho executavel e seguro"
    assert plan.recommended_task_type == "draft_plan"
    assert plan.continuity_action == "continuar"
    assert plan.open_loops == ["definir escopo final", "alinhar checkpoints"]
    assert plan.steps[0] == "retomar o loop principal da missao: definir escopo final"
    assert any("loop principal da missao" in criterion for criterion in plan.success_criteria)
    assert (
        plan.smallest_safe_next_action
        == "retomar definir escopo final antes de abrir novo escopo; "
        "ancora cognitiva: mente primaria mente executiva ancora a deliberacao "
        "sob tensao equilibrar ambicao estrategica com a menor proxima acao segura"
    )
    assert plan.metacognitive_guidance_applied is True
    assert plan.metacognitive_guidance_summary is not None
    assert "success_criteria" in plan.metacognitive_effects
    assert "smallest_safe_next_action" in plan.metacognitive_effects
    assert "conflito_missao=nenhum" in plan.rationale
    assert "recomendacao_previa=retomar o escopo final antes da proxima acao" in plan.rationale
    assert plan.continuity_source == "active_mission"
    assert plan.capability_decision_status == "resolved"
    assert plan.capability_decision_selected_mode == "core_with_local_operation"
    assert plan.capability_decision_authorization_status == "governance_review_required"
    assert plan.request_confirmation_mode == "bounded_autonomy"
    assert plan.capability_decision_tool_class == "local_artifact_generation"
    assert plan.capability_decision_handoff_mode == "through_core_only"
    assert "local_safe_operation" in plan.capability_decision_selected_capabilities
    assert "specialist_handoff" in plan.capability_decision_selected_capabilities


def test_planning_engine_applies_bounded_reflection_influence() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M4",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            reflection_influence_status="applied",
            reflection_influence_refs=["reflection://mission-a/req-1"],
            reflection_influence_summary=(
                "keep the observed pattern as reviewable learning material"
            ),
        )
    )

    assert plan.reflection_influence_status == "applied"
    assert plan.reflection_influence_refs == ["reflection://mission-a/req-1"]
    assert plan.reflection_influence_summary == (
        "keep the observed pattern as reviewable learning material"
    )
    assert "reflection_influence=applied" in plan.plan_summary
    assert "reflection_influence_status=applied" in plan.rationale
    assert any("reflexao pos-tarefa relevante" in step for step in plan.steps)
    assert any("nao promover mudanca sem revisao humana" in item for item in plan.constraints)


def test_planning_engine_applies_reviewed_learning_influence() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M5",
            recovered_context=[],
            active_domains=["software_development"],
            active_minds=["mente_executiva"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            primary_route="software_development",
            route_workflow_profile="software_change_workflow",
            reviewed_learning_influence_status="applied",
            reviewed_learning_influence_refs=[
                "reviewed-learning-guidance://review-1"
            ],
            reviewed_learning_influence_summary=(
                "prefer small reversible patches with direct tests"
            ),
            reviewed_learning_influence_reason="workflow_match+route_match",
        )
    )

    assert plan.reviewed_learning_influence_status == "applied"
    assert plan.reviewed_learning_influence_refs == [
        "reviewed-learning-guidance://review-1"
    ]
    assert "reviewed_learning_influence=applied" in plan.plan_summary
    assert "reviewed_learning_influence_status=applied" in plan.rationale
    assert any("aprendizado revisado por humano" in step for step in plan.steps)
    assert any("sem release gate" in item for item in plan.constraints)


def test_planning_engine_marks_related_continuity_source_when_candidate_is_present() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Continue the risk analysis.",
            recovered_context=["context_summary=milestone M3 teve dois fluxos proximos"],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_executiva"],
            knowledge_snippets=["Preserve continuidade entre missoes relacionadas."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            dominant_goal="dar continuidade analitica segura",
            identity_mode="deep_analysis",
            related_mission_id="mission-a",
            related_mission_goal="Plan milestone M3 rollout.",
            related_continuity_reason="foco_compartilhado=strategy,planning",
            related_continuity_priority=0.8,
            related_continuity_confidence=0.7,
            continuity_recommendation="retomar_missao_relacionada",
            continuity_ranking_summary=(
                "missao relacionada mission-a venceu o ranking de continuidade com prioridade 0.80"
            ),
        )
    )
    assert plan.continuity_action == "retomar"
    assert plan.continuity_source == "related_mission"
    assert plan.continuity_target_mission_id == "mission-a"
    assert plan.continuity_target_goal == "Plan milestone M3 rollout."
    assert plan.steps[0] == "retomar explicitamente a missao relacionada antes de abrir novo escopo"
    assert plan.continuity_reason is not None
    assert "missao_relacionada=Plan milestone M3 rollout." in plan.rationale
    assert "prioridade_relacionada=0.80" in plan.rationale
    assert "motivo_continuidade=missao relacionada mission-a venceu o ranking" in plan.rationale
    assert "ranking_continuidade=missao relacionada mission-a venceu o ranking" in plan.rationale


def test_planning_engine_contains_capabilities_for_clarification_only() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Need help, but first clarify the target environment.",
            recovered_context=[],
            active_domains=["analysis"],
            active_minds=["mente_analitica"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=True,
            preferred_response_mode="analysis_only",
            dominant_goal="esclarecer o pedido antes de qualquer execucao",
        )
    )

    assert plan.capability_decision_status == "contained"
    assert plan.capability_decision_selected_mode == "clarification_only"
    assert plan.capability_decision_authorization_status == "clarification_required"
    assert plan.capability_decision_handoff_mode == "none"
    assert plan.capability_decision_tool_class is None
    assert plan.capability_decision_selected_capabilities == ["core_reasoning"]


def test_planning_engine_uses_memory_route_priority_and_mind_composition_guidance() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Continue the governed analysis.",
            recovered_context=["context_summary=analysis mission already active"],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica", "mente_logica"],
            knowledge_snippets=["Preserve the analytical chain."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            route_workflow_profile="structured_analysis_workflow",
            route_workflow_checkpoints=["analysis_scope_confirmed"],
            route_workflow_decision_points=["insight_governed"],
            route_expected_deliverables=["analysis_frame"],
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            dominant_goal="aprofundar a leitura analitica sem perder continuidade",
            primary_mind="mente_analitica",
            primary_mind_family="fundamental",
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            supporting_minds=["mente_logica", "mente_critica"],
            suppressed_minds=["mente_pragmatica"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            arbitration_summary="mente analitica lidera com revisao critica",
            mission_goal="Continue the governed analysis.",
            continuity_recommendation="retomar_missao_relacionada",
            related_mission_id="mission-analysis",
            related_mission_goal="Continue the governed analysis.",
            related_continuity_reason="foco_compartilhado=analysis",
            related_continuity_priority=0.92,
            continuity_ranking_summary="mission-analysis venceu o ranking de continuidade",
            memory_priority_status="memory_guided",
            memory_priority_domains=["analysis"],
            memory_priority_specialists=["structured_analysis_specialist"],
            memory_priority_sources=["mission_focus", "continuity_ranking"],
            memory_priority_summary="analysis:6[mission_focus,continuity_ranking]",
        )
    )

    assert "memory_priority_status=memory_guided" in plan.plan_summary
    assert "memory_priority_domains=analysis" in plan.rationale
    assert "reconciliar o apoio de mente_logica, mente_critica" in " ".join(plan.steps)
    assert any(
        "mente_pragmatica" in criterion for criterion in plan.success_criteria
    )
    assert "preservar a rota priorizada por memoria em analysis" in (
        plan.smallest_safe_next_action
    )


def test_planning_engine_uses_compaction_and_cross_session_recall_as_constraints() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Continue the release trade-off analysis.",
            recovered_context=[
                "context_summary=release analysis already exists",
                "context_compaction_status=compressed_live_context",
                "context_live_summary=turns=2;user_scope=recoverable;continuity=none;cross_session=active",
                "cross_session_recall_status=active",
                (
                    "cross_session_recall_summary="
                    "user_scope=intents=planning,analysis | "
                    "related=Plan milestone M3 rollout"
                ),
                "mission_semantic_brief=objetivo=Continue the release trade-off analysis.",
            ],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_executiva"],
            knowledge_snippets=["Preserve trade-off clarity."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            dominant_goal="aprofundar a leitura comparativa com continuidade",
            primary_mind="mente_analitica",
            primary_domain_driver="analise_estruturada_e_modelagem",
            mission_goal="Continue the release trade-off analysis.",
            context_compaction_status="compressed_live_context",
            context_compaction_summary="live_turns=2;continuity_hints=0;recalled_sources=2",
            context_live_summary=(
                "turns=2;user_scope=recoverable;continuity=none;cross_session=active"
            ),
            cross_session_recall_status="active",
            cross_session_recall_summary=(
                "user_scope=intents=planning,analysis | related=Plan milestone M3 rollout"
            ),
        )
    )

    assert any(
        "contexto vivo compactado" in constraint for constraint in plan.constraints
    )
    assert any(
        "recall cross-session" in constraint for constraint in plan.constraints
    )
    assert "context_compaction=compressed_live_context" in plan.plan_summary
    assert "cross_session_recall=active" in plan.rationale


def test_planning_engine_repairs_missing_required_contract_fields() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Stabilize the next step safely.",
            recovered_context=[],
            active_domains=[],
            active_minds=[],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
        )
    )

    assert plan.contract_validation_status == "repaired"
    assert plan.contract_validation_retry_applied is True
    assert "missing_required_field:active_minds" in plan.contract_validation_errors
    assert plan.active_minds == ["mente_executiva"]
    assert plan.steps
    assert plan.success_criteria


def test_planning_engine_reformulates_when_new_request_conflicts_with_active_mission() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Start a new marketing campaign instead.",
            recovered_context=[
                (
                    "identity_continuity_brief=objetivo=Plan milestone M3; "
                    "prioridade=definir escopo final"
                ),
                "open_loops=definir escopo final;alinhar checkpoints",
                "mission_goal=Plan milestone M3",
            ],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=["Preserve rastreabilidade."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            dominant_goal="definir um caminho executavel e seguro",
            identity_mode="structured_planning",
            primary_mind="mente_executiva",
            supporting_minds=["mente_estrategica"],
            arbitration_summary="mente_executiva lidera com foco em continuidade",
            identity_continuity_brief=(
                "objetivo=Plan milestone M3; prioridade=definir escopo final"
            ),
            open_loops=["definir escopo final", "alinhar checkpoints"],
            mission_goal="Plan milestone M3",
            mission_recommendation="retomar o escopo final antes da proxima acao",
            last_decision_frame="planning",
        )
    )
    assert plan.continuity_action == "reformular"
    assert plan.recommended_task_type == "general_response"
    assert plan.requires_human_validation is True
    assert (
        plan.steps[0]
        == "reformular a missao ativa sem perder rastreabilidade: Plan milestone M3"
    )
    assert any("deslocar a missao ativa" in risk for risk in plan.risks)
    assert plan.metacognitive_guidance_applied is True
    assert "containment_recommendation" in plan.metacognitive_effects
    assert plan.metacognitive_containment_recommendation is not None
    assert plan.capability_decision_status == "contained"
    assert plan.capability_decision_selected_mode == "contained_guidance"
    assert plan.capability_decision_authorization_status == "human_validation_required"
    assert plan.capability_decision_handoff_mode == "none"
    assert (
        "conflito_missao=pedido atual desloca o foco da missao ativa 'Plan milestone M3'"
        in plan.rationale
    )


def test_planning_engine_prefers_specialist_handoff_for_guided_analysis() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze the strongest pilot risk and explain the trade-offs.",
            recovered_context=[],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Preserve evidence-first reasoning."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            dominant_goal="aprofundar a leitura analitica com apoio especialista",
            route_workflow_profile="structured_analysis_workflow",
            specialist_hints=["structured_analysis_specialist"],
        )
    )

    assert plan.recommended_task_type == "produce_analysis_brief"
    assert plan.capability_decision_status == "resolved"
    assert plan.capability_decision_selected_mode == "core_with_specialist_handoff"
    assert plan.capability_decision_authorization_status == "pre_authorized_internal"
    assert plan.capability_decision_handoff_mode == "through_core_only"
    assert plan.capability_decision_tool_class is None
    assert "specialist_handoff" in plan.capability_decision_selected_capabilities


def test_planning_engine_materializes_mind_domain_specialist_contract() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze the rollout trade-offs with explicit specialist guidance.",
            recovered_context=[],
            active_domains=["strategy", "analysis"],
            active_minds=["mente_decisoria", "mente_analitica"],
            knowledge_snippets=["Preserve the sovereign chain."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            primary_mind="mente_decisoria",
            primary_mind_family="estrategica_decisoria",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            arbitration_source="mind_registry",
            primary_route="strategy",
            specialist_hints=["structured_analysis_specialist"],
            route_workflow_profile="strategic_direction_workflow",
            dominant_goal="explicitar a direcao recomendada com criterio dominante",
        )
    )

    assert plan.mind_domain_specialist_contract_status == "authoritative_chain"
    assert plan.mind_domain_specialist_contract_summary is not None
    assert plan.mind_domain_specialist_contract_chain == (
        "mente_decisoria -> estrategia_e_pensamento_sistemico -> "
        "strategy -> structured_analysis_specialist"
    )
    assert (
        plan.mind_domain_specialist_active_specialist
        == "structured_analysis_specialist"
    )
    assert plan.mind_domain_specialist_override_mode is None
    assert plan.mind_domain_specialist_fallback_mode is None
    assert "mind_domain_specialist_status=authoritative_chain" in plan.rationale


def test_planning_engine_closes_active_loop_explicitly() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Encerrar checkpoint principal da sprint.",
            recovered_context=[
                "identity_continuity_brief=objetivo=Plan milestone M3; prioridade=checkpoint",
                "open_loops=checkpoint principal;alinhar aprovacao final",
                "mission_goal=Plan milestone M3",
            ],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=["Feche loops explicitamente antes de abrir nova frente."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            dominant_goal="fechar o ciclo atual com clareza",
            identity_mode="structured_planning",
            open_loops=["checkpoint principal", "alinhar aprovacao final"],
            mission_goal="Plan milestone M3",
        )
    )
    assert plan.continuity_action == "encerrar"
    assert plan.steps[0] == "fechar explicitamente o loop principal: checkpoint principal"
    assert (
        plan.continuity_reason
        == "pedido explicita fechamento do loop principal checkpoint principal"
    )
    assert (
        plan.smallest_safe_next_action
        == "fechar checkpoint principal com criterio explicito"
    )


def test_planning_engine_carries_primary_route_contract_into_plan() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan strategic options for the release.",
            recovered_context=[],
            active_domains=["strategy", "analysis"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=["Priorize criterio explicito de decisao."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            canonical_domains=[
                "estrategia_e_pensamento_sistemico",
                "tomada_de_decisao_complexa",
            ],
            primary_canonical_domain="estrategia_e_pensamento_sistemico",
            primary_route="strategy",
            route_consumer_profile="strategy_tradeoff_review",
            route_consumer_objective=(
                "clarificar trade-offs estrategicos, enquadramento de cenario e direcao recomendada"
            ),
            route_expected_deliverables=[
                "tradeoff_map",
                "decision_criteria",
                "recommended_direction",
            ],
            route_telemetry_focus=[
                "tradeoff_clarity",
                "decision_trace",
                "domain_alignment",
            ],
            route_workflow_profile="strategic_direction_workflow",
            route_workflow_steps=[
                "frame the strategic scenario and the decision horizon",
                "compare trade-offs, constraints and leverage points",
                "recommend a direction with explicit criteria",
            ],
            route_workflow_checkpoints=[
                "scenario_framed",
                "tradeoffs_compared",
                "direction_recommended",
            ],
            route_workflow_decision_points=[
                "scenario_scope_confirmed",
                "tradeoff_criteria_governed",
                "direction_governed",
            ],
            cognitive_rationale="intent=planning; mente_primaria=mente_decisoria",
            dominant_goal="comparar direcoes estrategicas do release",
            identity_mode="structured_planning",
            primary_mind="mente_decisoria",
            primary_mind_family="estrategica_decisoria",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            arbitration_source="mind_registry",
            mission_semantic_brief="objetivo=Plan strategic options; foco=trade-offs do release",
            mission_focus=["estrategia_e_pensamento_sistemico", "strategy"],
            mission_recommendation="manter o ultimo fio decisorio governado",
            procedural_artifact_status="candidate",
            procedural_artifact_ref="artifact://procedural/strategy/strategic_direction_workflow/v1",
            procedural_artifact_version=1,
            procedural_artifact_summary="procedimento guiado para revisao de trade-offs",
            last_decision_frame="strategic_tradeoff_review",
            dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        )
    )

    assert plan.primary_mind == "mente_decisoria"
    assert plan.primary_mind_family == "estrategica_decisoria"
    assert plan.primary_domain_driver == "estrategia_e_pensamento_sistemico"
    assert plan.arbitration_source == "mind_registry"
    assert plan.primary_route == "strategy"
    assert plan.route_consumer_profile == "strategy_tradeoff_review"
    assert "tradeoff_map" in plan.route_expected_deliverables
    assert "tradeoff_clarity" in plan.route_telemetry_focus
    assert plan.route_workflow_profile == "strategic_direction_workflow"
    assert plan.route_workflow_checkpoints[0] == "scenario_framed"
    assert plan.route_workflow_decision_points[0] == "scenario_scope_confirmed"
    assert plan.workflow_policy_decision is not None
    assert plan.workflow_policy_decision.resolution_status == "resolved"
    assert plan.workflow_policy_decision.application_status == "applied"
    assert plan.workflow_policy_decision.policy_version == "1.0.0"
    assert plan.workflow_policy_decision.route == "strategy"
    assert plan.workflow_policy_decision.effects == [
        "planning_focus",
        "success_focus",
        "semantic_memory_role",
        "procedural_memory_role",
        "response_focus",
        "adaptive_intervention_priority",
    ]
    assert "workflow_policy=applied" in plan.plan_summary
    assert "workflow_policy_resolution=resolved" in plan.rationale
    assert plan.procedural_artifact_status == "candidate"
    assert (
        plan.procedural_artifact_ref
        == "artifact://procedural/strategy/strategic_direction_workflow/v1"
    )
    assert plan.procedural_artifact_version == 1
    assert "consumer_profile=strategy_tradeoff_review" in plan.rationale
    assert "dominio_primario=estrategia_e_pensamento_sistemico" in plan.rationale
    assert "procedural_artifact_status=candidate" in plan.rationale
    assert "artifact://procedural/strategy/strategic_direction_workflow/v1" in plan.rationale
    assert any("tradeoff_map" in criterion for criterion in plan.success_criteria)
    assert any(
        "direcao recomendada com criterios explicitos" in criterion
        for criterion in plan.success_criteria
    )
    assert any(
        "manter framing estrategico e comparacao de trade-offs" in criterion
        for criterion in plan.success_criteria
    )
    assert any("scenario framed" in criterion for criterion in plan.success_criteria)
    assert any(
        "preservar continuidade do fio decisorio e criterio de progressao" in criterion
        for criterion in plan.success_criteria
    )
    assert any(
        "ancora cognitiva mente decisoria deve manter estrategia e pensamento sistemico"
        in criterion
        for criterion in plan.success_criteria
    )
    assert any(
        "usar memoria semantica para framing estrategico e comparacao de trade-offs"
        in step
        for step in plan.steps
    )
    assert any(
        "usar memoria procedural para continuidade do fio decisorio e criterio de progressao"
        in step
        for step in plan.steps
    )
    assert any(
        "governar o decision point ativo: scenario scope confirmed" in constraint
        for constraint in plan.constraints
    )
    assert any(
        "usar memoria semantica apenas para framing estrategico e comparacao de trade-offs"
        in constraint
        for constraint in plan.constraints
    )
    assert any(
        "usar memoria procedural apenas para continuidade do fio decisorio e criterio de progressao"
        in constraint
        for constraint in plan.constraints
    )
    assert (
        plan.smallest_safe_next_action
        == "retomar comparar direcoes estrategicas do release preservando "
        "continuidade do fio decisorio e criterio de progressao: "
        "manter o ultimo fio decisorio governado; ancora cognitiva: "
        "mente decisoria ancora estrategia e pensamento sistemico via strategy "
        "sob tensao equilibrar ambicao estrategica com a menor proxima acao segura"
    )
    assert plan.metacognitive_guidance_applied is True
    assert plan.metacognitive_guidance_summary == (
        "mente decisoria ancora estrategia e pensamento sistemico via strategy "
        "sob tensao equilibrar ambicao estrategica com a menor proxima acao segura"
    )


def test_planning_engine_bounds_route_profile_policy_mismatch() -> None:
    plan = PlanningEngine().build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan a bounded strategic release.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            primary_route="strategy",
            route_workflow_profile="software_change_workflow",
            route_workflow_steps=["apply software workflow outside its route"],
            route_workflow_checkpoints=["patch_ready"],
            route_workflow_decision_points=["patch_gate"],
        )
    )

    assert plan.workflow_policy_decision is not None
    assert (
        plan.workflow_policy_decision.resolution_status
        == "rejected_route_profile_mismatch"
    )
    assert plan.workflow_policy_decision.application_status == "not_applied"
    assert plan.workflow_policy_decision.non_use_reason == "route_profile_mismatch"
    assert plan.workflow_policy_decision.effects == []
    assert plan.route_workflow_profile is None
    assert plan.route_workflow_steps == []
    assert plan.route_workflow_checkpoints == []
    assert plan.route_workflow_decision_points == []
    assert "workflow_policy=not_applied" in plan.plan_summary
    assert "workflow_policy_non_use=route_profile_mismatch" in plan.rationale


def test_planning_engine_adds_priority_and_recommendation_memory_guidance() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Recommend the safest strategic direction.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=["Preserve strategic continuity."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            mission_id="mission-semantic-evidence",
            request_timestamp="2026-07-18T12:00:00Z",
            canonical_domains=["estrategia_e_pensamento_sistemico"],
            primary_canonical_domain="estrategia_e_pensamento_sistemico",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            dominant_goal="clarificar a direcao recomendada",
            primary_mind="mente_decisoria",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            mission_goal="Recommend the safest strategic direction.",
            mission_semantic_brief="objetivo=Recommend the safest strategic direction.",
            mission_focus=["strategy", "tradeoff"],
            mission_recommendation="retomar o ultimo criterio estrategico governado",
            last_decision_frame="strategy",
            semantic_memory_candidates=[
                SemanticMemoryCandidateContract(
                    anchor_ref=(
                        "memory://mission/mission-semantic-evidence/semantic"
                    ),
                    source_kind="active_mission",
                    summary=(
                        "objetivo=Recommend the safest strategic direction."
                    ),
                    evidence_refs=[
                        "mission-state://mission-semantic-evidence/semantic/abc123",
                        (
                            "mission-state-updated://mission-semantic-evidence/"
                            "2026-07-18T11:00:00Z"
                        ),
                    ],
                    observed_at="2026-07-18T11:00:00Z",
                    freshness_status="current",
                    relevance_score=0.95,
                    relevance_reason="active_mission_id_match",
                    domain_hints=[
                        "strategy",
                        "estrategia_e_pensamento_sistemico",
                    ],
                )
            ],
        )
    )

    assert "priority" in plan.semantic_memory_effects
    assert "recommendation" in plan.semantic_memory_effects
    assert plan.semantic_memory_anchor_refs == [
        "memory://mission/mission-semantic-evidence/semantic"
    ]
    assert "mission-state://mission-semantic-evidence/semantic/abc123" in (
        plan.semantic_memory_evidence_refs
    )
    assert plan.memory_influence_policy_decision is not None
    assert plan.memory_influence_policy_decision.freshness_statuses == {
        "memory://mission/mission-semantic-evidence/semantic": "current"
    }
    assert plan.memory_influence_policy_decision.relevance_scores == {
        "memory://mission/mission-semantic-evidence/semantic": 0.95
    }
    assert plan.semantic_memory_use_reason is not None
    assert plan.semantic_memory_non_use_reason is None
    assert "semantic_memory_anchor_refs=" in plan.plan_summary
    assert "semantic_memory_use_reason=" in plan.rationale
    assert "priority" in plan.procedural_memory_effects
    assert "recommendation" in plan.procedural_memory_effects
    assert any("priorizar a leitura semantica" in step for step in plan.steps)
    assert any(
        "framing semantico dominante" in criterion for criterion in plan.success_criteria
    )
    assert any(
        "continuidade procedural do workflow" in criterion
        for criterion in plan.success_criteria
    )
    assert plan.metacognitive_effects == [
        "success_criteria",
        "smallest_safe_next_action",
    ]


def test_planning_engine_does_not_presume_semantic_influence_without_candidate() -> None:
    plan = PlanningEngine().build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan the next strategic checkpoint.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            mission_id="mission-no-semantic-evidence",
            request_timestamp="2026-07-18T12:00:00Z",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            mission_semantic_brief="unverified recovered text",
            mission_focus=["strategy"],
            semantic_memory_candidates=[],
        )
    )

    assert plan.semantic_memory_source is None
    assert plan.semantic_memory_anchor_refs == []
    assert plan.semantic_memory_evidence_refs == []
    assert plan.semantic_memory_effects == []
    assert plan.semantic_memory_use_reason is None
    assert plan.semantic_memory_non_use_reason == "no_semantic_memory_candidate"


def test_planning_engine_audits_stale_semantic_candidate_non_use() -> None:
    candidate = SemanticMemoryCandidateContract(
        anchor_ref="memory://mission/stale/semantic",
        source_kind="related_mission",
        summary="stale strategic frame",
        evidence_refs=["mission-state://stale/semantic/abc123"],
        observed_at="2026-05-01T12:00:00Z",
        freshness_status="stale",
        relevance_score=0.8,
        relevance_reason="related_mission_similarity",
        domain_hints=["strategy"],
        lifecycle_status="expired",
    )
    plan = PlanningEngine().build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan a fresh strategic checkpoint.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            request_timestamp="2026-07-18T12:00:00Z",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            mission_semantic_brief="fresh mission context",
            mission_focus=["strategy"],
            semantic_memory_candidates=[candidate],
        )
    )

    decision = plan.memory_influence_policy_decision
    assert decision is not None
    assert candidate.anchor_ref in decision.ignored_refs
    assert decision.freshness_statuses[candidate.anchor_ref] == "stale"
    assert decision.non_use_reasons[candidate.anchor_ref] == (
        "freshness_not_eligible:stale"
    )
    assert plan.semantic_memory_effects == []
    assert plan.semantic_memory_non_use_reason == (
        f"{candidate.anchor_ref}:freshness_not_eligible:stale"
    )


def test_planning_engine_resolves_semantic_candidate_conflict_by_relevance() -> None:
    common = {
        "source_kind": "related_mission",
        "observed_at": "2026-07-18T11:00:00Z",
        "freshness_status": "current",
        "domain_hints": ["strategy"],
    }
    lower = SemanticMemoryCandidateContract(
        anchor_ref="memory://mission/a-lower/semantic",
        summary="reuse the related direction",
        evidence_refs=["mission-state://a-lower/semantic/abc123"],
        relevance_score=0.6,
        relevance_reason="related_mission_similarity",
        **common,
    )
    higher = SemanticMemoryCandidateContract(
        anchor_ref="memory://mission/z-higher/semantic",
        summary="continue the active direction",
        evidence_refs=["mission-state://z-higher/semantic/def456"],
        relevance_score=0.95,
        relevance_reason="active_mission_id_match",
        **common,
    )
    plan = PlanningEngine().build_task_plan(
        PlanningContext(
            intent="planning",
            query="Continue the strategic direction.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            request_timestamp="2026-07-18T12:00:00Z",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            mission_semantic_brief="continue the active direction",
            mission_focus=["strategy"],
            semantic_memory_candidates=[lower, higher],
        )
    )

    decision = plan.memory_influence_policy_decision
    assert decision is not None
    assert plan.semantic_memory_anchor_refs == [higher.anchor_ref]
    assert lower.anchor_ref in decision.ignored_refs
    assert decision.conflict_refs == [higher.anchor_ref, lower.anchor_ref]
    assert decision.non_use_reasons[lower.anchor_ref] == (
        f"conflict_with_higher_priority:{higher.anchor_ref}"
    )


def test_planning_engine_applies_only_latest_reviewed_procedural_playbook_as_guidance() -> None:
    older = _reviewed_procedural_playbook(version="1.0.0")
    latest = _reviewed_procedural_playbook(
        version="2.0.0",
        bounded_steps=[
            "collect current decision evidence",
            "validate rollback before recommendation",
        ],
    )

    plan = PlanningEngine().build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan the next governed strategic checkpoint.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            request_timestamp="2026-07-18T12:05:00Z",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            reviewed_procedural_playbooks=[older, latest],
        )
    )

    decision = plan.memory_influence_policy_decision
    assert decision is not None
    latest_ref = f"{latest.playbook_id}@{latest.version}"
    older_ref = f"{older.playbook_id}@{older.version}"
    assert latest_ref in decision.selected_refs
    assert older_ref in decision.ignored_refs
    assert decision.non_use_reasons[older_ref] == (
        f"superseded_by_newer_version:{latest_ref}"
    )
    assert decision.version_refs == {
        older_ref: "1.0.0",
        latest_ref: "2.0.0",
    }
    assert decision.review_decision_refs[latest_ref] == (
        latest.source_review_decision_id
    )
    assert decision.execution_allowed is False
    assert decision.tool_dispatch_allowed is False
    assert any(
        "reviewed procedural playbook as read-only guidance" in step
        and "@2.0.0" in step
        and "collect current decision evidence" in step
        for step in plan.steps
    )
    assert not any("@1.0.0" in step for step in plan.steps)
    assert any("do not execute tools" in item for item in plan.constraints)


def test_planning_engine_audits_playbooks_outside_application_capacity() -> None:
    selected = _reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://strategy/primary",
        version="2.0.0",
    )
    capacity_limited = _reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://strategy/secondary",
        version="1.0.0",
    )

    plan = PlanningEngine().build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan the next governed strategic checkpoint.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            request_timestamp="2026-07-18T12:05:00Z",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            reviewed_procedural_playbooks=[capacity_limited, selected],
        )
    )

    decision = plan.memory_influence_policy_decision
    assert decision is not None
    selected_ref = f"{selected.playbook_id}@{selected.version}"
    limited_ref = f"{capacity_limited.playbook_id}@{capacity_limited.version}"
    assert selected_ref in decision.selected_refs
    assert limited_ref in decision.ignored_refs
    assert decision.non_use_reasons[limited_ref] == (
        f"reviewed_procedural_application_limit_exceeded:{selected_ref}"
    )
    assert any(selected_ref in step for step in plan.steps)
    assert not any(limited_ref in step for step in plan.steps)


def test_planning_engine_audits_revoked_and_scope_mismatched_playbook_non_use() -> None:
    revoked = _reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://strategy/revoked",
        review_status="revoked",
    )
    wrong_scope = _reviewed_procedural_playbook(
        playbook_id="reviewed-playbook://analysis/mismatch",
        route="analysis",
    )

    plan = PlanningEngine().build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan the next governed strategic checkpoint.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            request_timestamp="2026-07-18T12:05:00Z",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            reviewed_procedural_playbooks=[revoked, wrong_scope],
        )
    )

    decision = plan.memory_influence_policy_decision
    assert decision is not None
    revoked_ref = f"{revoked.playbook_id}@{revoked.version}"
    mismatch_ref = f"{wrong_scope.playbook_id}@{wrong_scope.version}"
    assert decision.selected_refs == []
    assert decision.non_use_reasons[revoked_ref] == (
        "review_status_not_eligible:revoked"
    )
    assert decision.non_use_reasons[mismatch_ref] == "scope_mismatch:route"
    assert not any(
        "reviewed procedural playbook as read-only guidance" in step
        for step in plan.steps
    )


def test_reviewed_playbook_does_not_reenable_rejected_legacy_procedural_memory() -> None:
    playbook = _reviewed_procedural_playbook()
    legacy_anchor = "legacy mission recommendation must remain suppressed"
    context = PlanningContext(
            intent="planning",
            query="Plan a new governed strategic checkpoint.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            mission_id="mission-legacy-procedural-rejected",
            request_timestamp="2026-07-18T12:05:00Z",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            mission_recommendation=legacy_anchor,
            continuity_recommendation="seguir_novo_pedido",
            reviewed_procedural_playbooks=[],
    )
    engine = PlanningEngine()
    baseline = engine.build_task_plan(context)
    plan = engine.build_task_plan(
        replace(context, reviewed_procedural_playbooks=[playbook])
    )

    decision = plan.memory_influence_policy_decision
    assert decision is not None
    reviewed_ref = f"{playbook.playbook_id}@{playbook.version}"
    legacy_ref = (
        "memory://mission/mission-legacy-procedural-rejected/procedural"
    )
    assert reviewed_ref in decision.selected_refs
    assert legacy_ref in decision.ignored_refs
    assert decision.non_use_reasons[legacy_ref] == (
        "lifecycle_not_eligible:aging"
    )
    assert plan.procedural_memory_source is None
    assert plan.procedural_memory_effects == []
    assert plan.smallest_safe_next_action == baseline.smallest_safe_next_action
    assert not any(
        "priorizar a memoria procedural" in step for step in plan.steps
    )
    assert any(
        "reviewed procedural playbook as read-only guidance" in step
        for step in plan.steps
    )


def test_planning_engine_refines_plan_and_consolidates_specialists() -> None:
    engine = PlanningEngine()
    base_plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze rollout options",
            recovered_context=[],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Compare custo, risco e reversibilidade."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            tensions=["equilibrar profundidade analitica com conclusao util"],
            specialist_hints=[
                "operational_planning_specialist",
                "structured_analysis_specialist",
            ],
            dominant_goal="produzir leitura confiavel antes de agir",
            identity_mode="deep_analysis",
            primary_mind="mente_analitica",
            supporting_minds=["mente_critica", "mente_logica"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            arbitration_summary="mente_analitica lidera com apoio critico",
        )
    )
    refined = engine.refine_task_plan(
        base_plan,
        specialist_summary="ajustar checkpoints e explicitar criterio dominante",
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="operational_planning_specialist",
                role="planejamento_operacional_subordinado",
                focus="sequenciamento reversivel e checkpoints claros",
                findings=[
                    "constraint: validar checkpoint intermediario com base em contexto local",
                    "open_loop: confirmar checkpoint principal",
                ],
                recommendation=(
                    "encadear o plano em etapas pequenas, verificaveis "
                    "e conectadas a missao"
                ),
                confidence=0.79,
            ),
            SpecialistContributionContract(
                specialist_type="structured_analysis_specialist",
                role="analise_estruturada_subordinada",
                focus="trade-offs, evidencia e criterio de decisao",
                findings=[
                    "success: conclusao deve explicitar o criterio dominante de escolha",
                    "constraint: separar observacao, implicacao e recomendacao final",
                ],
                recommendation=(
                    "fundir comparacao, implicacao e recomendacao "
                    "em uma unica linha analitica"
                ),
                confidence=0.82,
            ),
        ],
    )
    assert refined.specialist_resolution_summary is not None
    assert refined.open_loops == ["confirmar checkpoint principal"]
    assert any("checkpoint intermediario" in step for step in refined.steps)
    assert any("criterio dominante" in criterion for criterion in refined.success_criteria)
    assert "resolucao_especialistas=" in refined.rationale


def test_planning_engine_records_semantic_memory_non_use_reason() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze a fresh request.",
            recovered_context=[],
            active_domains=["analysis"],
            active_minds=["mente_analitica"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            primary_route="analysis",
            route_workflow_profile="structured_analysis_workflow",
        )
    )

    assert plan.semantic_memory_source is None
    assert plan.semantic_memory_anchor_refs == []
    assert plan.semantic_memory_evidence_refs == [
        "workflow://structured_analysis_workflow",
        "route://analysis",
    ]
    assert plan.semantic_memory_use_reason is None
    assert plan.semantic_memory_non_use_reason == "no_semantic_anchor_recovered"
    assert "semantic_memory_non_use_reason=no_semantic_anchor_recovered" in (
        plan.rationale
    )


def test_planning_engine_applies_mid_flow_cognitive_strategy_shift_when_impasse_persists() -> None:
    engine = PlanningEngine()
    base_plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze rollout options",
            recovered_context=[],
            active_domains=["analysis"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Compare custo, risco e reversibilidade."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            route_workflow_profile="structured_analysis_workflow",
            route_workflow_checkpoints=["analysis_framed"],
            route_workflow_decision_points=["analysis_scope_governed"],
            dominant_goal="produzir leitura confiavel antes de agir",
            primary_mind="mente_analitica",
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            supporting_minds=["mente_critica", "mente_logica"],
            suppressed_minds=["mente_expressiva"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
        )
    )
    base_plan.mind_disagreement_status = "validation_required"
    base_plan.mind_validation_checkpoints = [
        (
            "validar a tensao dominante antes de concluir: equilibrar "
            "profundidade analitica com conclusao util"
        )
    ]
    base_plan.smallest_safe_next_action = "comparar os cenarios antes da sintese final"

    refined = engine.refine_task_plan(
        base_plan,
        specialist_summary="trade-offs seguem abertos sob checkpoint governado",
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="structured_analysis_specialist",
                role="analise_estruturada_subordinada",
                focus="trade-offs, evidencia e criterio de decisao",
                findings=[
                    "risk: impasse analitico ainda pede validacao adicional",
                    "open_loop: consolidar criterio dominante",
                ],
                recommendation="manter comparacao governada antes da recomendacao final",
                confidence=0.82,
            ),
        ],
    )

    assert refined.cognitive_strategy_shift_applied is True
    assert refined.cognitive_strategy_shift_trigger == "guided_validation_impasse"
    assert refined.cognitive_strategy_shift_summary is not None
    assert "steps" in refined.cognitive_strategy_shift_effects
    assert refined.steps[0].startswith(
        "executar mudanca de estrategia cognitiva mid-flow:"
    )
    assert refined.smallest_safe_next_action == "revisar analysis framed antes da sintese final"
    assert any(
        "discordancia" in criterion or "criterio dominante" in criterion
        for criterion in refined.success_criteria
    )
    assert "mudanca_estrategia_mid_flow=guided_validation_impasse:" in refined.rationale
    assert refined.adaptive_intervention_selected_action == "specialist_reevaluation"
    assert refined.requires_human_validation is False


def test_planning_engine_routes_governed_replay_to_safe_recovery() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Continue the sprint plan.",
            recovered_context=[
                "continuity_replay_status=awaiting_validation",
                "continuity_recovery_mode=governed_review",
                "continuity_resume_point=continuar:fechar checkpoint principal",
            ],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=["Retome com revisao explicita quando houver checkpoint governado."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            mission_goal="Plan milestone M3",
            open_loops=["fechar checkpoint principal"],
            continuity_replay_status="awaiting_validation",
            continuity_recovery_mode="governed_review",
            continuity_resume_point="continuar:fechar checkpoint principal",
            continuity_requires_manual_resume=True,
        )
    )
    assert plan.recommended_task_type == "general_response"
    assert plan.requires_human_validation is True
    assert plan.steps[0].startswith("revisar o ponto de retomada antes de continuar")
    assert any("checkpoint governado" in constraint for constraint in plan.constraints)
    assert any("aguarda validacao" in risk for risk in plan.risks)
    assert plan.continuity_replay_status == "awaiting_validation"
    assert plan.continuity_recovery_mode == "governed_review"
    assert plan.continuity_resume_point == "continuar:fechar checkpoint principal"


def test_planning_engine_prioritizes_specialist_reevaluation_for_analysis_workflows() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Compare the rollout trade-offs and decide the safest path.",
            recovered_context=[],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Compare evidence before closing the recommendation."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            route_workflow_profile="structured_analysis_workflow",
            route_workflow_checkpoints=["analysis_framed"],
            route_workflow_decision_points=["tradeoff_review_governed"],
            supporting_minds=["mente_critica", "mente_logica"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            memory_retention_pressure="high",
        )
    )

    assert plan.adaptive_intervention_status == "applied"
    assert plan.adaptive_intervention_selected_action == "specialist_reevaluation"
    assert plan.adaptive_intervention_trigger == "mind_validation_required"
    assert "prioridade soberana de structured_analysis_workflow" in (
        plan.adaptive_intervention_reason or ""
    )


def test_planning_engine_prioritizes_memory_review_for_readiness_workflows() -> None:
    engine = PlanningEngine()
    selected = engine._select_workflow_adaptive_intervention(
        workflow_profile="operational_readiness_workflow",
        candidates=[
            AdaptiveIntervention(
                applied=True,
                status="applied",
                reason="pressao de memoria pede revisao antes de prosseguir",
                trigger="memory_retention_pressure_high",
                selected_action="memory_review_checkpoint",
                expected_effect="stabilize recall usage before final synthesis or reuse expansion",
                effects=["steps", "constraints"],
            ),
            AdaptiveIntervention(
                applied=True,
                status="applied",
                reason="discordancia especializada pede reavaliacao antes do fechamento",
                trigger="mind_validation_required",
                selected_action="specialist_reevaluation",
                expected_effect="force governed specialist reevaluation before closing",
                effects=["steps", "success_criteria"],
            ),
        ],
    )

    assert selected is not None
    assert selected.selected_action == "memory_review_checkpoint"
    assert selected.trigger == "memory_retention_pressure_high"
    assert "prioridade soberana de operational_readiness_workflow" in (
        selected.reason or ""
    )
