"""Bounded, content-free failure handling for an injected Responses transport."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from math import isfinite
from threading import Event
from time import monotonic
from typing import Protocol

from inference_service.http_transport import PLAN_TRANSPORT_ERROR_CODES, PlanTransportError
from shared.model_inference import InferenceRequest, InferenceResult


class ResponsesTransport(Protocol):
    """Transport must honor timeout/cancellation during its own blocking operations.

    HTTP is opt-in through PlanResponsesHttpsTransport; no default is activated.
    The adapter can check deadlines between yields, not interrupt arbitrary Python.
    """

    def __call__(
        self, payload: dict[str, object], *, timeout_seconds: float, cancellation: Event
    ) -> Iterable[dict[str, object]]: ...


_KNOWN_ERRORS = frozenset(
    {
        "subscription_sharing_usage_limit_exceeded",
        "subscription_sharing_usage_unavailable",
        "subscription_sharing_unsupported_capability",
        "invalid_api_key",
        "rate_limit_exceeded",
        "model_not_found",
        "insufficient_quota",
        "server_error",
    }
)


class _Failure(Exception):
    def __init__(self, code: str, status: str = "failed") -> None:
        self.code = code
        self.status = status
        super().__init__(code)


def _clock_value(clock: Callable[[], float]) -> float:
    value = clock()
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
        raise _Failure("invalid_clock")
    return value


def _result(request: InferenceRequest, provider: str, evidence: str, **values) -> InferenceResult:
    return InferenceResult(
        request_id=request.request_id,
        model=request.model,
        provider_id=provider,
        evidence_mode=evidence,
        **values,
    )


class FakeInferenceProvider:
    """Deterministic test fixture, never evidence of live model inference."""

    provider_id = "fixture"

    def __init__(self, text: str = "Fixture response: no live model was called.") -> None:
        if not isinstance(text, str) or not text.strip() or len(text) > 64_000:
            raise ValueError("invalid_fixture_text")
        self._text = text

    def infer(
        self, request: InferenceRequest, *, cancellation: Event | None = None
    ) -> InferenceResult:
        if cancellation is not None and cancellation.is_set():
            return _result(
                request, self.provider_id, "fixture", status="cancelled", error_code="cancelled"
            )
        if len(self._text) > request.max_output_chars:
            return _result(
                request,
                self.provider_id,
                "fixture",
                status="failed",
                error_code="output_limit_exceeded",
            )
        return _result(request, self.provider_id, "fixture", status="completed", text=self._text)


class ResponsesPlanInferenceProvider:
    """SIWC payload and stream parser only; transport injection is mandatory.

    Text is withheld until completion and clean stream termination. Model output
    remains untrusted data for Core-owned synthesis, not a tool/action dispatch.
    """

    provider_id = "responses_plan"

    def __init__(
        self,
        transport: ResponsesTransport,
        *,
        clock: Callable[[], float] = monotonic,
        telemetry: Callable[[dict[str, object]], None] | None = None,
        max_events: int = 4096,
        max_event_bytes: int = 262_144,
        max_stream_bytes: int = 2_097_152,
    ) -> None:
        if not callable(transport) or not callable(clock):
            raise ValueError("invalid_transport_or_clock")
        if telemetry is not None and not callable(telemetry):
            raise ValueError("invalid_telemetry")
        for value, bound in (
            (max_events, 10_000),
            (max_event_bytes, 1_048_576),
            (max_stream_bytes, 8_388_608),
        ):
            if type(value) is not int or not 1 <= value <= bound:
                raise ValueError("invalid_stream_limit")
        self._transport = transport
        self._clock = clock
        self._telemetry = telemetry
        self._max_events = max_events
        self._max_event_bytes = max_event_bytes
        self._max_stream_bytes = max_stream_bytes

    def infer(
        self, request: InferenceRequest, *, cancellation: Event | None = None
    ) -> InferenceResult:
        token = cancellation if cancellation is not None else Event()
        count = 0
        stream = None
        try:
            start = _clock_value(self._clock)
            deadline = start + request.timeout_seconds
            last_clock = start

            def check() -> None:
                nonlocal last_clock
                if token.is_set():
                    raise _Failure("cancelled", "cancelled")
                now = _clock_value(self._clock)
                if now < last_clock:
                    raise _Failure("invalid_clock")
                last_clock = now
                if now >= deadline:
                    raise _Failure("timeout", "timed_out")

            check()
            payload: dict[str, object] = {
                "model": request.model,
                "input": [
                    {"role": message.role, "content": message.content}
                    for message in request.messages
                ],
                "store": False,
                "stream": True,
            }
            if request.instructions:
                payload["instructions"] = request.instructions
            stream = iter(
                self._transport(
                    payload,
                    timeout_seconds=request.timeout_seconds,
                    cancellation=token,
                )
            )
            check()
            response_id = None
            deltas: list[str] = []
            output_chars = 0
            stream_bytes = 0
            completed = None
            finished_text: str | None = None
            while True:
                check()
                try:
                    event = next(stream)
                except StopIteration:
                    break
                check()
                count += 1
                if count > self._max_events:
                    raise _Failure("event_limit_exceeded")
                if completed is not None:
                    raise _Failure("event_after_terminal")
                if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                    raise _Failure("malformed_event")
                try:
                    size = len(
                        json.dumps(event, ensure_ascii=False, allow_nan=False).encode("utf-8")
                    )
                except (TypeError, ValueError, OverflowError, RecursionError):
                    raise _Failure("malformed_event") from None
                stream_bytes += size
                if size > self._max_event_bytes or stream_bytes > self._max_stream_bytes:
                    raise _Failure("stream_limit_exceeded")
                kind = event["type"]
                for index in ("output_index", "content_index", "summary_index"):
                    if index in event and (type(event[index]) is not int or event[index] < 0):
                        raise _Failure("malformed_event")
                response = event.get("response")
                if response is not None:
                    if not isinstance(response, dict):
                        raise _Failure("malformed_response")
                    current_id = response.get("id")
                    if not isinstance(current_id, str) or not current_id or len(current_id) > 160:
                        raise _Failure("malformed_response")
                    if response_id is not None and current_id != response_id:
                        raise _Failure("response_identity_mismatch")
                    response_id = current_id
                    if response.get("model") != request.model:
                        raise _Failure("model_mismatch")
                explicit_id = event.get("response_id")
                if explicit_id is not None:
                    if (
                        not isinstance(explicit_id, str)
                        or not explicit_id
                        or len(explicit_id) > 160
                    ):
                        raise _Failure("malformed_event")
                    if response_id is not None and explicit_id != response_id:
                        raise _Failure("response_identity_mismatch")
                    response_id = explicit_id
                if kind == "response.output_text.delta":
                    delta = event.get("delta")
                    if not isinstance(delta, str):
                        raise _Failure("malformed_delta")
                    if finished_text is not None:
                        raise _Failure("text_after_done")
                    output_chars += len(delta)
                    if output_chars > request.max_output_chars:
                        raise _Failure("output_limit_exceeded")
                    deltas.append(delta)
                elif kind == "response.completed":
                    if (
                        not isinstance(response, dict)
                        or response.get("status") != "completed"
                        or response.get("error") is not None
                        or response.get("incomplete_details") is not None
                    ):
                        raise _Failure("malformed_completion")
                    text = self._completed_text(response, request.max_output_chars)
                    if deltas and text != "".join(deltas):
                        raise _Failure("output_mismatch")
                    if finished_text is not None and text != finished_text:
                        raise _Failure("output_mismatch")
                    usage = self._usage(response)
                    completed = _result(
                        request,
                        self.provider_id,
                        "injected_transport",
                        status="completed",
                        text=text,
                        input_tokens=usage[0],
                        output_tokens=usage[1],
                    )
                elif kind in {"response.failed", "error"}:
                    error = response.get("error") if isinstance(response, dict) else event
                    code = error.get("code") if isinstance(error, dict) else None
                    normalized = code if isinstance(code, str) and code in _KNOWN_ERRORS else None
                    raise _Failure(normalized or "provider_error")
                elif kind == "response.incomplete":
                    raise _Failure("response_incomplete")
                elif kind in {"response.created", "response.in_progress", "response.queued"}:
                    if not isinstance(response, dict):
                        raise _Failure("malformed_response")
                elif kind in {"response.output_item.added", "response.output_item.done"}:
                    item = event.get("item")
                    if not isinstance(item, dict) or item.get("type") not in {
                        "message",
                        "reasoning",
                    }:
                        raise _Failure("unsupported_output")
                    if item["type"] == "message":
                        if item.get("role") != "assistant":
                            raise _Failure("unsupported_output")
                        if "content" in item:
                            if not isinstance(item["content"], list):
                                raise _Failure("malformed_event")
                            parts = [self._text_part(part) for part in item["content"]]
                            if kind == "response.output_item.done" and parts:
                                item_text = "".join(parts)
                                if len(item_text) > request.max_output_chars:
                                    raise _Failure("output_limit_exceeded")
                                if deltas and item_text != "".join(deltas):
                                    raise _Failure("output_mismatch")
                                if finished_text is not None and item_text != finished_text:
                                    raise _Failure("output_mismatch")
                                finished_text = item_text
                        if "status" in item and item["status"] not in {"in_progress", "completed"}:
                            raise _Failure("malformed_event")
                        if (
                            kind == "response.output_item.done"
                            and "status" in item
                            and item["status"] != "completed"
                        ):
                            raise _Failure("malformed_event")
                elif kind in {"response.content_part.added", "response.content_part.done"}:
                    part_text = self._text_part(event.get("part"))
                    if len(part_text) > request.max_output_chars:
                        raise _Failure("output_limit_exceeded")
                    if kind == "response.content_part.done":
                        if deltas and part_text != "".join(deltas):
                            raise _Failure("output_mismatch")
                        if finished_text is not None and part_text != finished_text:
                            raise _Failure("output_mismatch")
                        finished_text = part_text
                elif kind == "response.output_text.done":
                    if not isinstance(event.get("text"), str):
                        raise _Failure("malformed_event")
                    if len(event["text"]) > request.max_output_chars:
                        raise _Failure("output_limit_exceeded")
                    if deltas and event["text"] != "".join(deltas):
                        raise _Failure("output_mismatch")
                    if finished_text is not None and event["text"] != finished_text:
                        raise _Failure("output_mismatch")
                    finished_text = event["text"]
                elif kind in {
                    "response.reasoning_summary_part.added",
                    "response.reasoning_summary_part.done",
                }:
                    part = event.get("part")
                    if (
                        not isinstance(part, dict)
                        or part.get("type") != "summary_text"
                        or not isinstance(part.get("text"), str)
                    ):
                        raise _Failure("malformed_event")
                elif kind == "response.reasoning_summary_text.delta":
                    if not isinstance(event.get("delta"), str):
                        raise _Failure("malformed_event")
                elif kind == "response.reasoning_summary_text.done":
                    if not isinstance(event.get("text"), str):
                        raise _Failure("malformed_event")
                else:
                    raise _Failure("unsupported_event")
            check()
            if completed is None:
                raise _Failure("stream_interrupted")
            result = completed
        except _Failure as exc:
            result = _result(
                request,
                self.provider_id,
                "injected_transport",
                status=exc.status,
                error_code=exc.code,
            )
        except PlanTransportError as exc:
            code = (exc.code if type(exc.code) is str and exc.code in PLAN_TRANSPORT_ERROR_CODES
                    else "transport_error")
            status = {"cancelled": "cancelled", "timeout": "timed_out"}.get(code, "failed")
            result = _result(
                request, self.provider_id, "injected_transport", status=status, error_code=code,
            )
        except TimeoutError:
            result = _result(
                request,
                self.provider_id,
                "injected_transport",
                status="timed_out",
                error_code="timeout",
            )
        except Exception:
            result = _result(
                request,
                self.provider_id,
                "injected_transport",
                status="failed",
                error_code="transport_error",
            )
        finally:
            try:
                close = getattr(stream, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
        if self._telemetry is not None:
            try:
                self._telemetry(
                    {
                        "event": "inference_finished",
                        "status": result.status,
                        "error_code": result.error_code,
                        "event_count": count,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "evidence_mode": "injected_transport",
                    }
                )
            except Exception:
                pass  # Observability failure must not publish content or change inference.
        return result

    @staticmethod
    def _text_part(part: object) -> str:
        if (
            not isinstance(part, dict)
            or part.get("type") != "output_text"
            or not isinstance(part.get("text"), str)
        ):
            raise _Failure("unsupported_output")
        return part["text"]

    @staticmethod
    def _completed_text(response: dict, limit: int) -> str:
        output = response.get("output")
        if not isinstance(output, list):
            raise _Failure("malformed_completion")
        texts = []
        length = 0
        for item in output:
            if not isinstance(item, dict):
                raise _Failure("malformed_completion")
            if item.get("type") == "reasoning":
                continue
            if item.get("type") != "message" or item.get("role") != "assistant":
                raise _Failure("unsupported_output")
            if "status" in item and item["status"] != "completed":
                raise _Failure("malformed_completion")
            content = item.get("content")
            if not isinstance(content, list):
                raise _Failure("malformed_completion")
            for part in content:
                if (
                    not isinstance(part, dict)
                    or part.get("type") != "output_text"
                    or not isinstance(part.get("text"), str)
                ):
                    raise _Failure("unsupported_output")
                length += len(part["text"])
                if length > limit:
                    raise _Failure("output_limit_exceeded")
                texts.append(part["text"])
        text = "".join(texts)
        if not text.strip():
            raise _Failure("empty_output")
        return text

    @staticmethod
    def _usage(response: dict) -> tuple[int | None, int | None]:
        usage = response.get("usage")
        if usage is None:
            return None, None
        if not isinstance(usage, dict):
            raise _Failure("malformed_usage")
        counts = usage.get("input_tokens"), usage.get("output_tokens")
        if any(type(count) is not int or not 0 <= count <= 1_000_000_000 for count in counts):
            raise _Failure("malformed_usage")
        total = usage.get("total_tokens")
        if "total_tokens" in usage and (type(total) is not int or total != sum(counts)):
            raise _Failure("malformed_usage")
        return counts
