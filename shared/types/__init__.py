"""Canonical shared types for JARVIS."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import NewType

Timestamp = str
CreatedAt = str
UpdatedAt = str


@dataclass(frozen=True)
class TimeWindow:
    """Canonical temporal or logical window."""

    start: Timestamp | None = None
    end: Timestamp | None = None
    label: str | None = None


RequestId = NewType("RequestId", str)
SessionId = NewType("SessionId", str)
MissionId = NewType("MissionId", str)
OperationId = NewType("OperationId", str)
GovernanceCheckId = NewType("GovernanceCheckId", str)
GovernanceDecisionId = NewType("GovernanceDecisionId", str)
MemoryQueryId = NewType("MemoryQueryId", str)
MemoryRecordId = NewType("MemoryRecordId", str)
ArtifactId = NewType("ArtifactId", str)
EvolutionProposalId = NewType("EvolutionProposalId", str)
EvolutionDecisionId = NewType("EvolutionDecisionId", str)
VoiceSessionId = NewType("VoiceSessionId", str)
VoiceTurnId = NewType("VoiceTurnId", str)
VoiceResponseId = NewType("VoiceResponseId", str)


class ChannelType(StrEnum):
    CHAT = "chat"
    VOICE = "voice"
    API = "api"
    WEB = "web"
    CONSOLE = "console"
    SYSTEM_EVENT = "system_event"


class InputType(StrEnum):
    TEXT = "text"
    AUDIO = "audio"
    DOCUMENT = "document"
    IMAGE = "image"
    EVENT = "event"
    STRUCTURED_PAYLOAD = "structured_payload"


class RiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionDecision(StrEnum):
    ALLOW = "allow"
    ALLOW_WITH_CONDITIONS = "allow_with_conditions"
    BLOCK = "block"
    DEFER_FOR_VALIDATION = "defer_for_validation"


class MissionStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELED = "canceled"


class OperationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    WAITING = "waiting"


class ArtifactStatus(StrEnum):
    GENERATED = "generated"
    PARTIAL = "partial"
    FAILED = "failed"
    VALIDATED = "validated"
    ARCHIVED = "archived"


class RecoveryType(StrEnum):
    CONTEXTUAL = "contextual"
    USER = "user"
    MISSION = "mission"
    DOMAIN = "domain"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    HYBRID = "hybrid"


class MemoryClass(StrEnum):
    IDENTITY = "identity"
    NORMATIVE = "normative"
    USER = "user"
    RELATIONAL = "relational"
    CONTEXTUAL = "contextual"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    MISSION = "mission"
    DOMAIN = "domain"
    EVOLUTIONARY = "evolutionary"


class VoiceTurnStatus(StrEnum):
    LISTENING = "listening"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class VoiceResponseStatus(StrEnum):
    PREPARING = "preparing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    TRUNCATED = "truncated"
    FAILED = "failed"


@dataclass
class SessionState:
    session_id: SessionId
    current_goal: str | None = None
    active_context: dict[str, object] = field(default_factory=dict)
    active_domains: list[str] = field(default_factory=list)
    active_minds: list[str] = field(default_factory=list)
    last_outputs: list[str] = field(default_factory=list)
    state_version: int = 1


@dataclass
class MissionState:
    mission_id: MissionId
    mission_goal: str
    mission_status: MissionStatus
    checkpoints: list[str] = field(default_factory=list)
    active_tasks: list[str] = field(default_factory=list)
    related_memories: list[str] = field(default_factory=list)
    updated_at: str = ""


@dataclass
class OperationState:
    operation_id: OperationId
    task_status: OperationStatus
    current_step: str | None = None
    tool_usage: list[str] = field(default_factory=list)
    produced_artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    resumable: bool = False


@dataclass
class GovernanceState:
    governance_check_id: GovernanceCheckId
    subject: str
    risk_level: RiskLevel
    permission_state: PermissionDecision
    containment_state: str | None = None
    audit_required: bool = False


@dataclass
class VoiceSessionState:
    voice_session_id: VoiceSessionId
    connection_state: str
    current_turn_state: str | None = None
    current_response_state: str | None = None
    interruption_count: int = 0
    active_operation_ref: str | None = None
