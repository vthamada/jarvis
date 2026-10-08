"""Lazy, explicitly authorized account inference with one end-to-end budget.

This leaf never logs in, loads a profile, refreshes credentials or retries. The
caller owns Core eligibility and final synthesis. Account identity is not a
JARVIS principal. Cancellation is cooperative; this is not a process sandbox.
"""

from __future__ import annotations

import http.client
import time
from dataclasses import replace
from threading import Event

from inference_service.diagnostics import emit_diagnostic
from inference_service.oauth_http import ModelCatalog, ModelChoice, SiwcHttpsClient
from inference_service.providers import ResponsesPlanInferenceProvider
from inference_service.siwc_contracts import SiwcCredentials, SiwcError, finite_number
from inference_service.siwc_session import SiwcSession
from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult


class _Refusal(Exception):
    def __init__(self, code, status="failed"):
        self.code, self.status = code, status


class _ObservedResource:
    """Observe cleanup even when the underlying transport suppresses errors."""

    def __init__(self, resource, resources):
        self._resource, self._resources = resource, resources
        self.closed, self.failed = False, False
        resources.append(self)

    def __getattr__(self, name):
        return getattr(self._resource, name)

    @property
    def timeout(self):
        return self._resource.timeout

    @timeout.setter
    def timeout(self, value):
        self._resource.timeout = value

    def getresponse(self):
        return _ObservedResource(self._resource.getresponse(), self._resources)

    def close(self):
        try:
            self._resource.close()
            self.closed = True
        except Exception:
            self.failed = True
            raise


class SessionInferencePort:
    """One selected model, one catalog request, at most one infer per call.

    Injected factories/clients/session methods can never establish live evidence.
    Construction is inert. The default-off authorization is local consent, not
    a governance decision or authenticated operator grant.
    """

    provider_id = "responses_plan"

    def __init__(self, session: SiwcSession, *, model: str, authorized: bool = False,
                 clock=time.monotonic, connection_factory=None, telemetry=None):
        if (not isinstance(session, SiwcSession) or type(authorized) is not bool
                or not callable(clock)
                or (connection_factory is not None and not callable(connection_factory))
                or (telemetry is not None and not callable(telemetry))):
            raise ValueError("invalid_session_inference_options")
        ModelChoice(model, "Selected model")
        self._session, self._model, self._authorized = session, model, authorized
        self._clock, self._factory = clock, connection_factory
        self._telemetry = telemetry

    def __repr__(self):
        return "SessionInferencePort(authority='none', lazy=True)"

    @property
    def evidence_mode(self):
        session = self._session
        normal = (
            type(session) is SiwcSession and type(session._client) is SiwcHttpsClient
            and session._client.evidence_mode == "fixed_https_transport"
            and getattr(session.catalog, "__func__", None) is SiwcSession.catalog
            and getattr(session.provider, "__func__", None) is SiwcSession.provider
            and self._factory is None
        )
        return "live" if normal else "injected_transport"

    def _snapshot(self):
        session = self._session
        with session._lock:
            creds = session._credentials
            if (type(creds) is not SiwcCredentials or creds.host_id != session._host
                    or type(session._generation) is not int or session._generation < 0):
                raise _Refusal("session_account_unavailable")
            # Retained only in-process; no token/account/host values in metadata.
            creds.__post_init__()
            return (session._generation, creds, session._host,
                    creds.client_id, creds.subject, creds.issuer, session._client,
                    creds.access_token, creds.refresh_token, creds.id_token,
                    creds.scopes, creds.expires_at, creds.saved_at)

    def _fence(self, snapshot):
        current = self._snapshot()
        if (current[0] != snapshot[0] or current[1] is not snapshot[1]
                or current[2:] != snapshot[2:]):
            raise _Refusal("session_binding_changed")

    def infer(self, request: InferenceRequest, *, cancellation: Event | None = None):
        # Reconstruct even frozen records: trusted Python can forge/mutate them.
        if type(request) is not InferenceRequest:
            raise ValueError("invalid_inference_request")
        request = replace(request)
        request = replace(request, messages=tuple(
            InferenceMessage(message.role, message.content) for message in request.messages
        ))
        evidence = "injected_transport"
        phase = "session_preflight"
        telemetry = self._telemetry
        diagnostic_code = None
        def port_binding():
            session = self._session
            return (self._model, self.provider_id, self._factory,
                    getattr(session.catalog, "__func__", session.catalog),
                    getattr(session.provider, "__func__", session.provider))

        try:
            evidence = self.evidence_mode
            original_port = port_binding() if telemetry is not None else None
            if cancellation is not None and not isinstance(cancellation, Event):
                raise _Refusal("invalid_cancellation")
            token = cancellation if cancellation is not None else Event()
            if not self._authorized:
                raise _Refusal("session_inference_not_authorized")
            if request.model != self._model:
                raise _Refusal("session_model_mismatch")
            start = self._clock()
            if not finite_number(start):
                raise _Refusal("invalid_clock")
            deadline, last = start + request.timeout_seconds, start

            def remaining():
                nonlocal last
                if token.is_set():
                    raise _Refusal("cancelled", "cancelled")
                now = self._clock()
                if not finite_number(now) or now < last:
                    raise _Refusal("invalid_clock")
                last = now
                if now >= deadline:
                    raise _Refusal("timeout", "timed_out")
                return deadline - now

            remaining()
            snapshot = self._snapshot()
            if telemetry is not None:
                emit_diagnostic(telemetry, phase=phase, status="completed")
                remaining()
                self._fence(snapshot)
            phase = "catalog"
            if telemetry is not None:
                emit_diagnostic(telemetry, phase=phase, status="started")
                remaining()
                self._fence(snapshot)
            catalog = self._session.catalog(authorized=True, timeout_seconds=remaining(),
                                            cancellation=token)
            remaining()
            self._fence(snapshot)
            if type(catalog) is not ModelCatalog:
                raise _Refusal("session_catalog_invalid")
            catalog.__post_init__()
            if telemetry is not None:
                emit_diagnostic(telemetry, phase=phase, status="completed")
                remaining()
                self._fence(snapshot)
            phase = "model_selection"
            catalog.select(self._model)
            if catalog.evidence_mode != "fixed_https_transport":
                evidence = "injected_transport"
            if telemetry is not None:
                emit_diagnostic(telemetry, phase=phase, status="completed")
                remaining()
                self._fence(snapshot)
            resources = []

            def observed_factory(*args, **kwargs):
                factory = self._factory or http.client.HTTPSConnection
                return _ObservedResource(factory(*args, **kwargs), resources)

            phase = "provider_setup"
            provider_options = dict(authorized=True, connection_factory=observed_factory)
            if telemetry is not None:
                provider_options["telemetry"] = telemetry
            provider = self._session.provider(self._model, **provider_options)
            remaining()
            self._fence(snapshot)
            # A replacement provider is useful as a test seam, never live proof.
            if type(provider) is not ResponsesPlanInferenceProvider:
                evidence = "injected_transport"
            if telemetry is not None:
                emit_diagnostic(telemetry, phase=phase, status="completed")
                remaining()
                self._fence(snapshot)
            phase = "provider_result"
            result = provider.infer(replace(request, timeout_seconds=remaining()),
                                    cancellation=token)
            remaining()
            self._fence(snapshot)
            if any(resource.failed or not resource.closed for resource in resources):
                raise _Refusal("session_cleanup_failed")
            if self.evidence_mode != "live":
                evidence = "injected_transport"
            if type(result) is not InferenceResult:
                raise _Refusal("session_result_invalid")
            result = replace(result)
            if (result.request_id != request.request_id or result.model != self._model
                    or result.provider_id != self.provider_id
                    or result.evidence_mode != "injected_transport"
                    or len(result.text) > request.max_output_chars
                    or any(count is not None and count > 1_000_000_000
                           for count in (result.input_tokens, result.output_tokens))):
                raise _Refusal("session_result_invalid")
            if result.status != "completed":
                if telemetry is not None:
                    emit_diagnostic(telemetry, phase=phase, status=result.status,
                                    code=result.error_code)
                    remaining()
                    self._fence(snapshot)
                status = result.status
                code = {"cancelled": "cancelled", "timed_out": "timeout"}.get(
                    status, "session_inference_failed")
                raise _Refusal(code, status)
            remaining()
            self._fence(snapshot)
            if telemetry is not None:
                emit_diagnostic(telemetry, phase="session_result", status="completed")
                remaining()
                self._fence(snapshot)
                if (port_binding() != original_port
                        or result.model != self._model or result.provider_id != self.provider_id):
                    raise _Refusal("session_binding_changed")
                if evidence == "live" and self.evidence_mode != "live":
                    raise _Refusal("session_binding_changed")
            return replace(result, evidence_mode=evidence)
        except _Refusal as exc:
            status, code = exc.status, exc.code
        except SiwcError as exc:
            diagnostic_code = exc.code
            status, code = {
                "siwc_cancelled": ("cancelled", "cancelled"),
                "siwc_timeout": ("timed_out", "timeout"),
            }.get(exc.code, ("failed", "session_inference_failed"))
        except TimeoutError:
            status, code = "timed_out", "timeout"
        except Exception:
            status, code = "failed", "session_inference_failed"
        emit_diagnostic(telemetry, phase=phase, status=status,
                        code=diagnostic_code if diagnostic_code is not None else code)
        emit_diagnostic(telemetry, phase="session_result", status=status, code=code)
        return InferenceResult(request.request_id, request.model, self.provider_id,
                               status, error_code=code, evidence_mode=evidence)
