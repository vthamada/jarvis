"""Inert, explicit model composition; lazy account access after Core eligibility.

This leaf grants no authority and neither logs in, refreshes nor retries. Its
single cooperative budget includes factory construction and inference. It can
reject an overdue synchronous factory, not forcibly interrupt arbitrary Python.
Injected composition is never evidence of a live account or model acceptance.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Event

from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult


def _invalid():
    raise ValueError("invalid_local_generative_profile") from None


class _Refusal(Exception):
    def __init__(self, code, status="failed"):
        self.code, self.status = code, status


class _Cancellation(Event):
    """Combine service and consumer flags without creating a polling thread."""

    def __init__(self, service, consumer):
        super().__init__()
        self._service, self._consumer = service, consumer

    def is_set(self):
        return (super().is_set() or self._service.is_set() or self._consumer.is_set())


def _identifier(value):
    return (type(value) is str and 1 <= len(value) <= 160
            and all(33 <= ord(char) <= 126 for char in value))


def _finite(value):
    return type(value) in {int, float} and math.isfinite(value)


@dataclass(frozen=True, repr=False)
class _Options:
    authorized: bool
    model: str
    credential_dir: Path
    profile_ref: str
    timeout_seconds: float
    factory: object
    clock: object
    evidence_mode: str
    diagnostic_sink: object


class GenerativeProfile:
    """Explicit selection, without constructor IO or retained request content."""

    def __init__(self, *, authorized=False, model: str, credential_dir: Path,
                 profile_ref: str, timeout_seconds=20.0, port_factory=None,
                 clock=time.monotonic, diagnostic_sink=None):
        if (authorized is not True or not _identifier(model)
                or type(profile_ref) is not str
                or re.fullmatch(r"profile-[0-9a-f]{64}", profile_ref) is None
                or not isinstance(credential_dir, Path) or not credential_dir.is_absolute()
                or not _finite(timeout_seconds) or not 0 < timeout_seconds <= 20
                or not callable(clock)
                or (diagnostic_sink is not None and not callable(diagnostic_sink))
                or (port_factory is not None and not callable(port_factory))):
            _invalid()
        self._options = _Options(authorized, model, credential_dir, profile_ref,
                                 float(timeout_seconds), port_factory, clock,
                                 "live" if port_factory is None else "injected_transport",
                                 diagnostic_sink)
        self._initial = self._snapshot()

    def __repr__(self):
        return "GenerativeProfile(authority='none', lazy=True)"

    def _snapshot(self):
        options = self._options
        if type(options) is not _Options:
            _invalid()
        return (options.authorized, options.model, options.credential_dir,
                options.profile_ref, options.timeout_seconds, options.factory,
                options.clock, options.evidence_mode, options.diagnostic_sink)

    def _fence(self, snapshot):
        current = self._snapshot()
        if (current != snapshot or current != self._initial
                or current[5] is not snapshot[5] or current[6] is not snapshot[6]
                or current[8] is not snapshot[8]):
            raise _Refusal("profile_changed")

    @property
    def model(self):
        return self._options.model

    @property
    def timeout_seconds(self):
        return self._options.timeout_seconds

    @property
    def provider_id(self):
        return "responses_plan"

    @property
    def evidence_mode(self):
        return self._options.evidence_mode

    def port_for(self, cancellation: Event):
        try:
            self._fence(self._initial)
            if not isinstance(cancellation, Event):
                _invalid()
            return _LazyPort(self, self._initial, cancellation)
        except Exception:
            _invalid()


class _LazyPort:
    def __init__(self, profile, snapshot, cancellation):
        self._profile, self._snapshot, self._cancellation = profile, snapshot, cancellation

    def __repr__(self):
        return "LocalGenerativePort(authority='none', lazy=True)"

    @property
    def provider_id(self):
        return "responses_plan"

    @property
    def evidence_mode(self):
        return self._snapshot[7]

    def infer(self, request, *, cancellation=None):
        # Frozen records can be forged by trusted Python: reconstruct and retain
        # no content on the port, including failure paths.
        try:
            if type(request) is not InferenceRequest:
                _invalid()
            bound = replace(request)
            if any(type(message) is not InferenceMessage for message in bound.messages):
                _invalid()
            bound = replace(bound, messages=tuple(
                InferenceMessage(message.role, message.content) for message in bound.messages
            ))
            original = (request.request_id, request.model, request.messages,
                        request.instructions, request.timeout_seconds, request.max_output_chars)
        except Exception:
            raise ValueError("invalid_local_inference_request") from None
        snapshot = self._snapshot
        evidence = snapshot[7]
        phase = "profile_setup"
        from inference_service.diagnostics import emit_diagnostic

        try:
            profile = self._profile
            profile._fence(snapshot)
            if cancellation is not None and not isinstance(cancellation, Event):
                raise _Refusal("invalid_cancellation")
            if bound.model != snapshot[1]:
                raise _Refusal("model_mismatch")
            clock = snapshot[6]
            start = clock()
            if not _finite(start):
                raise _Refusal("invalid_clock")
            deadline, last = start + min(bound.timeout_seconds, snapshot[4]), start
            if not _finite(deadline) or deadline <= start:
                raise _Refusal("invalid_clock")

            def remaining():
                nonlocal last
                profile._fence(snapshot)
                if self._cancellation.is_set() or (cancellation is not None
                                                  and cancellation.is_set()):
                    raise _Refusal("cancelled", "cancelled")
                now = clock()
                if not _finite(now) or now < last:
                    raise _Refusal("invalid_clock")
                last = now
                if now >= deadline:
                    raise _Refusal("timeout", "timed_out")
                return deadline - now

            remaining()
            factory = snapshot[5]
            if snapshot[8] is not None:
                emit_diagnostic(snapshot[8], phase=phase, status="started")
                remaining()
            if factory is None:
                from apps.jarvis_console.generative_analysis_cli import _session_factory
                factory = _session_factory
            if snapshot[5] is None and snapshot[8] is not None:
                port = factory(snapshot[2], snapshot[3], snapshot[1], telemetry=snapshot[8])
            else:
                port = factory(snapshot[2], snapshot[3], snapshot[1])
            remaining()
            if (port.provider_id != "responses_plan" or port.evidence_mode != evidence
                    or not callable(port.infer)):
                raise _Refusal("binding_mismatch")
            if snapshot[8] is not None:
                emit_diagnostic(snapshot[8], phase=phase, status="completed")
                remaining()
            phase = "profile_result"
            token = (self._cancellation if cancellation is None
                     or cancellation is self._cancellation
                     else _Cancellation(self._cancellation, cancellation))
            forwarded = replace(bound, timeout_seconds=remaining())
            forwarded_snapshot = replace(forwarded, messages=tuple(
                InferenceMessage(message.role, message.content) for message in forwarded.messages
            ))
            result = port.infer(forwarded, cancellation=token)
            if token.is_set():
                raise _Refusal("cancelled", "cancelled")
            remaining()
            if (forwarded != forwarded_snapshot
                    or original != (request.request_id, request.model, request.messages,
                             request.instructions, request.timeout_seconds,
                             request.max_output_chars)
                    or request.messages != bound.messages):
                raise _Refusal("request_changed")
            if type(result) is not InferenceResult:
                raise _Refusal("invalid_result")
            result = replace(result)
            if (result.request_id != bound.request_id or result.model != snapshot[1]
                    or result.provider_id != "responses_plan" or result.evidence_mode != evidence
                    or any(type(value) is not str for value in (
                        result.request_id, result.model, result.provider_id,
                        result.status, result.evidence_mode))
                    or port.provider_id != "responses_plan" or port.evidence_mode != evidence
                    or type(result.text) is not str or len(result.text) > bound.max_output_chars
                    or any(count is not None and count > 1_000_000_000
                           for count in (result.input_tokens, result.output_tokens))):
                raise _Refusal("binding_mismatch")
            result.text.encode("utf-8", errors="strict")
            if result.status != "completed":
                raise _Refusal({"cancelled": "cancelled", "timed_out": "timeout"}.get(
                    result.status, "inference_failed"), result.status)
            remaining()
            if snapshot[8] is not None:
                emit_diagnostic(snapshot[8], phase=phase, status="completed")
                remaining()
                if (forwarded != forwarded_snapshot
                        or original != (request.request_id, request.model, request.messages,
                                        request.instructions, request.timeout_seconds,
                                        request.max_output_chars)
                        or request.messages != bound.messages):
                    raise _Refusal("request_changed")
                if (port.provider_id != "responses_plan" or port.evidence_mode != evidence
                        or not callable(port.infer)):
                    raise _Refusal("binding_mismatch")
            return result
        except _Refusal as exc:
            code, status = exc.code, exc.status
        except TimeoutError:
            code, status = "timeout", "timed_out"
        except Exception:
            code, status = "inference_unavailable", "failed"
        emit_diagnostic(snapshot[8], phase=phase, status=status, code=code)
        return InferenceResult(bound.request_id, bound.model, "responses_plan", status,
                               error_code=code, evidence_mode=evidence)
