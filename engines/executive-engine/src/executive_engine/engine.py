"""Executive engine for intent classification and unitary routing."""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import InputContract

from .intent_scope import (
    MAX_ROUTING_CHARS,
    inspect_intent_scope,
    keyword_hits,
    matching_keywords,
    normalize_routing_text,
)

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

        scope = inspect_intent_scope(contract.content)
        lowered = scope.normalized
        planning_hits = keyword_hits(lowered, PLANNING_KEYWORDS)
        analysis_hits = keyword_hits(lowered, ANALYSIS_KEYWORDS)
        execution_hits = scope.execution_hits
        risk_markers = self.extract_risk_markers(contract.content)
        intent = self.classify_intent(
            contract.content,
            planning_hits=planning_hits,
            analysis_hits=analysis_hits,
            risk_markers=risk_markers,
        )
        dominant_goal = self.dominant_goal(contract.content, intent)
        secondary_goals = self.secondary_goals(
            lowered,
            intent=intent,
            planning_hits=planning_hits,
            analysis_hits=analysis_hits,
        )
        ambiguity_reason = scope.uncertainty or self.ambiguity_reason(
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
            read_only=scope.read_only,
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

    def classify_intent(
        self,
        content: str,
        *,
        planning_hits: int,
        analysis_hits: int,
        risk_markers: list[str] | None = None,
    ) -> str:
        """Map free text to the current canonical intent set."""

        lowered = normalize_routing_text(content[:MAX_ROUTING_CHARS])
        markers = self.extract_risk_markers(content) if risk_markers is None else risk_markers
        if any(keyword in markers for keyword in HIGH_RISK_KEYWORDS):
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

        lowered = normalize_routing_text(content)
        markers = matching_keywords(lowered, HIGH_RISK_KEYWORDS)
        markers.extend(matching_keywords(lowered, MODERATE_RISK_KEYWORDS))
        return markers

    def dominant_goal(self, content: str, intent: str) -> str:
        lowered = normalize_routing_text(content[:MAX_ROUTING_CHARS]).strip()
        if intent == "analysis":
            return "produzir leitura confiavel antes de agir"
        if intent == "planning":
            return "definir um caminho executavel e seguro"
        if intent == "sensitive_action":
            return "preservar limites e evitar mudanca destrutiva"
        if keyword_hits(lowered, EXECUTION_KEYWORDS):
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
        if intent == "planning" and keyword_hits(lowered, ("compare",)):
            goals.append("comparar opcoes sem perder a proxima acao")
        if intent == "analysis" and keyword_hits(lowered, ("plan", "planej")):
            goals.append("indicar caminho pratico apos a analise")
        if keyword_hits(lowered, MODERATE_RISK_KEYWORDS):
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
        if keyword_hits(lowered, AMBIGUOUS_KEYWORDS):
            return "objetivo insuficientemente especificado"
        if intent == "general_assistance" and len(lowered.split()) <= 4:
            return "pedido curto demais para orientar a resposta"
        if (
            intent == "planning"
            and planning_hits > 0
            and analysis_hits > 0
            and not keyword_hits(lowered, ("primeiro", "first"))
        ):
            return "pedido mistura planejamento e analise sem prioridade explicita"
        if execution_hits > 0 and analysis_hits > 0:
            return "pedido mistura analise e execucao sem criterio de precedencia"
        return None

    @staticmethod
    def preferred_response_mode(
        *,
        intent: str,
        requires_clarification: bool,
        analysis_hits: int,
        read_only: bool = False,
    ) -> str:
        if requires_clarification:
            return "clarifying_guidance"
        if read_only:
            return "analysis_only"
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
