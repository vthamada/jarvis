from operational_service.service import OperationalService


def test_operational_service_name() -> None:
    assert OperationalService.name == "operational-service"
