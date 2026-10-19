"""Real disposable Core/canonical readback; synthetic injected inference only."""

import json
import re

from apps.jarvis_console.voice_pilot import _isolated_core
from evals.operator_tasks import campaign_cli as cli
from shared.model_inference import InferenceResult

PROFILE = "profile-" + "b" * 64


def _public_product(value):
    """Independent public-source parser, never a mission/oracle lookup."""
    source = value["sources"][-1]
    brief = value["brief"]
    keys = re.search(r"exactly these keys: ([^.]+)\.", brief).group(1).split(",")
    facts, citations = {}, []
    for key in keys:
        match = re.search(rf"{key}=([A-Za-z0-9_]+)", source["text"])
        raw = match.group(1)
        facts[key] = int(raw) if raw.isdigit() else raw
        citations.append({"key": key, "source_ref": source["ref"],
                          "start": match.start(), "end": match.end()})
    return json.dumps({"binding": value["binding"], "status": "completed", "product": {
        "kind": re.search(r"kind='([^']+)'", brief).group(1), "draft": True,
        "facts": facts, "citations": citations, "order": [], "artifact": None,
    }})


class InjectedInference:
    provider_id = "responses_plan"
    evidence_mode = "injected_transport"

    def __init__(self, *, fail=False):
        self.fail, self.requests = fail, []

    def infer(self, request, *, cancellation=None):
        self.requests.append(request)
        if self.fail:
            return InferenceResult(
                request_id=request.request_id, model=request.model, provider_id=self.provider_id,
                status="failed", error_code="transport_unavailable",
                evidence_mode=self.evidence_mode,
            )
        value = json.loads(request.messages[0].content)
        if "binding" in value:
            text = _public_product(value)
        else:
            # The public mission briefs still require native clarification.
            # Never reconstruct an evaluation binding from hidden fixture state
            # or reinterpret the old mixed-content grammar to fake competence.
            raise AssertionError("scope-refused native mission reached inference")
        return InferenceResult(
            request_id=request.request_id, model=request.model, provider_id=self.provider_id,
            status="completed", text=text, evidence_mode=self.evidence_mode,
        )


def test_real_native_slice_exposes_clarification_and_cleans_disposable_runtime(monkeypatch):
    # Full 25-case accounting is a unit composition check. This real-Core slice
    # validates the affected end-to-end seam without making a competence claim.
    monkeypatch.setattr(cli, "MISSIONS", cli.MISSIONS[:1])
    cores, roots, routed = [], [], []

    def factory(path):
        roots.append(path)
        core = _isolated_core(path)
        cores.append(core)
        direct = core.executive_engine.direct

        def capture(contract):
            routed.append(contract.content)
            return direct(contract)

        core.executive_engine.direct = capture
        return core

    result = cli.run_native_baseline(authorized=True, core_factory=factory)
    assert len(cores) == 2
    assert result["canonical_core"]["core_turns"] == 0
    # Exact public mission text hits the current lexical routing guard. This is
    # an observed capability gap, not permission to force ALLOW for a benchmark.
    assert result["canonical_core"]["canonical_finals_verified"] == 0
    assert result["canonical_core"]["clarifications_required"] == 2
    assert result["canonical_core"]["native_decisions_required"] == 0
    assert result["canonical_core"]["last_outcome"] == "core_scope_refused"
    assert result["canonical_core"]["source_routing"] == "request_bound_reviewed_bundle"
    assert routed == [cli.MISSIONS[0].brief] * 2
    assert all(source.text not in text for text in routed for source in cli.MISSIONS[0].sources)
    native = [item for item in result["campaign"]["measurements"]
              if item["arm_id"] == "jarvis-native"]
    assert len(native) == 2
    assert all(item["outcome"] == "needs_decision" and not item["success"] for item in native)
    assert result["campaign"]["expected_measurements"] == 4
    assert result["campaign"]["comparison_status"] == "not_comparable"
    assert not result["production_memory_opened"] and not result["external_model_used"]
    assert all(not path.exists() for path in roots)
    assert not result["promotion_allowed"] and not result["improvement_claim"]


def test_injected_two_arm_pilot_preserves_native_refusal_without_source_inference(tmp_path):
    inference, factories, finals, roots, routed = InjectedInference(), [], [], [], []

    def account_factory(*args):
        factories.append(args)
        return inference

    def core_factory(path):
        roots.append(path)
        core = _isolated_core(path)
        original = core.handle_input
        direct = core.executive_engine.direct

        def observed(contract, **options):
            response = original(contract, **options)
            turns = core.memory_service.repository.fetch_recent_turns(str(contract.session_id), 2)
            assert len(turns) == 1
            assert turns[0].response_text == response.response_text
            assert turns[0].request_content == contract.content
            assert response.memory_record.record_type == "interaction_turn"
            finals.append((str(response.request_id), str(response.session_id),
                           response.response_text))
            return response

        def capture(contract):
            routed.append(contract.content)
            return direct(contract)

        core.executive_engine.direct = capture
        core.handle_input = observed
        return core

    result = cli.run_model_pilot(
        authorized=True, confirmed=True, credential_dir=tmp_path / "unopened-account",
        profile_ref=PROFILE, inference_evidence_mode="injected_transport",
        port_factory=account_factory, core_factory=core_factory,
    )
    assert len(factories) == 1
    assert factories[0] == (tmp_path / "unopened-account", PROFILE, "gpt-6.1-sol")
    assert len(roots) == 4
    assert len(finals) == result["canonical_core"]["core_turns"] == 0
    assert result["canonical_core"]["canonical_finals_verified"] == 0
    assert result["canonical_core"]["clarifications_required"] == 4
    assert result["canonical_core"]["native_decisions_required"] == 0
    assert result["canonical_core"]["last_outcome"] == "core_scope_refused"
    assert len(routed) == 4
    assert set(routed) == {mission.brief for mission in cli.MISSIONS[:2]}
    assert all("\nRequest binding: " not in text and "\nSupplied sources: " not in text
               for text in routed)
    assert all(source.text not in text for text in routed
               for mission in cli.MISSIONS[:2] for source in mission.sources)
    native = [item for item in result["campaign"]["measurements"]
              if item["arm_id"] == "jarvis-canonical"]
    assert len(native) == 4
    assert all(item["outcome"] == "needs_decision" and not item["success"] for item in native)
    assert len(inference.requests) == 4  # Reference only; native never bypasses clarification.
    assert result["inference_budget"]["attempted_model_calls"] == len(inference.requests)
    assert result["campaign"]["expected_measurements"] == 8
    assert result["campaign"]["comparison_status"] == "matched_configuration_only"
    assert result["evidence_mode"] == "injected_transport" and not result["account_opened"]
    assert not result["campaign"]["paired_budget_execution_verified"]
    assert all(not path.exists() for path in roots)
    assert not (tmp_path / "unopened-account").exists()
    encoded = json.dumps(result)
    assert PROFILE not in encoded and str(tmp_path) not in encoded
    for request_id, session_id, response in finals:
        assert request_id not in encoded and session_id not in encoded and response not in encoded


def test_first_injected_session_failure_never_constructs_core_or_attempts_again(tmp_path):
    inference = InjectedInference(fail=True)
    opened = []

    def forbidden_core(_path):
        raise AssertionError("failure should stop before canonical Core construction")

    def account_factory(*_args):
        opened.append(1)
        return inference

    result = cli.run_model_pilot(
        authorized=True, confirmed=True, credential_dir=tmp_path / "unopened-account",
        profile_ref=PROFILE, inference_evidence_mode="injected_transport",
        port_factory=account_factory, core_factory=forbidden_core,
    )
    assert len(opened) == len(inference.requests) == 1
    assert result["inference_budget"]["stopped"]
    assert result["inference_budget"]["attempted_model_calls"] == 1
    assert result["canonical_core"]["core_turns"] == 0
    assert result["campaign"]["port_dispatches"] == 1
    assert all(not item["success"] for item in result["campaign"]["measurements"])
    assert not result["session_renewal_allowed"] and not result["paid_fallback_allowed"]
