from memory_service.service import MemoryRecordResult, MemoryRecoveryResult, MemoryService
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, MemoryClass, RequestId, SessionId


def test_memory_service_name() -> None:
    assert MemoryService.name == "memory-service"


def test_memory_service_recovers_empty_context_for_new_session() -> None:
    service = MemoryService()
    result = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Hello",
            timestamp="2026-03-17T00:00:00Z",
        )
    )

    assert isinstance(result, MemoryRecoveryResult)
    assert result.recovered_items == []
    assert result.recovery_contract.requested_scopes == [
        MemoryClass.CONTEXTUAL,
        MemoryClass.EPISODIC,
    ]



def test_memory_service_records_and_recovers_session_history() -> None:
    service = MemoryService()
    contract = InputContract(
        request_id=RequestId("req-2"),
        session_id=SessionId("sess-2"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )

    record = service.record_turn(contract, intent="planning", response_text="Plan created.")
    recovered = service.recover_for_input(contract)

    assert isinstance(record, MemoryRecordResult)
    assert record.record_contract.record_type == "interaction_turn"
    assert len(recovered.recovered_items) == 1
    assert "planning" in recovered.recovered_items[0]
