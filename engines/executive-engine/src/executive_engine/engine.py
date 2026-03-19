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


@dataclass(frozen=True)
class ExecutiveDirective:
    """High-level routing decision for the orchestrator."""

    intent: str
    should_query_knowledge: bool
    should_execute_operation: bool
    risk_markers: list[str]


class ExecutiveEngine:
    """Centralize first-pass intent classification and routing hints."""

    name = "executive-engine"

    def direct(self, contract: InputContract) -> ExecutiveDirective:
        """Return a directive for knowledge, operation, and risk scanning."""

        intent = self.classify_intent(contract.content)
        risk_markers = self.extract_risk_markers(contract.content)
        return ExecutiveDirective(
            intent=intent,
            should_query_knowledge=intent in {"planning", "analysis", "general_assistance"},
            should_execute_operation=intent != "sensitive_action",
            risk_markers=risk_markers,
        )

    def classify_intent(self, content: str) -> str:
        """Map free text to the current canonical intent set."""

        lowered = content.lower()
        if any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS):
            return "sensitive_action"
        if "plan" in lowered or "planej" in lowered:
            return "planning"
        if "analis" in lowered or "analy" in lowered:
            return "analysis"
        return "general_assistance"

    def extract_risk_markers(self, content: str) -> list[str]:
        """Collect risk markers without making the final governance decision."""

        lowered = content.lower()
        markers = [keyword for keyword in HIGH_RISK_KEYWORDS if keyword in lowered]
        markers.extend(keyword for keyword in MODERATE_RISK_KEYWORDS if keyword in lowered)
        return markers
