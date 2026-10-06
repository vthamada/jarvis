"""Bounded lexical routing guards, never authorization or a language parser.

Only explicit local restrictions are recognized. Uncertain scope asks for
clarification; risk scanning is deliberately independent of these restrictions.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

MAX_ROUTING_CHARS = 32768

# These are word families, not arbitrary substrings ("run" is not "runtime").
_FAMILIES = {
    "plan": r"plan(?:s|o|os|ned|ning)?",
    "roadmap": r"roadmaps?",
    "milestone": r"milestones?",
    "etapa": r"etapas?",
    "sprint": r"sprints?",
    "planej": r"planej\w*",
    "analis": r"analis\w*",
    "analy": r"analy(?:s\w*|z\w*)",
    "avali": r"avali\w*",
    "evid": r"evid(?:ence|ences|encia|encias|ente|entes)?",
    "review": r"review(?:s|ed|ing)?",
    "audit": r"audit(?:s|ed|ing)?",
    "compare": r"compar(?:e|es|ed|ing)",
    "delete": r"delet(?:e|es|ed|ing)",
    "drop": r"drop(?:s|ped|ping)?",
    "destroy": r"destroy(?:s|ed|ing)?",
    "excluir": r"exclu(?:ir|i|a|am|indo|ido|idos|ida|idas|sao|soes)",
    "apagar": r"apag(?:ar|a|ue|uem|ando|ado|ados|ada|adas)",
    "deletar": r"delet(?:ar|a|e|em|ando|ado|ados|ada|adas)",
    "remover": r"remov(?:er|a|am|e|endo|ido|idos|ida|idas)",
    "deploy": r"deploy(?:s|ed|ing|ment|ments)?",
    "publish": r"publish(?:es|ed|ing)?",
    "release": r"releas(?:e|es|ed|ing)",
    "migrate": r"migrat(?:e|es|ed|ing|ion|ions)",
    "update": r"updat(?:e|es|ed|ing)",
    "rewrite": r"rewrit(?:e|es|ten|ing)",
    "alter": r"alter(?:s|ed|ing|ation|ations)?",
    "change": r"chang(?:e|es|ed|ing)",
}

_OPERATIONS = re.compile(
    r"\b(?:execute|executes|executing|run|runs|running|apply|applies|applying|"
    r"executar|execute|executem|executando|rodar|rode|rodem|aplicar|aplique|apliquem)\b"
)
_NEGATOR = re.compile(
    r"\b(?:do\s+not|don['’]?t|must\s+not|should\s+not|shall\s+not|"
    r"cannot|can['’]?t|never|nao|nunca|jamais|sem|without|no|not)\b"
)
_CLAUSE_BOUNDARY = re.compile(
    r"[.;!?\n]|\b(?:but|however|then|mas|porem|entao|depois)\b"
)
_READ_ONLY = re.compile(
    r"\bread[ -]only\b|\b(?:somente|apenas)\s+(?:de\s+)?leitura\b|"
    r"\b(?:no|without|sem|nenhuma)\b[^.;!?\n]{0,64}\b"
    r"(?:execution|execucao|tool\s+use|uso\s+de\s+ferramentas)\b|"
    r"\b(?:do\s+not|don['’]?t|never)\s+use\s+(?:any\s+)?tools\b|"
    r"\b(?:nao|nunca)\s+(?:use|utilize)\s+ferramentas\b"
)
_TEXT_PREPARATION = re.compile(
    r"\b(?:draft|prepare|write|produce|gerar|gere|escreva|redija|produza|elabore)\b"
    r"(?:\W+\w+){0,6}\W+(?:plan|planning|plano|report|relatorio|summary|resumo|"
    r"proposal|proposta|draft|rascunho|document|documento|list|lista|json|csv)\b"
)
_INDIRECT_NEGATION = re.compile(
    r"\b(?:fail|forget|refuse|avoid|stop|deixe|deixar|evite|evitar|esqueca)\b"
)
_QUOTED_OR_CODE = re.compile(
    r'["“”«»‹›`]|(?<!\w)\'|‘[^’\n]*’|(?:^|\n)\s*>|'
    r"\b(?:source|quote|system|assistant|developer|tool)\s*:|"
    r"<\s*(?:source|system|assistant|developer|tool)\b",
    re.DOTALL,
)


def normalize_routing_text(content: str) -> str:
    """Normalize visible word forms; format controls remain an uncertainty flag."""
    normalized = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", content))
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


@lru_cache(maxsize=128)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    family = _FAMILIES.get(keyword, re.escape(keyword).replace(r"\ ", r"\s+"))
    return re.compile(r"(?<!\w)(?:" + family + r")(?!\w)")


def keyword_hits(normalized: str, keywords: tuple[str, ...]) -> int:
    """Count matching keyword families once each, preserving legacy hit weighting."""
    return sum(bool(_keyword_pattern(keyword).search(normalized)) for keyword in keywords)


def matching_keywords(normalized: str, keywords: tuple[str, ...]) -> list[str]:
    return [keyword for keyword in keywords if _keyword_pattern(keyword).search(normalized)]


@dataclass(frozen=True)
class IntentScope:
    """Restriction hints only. A positive operation is still not an authority grant."""

    normalized: str
    execution_hits: int
    read_only: bool
    uncertainty: str | None = None


def inspect_intent_scope(content: str) -> IntentScope:
    """Recognize local negation without letting it cover subsequent clauses.

    Multiple operations in a negated clause, double/indirect negatives, quotes,
    and malformed or oversized inputs are deliberately not interpreted as a
    permission. This is a conservative routing guard, not semantic understanding.
    """
    if len(content) > MAX_ROUTING_CHARS:
        return IntentScope("", 0, True, "input exceeds lexical routing limit")
    normalized = normalize_routing_text(content)
    if any(
        unicodedata.category(char) == "Cf"
        or (unicodedata.category(char) == "Cc" and char not in "\t\r\n")
        for char in content
    ):
        return IntentScope(normalized, 0, True, "input contains ambiguous control characters")

    positive = 0
    negated = False
    uncertain = None
    for clause in _CLAUSE_BOUNDARY.split(normalized):
        operations = tuple(_OPERATIONS.finditer(clause))
        negators = tuple(_NEGATOR.finditer(clause))
        if not operations:
            continue
        for operation in operations:
            preceding = [item for item in negators if item.end() <= operation.start()]
            local = [item for item in preceding if operation.start() - item.end() <= 96]
            if not local:
                positive += 1
                continue
            between = clause[local[-1].end() : operation.start()]
            if (
                len(preceding) > 1
                or len(operations) > 1
                or _INDIRECT_NEGATION.search(between)
            ):
                uncertain = "operation negation has uncertain scope"
            negated = True

    read_only = bool(_READ_ONLY.search(normalized) or _TEXT_PREPARATION.search(normalized))
    read_only = read_only or negated
    # Quoted/code/source instructions cannot create or widen an operation route.
    if _QUOTED_OR_CODE.search(normalized) and (
        _OPERATIONS.search(normalized)
        or keyword_hits(normalized, ("plan", "planej", "roadmap", "milestone", "etapa", "sprint"))
    ):
        uncertain = "quoted or source text cannot establish operation scope"
    if read_only and positive:
        uncertain = "read-only restriction conflicts with a positive operation"
    return IntentScope(normalized, positive, read_only, uncertain)
