"""Public mission catalog and explicit isolated native/model pilot campaigns.

No scheduler, login, session renewal, paid fallback or external-agent substitute.
The live pilot is restricted to the approved model, one selected account and
eight planned dispatches under one shared ceiling of at most ten infer attempts.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Event

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths

from .campaign import CampaignArm, CampaignBudget, MissionCampaign
from .mission_corpus import CORPUS_DIGEST, MISSIONS, VERSION

SCHEMA = "jarvis-mission-campaign-command-v1"
APPROVED_MODEL = "gpt-6.1-sol"
_TEXT_CAPABILITIES = ("text_reasoning", "source_reading", "artifact_drafting")
_TEST_MODES = {"fixture", "injected_transport"}


def _invalid():
    raise ValueError("mission_campaign_cli_refused")


def catalog():
    """Public metadata only; no credential, runtime, port or Core construction."""
    return {
        "schema_version": SCHEMA, "operation": "catalog", "corpus_version": VERSION,
        "corpus_digest": CORPUS_DIGEST, "mission_count": len(MISSIONS),
        "missions": [{
            "case_id": mission.case_id, "category": mission.category, "split": mission.split,
            "required_capabilities": list(mission.required_capabilities),
            "effect_capabilities": list(mission.effect_capabilities),
        } for mission in MISSIONS],
        "data_scope": "public_authored_synthetic", "secret_holdout": False,
        "account_opened": False, "core_constructed": False, "port_dispatches": 0,
        "promotion_allowed": False, "improvement_claim": False, "sota_claim": False,
    }


def _options(authorized, timeout_seconds, campaign_timeout_seconds, core_factory, clock):
    if (authorized is not True or not callable(clock)
            or core_factory is not None and not callable(core_factory)):
        _invalid()
    for value, maximum in ((timeout_seconds, 120), (campaign_timeout_seconds, 3600)):
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not 0 < value <= maximum):
            _invalid()


@contextmanager
def _temporary_runtime():
    base = Path(tempfile.gettempdir()).resolve()
    if (not base.is_absolute() or base == Path(base.anchor)
            or base.is_relative_to(ROOT.resolve())
            or any("onedrive" in part.casefold() for part in base.parts)):
        _invalid()
    with tempfile.TemporaryDirectory(prefix="jarvis-mission-campaign-", dir=str(base)) as value:
        root = Path(value)
        if not root.is_absolute() or root.resolve().is_relative_to(ROOT.resolve()):
            _invalid()
        yield root


class _UnavailableReference:
    """An unimplemented comparison arm; never an executed external harness."""

    evidence_mode = "fixture"

    def execute(self, _request):
        raise ValueError("reference_not_available")


def _arm(identifier, harness, revision, mode, port, budget, *, model=None, provider=None,
         capabilities=_TEXT_CAPABILITIES):
    return CampaignArm(
        arm_id=identifier, harness_id=harness, revision=revision, evidence_mode=mode,
        model_id=model, provider_id=provider, environment_id="isolated-local-python",
        tool_policy_id="assist-only-no-effects", capabilities=capabilities, port=port,
        budget=budget,
    )


def _safe_result(payload):
    # These paths are display guards only, not claims of universal PII detection.
    from apps.jarvis_console.review_input import _requires_redaction
    from apps.jarvis_console.runtime import ConsoleRuntime

    runtime = ConsoleRuntime(output_format="json", sensitive_paths=(str(ROOT), str(Path.home())))
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True)
    if len(encoded.encode("ascii")) > 1_048_576 or _requires_redaction(payload, runtime):
        _invalid()
    return payload


def run_native_baseline(*, authorized=False, timeout_seconds=30,
                        campaign_timeout_seconds=900, core_factory=None,
                        clock=time.monotonic):
    """All 25 missions/repeats remain in denominators, including unsupported effects."""
    _options(authorized, timeout_seconds, campaign_timeout_seconds, core_factory, clock)
    from .canonical_mission_port import CanonicalMissionTaskPort

    with _temporary_runtime() as runtime:
        options = {"core_factory": core_factory} if core_factory is not None else {}
        native = CanonicalMissionTaskPort(runtime, authorized=True, clock=clock, **options)
        budget = CampaignBudget(timeout_seconds=timeout_seconds)
        report = MissionCampaign(
            baseline=_arm("jarvis-native", "jarvis-core", "native-baseline-v1",
                          "core_local", native, budget),
            candidate=_arm("unavailable-reference", "not-implemented", "unavailable-v1",
                           "fixture", _UnavailableReference(), budget, capabilities=()),
            repeats=2, clock=clock,
        ).run(tuple(mission.case_id for mission in MISSIONS), run_id="native-mission-baseline",
              authorized=True, timeout_seconds=campaign_timeout_seconds, max_executions=50)
        return _safe_result({
            "schema_version": SCHEMA, "operation": "native-baseline",
            "campaign": report.export_metrics(), "canonical_core": native.snapshot(),
            "reference_available": False, "external_harness_executed": False,
            "account_opened": False, "external_model_used": False,
            "production_memory_opened": False, "runtime_mode": "disposable_local_sqlite",
            "promotion_allowed": False, "improvement_claim": False, "sota_claim": False,
        })


def _pilot_options(confirmed, credential_dir, profile_ref, model, max_calls,
                   inference_evidence_mode, port_factory, core_factory, cancellation):
    if (confirmed is not True or model != APPROVED_MODEL
            or type(profile_ref) is not str
            or re.fullmatch(r"profile-[a-f0-9]{64}", profile_ref) is None
            or not isinstance(credential_dir, Path) or not credential_dir.is_absolute()
            or ".." in credential_dir.parts or credential_dir == Path(credential_dir.anchor)
            or credential_dir == Path.home() or str(credential_dir).startswith(("\\\\", "//"))
            or credential_dir.is_relative_to(ROOT)
            or any("onedrive" in part.casefold() for part in credential_dir.parts)
            or type(max_calls) is not int or not 1 <= max_calls <= 10
            or type(inference_evidence_mode) is not str
            or (port_factory is not None and not callable(port_factory))
            or (cancellation is not None and not isinstance(cancellation, Event))):
        _invalid()
    injected = port_factory is not None or core_factory is not None
    if injected:
        if port_factory is None or inference_evidence_mode not in _TEST_MODES:
            _invalid()
    elif inference_evidence_mode != "live":
        _invalid()


def run_model_pilot(*, authorized=False, confirmed=False, credential_dir, profile_ref,
                    model=APPROVED_MODEL, max_calls=10, timeout_seconds=30,
                    campaign_timeout_seconds=600, inference_evidence_mode="live",
                    port_factory=None, core_factory=None, cancellation=None,
                    clock=time.monotonic):
    """Factory hooks are test evidence only; default session is opened lazily once."""
    _options(authorized, timeout_seconds, campaign_timeout_seconds, core_factory, clock)
    _pilot_options(confirmed, credential_dir, profile_ref, model, max_calls,
                   inference_evidence_mode, port_factory, core_factory, cancellation)
    ensure_src_paths()
    from inference_service.diagnostics import emit_diagnostic

    from .canonical_mission_port import CanonicalMissionTaskPort
    from .inference_guard import CampaignInferenceGuard
    from .model_reference_port import ModelReferenceTaskPort

    token = cancellation if cancellation is not None else Event()
    factory_state = {"invoked": False, "returned": False}
    diagnostics, diagnostic_limit = [], {"truncated": False}

    def diagnostic_sink(record):
        if len(diagnostics) >= 960:
            diagnostic_limit["truncated"] = True
        else:
            diagnostics.append(record.copy())

    def observe_diagnostic(record):
        # Read only the four allowlisted metadata fields, not arbitrary bodies,
        # headers, account/profile/request IDs, model text or exception strings.
        if type(record) is dict:
            emit_diagnostic(diagnostic_sink, phase=record.get("phase"),
                            status=record.get("status"), code=record.get("code"),
                            http_status=record.get("http_status"))

    def selected_port():
        factory_state["invoked"] = True
        if port_factory is not None:
            selected = port_factory(credential_dir, profile_ref, model)
        else:
            from apps.jarvis_console.generative_analysis_cli import _session_factory

            selected = _session_factory(credential_dir, profile_ref, model,
                                        telemetry=observe_diagnostic)
        factory_state["returned"] = True
        return selected

    guard = CampaignInferenceGuard(
        selected_port, model=model, provider_id="responses_plan",
        evidence_mode=inference_evidence_mode, authorized=True,
        max_calls=max_calls, clock=clock, cancellation=token,
    )
    case_ids = tuple(mission.case_id for mission in MISSIONS
                     if mission.split == "dev" and not mission.effect_capabilities
                     and set(mission.required_capabilities) <= set(_TEXT_CAPABILITIES))[:2]
    if len(case_ids) != 2:
        _invalid()
    with _temporary_runtime() as runtime:
        options = {"core_factory": core_factory} if core_factory is not None else {}
        canonical = CanonicalMissionTaskPort(
            runtime, authorized=True, inference_port=guard, model=model,
            provider_id="responses_plan", inference_evidence_mode=inference_evidence_mode,
            cancellation=token, clock=clock, **options,
        )
        reference = ModelReferenceTaskPort(
            guard, model=model, provider_id="responses_plan",
            inference_evidence_mode=inference_evidence_mode, authorized=True,
            max_calls=4, timeout_seconds=timeout_seconds, max_output_bytes=4000,
            clock=clock, cancellation=token,
        )
        mode = "model_real" if inference_evidence_mode == "live" else inference_evidence_mode
        budget = CampaignBudget(timeout_seconds=timeout_seconds)
        report = MissionCampaign(
            baseline=_arm("model-reference", "single-model-no-tools", "model-reference-v1",
                          mode, reference, budget, model=model, provider="responses_plan"),
            candidate=_arm("jarvis-canonical", "jarvis-core", "canonical-mission-v1",
                           mode, canonical, budget, model=model, provider="responses_plan"),
            repeats=2, clock=clock,
        ).run(case_ids, run_id="approved-model-mission-pilot", authorized=True,
              timeout_seconds=campaign_timeout_seconds, max_executions=8,
              cancelled=lambda: token.is_set() or guard.stopped)
        return _safe_result({
            "schema_version": SCHEMA, "operation": "pilot",
            "campaign": report.export_metrics(), "inference_budget": guard.snapshot(),
            "inference_diagnostics": diagnostics,
            "inference_diagnostics_status": (
                "not_observed_injected" if port_factory is not None
                else "observed" if diagnostics else "not_observed"
            ),
            "inference_diagnostics_truncated": diagnostic_limit["truncated"],
            "http_request_count": None,
            "canonical_core": canonical.snapshot(), "model_reference": reference.snapshot(),
            "planned_model_dispatches": 8, "same_selected_account": True,
            "account_factory_invoked": factory_state["invoked"] and port_factory is None,
            "account_opened": (
                False if port_factory is not None or not factory_state["invoked"]
                else True if factory_state["returned"] else None
            ),
            "model": model, "provider": "responses_plan", "evidence_mode": mode,
            "external_harness_executed": False, "session_renewal_allowed": False,
            "paid_fallback_allowed": False, "production_memory_opened": False,
            "runtime_mode": "disposable_local_sqlite", "promotion_allowed": False,
            "improvement_claim": False, "sota_claim": False,
        })


class _SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        _invalid()


def main(argv=None):
    parser = _SafeParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("catalog")
    native = commands.add_parser("native-baseline")
    pilot = commands.add_parser("pilot")
    for command in (native, pilot):
        command.add_argument("--authorized", action="store_true", required=True)
        command.add_argument("--timeout-seconds", type=float, default=30)
        command.add_argument("--campaign-timeout-seconds", type=float, default=600)
    pilot.add_argument("--confirm-input", action="store_true", required=True)
    pilot.add_argument("--credential-dir", type=Path, required=True)
    pilot.add_argument("--profile-ref", required=True)
    pilot.add_argument("--model", default=APPROVED_MODEL)
    pilot.add_argument("--max-calls", type=int, default=10)
    try:
        args = parser.parse_args(argv)
        options = vars(args).copy()
        operation = options.pop("operation")
        if operation == "catalog":
            payload = catalog()
        elif operation == "native-baseline":
            payload = run_native_baseline(**options)
        else:
            options["confirmed"] = options.pop("confirm_input")
            payload = run_model_pilot(**options)
        print(json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"mission_campaign_interrupted"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"mission_campaign_cli_refused"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
