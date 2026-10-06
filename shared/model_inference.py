"""Bounded inference contracts: model output is data, never action authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from threading import Event
from typing import Literal, Protocol

InferenceStatus = Literal["completed", "failed", "cancelled", "timed_out"]
InferenceEvidenceMode = Literal["fixture", "injected_transport", "live"]


@dataclass(frozen=True)
class InferenceMessage:
    role: Literal["user", "assistant"]
    content: str = field(repr=False)

    def __post_init__(self) -> None:
        if self.role not in {"user", "assistant"}:
            raise ValueError("unsupported_message_role")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("empty_message")
        if len(self.content) > 32_000:
            raise ValueError("message_too_large")


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    model: str
    messages: tuple[InferenceMessage, ...] = field(repr=False)
    instructions: str = field(default="", repr=False)
    timeout_seconds: float = 30.0
    max_output_chars: int = 32_000

    def __post_init__(self) -> None:
        for value in (self.request_id, self.model):
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 160
                or any(ord(char) < 33 or ord(char) > 126 for char in value)
            ):
                raise ValueError("invalid_request_identifier")
        if (
            not isinstance(self.messages, tuple)
            or not 1 <= len(self.messages) <= 32
            or any(not isinstance(message, InferenceMessage) for message in self.messages)
        ):
            raise ValueError("invalid_messages")
        if not isinstance(self.instructions, str) or len(self.instructions) > 16_000:
            raise ValueError("invalid_instructions")
        if sum(len(message.content) for message in self.messages) > 64_000:
            raise ValueError("context_too_large")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (float, int))
            or not isfinite(self.timeout_seconds)
            or not 0 < self.timeout_seconds <= 120
        ):
            raise ValueError("invalid_timeout")
        if type(self.max_output_chars) is not int or not 1 <= self.max_output_chars <= 64_000:
            raise ValueError("invalid_output_limit")


@dataclass(frozen=True)
class InferenceResult:
    request_id: str
    model: str
    provider_id: str
    status: InferenceStatus
    text: str = field(default="", repr=False)
    error_code: str | None = None
    evidence_mode: InferenceEvidenceMode = "fixture"
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        for value in (self.request_id, self.model, self.provider_id):
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 160
                or any(ord(char) < 33 or ord(char) > 126 for char in value)
            ):
                raise ValueError("invalid_result_identifier")
        if self.error_code is not None and (
            not isinstance(self.error_code, str)
            or not 1 <= len(self.error_code) <= 160
            or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_" for char in self.error_code)
        ):
            raise ValueError("invalid_error_code")
        if self.status not in {"completed", "failed", "cancelled", "timed_out"}:
            raise ValueError("invalid_inference_status")
        if self.evidence_mode not in {"fixture", "injected_transport", "live"}:
            raise ValueError("invalid_evidence_mode")
        if not isinstance(self.text, str) or len(self.text) > 64_000:
            raise ValueError("invalid_output_text")
        if self.status != "completed" and self.text:
            raise ValueError("failed_inference_cannot_publish_text")
        if self.status == "completed" and (not self.text.strip() or self.error_code is not None):
            raise ValueError("invalid_completed_result")
        if self.status != "completed" and not self.error_code:
            raise ValueError("failure_requires_error_code")
        for count in (self.input_tokens, self.output_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise ValueError("invalid_usage_count")


class ModelInferencePort(Protocol):
    def infer(
        self,
        request: InferenceRequest,
        *,
        cancellation: Event | None = None,
    ) -> InferenceResult:
        """Complete a bounded inference or return a content-free failure."""
        ...
