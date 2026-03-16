from observability_service.service import ObservabilityService


def test_observability_service_name() -> None:
    assert ObservabilityService.name == "observability-service"
