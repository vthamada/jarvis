"""PT noun routing parity, not broader linguistic or permission coverage."""

import pytest
from knowledge_service.routing_aliases import routing_aliases
from knowledge_service.service import KnowledgeService

PAIRS = (
    ("Compare documentation and observability pilot reports.",
     "Compare os relatórios de documentação e observabilidade do piloto."),
    ("Review the documentation, telemetry dashboard and pilot baseline report.",
     "Revise a documentação, o painel de telemetria e o relatório de baseline do piloto."),
    ("Review documentation and telemetry pilot reports.",
     "Revise documentação e telemetria nos relatórios do piloto."),
    ("Review documentation and observability dashboard pilot reports.",
     "Revise documentação e painel de observabilidade nos relatórios do piloto."),
    ("Compare documentation pilot reports.",
     "Compare os relatórios de documentação do piloto."),
    ("Review observability reports.", "Revise os relatórios de observabilidade."),
)


@pytest.mark.parametrize("english,portuguese", PAIRS)
def test_domain_selection_and_specialists_equal_without_prior_changes(english, portuguese):
    knowledge = KnowledgeService()
    en = knowledge.retrieve_for_intent(intent="analysis", query=english,
                                      as_of="2026-10-06T00:00:00Z")
    pt = knowledge.retrieve_for_intent(intent="analysis", query=portuguese,
                                      as_of="2026-10-06T00:00:00Z")
    assert en.active_domains == pt.active_domains
    assert en.registry_domains == pt.registry_domains
    assert en.specialist_routes == pt.specialist_routes
    assert en.source_evidence == pt.source_evidence
    assert pt.query == portuguese and en.query == english
    assert KnowledgeService._DOMAIN_NAME_MATCH_WEIGHT == 1.6
    assert KnowledgeService._KEYWORD_MATCH_WEIGHT == 1.25
    assert KnowledgeService._REGISTRY_ROUTE_MATCH_WEIGHT == 6.0
    assert KnowledgeService._REGISTRY_CANONICAL_MATCH_WEIGHT == 5.0


@pytest.mark.parametrize("source,expected", (
    ("documentacao", "documentation"), ("documentacoes", "documentations"),
    ("observabilidade", "observability"), ("telemetria", "telemetry"),
    ("relatorio", "report"), ("relatorios", "reports"),
    ("piloto", "pilot"), ("pilotos", "pilots"),
    ("comparacao", "comparison"), ("comparacoes", "comparisons"),
    ("painel de telemetria", "telemetry dashboard"),
    ("painel de observabilidade", "observability dashboard"),
    ("painel   de\ttelemetria", "telemetry dashboard"),
    ("painel de\nobservabilidade", "observability dashboard"),
    ("documentation observability telemetry dashboard pilot report comparison",
     "documentation observability telemetry dashboard pilot report comparison"),
))
def test_exact_aliases_replace_not_append_keyword_slots(source, expected):
    assert routing_aliases(source) == expected


@pytest.mark.parametrize("source", (
    "telemetriacoisa", "pretelemetria", "observabilidadecoisa", "documentacaoextra",
    "relatoriox", "copiloto", "pilotar", "pilotosx", "comparacaox",
    "painel solar", "painel administrativo", "painel de; telemetria", "",
))
def test_substrings_and_unrelated_panel_are_not_translated(source):
    result = routing_aliases(source)
    assert "dashboard" not in result
    if source != "painel de; telemetria":
        assert result == source


def test_alias_normalization_only_applies_to_routing_copy():
    query = "Revise a DOCUMENTAÇÃO e o painel de TELEMETRIA, piloto 😀."
    knowledge = KnowledgeService()
    result = knowledge.retrieve_for_intent(intent="analysis", query=query)
    assert result.query == query
    assert routing_aliases(knowledge._normalize_text(query)) == (
        "revise a documentation e o telemetry dashboard, pilot ."
    )


def test_bilingual_alias_does_not_change_boolean_keyword_hit_count():
    knowledge = KnowledgeService()
    single = knowledge._select_domains("analysis", "documentation observability pilot reports")
    bilingual = knowledge._select_domains(
        "analysis", "documentation documentação observability observabilidade "
        "pilot piloto reports relatórios"
    )
    assert single == bilingual
