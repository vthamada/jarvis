"""Content-free opt-in inference observations, never acceptance or authority.

Only literal internal labels cross this boundary. No exception strings, bodies,
headers, credentials, URLs, model/account/request identities or content are read.
Sinks are trusted synchronous observers, not a deadline or process sandbox.
"""

DIAGNOSTIC_PHASES = frozenset({
    "profile_setup", "session_preflight", "catalog", "model_selection", "provider_setup",
    "responses_request", "responses_http", "responses_stream", "provider_result",
    "session_result", "profile_result",
})
DIAGNOSTIC_STATUSES = frozenset({
    "started", "completed", "failed", "cancelled", "timed_out", "observed",
})
DIAGNOSTIC_CODES = frozenset({
    "diagnostic_code_withheld", "invalid_timeout", "invalid_cancellation",
    "invalid_request_payload", "unsupported_request_field", "request_limit_exceeded",
    "invalid_clock", "cancelled", "timeout", "plan_usage_not_authorized",
    "plan_usage_scope_missing", "credential_expired", "tls_verification_required",
    "plan_authentication_refused", "plan_permission_refused", "plan_usage_limited",
    "http_request_refused", "unsupported_response_encoding", "transport_error",
    "event_limit_exceeded", "ambiguous_stream_terminal", "malformed_sse_event",
    "malformed_stream_chunk", "stream_limit_exceeded", "line_limit_exceeded",
    "ambiguous_sse_event", "stream_interrupted", "event_after_terminal", "malformed_event",
    "malformed_response", "response_identity_mismatch", "model_mismatch", "malformed_delta",
    "text_after_done", "output_limit_exceeded", "malformed_completion", "output_mismatch",
    "provider_error", "response_incomplete", "unsupported_output", "unsupported_event",
    "empty_output", "malformed_usage", "subscription_sharing_usage_limit_exceeded",
    "subscription_sharing_usage_unavailable", "subscription_sharing_unsupported_capability",
    "invalid_api_key", "rate_limit_exceeded", "model_not_found", "insufficient_quota",
    "server_error", "siwc_catalog_invalid", "siwc_model_unavailable", "siwc_response_invalid",
    "siwc_transport_configuration_invalid", "siwc_discovery_invalid", "siwc_jwks_invalid",
    "siwc_token_request_invalid", "siwc_credential_invalid", "siwc_clock_invalid",
    "siwc_credential_expired", "siwc_plan_scope_missing", "siwc_timeout_invalid",
    "siwc_cancellation_invalid", "siwc_network_not_authorized", "siwc_cancelled", "siwc_timeout",
    "siwc_tls_verification_required", "siwc_http_refused", "siwc_response_limit_exceeded",
    "siwc_authentication_refused", "siwc_permission_refused", "siwc_usage_limited",
    "siwc_transport_failed", "siwc_cleanup_failed", "siwc_invalid_grant", "siwc_invalid_client",
    "siwc_invalid_request", "siwc_unauthorized_client", "siwc_unsupported_grant_type",
    "siwc_invalid_scope", "siwc_access_denied", "siwc_temporarily_unavailable",
    "siwc_identity_invalid", "siwc_credentials_invalid", "siwc_token_response_invalid",
    "siwc_session_input_invalid", "siwc_account_missing", "siwc_registration_missing",
    "siwc_storage_binding_mismatch", "siwc_storage_busy", "siwc_storage_input_invalid",
    "siwc_storage_invalid", "siwc_storage_limit_exceeded", "siwc_storage_lock_required",
    "siwc_storage_not_authorized", "siwc_storage_path_refused", "siwc_storage_permissions_refused",
    "siwc_storage_protection_failed", "siwc_storage_protection_refused",
    "siwc_storage_protection_unavailable", "siwc_storage_record_missing",
    "siwc_storage_unavailable", "siwc_storage_uninitialized", "siwc_storage_write_failed",
    "siwc_refresh_not_authorized", "siwc_catalog_not_authorized", "siwc_inference_not_authorized",
    "siwc_session_replaced", "siwc_model_selection_mismatch", "session_account_unavailable",
    "session_binding_changed", "session_inference_not_authorized", "session_model_mismatch",
    "session_catalog_invalid", "session_cleanup_failed", "session_result_invalid",
    "session_inference_failed", "profile_changed", "binding_mismatch", "request_changed",
    "invalid_result", "inference_failed", "inference_unavailable",
})


def emit_diagnostic(sink, *, phase, status, code=None, http_status=None):
    """Emit a fresh fixed record; invalid phase/status drops rather than echoes."""
    try:
        if (not callable(sink) or type(phase) is not str or phase not in DIAGNOSTIC_PHASES
                or type(status) is not str or status not in DIAGNOSTIC_STATUSES):
            return
        safe_code = (None if code is None else code if type(code) is str
                     and code in DIAGNOSTIC_CODES else "diagnostic_code_withheld")
        safe_http = http_status if type(http_status) is int and 100 <= http_status <= 599 else None
        sink({"schema_version": "jarvis-inference-diagnostic-v1", "phase": phase,
              "status": status, "code": safe_code, "http_status": safe_http})
    except Exception:
        pass  # Observation must never change inference or publish partial content.
