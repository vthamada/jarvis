"""Cognitive engine for active minds, tensions, and specialist hints."""

from __future__ import annotations

from dataclasses import dataclass

V1_NUCLEAR_MINDS = [
    "mente_logica",
    "mente_analitica",
    "mente_sistemica",
    "mente_probabilistica",
    "mente_estrategica",
    "mente_tatica",
    "mente_decisoria",
    "mente_pragmatica",
    "mente_executiva",
    "mente_critica",
    "mente_comunicacional",
    "mente_etica",
]


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
    supporting_minds: list[str]
    suppressed_minds: list[str]
    dominant_tension: str
    arbitration_summary: str


class CognitiveEngine:
    """Select the first meaningful minds and tensions for the v1 nucleus."""

    name = "cognitive-engine"

    def build_snapshot(
        self,
        *,
        intent: str,
        risk_markers: list[str],
        retrieved_domains: list[str],
        mind_hints: list[str] | None = None,
    ) -> CognitiveSnapshot:
        """Return an initial cognitive decomposition for the request."""

        active_domains = retrieved_domains or ["assistencia_geral"]
        minds = self._select_minds(
            intent=intent,
            risk_markers=risk_markers,
            domains=active_domains,
            mind_hints=mind_hints,
        )
        tensions = self._select_tensions(
            intent=intent,
            risk_markers=risk_markers,
            domains=active_domains,
        )
        primary_mind = minds[0]
        supporting_minds = minds[1:3]
        suppressed_minds = minds[3:6]
        dominant_tension = tensions[0]
        specialist_hints = self._select_specialist_hints(
            intent=intent,
            domains=active_domains,
            dominant_tension=dominant_tension,
            risk_markers=risk_markers,
        )
        arbitration_summary = self._build_arbitration_summary(
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            dominant_tension=dominant_tension,
            domains=active_domains,
        )
        deliberation_notes = self._build_deliberation_notes(
            intent=intent,
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            dominant_tension=dominant_tension,
            specialist_hints=specialist_hints,
        )
        rationale = (
            f"mente_primaria={primary_mind}; suporte={', '.join(supporting_minds) or 'nenhum'}; "
            f"tensao_dominante={dominant_tension}; dominios={active_domains}; "
            f"arbitragem={arbitration_summary}"
        )
        return CognitiveSnapshot(
            active_minds=[primary_mind, *supporting_minds],
            active_domains=active_domains,
            rationale=rationale,
            primary_mind=primary_mind,
            tensions=tensions,
            specialist_hints=specialist_hints,
            deliberation_notes=deliberation_notes,
            supporting_minds=supporting_minds,
            suppressed_minds=suppressed_minds,
            dominant_tension=dominant_tension,
            arbitration_summary=arbitration_summary,
        )

    @staticmethod
    def _select_minds(
        *,
        intent: str,
        risk_markers: list[str],
        domains: list[str],
        mind_hints: list[str] | None = None,
    ) -> list[str]:
        minds = [mind for mind in (mind_hints or []) if mind in V1_NUCLEAR_MINDS]
        if intent == "planning":
            minds.extend(["mente_executiva", "mente_estrategica", "mente_pragmatica"])
        elif intent == "analysis":
            minds.extend(["mente_analitica", "mente_critica", "mente_logica"])
        elif intent == "sensitive_action":
            minds.extend(["mente_etica", "mente_critica", "mente_decisoria"])
        else:
            minds.extend(["mente_executiva", "mente_comunicacional", "mente_pragmatica"])
        if len(domains) > 1:
            minds.append("mente_sistemica")
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
            tensions.append("equilibrar ambicao estrategica com a menor proxima acao segura")
        elif intent == "analysis":
            tensions.append("equilibrar profundidade analitica com conclusao util")
        elif intent == "sensitive_action":
            tensions.append("equilibrar solicitacao do usuario com limites normativos")
        else:
            tensions.append("equilibrar clareza executiva com contexto suficiente")
        if len(domains) > 1:
            tensions.append("integrar dominios sem diluir o objetivo dominante")
        if risk_markers:
            tensions.append("equilibrar velocidade de resposta com cautela operacional")
        return tensions

    @staticmethod
    def _select_specialist_hints(
        *,
        intent: str,
        domains: list[str],
        dominant_tension: str,
        risk_markers: list[str],
    ) -> list[str]:
        hints: list[str] = []
        if intent == "planning" or "continuidade" in dominant_tension or len(domains) > 1:
            hints.append("especialista_planejamento_operacional")
        if intent == "analysis" or any(domain in domains for domain in ["analysis", "strategy"]):
            hints.append("especialista_analise_estruturada")
        if risk_markers or "governance" in domains or "normativos" in dominant_tension:
            hints.append("especialista_revisao_governanca")
        return hints[:3]

    @staticmethod
    def _build_arbitration_summary(
        *,
        primary_mind: str,
        supporting_minds: list[str],
        dominant_tension: str,
        domains: list[str],
    ) -> str:
        support = ", ".join(supporting_minds) if supporting_minds else "sem apoio adicional"
        domain_hint = ", ".join(domains[:2])
        return (
            f"{primary_mind} lidera a resposta com apoio de {support}, "
            f"mantendo foco em {domain_hint} enquanto arbitra {dominant_tension}"
        )

    @staticmethod
    def _build_deliberation_notes(
        *,
        intent: str,
        primary_mind: str,
        supporting_minds: list[str],
        dominant_tension: str,
        specialist_hints: list[str],
    ) -> list[str]:
        notes = [
            f"linha_primaria={primary_mind}",
            f"modo={intent}",
            f"tensao_central={dominant_tension}",
        ]
        if supporting_minds:
            notes.append(f"apoio={', '.join(supporting_minds)}")
        if specialist_hints:
            notes.append(f"apoio_subordinado={', '.join(specialist_hints[:2])}")
        return notes
