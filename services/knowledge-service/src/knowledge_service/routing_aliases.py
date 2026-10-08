"""Bounded PT/EN noun aliases for local routing, never an authority decision.

Only the routing copy is translated. Original queries, source offsets and
canonical memory remain unchanged. Aliases replace tokens rather than add
keyword slots, preserving the existing scoring weights and priors.
"""

import re

_ALIASES = {
    "painel de telemetria": "telemetry dashboard",
    "painel de observabilidade": "observability dashboard",
    "documentacao": "documentation",
    "documentacoes": "documentations",
    "observabilidade": "observability",
    "telemetria": "telemetry",
    "relatorio": "report",
    "relatorios": "reports",
    "piloto": "pilot",
    "pilotos": "pilots",
    "comparacao": "comparison",
    "comparacoes": "comparisons",
}
_PATTERN = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(key).replace(r"\ ", r"\s+") for key in _ALIASES)
    + r")(?!\w)"
)


def routing_aliases(normalized_query: str) -> str:
    """Accept the existing accent-folded routing copy, not source text."""
    return _PATTERN.sub(
        lambda match: _ALIASES[re.sub(r"\s+", " ", match.group())], normalized_query
    )
