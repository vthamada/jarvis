"""Catalog cleanup failures never allow activation of inference."""

import importlib.util
from pathlib import Path

import pytest
from inference_service.siwc_contracts import SiwcError

_SPEC = importlib.util.spec_from_file_location(
    "jarvis_oauth_catalog_cleanup_fixture",
    Path(__file__).with_name("test_siwc_oauth_http.py"),
)
fixture = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixture)


@pytest.mark.parametrize("broken", ["response", "connection", "both"])
@pytest.mark.parametrize("operation", ["discovery", "catalog"])
def test_cleanup_error_discards_otherwise_complete_success(broken, operation):
    body = (fixture.discovery() if operation == "discovery" else
            {"models": [{"slug": "fixture-model", "display_name": "Synthetic model"}]})
    client, factory, response = fixture.fixture(body)
    closed = []

    def close(name):
        closed.append(name)
        if broken in {name, "both"}:
            raise RuntimeError("synthetic private close error")

    response.close = lambda: close("response")
    factory.connection.close = lambda: close("connection")
    with pytest.raises(SiwcError, match="^siwc_cleanup_failed$"):
        if operation == "discovery":
            client.discovery()
        else:
            fixture.models(client)
    assert closed == ["response", "connection"]
