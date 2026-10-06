"""A transport error remains a bounded content-free provider result."""

import pytest
from inference_service.http_transport import PlanTransportError
from inference_service.providers import ResponsesPlanInferenceProvider

from shared.model_inference import InferenceMessage, InferenceRequest


@pytest.mark.parametrize("code,status", [
    ("timeout", "timed_out"), ("cancelled", "cancelled"),
    ("credential_expired", "failed"), ("plan_usage_scope_missing", "failed"),
    ("plan_usage_not_authorized", "failed"), ("plan_usage_limited", "failed"),
    ("private-marker password=sensitive", "failed"),
])
def test_mapping_and_telemetry_do_not_expose_arbitrary_error(code, status):
    def transport(*args, **kwargs):
        error = PlanTransportError("transport_error")
        error.code = code  # adversarial trusted-injection seam, not remote input
        error.status = "completed"
        raise error

    events = []
    result = ResponsesPlanInferenceProvider(transport, telemetry=events.append).infer(
        InferenceRequest("request-one", "chosen-model", (InferenceMessage("user", "Test."),))
    )
    assert result.status == status and result.text == ""
    assert result.error_code == ("transport_error" if "private-marker" in code else code)
    assert "private-marker" not in str(events) and "sensitive" not in repr(result)
    assert events[0]["error_code"] == result.error_code
