from orchestrator_service.service import OrchestratorService


def test_orchestrator_service_name() -> None:
    assert OrchestratorService.name == "orchestrator-service"
