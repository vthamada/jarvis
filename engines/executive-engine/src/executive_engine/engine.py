"""Executive engine for intent classification and high-level routing."""

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


class ExecutiveEngine:
    """Centralize first-pass intent classification and routing hints."""

    name = "executive-engine"

    def direct(self, contract: InputContract) -> ExecutiveDirective:
        """Return a directive for knowledge, deliberation, and operation routing."""

        lowered = contract.content.lower()
        planning_hits = sum(1 for keyword in PLANNING_KEYWORDS if keyword in lowered)
        analysis_hits = sum(1 for keyword in ANALYSIS_KEYWORDS if keyword in lowered)
        risk_markers = self.extract_risk_markers(contract.content)
        intent = self.classify_intent(
            contract.content, planning_hits=planning_hits, analysis_hits=analysis_hits
        )
        requires_clarification = self.requires_clarification(
            lowered,
            intent=intent,
            planning_hits=planning_hits,
            analysis_hits=analysis_hits,
        )
        preferred_response_mode = self.preferred_response_mode(
            intent=intent,
            requires_clarification=requires_clarification,
            analysis_hits=analysis_hits,
        )
        return ExecutiveDirective(
            intent=intent,
            intent_confidence=self.intent_confidence(
                intent, planning_hits, analysis_hits, requires_clarification
            ),
            requires_clarification=requires_clarification,
            should_query_knowledge=intent in {"planning", "analysis", "general_assistance"},
            should_execute_operation=(
                intent != "sensitive_action"
                and not requires_clarification
                and preferred_response_mode not in {"analysis_only", "clarifying_guidance"}
            ),
            preferred_response_mode=preferred_response_mode,
            risk_markers=risk_markers,
            mind_hints=self.mind_hints_for_intent(intent),
        )

    def classify_intent(self, content: str, *, planning_hits: int, analysis_hits: int) -> str:
        """Map free text to the current canonical intent set."""

        lowered = content.lower()
        if any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS):
            return "sensitive_action"
        if analysis_hits > 0 and lowered.startswith(("analyze", "analyse", "análise", "analis")):
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

    @staticmethod
    def requires_clarification(
        lowered: str,
        *,
        intent: str,
        planning_hits: int,
        analysis_hits: int,
    ) -> bool:
        if any(keyword in lowered for keyword in AMBIGUOUS_KEYWORDS):
            return True
        if intent == "general_assistance" and len(lowered.split()) <= 4:
            return True
        if (
            intent == "planning"
            and planning_hits > 0
            and analysis_hits > 0
            and "first" not in lowered
            and "primeiro" not in lowered
        ):
            return True
        return False

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
            return min(0.65 + (planning_hits * 0.1), 0.95)
        if intent == "analysis":
            return min(0.65 + (analysis_hits * 0.1), 0.95)
        return 0.6

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
