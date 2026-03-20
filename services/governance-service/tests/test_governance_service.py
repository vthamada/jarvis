from governance_service.service import GovernanceAssessment, GovernanceService

from shared.contracts import DeliberativePlanContract, InputContract
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
