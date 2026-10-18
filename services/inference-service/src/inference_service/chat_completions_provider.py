"""Text-only Chat Completions port; proposals are data, never Core authority."""

from __future__ import annotations

import json
from collections.abc import Callable
from math import isfinite
from threading import Event
from time import monotonic
from typing import Protocol

from inference_service.local_chat_transport import (
    LOCAL_CHAT_ERROR_CODES,
    LocalChatHttpTransport,
    LocalChatTransportError,
)
from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult

_PROVIDER_ID = "chat_completions_local"


class ChatCompletionsTransport(Protocol):
    """Injected implementations must themselves honor total timeout/cancellation."""

    def __call__(self, payload: dict[str, object], *, timeout_seconds: float,
                 cancellation: Event) -> bytes: ...


class _Failure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


def _constant(_value):
    raise ValueError("non_finite_json")


def _float(value):
    number = float(value)
    if not isfinite(number):
        raise ValueError("non_finite_json")
    return number


def _number(value):
    try:
        return type(value) in {int, float} and isfinite(value)
    except OverflowError:
        return False


def _request_state(request):
    """Independent primitive snapshot, not an alias to frozen-but-forgeable records."""
    if (type(request) is not InferenceRequest or type(request.messages) is not tuple
            or not 1 <= len(request.messages) <= 32
            or any(type(message) is not InferenceMessage for message in request.messages)
            or any(type(value) is not str for value in (
                request.request_id, request.model, request.instructions,
                *(part for message in request.messages for part in (message.role, message.content)),
            )) or type(request.max_output_chars) is not int
            or not _number(request.timeout_seconds)):
        raise ValueError("invalid_inference_request")
    return (request.request_id, request.model, id(request.messages),
            tuple((id(message), message.role, message.content) for message in request.messages),
            request.instructions, type(request.timeout_seconds), request.timeout_seconds,
            request.max_output_chars)


def _bound_request(request):
    try:
        state = _request_state(request)
        messages = tuple(InferenceMessage(role, content) for _, role, content in state[3])
        bound = InferenceRequest(state[0], state[1], messages, state[4], state[6], state[7])
        for text in (bound.instructions, *(message.content for message in bound.messages)):
            text.encode("utf-8", errors="strict")
            if "\x00" in text:
                raise ValueError
        if _request_state(request) != state:
            raise ValueError
        return bound, state
    except Exception:
        # Invalid identifiers cannot be represented by a valid neutral Result.
        raise ValueError("invalid_inference_request") from None


def _payload_state(payload):
    if (type(payload) is not dict or set(payload) != {"model", "messages", "n", "stream"}
            or type(payload["model"]) is not str or type(payload["n"]) is not int
            or type(payload["stream"]) is not bool or type(payload["messages"]) is not list
            or not 1 <= len(payload["messages"]) <= 33):
        raise _Failure("request_changed")
    messages = []
    for message in payload["messages"]:
        if (type(message) is not dict or set(message) != {"role", "content"}
                or type(message["role"]) is not str or type(message["content"]) is not str):
            raise _Failure("request_changed")
        messages.append((message["role"], message["content"]))
    return payload["model"], tuple(messages), payload["n"], payload["stream"]


class ChatCompletionsInferenceProvider:
    """One exact configured model, nonstream/n=1; no native/server-side tools.

    ``live`` means the exact LocalChatHttpTransport performed socket I/O, not
    proof of a real model, local weights or absence of upstream cloud egress.
    Injected transports cannot claim live evidence. Failures never publish text.
    """

    provider_id = _PROVIDER_ID

    def __init__(self, *, model: str, transport: ChatCompletionsTransport,
                 evidence_mode: str = "injected_transport",
                 clock: Callable[[], float] = monotonic,
                 telemetry: Callable[[dict[str, object]], None] | None = None,
                 max_response_bytes: int = 1_048_576) -> None:
        if (type(model) is not str or not 1 <= len(model) <= 160
                or any(not 33 <= ord(c) <= 126 for c in model) or "://" in model):
            raise ValueError("invalid_chat_model")
        if not callable(transport) or not callable(clock):
            raise ValueError("invalid_chat_transport_or_clock")
        if telemetry is not None and not callable(telemetry):
            raise ValueError("invalid_chat_telemetry")
        if (type(evidence_mode) is not str
                or evidence_mode not in {"fixture", "injected_transport", "live"}
                or (evidence_mode == "live") != (type(transport) is LocalChatHttpTransport)):
            raise ValueError("invalid_chat_evidence_mode")
        if type(max_response_bytes) is not int or not 1 <= max_response_bytes <= 2_097_152:
            raise ValueError("invalid_chat_response_limit")
        self._model = model
        self._transport = transport
        self._evidence_mode = evidence_mode
        self._clock = clock
        self._telemetry = telemetry
        self._max_response = max_response_bytes
        self._initial = (model, transport, evidence_mode, clock, telemetry,
                         max_response_bytes, _PROVIDER_ID)

    def _fence(self, snapshot):
        if (self._initial is not snapshot or type(self._model) is not str
                or self._model != snapshot[0] or self._transport is not snapshot[1]
                or type(self._evidence_mode) is not str or self._evidence_mode != snapshot[2]
                or self._clock is not snapshot[3] or self._telemetry is not snapshot[4]
                or type(self._max_response) is not int or self._max_response != snapshot[5]
                or type(self.provider_id) is not str or self.provider_id != snapshot[6]):
            raise _Failure("configuration_changed")

    def infer(self, request: InferenceRequest, *, cancellation: Event | None = None
              ) -> InferenceResult:
        bound, original = _bound_request(request)
        snapshot = self._initial
        model, transport, evidence, clock, telemetry, response_limit, provider_id = snapshot
        values = {"request_id": bound.request_id, "model": bound.model,
                  "provider_id": provider_id, "evidence_mode": evidence}
        try:
            self._fence(snapshot)
            if cancellation is not None and not isinstance(cancellation, Event):
                raise _Failure("invalid_cancellation")
            token = cancellation if cancellation is not None else Event()
            if bound.model != model:
                raise _Failure("model_mismatch")
            start = clock()
            if not _number(start):
                raise _Failure("invalid_clock")
            last = start
            deadline = start + bound.timeout_seconds
            if not _number(deadline) or deadline <= start:
                raise _Failure("invalid_clock")
            payload = None
            payload_binding = None

            def fence():
                self._fence(snapshot)
                try:
                    if _request_state(request) != original:
                        raise _Failure("request_changed")
                except _Failure:
                    raise
                except Exception:
                    raise _Failure("request_changed") from None
                if payload_binding is not None and _payload_state(payload) != payload_binding:
                    raise _Failure("request_changed")

            def check():
                nonlocal last
                fence()
                if token.is_set():
                    raise _Failure("cancelled")
                now = clock()
                fence()  # A trusted injected clock/callback can mutate Python objects.
                if token.is_set():
                    raise _Failure("cancelled")
                if not _number(now) or now < last:
                    raise _Failure("invalid_clock")
                last = now
                if now >= deadline:
                    raise _Failure("timeout")
                return deadline - now

            check()
            messages = [{"role": item.role, "content": item.content} for item in bound.messages]
            if bound.instructions:
                messages.insert(0, {"role": "system", "content": bound.instructions})
            payload = {"model": model, "messages": messages, "n": 1, "stream": False}
            payload_binding = _payload_state(payload)
            raw = transport(payload, timeout_seconds=check(), cancellation=token)
            check()
            if type(raw) is not bytes or not 1 <= len(raw) <= response_limit:
                raise _Failure("response_limit_exceeded")
            try:
                response = json.loads(raw.decode("utf-8", errors="strict"),
                                      object_pairs_hook=_object, parse_constant=_constant,
                                      parse_float=_float)
            except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
                raise _Failure("malformed_response") from None
            check()
            text, usage = self._completed(response, bound.max_output_chars, model)
            check()
            result = InferenceResult(**values, status="completed", text=text,
                                     input_tokens=usage[0], output_tokens=usage[1])
        except (LocalChatTransportError, _Failure) as exc:
            code = exc.code
            if isinstance(exc, LocalChatTransportError) and code not in LOCAL_CHAT_ERROR_CODES:
                code = "transport_error"
            status = {"cancelled": "cancelled", "timeout": "timed_out"}.get(code, "failed")
            result = InferenceResult(**values, status=status, error_code=code)
        except TimeoutError:
            result = InferenceResult(**values, status="timed_out", error_code="timeout")
        except Exception:
            result = InferenceResult(**values, status="failed", error_code="transport_error")
        if telemetry is not None:
            try:
                telemetry({"event": "inference_finished", "provider_id": provider_id,
                                 "status": result.status, "error_code": result.error_code,
                                 "evidence_mode": evidence,
                                 "input_tokens": result.input_tokens,
                                 "output_tokens": result.output_tokens})
            except Exception:
                pass
        if result.status == "completed":
            try:
                check()
            except _Failure as exc:
                status = {"cancelled": "cancelled", "timeout": "timed_out"}.get(exc.code, "failed")
                result = InferenceResult(**values, status=status, error_code=exc.code)
            except Exception:
                result = InferenceResult(**values, status="failed", error_code="invalid_clock")
        return result

    @staticmethod
    def _completed(response, limit, model):
        if (type(response) is not dict or response.get("object") != "chat.completion"
                or type(response.get("id")) is not str or not 1 <= len(response["id"]) <= 256
                or any(not 33 <= ord(c) <= 126 for c in response["id"])
                or response.get("error") is not None
                or response.get("status", "completed") != "completed"
                or response.get("incomplete_details") is not None):
            raise _Failure("malformed_completion")
        if response.get("model") != model:
            raise _Failure("model_mismatch")
        choices = response.get("choices")
        if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
            raise _Failure("malformed_completion")
        choice = choices[0]
        if "delta" in choice or "tool_calls" in choice or "function_call" in choice:
            raise _Failure("unsupported_output")
        if type(choice.get("index")) is not int or choice["index"] != 0:
            raise _Failure("malformed_completion")
        if choice.get("finish_reason") != "stop":
            raise _Failure("response_incomplete")
        message = choice.get("message")
        if (type(message) is not dict or message.get("role") != "assistant"
                or "tool_calls" in message or "function_call" in message
                or message.get("refusal") is not None
                or message.get("audio") is not None):
            raise _Failure("unsupported_output")
        text = message.get("content")
        if type(text) is not str or not text.strip():
            raise _Failure("empty_output")
        if len(text) > limit:
            raise _Failure("output_limit_exceeded")
        try:
            text.encode("utf-8", errors="strict")
        except UnicodeError:
            raise _Failure("unsupported_output") from None
        if "\x00" in text:
            raise _Failure("unsupported_output")
        usage = response.get("usage")
        if usage is None:
            return text, (None, None)
        if type(usage) is not dict:
            raise _Failure("malformed_usage")
        keys = ("prompt_tokens", "completion_tokens", "total_tokens")
        counts = tuple(usage.get(key) for key in keys)
        if (any(type(count) is not int or not 0 <= count <= 2_147_483_647 for count in counts)
                or counts[2] != counts[0] + counts[1]):
            raise _Failure("malformed_usage")
        return text, counts[:2]
