"""No account/network: explicit command consent and shared injected call limits."""

import json
import re
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from threading import Event

import pytest

from evals.operator_tasks import campaign_cli as cli
from evals.operator_tasks.mission_corpus import MISSIONS
from evals.operator_tasks.model_reference_port import ModelReferenceTaskPort
from evals.operator_tasks.runner import ExecutionResult
from shared.model_inference import InferenceResult

PROFILE = "profile-" + "a" * 64


def _product(content):
    """Parse only the two supplied public grammars; no grader/oracle lookup."""
    value = json.loads(content)
    brief, sources = value["brief"], value["sources"]
    source = sources[-1]
    keys = re.search(r"exactly these keys: ([^.]+)\.", brief).group(1).split(",")
    facts, citations = {}, []
    for key in keys:
        match = re.search(rf"{key}=([A-Za-z0-9_]+)", source["text"])
        token = match.group(1)
        facts[key] = int(token) if token.isdigit() else token
        citations.append({"key": key, "source_ref": source["ref"],
                          "start": match.start(), "end": match.end()})
    return json.dumps({"binding": value["binding"], "status": "completed", "product": {
        "kind": re.search(r"kind='([^']+)'", brief).group(1), "draft": True,
        "facts": facts, "citations": citations, "order": [], "artifact": None,
    }})


class Inference:
    provider_id = "responses_plan"
    evidence_mode = "injected_transport"

    def __init__(self, *, status="completed", action=None):
        self.status, self.action, self.requests = status, action, []

    def infer(self, request, *, cancellation=None):
        self.requests.append(request)
        if self.action:
            self.action()
        return InferenceResult(
            request_id=request.request_id, model=request.model, provider_id=self.provider_id,
            status=self.status, text=_product(request.messages[0].content)
            if self.status == "completed" else "",
            evidence_mode=self.evidence_mode,
            error_code=None if self.status == "completed" else "transport_unavailable",
        )


class FakeCanonical:
    """Injected pipeline control, deliberately no claim of a canonical Core turn."""

    instances = []

    def __init__(self, runtime_root, *, inference_port=None, model=None,
                 provider_id="fixture", inference_evidence_mode="fixture", clock=None,
                 cancellation=None, **_options):
        self.root, self.requests = runtime_root, []
        self.evidence_mode = (
            {"fixture": "fixture", "injected_transport": "injected_transport", "live": "model_real"}
            [inference_evidence_mode] if inference_port else "core_local"
        )
        self.proxy = ModelReferenceTaskPort(
            inference_port, model=model, provider_id=provider_id,
            inference_evidence_mode=inference_evidence_mode, authorized=True,
            max_calls=4, clock=clock, cancellation=cancellation,
        ) if inference_port else None
        self.instances.append(self)

    def execute(self, request):
        self.requests.append(request)
        return self.proxy.execute(request) if self.proxy else ExecutionResult(
            request.binding, "incomplete",
        )

    def snapshot(self):
        return {"core_turns": 0, "canonical_finals_verified": 0,
                "production_memory_opened": False, "test_control": True}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    from evals.operator_tasks import canonical_mission_port

    FakeCanonical.instances = []
    monkeypatch.setattr(canonical_mission_port, "CanonicalMissionTaskPort", FakeCanonical)

    @contextmanager
    def runtime():
        yield tmp_path / "owned-disposable-runtime"

    monkeypatch.setattr(cli, "_temporary_runtime", runtime)
    return tmp_path


def pilot_options(tmp_path, inference, **patch):
    values = dict(
        authorized=True, confirmed=True, credential_dir=tmp_path / "unopened-account",
        profile_ref=PROFILE, inference_evidence_mode="injected_transport",
        port_factory=lambda *_args: inference,
    )
    values.update(patch)
    return values


def test_catalog_needs_no_authorization_runtime_core_or_account(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        pytest.fail("catalog touched private runtime/account")

    monkeypatch.setattr(cli, "_temporary_runtime", forbidden)
    assert cli.main(["catalog"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mission_count"] == 25 and not payload["account_opened"]
    assert not payload["core_constructed"] and payload["port_dispatches"] == 0
    assert all("brief" not in item and "sources" not in item for item in payload["missions"])


@pytest.mark.parametrize("patch", [
    {"authorized": False}, {"authorized": 1}, {"confirmed": False},
    {"model": "different-model"}, {"max_calls": 11}, {"max_calls": True},
    {"profile_ref": "private-profile"}, {"credential_dir": Path("relative")},
    {"inference_evidence_mode": "live"},
])
def test_pilot_refuses_before_file_factory_or_account(tmp_path, monkeypatch, patch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid pilot crossed side-effect boundary")

    monkeypatch.setattr(cli, "_temporary_runtime", forbidden)
    with pytest.raises(ValueError, match="mission_campaign_cli_refused"):
        cli.run_model_pilot(**pilot_options(tmp_path, Inference(), **patch))
    assert not (tmp_path / "unopened-account").exists()


def test_native_baseline_requires_opt_in_before_runtime(monkeypatch):
    monkeypatch.setattr(cli, "_temporary_runtime", lambda: pytest.fail("no native consent"))
    with pytest.raises(ValueError, match="mission_campaign_cli_refused"):
        cli.run_native_baseline()


def test_native_baseline_accounts_all_25_with_unavailable_reference(isolated):
    result = cli.run_native_baseline(authorized=True)
    report = result["campaign"]
    assert report["expected_measurements"] == report["reported_measurements"] == 100
    assert report["comparison_status"] == "not_comparable"
    assert [item["denominator_total"] for item in report["arms"]] == [50, 50]
    reference = report["arms"][1]
    assert reference["unsupported"] == reference["not_run"] == 50
    supported = sum(set(m.required_capabilities) <= set(cli._TEXT_CAPABILITIES) for m in MISSIONS)
    assert report["port_dispatches"] == supported * 2
    assert not result["external_harness_executed"] and not result["external_model_used"]


def test_two_arms_share_one_lazy_account_factory_and_eight_infer_attempts(isolated):
    inference = Inference()
    calls = []

    def factory(*args):
        calls.append(args)
        return inference

    result = cli.run_model_pilot(**pilot_options(isolated, inference, port_factory=factory))
    assert len(calls) == 1
    assert calls[0] == (isolated / "unopened-account", PROFILE, "gpt-6.1-sol")
    assert len(inference.requests) == 8
    assert result["inference_budget"]["attempted_model_calls"] == 8
    assert result["inference_budget"]["max_model_calls"] == 10
    assert result["campaign"]["expected_measurements"] == 8
    assert result["same_selected_account"] and not result["account_opened"]
    assert result["evidence_mode"] == "injected_transport"
    assert result["inference_diagnostics"] == []
    assert result["inference_diagnostics_status"] == "not_observed_injected"
    assert all(len(instance.requests) == 4 for instance in FakeCanonical.instances)
    assert not result["session_renewal_allowed"] and not result["paid_fallback_allowed"]
    encoded = json.dumps(result)
    assert PROFILE not in encoded and str(isolated) not in encoded
    assert all(asdict(request)["messages"][0]["content"] not in encoded
               for request in inference.requests)


@pytest.mark.parametrize("failure", ["provider", "factory", "metadata"])
def test_first_session_transport_or_factory_failure_stops_both_arms(isolated, failure):
    inference = Inference(status="failed")
    calls = []

    def factory(*_args):
        calls.append(1)
        if failure == "factory":
            raise ValueError("private credential storage path")
        if failure == "metadata":
            inference.evidence_mode = "live"
        return inference

    result = cli.run_model_pilot(**pilot_options(isolated, inference, port_factory=factory))
    assert len(calls) == 1
    assert len(inference.requests) == (1 if failure == "provider" else 0)
    assert result["inference_budget"]["stopped"]
    assert result["inference_budget"]["attempted_model_calls"] == 1
    assert result["campaign"]["port_dispatches"] == 1
    assert not any(item["success"] for item in result["campaign"]["measurements"])
    assert "private credential" not in json.dumps(result)


def test_smaller_call_ceiling_is_global_not_per_arm(isolated):
    inference = Inference()
    result = cli.run_model_pilot(**pilot_options(isolated, inference, max_calls=1))
    assert len(inference.requests) == 1
    assert result["inference_budget"]["attempted_model_calls"] == 1
    assert result["inference_budget"]["stopped"]


def test_cancelled_pilot_never_opens_injected_or_default_account(isolated):
    token = Event()
    token.set()
    inference = Inference()
    result = cli.run_model_pilot(**pilot_options(isolated, inference, cancellation=token))
    assert not inference.requests
    assert result["inference_budget"]["attempted_model_calls"] == 0
    assert not result["account_opened"]


def test_default_factory_mock_gets_bounded_whitelisted_diagnostics_not_private_content(
    isolated, monkeypatch,
):
    from apps.jarvis_console import generative_analysis_cli

    invoked = []
    sentinel = "private-body-profile-secret-sentinel"

    def factory(directory, profile, model, *, telemetry):
        invoked.append((directory, profile, model))
        telemetry({"phase": "session_preflight", "status": "failed",
                   "code": "siwc_credential_expired", "http_status": 401,
                   "body": sentinel, "profile_ref": PROFILE})
        telemetry({"phase": "responses_media_type", "status": "observed",
                   "code": "response_media_type_missing", "http_status": 200,
                   "headers": {"secret": sentinel}})
        telemetry({"phase": sentinel, "status": "failed", "code": sentinel})
        telemetry({"phase": "provider_result", "status": "failed", "code": sentinel})
        for _ in range(1000):
            telemetry({"phase": "responses_http", "status": "observed",
                       "http_status": 200, "body": sentinel})
        # This is not a live provider execution: the mocked factory fails before
        # returning any port or calling infer. It tests the default lazy seam.
        raise ValueError(sentinel)

    monkeypatch.setattr(generative_analysis_cli, "_session_factory", factory)
    result = cli.run_model_pilot(
        authorized=True, confirmed=True, credential_dir=isolated / "unopened-account",
        profile_ref=PROFILE,
    )
    assert len(invoked) == 1
    records = result["inference_diagnostics"]
    assert len(records) == 960 and result["inference_diagnostics_truncated"]
    assert records[0]["code"] == "siwc_credential_expired"
    assert records[1]["code"] == "response_media_type_missing"
    assert records[2]["code"] == "diagnostic_code_withheld"
    assert all(set(record) == {"schema_version", "phase", "status", "code", "http_status"}
               for record in records)
    assert result["inference_budget"]["attempted_model_calls"] == 1
    assert result["inference_budget"]["completed_model_calls"] == 0
    assert result["http_request_count"] is None
    encoded = json.dumps(result)
    assert sentinel not in encoded and PROFILE not in encoded and str(isolated) not in encoded


@pytest.mark.parametrize("argv", [
    ["catalog", "--profile-ref", "private-value"],
    ["pilot", "--authorized", "--credential-dir", "private-value"],
    ["native-baseline", "--unknown", "private-value"],
])
def test_parser_errors_are_content_free_without_reading_input(argv, capsys):
    assert cli.main(argv) == 2
    captured = capsys.readouterr()
    assert "private-value" not in captured.out + captured.err
    assert json.loads(captured.out)["error_code"] == "mission_campaign_cli_refused"
