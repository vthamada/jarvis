"""One shared, lazy pilot ceiling across reference and canonical Core arms.

Counts infer attempts, including failures, not guessed HTTP requests or money.
The trusted transport owns network timeouts; this is not process preemption.
"""

from __future__ import annotations

import math
import time
from dataclasses import replace
from threading import Event, RLock

from apps.jarvis_console.bootstrap import ensure_src_paths
from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult

ensure_src_paths()

from inference_service.diagnostics import DIAGNOSTIC_CODES  # noqa: E402


def _identifier(value):
    return (type(value) is str and 1 <= len(value) <= 160
            and all(33 <= ord(character) <= 126 for character in value))


def _binding(request):
    return (request.request_id, request.model,
            tuple((item.role, item.content) for item in request.messages),
            request.instructions, request.timeout_seconds, request.max_output_chars)


class CampaignInferenceGuard:
    """Trusted composition, no login/refresh/fallback, no provider in construction."""

    def __init__(self, port_factory, *, model, provider_id, evidence_mode, authorized=False,
                 max_calls=10, clock=time.monotonic, cancellation=None):
        if (not callable(port_factory) or not _identifier(model) or not _identifier(provider_id)
                or type(evidence_mode) is not str
                or evidence_mode not in {"fixture", "injected_transport", "live"}
                or type(authorized) is not bool or type(max_calls) is not int
                or not 1 <= max_calls <= 10 or not callable(clock)
                or (cancellation is not None and not isinstance(cancellation, Event))):
            raise ValueError("invalid_campaign_inference_guard")
        self.model, self.provider_id, self.evidence_mode = model, provider_id, evidence_mode
        self._factory, self._authorized, self._maximum = port_factory, authorized, max_calls
        self._clock, self._cancellation = clock, cancellation
        self._lock, self._inflight, self._port = RLock(), False, None
        self._attempted = self._completed = self._reported = 0
        self._input = self._output = 0
        self._usage_known, self._stopped, self._last_error = True, False, None
        self._last_time = None

    def __repr__(self):
        return "CampaignInferenceGuard(lazy=True, authority='none')"

    @property
    def stopped(self):
        with self._lock:
            return self._stopped

    def snapshot(self):
        with self._lock:
            usage = (self._usage_known and self._attempted > 0
                     and self._attempted == self._reported)
            return {
                "max_model_calls": self._maximum, "attempted_model_calls": self._attempted,
                "completed_model_calls": self._completed, "stopped": self._stopped,
                "last_error_code": self._last_error, "inference_evidence_mode": self.evidence_mode,
                "input_tokens": self._input if usage else None,
                "output_tokens": self._output if usage else None,
                "cost": None, "automatic_refresh": False, "paid_fallback": False,
            }

    def _now(self):
        current = self._clock()
        if (type(current) not in {int, float} or not math.isfinite(current)
                or (self._last_time is not None and current < self._last_time)):
            raise ValueError("invalid_clock")
        self._last_time = current
        return current

    def _cancelled(self, cancellation):
        for token in (cancellation, self._cancellation):
            if token is not None:
                if not isinstance(token, Event) or token.is_set() is not False:
                    raise ValueError("campaign_cancelled")

    def infer(self, request, *, cancellation=None):
        if self._authorized is not True or type(request) is not InferenceRequest:
            raise ValueError("campaign_inference_refused")
        request = replace(request, messages=tuple(
            InferenceMessage(item.role, item.content) for item in request.messages
        ))
        if request.model != self.model:
            raise ValueError("campaign_inference_refused")
        if not self._lock.acquire(blocking=False):
            raise ValueError("campaign_inference_refused")
        failed = False
        try:
            self._cancelled(cancellation)
            if self._stopped or self._inflight or self._attempted >= self._maximum:
                raise ValueError("campaign_inference_refused")
            self._inflight = True
            self._attempted += 1
            started = self._now()
            deadline = started + request.timeout_seconds
            config = (self.model, self.provider_id, self.evidence_mode, self._maximum)
            if self._port is None:
                selected = self._factory()
                if (getattr(selected, "provider_id", None) != self.provider_id
                        or getattr(selected, "evidence_mode", None) != self.evidence_mode
                        or not callable(getattr(selected, "infer", None))):
                    raise ValueError("campaign_inference_refused")
                self._port = selected
            self._cancelled(cancellation)
            remaining = deadline - self._now()
            if remaining <= 0:
                raise ValueError("campaign_inference_refused")
            selected_request = replace(request, timeout_seconds=remaining)
            original = _binding(selected_request)
            transport_cancellation = (
                cancellation if cancellation is not None else self._cancellation
            )
            result = self._port.infer(selected_request, cancellation=transport_cancellation)
            self._cancelled(cancellation)
            if (self._stopped or self._now() >= deadline or _binding(selected_request) != original
                    or config != (self.model, self.provider_id, self.evidence_mode, self._maximum)
                    or type(result) is not InferenceResult):
                raise ValueError("campaign_inference_refused")
            result = replace(result)
            if (result.request_id != request.request_id or result.model != self.model
                    or result.provider_id != self.provider_id
                    or result.evidence_mode != self.evidence_mode
                    or len(result.text) > request.max_output_chars):
                raise ValueError("campaign_inference_refused")
            self._reported += 1
            if result.input_tokens is None or result.output_tokens is None:
                self._usage_known = False
            else:
                self._input += result.input_tokens
                self._output += result.output_tokens
            if result.status == "completed":
                self._completed += 1
            else:
                self._stopped = True
                self._last_error = (result.error_code if result.error_code in DIAGNOSTIC_CODES
                                    else "diagnostic_code_withheld")
            return result
        except (Exception, KeyboardInterrupt):
            failed = True
            self._stopped = True
            self._last_error = self._last_error or "inference_unavailable"
        finally:
            self._inflight = False
            self._lock.release()
        if failed:
            # Outside the exception handler: no private provider/path context.
            raise ValueError("campaign_inference_refused") from None
