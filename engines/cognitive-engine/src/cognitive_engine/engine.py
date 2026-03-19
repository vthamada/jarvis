"""Cognitive engine for active minds, tensions, and specialist hints."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CognitiveSnapshot:
    """Selected minds, tensions, and specialist hints for the current request."""

    active_minds: list[str]
    active_domains: list[str]
    rationale: str
    primary_mind: str
    tensions: list[str]
    specialist_hints: list[str]
    deliberation_notes: list[str]


class CognitiveEngine:
    """Select the first meaningful minds and tensions for the v1 nucleus."""

    name = "cognitive-engine"

    def build_snapshot(
        self,
        *,
        intent: str,
        risk_markers: list[str],
        retrieved_domains: list[str],
    ) -> CognitiveSnapshot:
        """Return an initial cognitive decomposition for the request."""

        active_domains = retrieved_domains or ["assistencia_geral"]
        minds = self._select_minds(
            intent=intent,
            risk_markers=risk_markers,
            domains=active_domains,
        )
        tensions = self._select_tensions(
            intent=intent,
            risk_markers=risk_markers,
            domains=active_domains,
        )
        specialist_hints = self._select_specialist_hints(
            intent=intent,
            domains=active_domains,
        )
        deliberation_notes = self._build_deliberation_notes(
            intent=intent,
            minds=minds,
            tensions=tensions,
            specialist_hints=specialist_hints,
        )
        rationale = (
            f"intent={intent}; mente_primaria={minds[0]}; "
            f"tensoes={'; '.join(tensions)}; dominios={active_domains}; "
            f"especialistas={specialist_hints or ['nenhum_hint_especializado']}"
        )
        return CognitiveSnapshot(
            active_minds=minds,
            active_domains=active_domains,
            rationale=rationale,
            primary_mind=minds[0],
            tensions=tensions,
            specialist_hints=specialist_hints,
            deliberation_notes=deliberation_notes,
        )

    @staticmethod
    def _select_minds(
        *,
        intent: str,
        risk_markers: list[str],
        domains: list[str],
    ) -> list[str]:
        minds = ["mente_executiva", "mente_pragmatica"]
        if intent == "planning":
            minds.extend(["mente_estrategica", "mente_tatica"])
        elif intent == "analysis":
            minds.extend(["mente_analitica", "mente_critica", "mente_sistemica"])
        elif intent == "sensitive_action":
            minds.extend(["mente_etica", "mente_cetica"])
        else:
            minds.extend(["mente_comunicacional", "mente_integradora"])
        if len(domains) > 1:
            minds.append("mente_integradora")
        if risk_markers:
            minds.append("mente_probabilistica")
        return list(dict.fromkeys(minds))

    @staticmethod
    def _select_tensions(
        *,
        intent: str,
        risk_markers: list[str],
        domains: list[str],
    ) -> list[str]:
        tensions: list[str] = []
        if intent == "planning":
            tensions.append("equilibrar ambicao estrategica com proxima acao segura")
        elif intent == "analysis":
            tensions.append("equilibrar profundidade analitica com conclusao util")
        elif intent == "sensitive_action":
            tensions.append("equilibrar solicitacao do usuario com limites normativos")
        else:
            tensions.append("equilibrar clareza executiva com completude suficiente")
        if len(domains) > 1:
            tensions.append("integrar dominios sem perder foco operacional")
        if risk_markers:
            tensions.append("equilibrar velocidade de resposta com cautela operacional")
        return tensions

    @staticmethod
    def _select_specialist_hints(*, intent: str, domains: list[str]) -> list[str]:
        hints: list[str] = []
        planning_domains = ["strategy", "productivity"]
        if intent == "planning" or any(domain in domains for domain in planning_domains):
            hints.append("especialista_planejamento_operacional")
        if intent == "analysis" or "analysis" in domains:
            hints.append("especialista_analise_estruturada")
        if "governance" in domains:
            hints.append("especialista_revisao_governanca")
        return hints

    @staticmethod
    def _build_deliberation_notes(
        *,
        intent: str,
        minds: list[str],
        tensions: list[str],
        specialist_hints: list[str],
    ) -> list[str]:
        notes = [
            f"linha_primaria={minds[0]}",
            f"modo={intent}",
            f"tensao_central={tensions[0]}",
        ]
        if specialist_hints:
            notes.append(f"apoio_subordinado={specialist_hints[0]}")
        return notes
