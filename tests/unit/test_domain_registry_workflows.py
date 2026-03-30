from shared.domain_registry import RUNTIME_ROUTE_REGISTRY


def test_active_runtime_routes_define_workflow_contracts() -> None:
    active_routes = {
        name: entry
        for name, entry in RUNTIME_ROUTE_REGISTRY.items()
        if entry.maturity in {"active_registry", "active_specialist"}
    }

    assert active_routes
    for route_name, entry in active_routes.items():
        assert entry.workflow_profile, route_name
        assert list(entry.workflow_steps), route_name
        assert list(entry.workflow_checkpoints), route_name
        assert list(entry.workflow_decision_points), route_name
