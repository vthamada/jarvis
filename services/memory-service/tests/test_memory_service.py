from memory_service.service import MemoryService


def test_memory_service_name() -> None:
    assert MemoryService.name == "memory-service"
