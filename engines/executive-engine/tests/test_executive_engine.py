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
    assert directive.should_execute_operation is True
    assert directive.preferred_response_mode == "plan_and_operate"
    assert "update" in directive.risk_markers


def test_executive_engine_marks_hybrid_request_for_clarification() -> None:
    engine = ExecutiveEngine()
    directive = engine.direct(
        InputContract(
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan and analyze the roadmap.",
            timestamp="2026-03-18T00:00:00Z",
        )
    )

    assert directive.intent == "planning"
    assert directive.requires_clarification is True
    assert directive.should_execute_operation is False
    assert directive.preferred_response_mode == "clarifying_guidance"


def test_executive_engine_routes_analysis_without_operation() -> None:
    engine = ExecutiveEngine()
    directive = engine.direct(
        InputContract(
            request_id=RequestId("req-3"),
            session_id=SessionId("sess-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the previous milestone trade-offs.",
            timestamp="2026-03-18T00:00:00Z",
        )
    )

    assert directive.intent == "analysis"
    assert directive.should_execute_operation is False
    assert directive.preferred_response_mode == "analysis_only"


def test_executive_engine_blocks_sensitive_action_routing() -> None:
    engine = ExecutiveEngine()
    directive = engine.direct(
        InputContract(
            request_id=RequestId("req-4"),
            session_id=SessionId("sess-4"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete the deployment artifacts.",
            timestamp="2026-03-18T00:00:00Z",
        )
    )

    assert directive.intent == "sensitive_action"
    assert directive.should_execute_operation is False
    assert directive.intent_confidence >= 0.9
