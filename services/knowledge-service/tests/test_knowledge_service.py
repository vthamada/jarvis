from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from knowledge_service.service import KnowledgeService


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_knowledge_service_name() -> None:
    assert KnowledgeService.name == "knowledge-service"


def test_knowledge_service_returns_domains_and_snippets_for_planning() -> None:
    service = KnowledgeService()
    result = service.retrieve_for_intent(intent="planning", query="Plan the next milestone safely.")

    assert result.active_domains == ["strategy", "productivity"]
    assert len(result.snippets) == 2


def test_knowledge_service_adds_governance_domain_when_query_mentions_risk() -> None:
    service = KnowledgeService()
    result = service.retrieve_for_intent(intent="analysis", query="Analyze risk and governance gaps.")

    assert "governance" in result.active_domains


def test_knowledge_service_loads_curated_domains_from_custom_corpus() -> None:
    temp_dir = runtime_dir("knowledge-corpus")
    corpus_path = temp_dir / "custom_corpus.json"
    corpus_path.write_text(
        (
            '{'
            '"domains": ['
            '{"name": "architecture", "keywords": ["arch"], "snippets": ["Arquitetura first."]},'
            '{"name": "productivity", "keywords": ["execute"], "snippets": ["Execute o menor passo."]}'
            "]}"
        ),
        encoding="utf-8",
    )

    service = KnowledgeService(corpus_path=str(corpus_path))

    assert service.list_domains() == ["architecture", "productivity"]
    result = service.retrieve_for_intent(intent="general_assistance", query="Review arch options.")
    assert result.active_domains == ["productivity", "architecture"]
