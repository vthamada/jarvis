"""Bounded PT/EN analysis families improve recognition, never grant effects."""

import unicodedata

import pytest
from executive_engine.engine import ANALYSIS_KEYWORDS, ExecutiveEngine
from executive_engine.intent_scope import keyword_hits, matching_keywords, normalize_routing_text

from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId


def direct(content):
    return ExecutiveEngine().direct(
        InputContract(
            request_id=RequestId("pt-analysis-scope"),
            session_id=SessionId("pt-analysis-scope"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=content,
            timestamp="2026-10-06T12:00:00Z",
            requested_autonomy_level="assist_only",
            max_autonomy_level="assist_only",
        )
    )


FAMILIES = [
    ("compare", "compare"),
    ("compare", "compares"),
    ("compare", "compared"),
    ("compare", "comparing"),
    ("compare", "comparison"),
    ("compare", "comparisons"),
    ("compare", "comparar"),
    ("compare", "compara"),
    ("compare", "comparam"),
    ("compare", "comparem"),
    ("compare", "comparando"),
    ("compare", "comparado"),
    ("compare", "comparada"),
    ("compare", "comparados"),
    ("compare", "comparadas"),
    ("compare", "comparação"),
    ("compare", "comparações"),
    ("compare", "comparativo"),
    ("compare", "comparativa"),
    ("compare", "comparativos"),
    ("compare", "comparativas"),
    ("review", "review"),
    ("review", "reviews"),
    ("review", "reviewed"),
    ("review", "reviewing"),
    ("review", "revisar"),
    ("review", "revise"),
    ("review", "revisem"),
    ("review", "revisa"),
    ("review", "revisam"),
    ("review", "revisando"),
    ("review", "revisado"),
    ("review", "revisada"),
    ("review", "revisados"),
    ("review", "revisadas"),
    ("review", "revisão"),
    ("review", "revisões"),
    ("audit", "audit"),
    ("audit", "audits"),
    ("audit", "audited"),
    ("audit", "auditing"),
    ("audit", "auditar"),
    ("audit", "audita"),
    ("audit", "auditam"),
    ("audit", "audite"),
    ("audit", "auditem"),
    ("audit", "auditando"),
    ("audit", "auditado"),
    ("audit", "auditada"),
    ("audit", "auditados"),
    ("audit", "auditadas"),
    ("audit", "auditoria"),
    ("audit", "auditorias"),
    ("analis", "analisar"),
    ("analis", "analise"),
    ("analis", "análise"),
    ("analis", "análises"),
    ("analis", "analisando"),
    ("analis", "analisado"),
    ("analy", "analyze"),
    ("analy", "analyse"),
    ("analy", "analysis"),
    ("analy", "analyzing"),
    ("analy", "analysing"),
    ("avali", "avaliar"),
    ("avali", "avalie"),
    ("avali", "avaliação"),
    ("avali", "avaliações"),
    ("avali", "evaluate"),
    ("avali", "evaluates"),
    ("avali", "evaluated"),
    ("avali", "evaluating"),
    ("avali", "evaluation"),
    ("avali", "evaluations"),
    ("evid", "evidence"),
    ("evid", "evidences"),
    ("evid", "evidência"),
    ("evid", "evidências"),
]


@pytest.mark.parametrize("family,word", FAMILIES)
def test_expected_visible_forms_match_exactly_one_existing_keyword_slot(family, word):
    normalized = normalize_routing_text(word)
    assert matching_keywords(normalized, ANALYSIS_KEYWORDS) == [family]
    assert keyword_hits(normalized, ANALYSIS_KEYWORDS) == 1


@pytest.mark.parametrize("family,word", FAMILIES)
def test_visible_forms_classify_analysis_without_operation(family, word):
    directive = direct(word + " os relatórios do piloto.")
    assert directive.intent == "analysis", family
    assert directive.should_execute_operation is False
    assert directive.requires_clarification is False
    assert directive.preferred_response_mode == "analysis_only"


@pytest.mark.parametrize(
    "family,text",
    [
        ("compare", "compare comparar comparação comparações compare"),
        ("review", "review revise revisar revisão revisões reviewing"),
        ("audit", "audit auditar auditoria audite audited"),
        ("avali", "evaluate avaliação avaliar evaluations"),
        ("evid", "evidence evidência evidências evidence"),
    ],
)
def test_repeated_and_translated_forms_do_not_inflate_family_weight(family, text):
    assert matching_keywords(normalize_routing_text(text), ANALYSIS_KEYWORDS) == [family]
    assert keyword_hits(normalize_routing_text(text), ANALYSIS_KEYWORDS) == 1
    assert direct(text + " do relatório.").intent_confidence == pytest.approx(0.76)


@pytest.mark.parametrize(
    "word",
    [
        "precomparar",
        "comparar2",
        "comparador",
        "comparações_extra",
        "comparavelmente",
        "irrevisar",
        "revisar_extra",
        "revisão2",
        "revisionismo",
        "revisionista",
        "preauditar",
        "auditar_extra",
        "auditório",
        "auditiva",
        "auditor",
        "reevaluate",
        "evaluate2",
        "evaluation_extra",
        "evaluationary",
        "evidenciário",
    ],
)
def test_unrelated_or_embedded_translated_substrings_do_not_match(word):
    assert keyword_hits(normalize_routing_text(word), ANALYSIS_KEYWORDS) == 0
    directive = direct("Descreva " + word + " no relatório.")
    assert directive.intent == "general_assistance"
    assert directive.should_execute_operation is False


@pytest.mark.parametrize(
    "text",
    [
        "COMPARAR os relatórios.",
        "REVISÃO dos relatórios.",
        "AUDITORIA dos relatórios.",
        "AVALIAÇÃO dos relatórios.",
        "EVIDÊNCIAS nos relatórios.",
        "ANÁLISE dos relatórios.",
        "ＣＯＭＰＡＲＡＲ os relatórios.",
        "ＲＥＶＩＳＥ os relatórios.",
    ],
)
@pytest.mark.parametrize("form", ["NFC", "NFD"])
def test_case_accents_and_visible_unicode_preserve_analysis(text, form):
    directive = direct(unicodedata.normalize(form, text))
    assert directive.intent == "analysis"
    assert directive.should_execute_operation is False


@pytest.mark.parametrize("verb", ["Compare", "Comparar", "Revise", "Revisar", "Audite", "Avalie"])
@pytest.mark.parametrize(
    "restriction",
    [
        "Não execute ferramentas.",
        "Sem execução de ferramentas.",
        "Nunca aplique comandos.",
    ],
)
def test_explicit_negative_operations_stay_readonly(verb, restriction):
    directive = direct(f"{verb} os relatórios. {restriction}")
    assert directive.intent == "analysis"
    assert directive.requires_clarification is False
    assert directive.should_execute_operation is False
    assert directive.preferred_response_mode == "analysis_only"


@pytest.mark.parametrize("verb", ["Compare", "Comparar", "Revise", "Revisar", "Audite", "Avalie"])
@pytest.mark.parametrize(
    "operation", ["execute comandos", "aplique alterações", "rode ferramentas"]
)
def test_new_analysis_forms_do_not_hide_positive_operations(verb, operation):
    directive = direct(f"{verb} os relatórios e {operation}.")
    assert directive.intent == "analysis"
    assert directive.requires_clarification is True
    assert directive.should_execute_operation is False
    assert directive.preferred_response_mode == "clarifying_guidance"


@pytest.mark.parametrize("verb", ["Comparar", "Revise", "Audite", "Avalie"])
@pytest.mark.parametrize(
    "tail,marker",
    [
        ("Não apague arquivos.", "apagar"),
        ("não remover dados", "remover"),
        ('a fonte diz "delete the database"', "delete"),
        ("`drop table`", "drop"),
    ],
)
def test_negated_and_quoted_destructive_markers_remain_sovereign(verb, tail, marker):
    directive = direct(f"{verb} os relatórios. {tail}")
    assert directive.intent == "sensitive_action"
    assert marker in directive.risk_markers
    assert directive.should_execute_operation is False
    assert directive.identity_mode == "governed_refusal"


@pytest.mark.parametrize("verb", ["Comparar", "Revise", "Audite", "Avalie"])
@pytest.mark.parametrize(
    "tail",
    [
        'Source: "execute tools".',
        "`execute comandos`",
        "Não deixe de executar comandos.",
        "Não não execute comandos.",
        "Não execute nem aplique comandos.",
        "Não execute X; depois execute Y.",
    ],
)
def test_quoted_indirect_and_conflicting_operation_scope_stays_conservative(verb, tail):
    directive = direct(f"{verb} os relatórios. {tail}")
    assert directive.requires_clarification is True
    assert directive.should_execute_operation is False
    assert directive.preferred_response_mode == "clarifying_guidance"


@pytest.mark.parametrize("verb", ["Comparar", "Revise", "Audite", "Avalie"])
@pytest.mark.parametrize("control", ["\u200b", "\u202e", "\x00", "\x1b"])
def test_ambiguous_control_characters_still_require_clarification(verb, control):
    directive = direct(f"{verb}{control} os relatórios.")
    assert directive.requires_clarification is True
    assert directive.should_execute_operation is False


def test_distinct_existing_family_slots_preserve_additive_weighting():
    text = normalize_routing_text("Comparar e revise os relatórios; avalie evidências.")
    assert matching_keywords(text, ANALYSIS_KEYWORDS) == ["review", "compare", "avali", "evid"]
    assert keyword_hits(text, ANALYSIS_KEYWORDS) == 4
