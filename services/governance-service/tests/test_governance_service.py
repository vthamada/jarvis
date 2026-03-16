from governance_service.service import GovernanceService


def test_governance_service_name() -> None:
    assert GovernanceService.name == "governance-service"
