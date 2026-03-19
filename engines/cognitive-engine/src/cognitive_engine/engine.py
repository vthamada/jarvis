"""Cognitive engine for active minds and domains."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CognitiveSnapshot:
    """Selected minds and domains for the current request."""

    active_minds: list[str]
    active_domains: list[str]
    rationale: str


class CognitiveEngine:
    """Select the first meaningful minds and domains for the v1 nucleus."""

    name = "cognitive-engine"

    def build_snapshot(
        self,
        *,
        intent: str,
        risk_markers: list[str],
        retrieved_domains: list[str],
    ) -> CognitiveSnapshot:
        """Return an initial cognitive decomposition for the request."""

        minds = ["mente_executiva", "mente_pragmatica"]
        if intent == "planning":
            minds.extend(["mente_estrategica", "mente_tatica"])
        elif intent == "analysis":
            minds.extend(["mente_analitica", "mente_critica"])
        elif intent == "sensitive_action":
            minds.extend(["mente_etica", "mente_cetica"])
        if risk_markers:
            minds.append("mente_probabilistica")
        active_domains = retrieved_domains or ["assistencia_geral"]
        rationale = f"intent={intent}; risco={len(risk_markers)} marcador(es); dominios={active_domains}"
        return CognitiveSnapshot(
            active_minds=minds,
            active_domains=active_domains,
            rationale=rationale,
        )
