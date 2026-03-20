"""Executive engine for intent classification and unitary routing."""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import InputContract

HIGH_RISK_KEYWORDS = (
    "delete",
    "drop",
    "destroy",
    "excluir",
    "apagar",
    "deletar",
    "remover",
)

MODERATE_RISK_KEYWORDS = (
    "deploy",
    "publish",
    "release",
    "migrate",
    "update",
    "rewrite",
    "alter",
    "change",
)

PLANNING_KEYWORDS = (
    "plan",
    "planej",
    "roadmap",
    "milestone",
    "etapa",
    "sprint",
)

ANALYSIS_KEYWORDS = (
    "analis",
    "analy",
    "review",
    "audit",
    "compare",
    "trade-off",
    "tradeoff",
    "avali",
    "evid",
)

EXECUTION_KEYWORDS = (
    "execute",
    "run",
    "apply",
    "draft",
    "prepare",
    "gerar",
    "executar",
)

AMBIGUOUS_KEYWORDS = (
    "help me",
    "ajuda",
    "alguma coisa",
    "something",
    "melhorar isso",
)


@dataclass(frozen=True)
class ExecutiveDirective:
    """High-level routing decision for the orchestrator."""

    intent: str
    intent_confidence: float
    requires_clarification: bool
    should_query_knowledge: bool
    should_execute_operation: bool
    preferred_response_mode: str
    risk_markers: list[str]
    mind_hints: list[str]
    dominant_goal: str
    secondary_goals: list[str]
    ambiguity_reason: str | None
    identity_mode: str


class ExecutiveEngine:
    """Centralize first-pass intent classification and routing hints."""

    name = "executive-engine"

    def direct(self, contract: InputContract) -> ExecutiveDirective:
        """Return a directive for knowledge, deliberation, and operation routing."""

        lowered = contract.content.lower()
        planning_hits = sum(1 for keyword in PLANNING_KEYWORDS if keyword in lowered)
        analysis_hits = sum(1 for keyword in ANALYSIS_KEYWORDS if keyword in lowered)
        execution_hits = sum(1 for keyword in EXECUTION_KEYWORDS if keyword in lowered)
        risk_markers = self.extract_risk_markers(contract.content)
        intent = self.classify_intent(
            contract.content,
            planning_hits=planning_hits,
            analysis_hits=analysis_hits,
        )
        dominant_goal = self.dominant_goal(contract.content, intent)
        secondary_goals = self.secondary_goals(
            lowered,
            intent=intent,
            planning_hits=planning_hits,
            analysis_hits=analysis_hits,
        )
        ambiguity_reason = self.ambiguity_reason(
            lowered,
            intent=intent,
            planning_hits=planning_hits,
            analysis_hits=analysis_hits,
            execution_hits=execution_hits,
        )
        requires_clarification = ambiguity_reason is not None
        preferred_response_mode = self.preferred_response_mode(
            intent=intent,
            requires_clarification=requires_clarification,
            analysis_hits=analysis_hits,
        )
        identity_mode = self.identity_mode(
            intent=intent,
            blocked=intent == "sensitive_action",
            preferred_response_mode=preferred_response_mode,
        )
        return ExecutiveDirective(
            intent=intent,
            intent_confidence=self.intent_confidence(
                intent,
                planning_hits,
                analysis_hits,
                requires_clarification,
            ),
            requires_clarification=requires_clarification,
            should_query_knowledge=intent in {"planning", "analysis", "general_assistance"},
            should_execute_operation=(
                intent != "sensitive_action"
                and not requires_clarification
                and preferred_response_mode == "plan_and_operate"
            ),
            preferred_response_mode=preferred_response_mode,
            risk_markers=risk_markers,
            mind_hints=self.mind_hints_for_intent(intent),
            dominant_goal=dominant_goal,
            secondary_goals=secondary_goals,
            ambiguity_reason=ambiguity_reason,
            identity_mode=identity_mode,
        )

    def classify_intent(self, content: str, *, planning_hits: int, analysis_hits: int) -> str:
        """Map free text to the current canonical intent set."""

        lowered = content.lower()
        if any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS):
            return "sensitive_action"
        if analysis_hits > 0 and lowered.startswith(("analyze", "analyse", "analise", "analis")):
            return "analysis"
        if analysis_hits > planning_hits and analysis_hits > 0:
            return "analysis"
        if planning_hits > 0:
            return "planning"
        if analysis_hits > 0:
            return "analysis"
        return "general_assistance"

    def extract_risk_markers(self, content: str) -> list[str]:
        """Collect risk markers without making the final governance decision."""

        lowered = content.lower()
        markers = [keyword for keyword in HIGH_RISK_KEYWORDS if keyword in lowered]
        markers.extend(keyword for keyword in MODERATE_RISK_KEYWORDS if keyword in lowered)
        return markers

    def dominant_goal(self, content: str, intent: str) -> str:
        lowered = content.lower().strip()
        if intent == "analysis":
            return "produzir leitura confiavel antes de agir"
        if intent == "planning":
            return "definir um caminho executavel e seguro"
        if intent == "sensitive_action":
            return "preservar limites e evitar mudanca destrutiva"
        if any(keyword in lowered for keyword in EXECUTION_KEYWORDS):
            return "entregar orientacao pratica sem ampliar escopo"
        return "responder com orientacao util e coerente"

    @staticmethod
    def secondary_goals(
        lowered: str,
        *,
        intent: str,
        planning_hits: int,
        analysis_hits: int,
    ) -> list[str]:
        goals: list[str] = []
        if planning_hits > 0 and analysis_hits > 0:
            goals.append("preservar espaco para analise antes de executar")
        if intent == "planning" and "compare" in lowered:
            goals.append("comparar opcoes sem perder a proxima acao")
        if intent == "analysis" and any(keyword in lowered for keyword in ("plan", "planej")):
            goals.append("indicar caminho pratico apos a analise")
        if any(keyword in lowered for keyword in MODERATE_RISK_KEYWORDS):
            goals.append("manter operacao local e rastreavel")
        return goals[:2]

    @staticmethod
    def ambiguity_reason(
        lowered: str,
        *,
        intent: str,
        planning_hits: int,
        analysis_hits: int,
        execution_hits: int,
    ) -> str | None:
        if any(keyword in lowered for keyword in AMBIGUOUS_KEYWORDS):
            return "objetivo insuficientemente especificado"
        if intent == "general_assistance" and len(lowered.split()) <= 4:
            return "pedido curto demais para orientar a resposta"
        if (
            intent == "planning"
            and planning_hits > 0
            and analysis_hits > 0
            and "primeiro" not in lowered
            and "first" not in lowered
        ):
            return "pedido mistura planejamento e analise sem prioridade explicita"
        if execution_hits > 0 and intent == "analysis":
            return "pedido mistura analise e execucao sem criterio de precedencia"
        return None

    @staticmethod
    def preferred_response_mode(
        *,
        intent: str,
        requires_clarification: bool,
        analysis_hits: int,
    ) -> str:
        if requires_clarification:
            return "clarifying_guidance"
        if intent == "analysis" or analysis_hits > 0:
            return "analysis_only"
        if intent == "planning":
            return "plan_and_operate"
        return "direct_guidance"

    @staticmethod
    def identity_mode(*, intent: str, blocked: bool, preferred_response_mode: str) -> str:
        if blocked:
            return "governed_refusal"
        if preferred_response_mode == "analysis_only":
            return "deep_analysis"
        if preferred_response_mode == "plan_and_operate":
            return "structured_planning"
        return "executive_guidance"

    @staticmethod
    def intent_confidence(
        intent: str,
        planning_hits: int,
        analysis_hits: int,
        requires_clarification: bool,
    ) -> float:
        if requires_clarification:
            return 0.45
        if intent == "sensitive_action":
            return 0.95
        if intent == "planning":
            return min(0.66 + (planning_hits * 0.1), 0.95)
        if intent == "analysis":
            return min(0.66 + (analysis_hits * 0.1), 0.95)
        return 0.62

    @staticmethod
    def mind_hints_for_intent(intent: str) -> list[str]:
        """Return the preferred v1 nuclear minds for the given intent."""

        return {
            "planning": [
                "mente_executiva",
                "mente_pragmatica",
                "mente_estrategica",
                "mente_tatica",
            ],
            "analysis": [
                "mente_analitica",
                "mente_critica",
                "mente_logica",
                "mente_probabilistica",
            ],
            "general_assistance": [
                "mente_comunicacional",
                "mente_executiva",
                "mente_pragmatica",
                "mente_decisoria",
            ],
            "sensitive_action": [
                "mente_etica",
                "mente_critica",
                "mente_probabilistica",
                "mente_decisoria",
            ],
        }.get(intent, ["mente_executiva", "mente_pragmatica"])
