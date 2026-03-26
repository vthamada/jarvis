"""Identity engine for response posture and stable principles."""

from __future__ import annotations

from dataclasses import dataclass

from shared.state import SYSTEM_IDENTITY


@dataclass(frozen=True)
class IdentityProfile:
    """Compact identity snapshot consumed by synthesis and planning."""

    official_definition: str
    mission_statement: str
    posture: str
    traits: list[str]
    identity_signature: str
    governance_posture: str
    principle_focus: list[str]


class IdentityEngine:
    """Expose stable identity and communication posture for the v1 core."""

    name = "identity-engine"

    def get_profile(self) -> IdentityProfile:
        """Return the canonical identity profile used by the nucleus."""

        principle_focus = [
            SYSTEM_IDENTITY.nuclear_principles["truth_and_quality"][0],
            SYSTEM_IDENTITY.nuclear_principles["utility"][0],
            SYSTEM_IDENTITY.nuclear_principles["safety_and_governance"][0],
        ]
        return IdentityProfile(
            official_definition=SYSTEM_IDENTITY.official_definition,
            mission_statement=SYSTEM_IDENTITY.mission_statement,
            posture=", ".join(SYSTEM_IDENTITY.behavioral_posture[:3]),
            traits=list(SYSTEM_IDENTITY.core_traits[:4]),
            identity_signature="nucleo_soberano_unificado",
            governance_posture=", ".join(
                SYSTEM_IDENTITY.nuclear_principles["safety_and_governance"][:2]
            ),
            principle_focus=principle_focus,
        )

    def build_response_style(self, *, intent: str, blocked: bool) -> str:
        """Describe the tone that should shape the final synthesis."""

        if blocked:
            return "claro, firme e governado"
        if intent == "planning":
            return "estruturado, executivo e orientado a proximos passos"
        if intent == "analysis":
            return "analitico, sintetico e rigoroso"
        return "sereno, util e direto"
