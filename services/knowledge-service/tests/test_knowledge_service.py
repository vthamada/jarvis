from knowledge_service.service import KnowledgeService


def test_knowledge_service_name() -> None:
    assert KnowledgeService.name == "knowledge-service"
