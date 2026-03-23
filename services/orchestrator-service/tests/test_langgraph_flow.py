from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service import langgraph_flow
from orchestrator_service.service import OrchestratorService

from shared.contracts import InputContract
from shared.types import ChannelType, InputType, PermissionDecision, RequestId, SessionId


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_langgraph_flow_surfaces_optional_dependency_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = OrchestratorService()
    monkeypatch.setattr(
        langgraph_flow,
        "_load_langgraph",
        lambda: (_ for _ in ()).throw(
            RuntimeError(
                'LangGraph is not installed. Use `python -m pip install -e ".[langgraph]"` '
                "to run the experimental orchestrator flow."
            )
        ),
    )

    with pytest.raises(RuntimeError, match="LangGraph is not installed"):
        service.handle_input_langgraph_flow(
            InputContract(
                request_id=RequestId("req-lg-missing"),
                session_id=SessionId("sess-lg-missing"),
                channel=ChannelType.CHAT,
                input_type=InputType.TEXT,
                content="Plan the next pilot step.",
                timestamp="2026-03-19T00:00:00+00:00",
            )
        )


def test_langgraph_flow_replays_orchestrator_path_with_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCompiledGraph:
        def __init__(self, nodes: dict[str, object], edges: dict[str, str]) -> None:
            self.nodes = nodes
            self.edges = edges

        def invoke(self, initial_state):  # type: ignore[no-untyped-def]
            current = "__start__"
            state = dict(initial_state)
            while True:
                next_node = self.edges[current]
                if next_node == "__end__":
                    return state
                updates = self.nodes[next_node](state)
                state.update(updates)
                current = next_node

    class FakeStateGraph:
        def __init__(self, state_type) -> None:  # type: ignore[no-untyped-def]
            self.nodes: dict[str, object] = {}
            self.edges: dict[str, str] = {}

        def add_node(self, name: str, handler) -> None:  # type: ignore[no-untyped-def]
            self.nodes[name] = handler

        def add_edge(self, start: str, end: str) -> None:
            self.edges[start] = end

        def compile(self) -> FakeCompiledGraph:
            return FakeCompiledGraph(self.nodes, self.edges)

    monkeypatch.setattr(
        langgraph_flow,
        "_load_langgraph",
        lambda: (FakeStateGraph, "__start__", "__end__"),
    )

    temp_dir = runtime_dir("langgraph-flow")
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )

    result = service.handle_input_langgraph_flow(
        InputContract(
            request_id=RequestId("req-lg"),
            session_id=SessionId("sess-lg"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the internal pilot rollout.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )

    assert result.intent == "planning"
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.operation_result is not None
    assert any(event.event_name == "plan_built" for event in result.events)
    continuity_event = next(
        event for event in result.events if event.event_name == "continuity_subflow_completed"
    )
    assert continuity_event.payload["runtime_mode"] == "langgraph_subflow"
    assert continuity_event.payload["subflow_name"] == "continuity_stateful"
