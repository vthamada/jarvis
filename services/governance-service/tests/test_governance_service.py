from governance_service.service import GovernanceAssessment, GovernanceService

from shared.contracts import (
    DeliberativePlanContract,
    InputContract,
    MissionStateContract,
    OperatorFeedbackContract,
    SpecialistBoundaryContract,
    SpecialistInvocationContract,
    SpecialistSelectionContract,
)
from shared.types import (
    ChannelType,
    InputType,
    MemoryClass,
    MissionId,
    MissionStatus,
    PermissionDecision,
    RequestId,
    RiskLevel,
    SessionId,
)


def low_risk_plan() -> DeliberativePlanContract:
    return DeliberativePlanContract(
        plan_summary="estruturar milestone em etapas reversiveis",
        goal="Please plan the milestone.",
        steps=["definir objetivo", "listar etapas", "sugerir proxima acao"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=nenhum; apoio=baseline local",
        success_criteria=["plano deve indicar a menor proxima acao segura"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="definir objetivo",
        continuity_action="continuar",
        open_loops=["alinhar checkpoint principal"],
    )


def specialist_boundary(
    *,
    response_channel: str = "through_core",
    tool_access_mode: str = "none",
    memory_write_mode: str = "through_core_only",
) -> SpecialistBoundaryContract:
    return SpecialistBoundaryContract(
        specialist_type="operational_planning_specialist",
        runtime_scope="subordinated_internal",
        user_visibility="hidden_from_user",
        response_channel=response_channel,
        tool_access_mode=tool_access_mode,
        memory_write_mode=memory_write_mode,
        operation_mode="advisory_only",
    )


def specialist_invocation(*, boundary: SpecialistBoundaryContract) -> SpecialistInvocationContract:
    return SpecialistInvocationContract(
        invocation_id="invoc-1",
        specialist_type="operational_planning_specialist",
        requested_by_service="orchestrator-service",
        role="planejamento_operacional_subordinado",
        task_focus="sequenciar etapas pequenas",
        entry_summary="estruturar milestone em etapas reversiveis",
        handoff_inputs=["goal=Please plan the milestone."],
        expected_outputs=["structured_findings", "through_core_only"],
        boundary=boundary,
        session_id=SessionId("sess-specialist"),
    )


def test_governance_service_name() -> None:
    assert GovernanceService.name == "governance-service"


def test_governance_service_allows_reversible_analysis_requests() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the milestone.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="analysis",
        requested_by_service="orchestrator-service",
        identity_mode="deep_analysis",
        identity_signature="nucleo_soberano_unificado",
        response_style="analitico, sintetico e rigoroso",
        plan=DeliberativePlanContract(
            plan_summary="comparar trade-offs do milestone",
            goal="Analyze the milestone.",
            steps=["consolidar contexto", "comparar trade-offs", "recomendar caminho"],
            active_domains=["analysis"],
            active_minds=["mente_analitica"],
            constraints=["low-risk"],
            risks=["sem risco material alem do escopo controlado do v1"],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=False,
            rationale="contexto=nenhum; apoio=baseline local",
            success_criteria=["conclusao deve explicitar o trade-off dominante"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            smallest_safe_next_action="explicitar o trade-off dominante antes de recomendar",
            continuity_action="continuar",
        ),
    )
    assert isinstance(result, GovernanceAssessment)
    assert result.governance_decision.decision == PermissionDecision.ALLOW
    assert result.governance_decision.risk_level == RiskLevel.LOW
    assert result.governance_check.decision_frame == "analysis"
    assert result.governance_check.context["identity_signature"] == "nucleo_soberano_unificado"
    assert (
        result.governance_check.context["identity_guardrail"]
        == "preservar rigor analitico antes de concluir"
    )


def test_governance_service_conditions_local_safe_operations_that_close_loop() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please update the rollout plan.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
        plan=low_risk_plan(),
    )
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.governance_decision.requires_audit is True
    assert result.governance_decision.conditions
    assert result.governance_check.open_loops == ["alinhar checkpoint principal"]


def test_governance_service_carries_autonomy_ladder_context() -> None:
    service = GovernanceService()
    plan = low_risk_plan()
    plan.requested_autonomy_level = "supervised_external_action"
    plan.max_autonomy_level = "confirm_before_action"
    plan.effective_autonomy_level = "confirm_before_action"
    plan.autonomy_ladder_status = "downgraded_to_max"
    plan.max_autonomy_capability_mode = "core_with_specialist_handoff"
    plan.autonomy_human_confirmation_required = True
    plan.autonomy_confirmation_mode = "explicit"
    plan.autonomy_blocked_runtime_actions = [
        "execute_without_confirmation",
        "automatic_promotion",
        "core_mutation",
    ]
    plan.autonomy_policy_refs = ["policy://autonomy-ladder/runtime-contract"]
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-autonomy-governance"),
            session_id=SessionId("sess-autonomy-governance"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Prepare the governed rollout.",
            timestamp="2026-07-04T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
        plan=plan,
    )

    assert result.governance_check.context["effective_autonomy_level"] == (
        "confirm_before_action"
    )
    assert result.governance_check.context["autonomy_ladder_status"] == (
        "downgraded_to_max"
    )
    assert "automatic_promotion" in (
        result.governance_check.context["autonomy_blocked_runtime_actions"]
    )
    assert result.governance_check.context[
        "autonomy_automatic_promotion_allowed"
    ] is False
    assert result.governance_check.context["autonomy_core_mutation_allowed"] is False


def test_governance_service_defers_capability_above_autonomy_limit() -> None:
    service = GovernanceService()
    plan = low_risk_plan()
    plan.capability_decision_selected_mode = "core_with_local_operation"
    plan.capability_decision_authorization_status = "authorized_with_conditions"
    plan.effective_autonomy_level = "assist_only"
    plan.max_autonomy_level = "assist_only"
    plan.max_autonomy_capability_mode = "contained_guidance"
    plan.autonomy_ladder_status = "within_limit"
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-autonomy-defer"),
            session_id=SessionId("sess-autonomy-defer"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Execute the local operation.",
            timestamp="2026-07-04T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
        plan=plan,
    )

    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert result.governance_decision.containment_hint == (
        "defer_capability_above_autonomy_limit"
    )
    assert "policy://autonomy-ladder/enforce-max-capability" in (
        result.governance_decision.policy_refs
    )


def test_governance_allows_bounded_work_item_creation() -> None:
    service = GovernanceService()
    result = service.assess_work_item_transition(
        contract=InputContract(
            request_id=RequestId("req-work-item-create"),
            session_id=SessionId("sess-work-item-create"),
            mission_id=MissionId("mission-work-item-create"),
            channel=ChannelType.CONSOLE,
            input_type=InputType.STRUCTURED_PAYLOAD,
            content="work_item_transition:create",
            timestamp="2026-05-18T00:00:00Z",
        ),
        current_state=MissionStateContract(
            mission_id=MissionId("mission-work-item-create"),
            mission_goal="Plan rollout",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-18T00:00:00Z",
        ),
        requested_transition="create",
        requested_work_item_ref="work-item://mission-work-item-create/validate-plan",
        requested_next_action_ref=None,
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.governance_check.subject_type == "work_item_transition"
    assert result.governance_check.context["memory_write_mode"] == "through_core_only"


def test_governance_blocks_work_item_transition_with_unbounded_ref() -> None:
    service = GovernanceService()
    result = service.assess_work_item_transition(
        contract=InputContract(
            request_id=RequestId("req-work-item-block"),
            session_id=SessionId("sess-work-item-block"),
            mission_id=MissionId("mission-work-item-block"),
            channel=ChannelType.CONSOLE,
            input_type=InputType.STRUCTURED_PAYLOAD,
            content="work_item_transition:create",
            timestamp="2026-05-18T00:00:00Z",
        ),
        current_state=MissionStateContract(
            mission_id=MissionId("mission-work-item-block"),
            mission_goal="Plan rollout",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-18T00:00:00Z",
        ),
        requested_transition="create",
        requested_work_item_ref="work-item://unsafe\nspoof",
        requested_next_action_ref=None,
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.governance_decision.containment_hint == "block_unbounded_work_item_ref"


def test_governance_allows_bounded_artifact_registration() -> None:
    service = GovernanceService()
    result = service.assess_artifact_lifecycle_transition(
        contract=InputContract(
            request_id=RequestId("req-artifact-register"),
            session_id=SessionId("sess-artifact-register"),
            mission_id=MissionId("mission-artifact-register"),
            channel=ChannelType.CONSOLE,
            input_type=InputType.STRUCTURED_PAYLOAD,
            content="artifact_lifecycle_transition:register",
            timestamp="2026-05-18T00:00:00Z",
        ),
        current_state=MissionStateContract(
            mission_id=MissionId("mission-artifact-register"),
            mission_goal="Plan rollout",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-18T00:00:00Z",
        ),
        requested_transition="register",
        requested_artifact_ref="artifact://mission-artifact-register/plan/v1",
        requested_replacement_artifact_ref=None,
        requested_rollback_plan_ref="rollback://mission-artifact-register/plan/v1",
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.governance_check.subject_type == "artifact_lifecycle_transition"
    assert result.governance_check.context["memory_write_mode"] == "through_core_only"


def test_governance_blocks_artifact_replacement_without_replacement_ref() -> None:
    service = GovernanceService()
    result = service.assess_artifact_lifecycle_transition(
        contract=InputContract(
            request_id=RequestId("req-artifact-replace-block"),
            session_id=SessionId("sess-artifact-replace-block"),
            mission_id=MissionId("mission-artifact-replace-block"),
            channel=ChannelType.CONSOLE,
            input_type=InputType.STRUCTURED_PAYLOAD,
            content="artifact_lifecycle_transition:replace",
            timestamp="2026-05-18T00:00:00Z",
        ),
        current_state=MissionStateContract(
            mission_id=MissionId("mission-artifact-replace-block"),
            mission_goal="Plan rollout",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-18T00:00:00Z",
            artifact_refs=["artifact://mission-artifact-replace-block/plan/v1"],
        ),
        requested_transition="replace",
        requested_artifact_ref="artifact://mission-artifact-replace-block/plan/v1",
        requested_replacement_artifact_ref=None,
        requested_rollback_plan_ref=None,
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.governance_decision.containment_hint == "block_missing_replacement_ref"


def test_governance_service_defers_when_reframing_goal_with_open_loop() -> None:
    service = GovernanceService()
    plan = DeliberativePlanContract(
        plan_summary="reformular objetivo com impacto operacional",
        goal="Plan the next release.",
        steps=["avaliar impacto", "validar rollout", "autorizar mudanca"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["revisao humana"],
        risks=["pedido contem sinais de risco operacional"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=nenhum; apoio=baseline local",
        success_criteria=["mudanca de objetivo deve ficar explicita e governavel"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="reformular a missao atual antes de autorizar qualquer desvio",
        continuity_action="reformular",
        open_loops=["release anterior ainda aberta"],
    )
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-3"),
            session_id=SessionId("sess-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the next release.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
        plan=plan,
    )
    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert result.governance_decision.requires_rollback_plan is True


def test_governance_service_defers_when_related_resumption_competes_with_open_loop() -> None:
    service = GovernanceService()
    plan = DeliberativePlanContract(
        plan_summary="retomar continuidade relacionada com impacto em missao ativa",
        goal="Retomar analise relacionada.",
        steps=["retomar missao relacionada", "comparar impacto com loop ativo"],
        active_domains=["analysis"],
        active_minds=["mente_analitica"],
        constraints=["revisao humana"],
        risks=["retomada relacionada pode competir com loops ainda abertos da missao ativa"],
        recommended_task_type="produce_analysis_brief",
        requires_human_validation=True,
        rationale="contexto=nenhum; apoio=baseline local",
        success_criteria=["retomada deve parecer continuidade intencional"],
        dominant_tension="equilibrar loops ativos com a retomada de uma missao relacionada",
        smallest_safe_next_action="explicitar por que a missao relacionada deve ser retomada agora",
        continuity_action="retomar",
        continuity_reason="missao relacionada venceu o ranking de continuidade",
        continuity_source="related_mission",
        continuity_target_mission_id="mission-related",
        continuity_target_goal="Analyze rollout risks.",
        open_loops=["release anterior ainda aberta"],
    )
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-3b"),
            session_id=SessionId("sess-3b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the related risk analysis.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="analysis",
        requested_by_service="orchestrator-service",
        plan=plan,
    )
    assert result.governance_check.mission_continuity_hint == "retomada_relacionada"
    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert result.governance_decision.requires_rollback_plan is True


def test_governance_service_blocks_sensitive_action() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-4"),
            session_id=SessionId("sess-4"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all project files now.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="sensitive_action",
        requested_by_service="orchestrator-service",
        plan=low_risk_plan(),
    )
    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.governance_decision.risk_level == RiskLevel.HIGH


def test_governance_service_defers_critical_memory_mutation() -> None:
    service = GovernanceService()
    result = service.assess_memory_operation(
        memory_class=MemoryClass.IDENTITY, action="write", requested_by_service="memory-service"
    )
    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert result.governance_decision.requires_rollback_plan is True


def test_governance_service_defers_governed_replay_recovery() -> None:
    service = GovernanceService()
    plan = DeliberativePlanContract(
        plan_summary="retomar checkpoint governado da continuidade",
        goal="Continue the sprint plan.",
        steps=["revisar ponto de retomada", "pedir validacao antes de continuar"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["revisao humana"],
        risks=["checkpoint recuperado ainda aguarda validacao explicita"],
        recommended_task_type="general_response",
        requires_human_validation=True,
        rationale="contexto=checkpoint; apoio=baseline local",
        success_criteria=["retomada deve permanecer governada ate validacao"],
        continuity_action="continuar",
        continuity_replay_status="awaiting_validation",
        continuity_recovery_mode="governed_review",
        continuity_resume_point="continuar:fechar checkpoint principal",
        open_loops=["fechar checkpoint principal"],
    )
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-5"),
            session_id=SessionId("sess-5"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the sprint plan.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
        plan=plan,
    )
    assert result.governance_check.mission_continuity_hint == "checkpoint_aguarda_validacao"
    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert "nao pode ser retomado automaticamente" in result.governance_decision.justification


def test_governance_service_allows_internal_specialist_handoff() -> None:
    service = GovernanceService()
    contract = InputContract(
        request_id=RequestId("req-specialist-1"),
        session_id=SessionId("sess-specialist-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the milestone.",
        timestamp="2026-03-23T00:00:00Z",
    )
    result = service.assess_specialist_handoff(
        contract=contract,
        plan=low_risk_plan(),
        selections=[
            SpecialistSelectionContract(
                specialist_type="operational_planning_specialist",
                selection_status="selected",
                selection_score=0.84,
                rationale="o plano exige decomposicao e checkpoints",
            )
        ],
        invocations=[specialist_invocation(boundary=specialist_boundary())],
        requested_by_service="orchestrator-service",
    )
    assert result.governance_check.subject_type == "specialist_handoff"
    assert result.governance_decision.decision == PermissionDecision.ALLOW
    assert result.governance_decision.requires_audit is False


def test_governance_service_conditions_specialist_handoff_when_review_is_required() -> None:
    service = GovernanceService()
    contract = InputContract(
        request_id=RequestId("req-specialist-2"),
        session_id=SessionId("sess-specialist-2"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the milestone.",
        timestamp="2026-03-23T00:00:00Z",
    )
    result = service.assess_specialist_handoff(
        contract=contract,
        plan=low_risk_plan(),
        selections=[
            SpecialistSelectionContract(
                specialist_type="governance_review_specialist",
                selection_status="selected",
                selection_score=0.87,
                rationale="o plano exige cautela normativa",
                requires_governance_review=True,
            )
        ],
        invocations=[specialist_invocation(boundary=specialist_boundary())],
        requested_by_service="orchestrator-service",
    )
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.governance_decision.requires_audit is True
    assert result.governance_decision.conditions


def test_governance_service_blocks_specialist_handoff_with_invalid_boundary() -> None:
    service = GovernanceService()
    contract = InputContract(
        request_id=RequestId("req-specialist-3"),
        session_id=SessionId("sess-specialist-3"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the milestone.",
        timestamp="2026-03-23T00:00:00Z",
    )
    result = service.assess_specialist_handoff(
        contract=contract,
        plan=low_risk_plan(),
        selections=[
            SpecialistSelectionContract(
                specialist_type="operational_planning_specialist",
                selection_status="selected",
                selection_score=0.84,
                rationale="o plano exige decomposicao e checkpoints",
            )
        ],
        invocations=[
            specialist_invocation(
                boundary=specialist_boundary(response_channel="direct_to_user")
            )
        ],
        requested_by_service="orchestrator-service",
    )
    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.governance_decision.requires_rollback_plan is True


def test_governance_service_allows_bounded_operator_feedback() -> None:
    service = GovernanceService()
    contract = InputContract(
        request_id=RequestId("req-feedback-1"),
        session_id=SessionId("sess-feedback-1"),
        mission_id=MissionId("mission-feedback-1"),
        channel=ChannelType.CONSOLE,
        input_type=InputType.STRUCTURED_PAYLOAD,
        content="operator_feedback:not_helpful",
        timestamp="2026-07-16T00:00:00+00:00",
        operator_identity_ref="operator://local_console",
    )
    feedback = OperatorFeedbackContract(
        feedback_id="operator-feedback://mission-feedback-1/001",
        mission_id=MissionId("mission-feedback-1"),
        experience_id="experience://mission-feedback-1/001",
        assessment="not_helpful",
        operator_ref="operator://local_console",
        rating=2,
        comment="The recommendation omitted rollback evidence.",
        timestamp="2026-07-16T00:00:01+00:00",
    )

    result = service.assess_operator_feedback(
        contract=contract,
        feedback=feedback,
        experience_mission_id="mission-feedback-1",
        reflection_available=True,
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == (
        PermissionDecision.ALLOW_WITH_CONDITIONS
    )
    assert result.governance_decision.requires_audit is True
    assert "policy://operator-feedback/bounded-core-write" in (
        result.governance_decision.policy_refs
    )


def test_governance_service_blocks_unbounded_operator_correction() -> None:
    service = GovernanceService()
    contract = InputContract(
        request_id=RequestId("req-feedback-blocked"),
        session_id=SessionId("sess-feedback-blocked"),
        mission_id=MissionId("mission-feedback-blocked"),
        channel=ChannelType.CONSOLE,
        input_type=InputType.STRUCTURED_PAYLOAD,
        content="operator_feedback:correction",
        timestamp="2026-07-16T00:00:00+00:00",
    )
    feedback = OperatorFeedbackContract(
        feedback_id="operator-feedback://mission-feedback-blocked/001",
        mission_id=MissionId("mission-feedback-blocked"),
        experience_id="experience://mission-feedback-blocked/001",
        assessment="correction",
        operator_ref="operator://local_console",
        timestamp="2026-07-16T00:00:01+00:00",
    )

    result = service.assess_operator_feedback(
        contract=contract,
        feedback=feedback,
        experience_mission_id="mission-feedback-blocked",
        reflection_available=True,
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.governance_decision.containment_hint == "block_missing_correction"


def test_governance_service_allows_bounded_use_of_current_evidence() -> None:
    result = GovernanceService().assess_knowledge_evidence(
        provenance_status="complete",
        freshness_status="current",
        conflict_status="none_declared",
        source_refs=["corpus://jarvis/curated/v1/strategy"],
        uncertainty_notes=[],
        assessed_at="2026-07-16T12:00:00Z",
    )

    assert result.status == "evidence_ready"
    assert result.use_mode == "bounded_grounding"
    assert result.human_review_required is False
    assert result.request_decision_mutation_allowed is False
    assert result.automatic_promotion_allowed is False
    assert result.core_mutation_allowed is False


def test_governance_service_requires_review_for_missing_or_conflicting_evidence() -> None:
    service = GovernanceService()
    missing = service.assess_knowledge_evidence(
        provenance_status="missing",
        freshness_status="unknown",
        conflict_status="unknown",
        source_refs=["local://knowledge/strategy"],
        uncertainty_notes=["source metadata missing for strategy"],
    )
    conflicting = service.assess_knowledge_evidence(
        provenance_status="complete",
        freshness_status="current",
        conflict_status="conflict_detected",
        source_refs=["corpus://test/strategy"],
        uncertainty_notes=["source conflicts declared for strategy"],
    )

    assert missing.status == "review_required"
    assert missing.use_mode == "do_not_assert_as_verified"
    assert missing.human_review_required is True
    assert "Source provenance is missing." in missing.blockers
    assert conflicting.status == "review_required"
    assert conflicting.use_mode == "do_not_assert_as_verified"
    assert "Declared source conflicts require explicit resolution." in conflicting.blockers
