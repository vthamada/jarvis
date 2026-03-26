from governance_service.service import GovernanceAssessment, GovernanceService

from shared.contracts import (
    DeliberativePlanContract,
    InputContract,
    SpecialistBoundaryContract,
    SpecialistInvocationContract,
    SpecialistSelectionContract,
)
from shared.types import (
    ChannelType,
    InputType,
    MemoryClass,
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
        specialist_type="especialista_planejamento_operacional",
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
        specialist_type="especialista_planejamento_operacional",
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
                specialist_type="especialista_planejamento_operacional",
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
                specialist_type="especialista_revisao_governanca",
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
                specialist_type="especialista_planejamento_operacional",
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
