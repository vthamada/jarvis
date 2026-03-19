from executive_engine.engine import ExecutiveEngine
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId


def test_executive_engine_name() -> None:
    assert ExecutiveEngine.name == "executive-engine"


def test_executive_engine_directs_planning_request() -> None:
    engine = ExecutiveEngine()
    directive = engine.direct(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please update the rollout plan.",
            timestamp="2026-03-18T00:00:00Z",
        )
    )

    assert directive.intent == "planning"
    assert directive.should_query_knowledge is True
    assert "update" in directive.risk_markers
