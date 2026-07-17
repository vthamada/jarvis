"""Reusable offline domain eval pack loader and governed runtime runner."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from json import loads
from pathlib import Path
from re import fullmatch
from uuid import uuid4

from observability_service.service import ObservabilityQuery, ObservabilityService

from shared.contracts import (
    DomainEvalCaseContract,
    DomainEvalCaseResultContract,
    DomainEvalPackContract,
    DomainEvalRunContract,
    InputContract,
)
from shared.domain_registry import (
    RUNTIME_ROUTE_REGISTRY,
    is_promoted_specialist_route,
    route_metadata_payload,
)
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId
from tools.internal_pilot_support import build_orchestrator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOMAIN_EVAL_PACK_PATH = (
    ROOT / "tools" / "benchmarks" / "datasets" / "domain_analysis_eval_pack_v1.json"
)

_MAX_PACK_BYTES = 262_144
_MAX_CASES = 32
_MAX_INPUT_LENGTH = 4_096
_MAX_LIST_ITEMS = 32
_ID_PATTERN = r"[a-z][a-z0-9_-]{2,79}"
_SEMVER_PATTERN = r"[0-9]+\.[0-9]+\.[0-9]+"


def load_domain_eval_pack(
    path: Path | str = DEFAULT_DOMAIN_EVAL_PACK_PATH,
) -> DomainEvalPackContract:
    """Load a bounded versioned pack from local JSON."""

    resolved_path = Path(path)
    if resolved_path.stat().st_size > _MAX_PACK_BYTES:
        raise ValueError("domain eval pack exceeds the bounded size limit")
    payload = loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("domain eval pack must be a JSON object")
    raw_cases = payload.pop("cases", None)
    if not isinstance(raw_cases, list):
        raise ValueError("domain eval pack requires a cases list")
    cases = []
    for item in raw_cases:
        if not isinstance(item, dict):
            raise ValueError("domain eval cases must be JSON objects")
        cases.append(DomainEvalCaseContract(**item))
    return DomainEvalPackContract(cases=cases, **payload)


def validate_domain_eval_pack(pack: DomainEvalPackContract) -> list[str]:
    """Return semantic blockers for a pack without executing it."""

    blockers: list[str] = []
    route = RUNTIME_ROUTE_REGISTRY.get(pack.route_name)
    if route is None:
        blockers.append("unknown_runtime_route")
    elif not is_promoted_specialist_route(pack.route_name):
        blockers.append("route_not_promoted_for_governed_eval")
    route_payload = route_metadata_payload(pack.route_name)
    if set(pack.canonical_domain_refs) != set(route_payload["canonical_domain_refs"]):
        blockers.append("pack_domain_refs_do_not_match_route")
    if pack.workflow_profile != route_payload["workflow_profile"]:
        blockers.append("pack_workflow_does_not_match_route")
    if pack.specialist_type != route_payload["linked_specialist_type"]:
        blockers.append("pack_specialist_does_not_match_route")
    if fullmatch(_SEMVER_PATTERN, str(pack.version or "")) is None:
        blockers.append("invalid_pack_version")
    if not 0.0 < pack.minimum_pass_rate <= 1.0:
        blockers.append("invalid_minimum_pass_rate")
    if not pack.offline_only:
        blockers.append("external_network_eval_not_allowed")
    if not pack.human_review_required:
        blockers.append("human_review_not_required")
    if pack.automatic_promotion_allowed:
        blockers.append("automatic_promotion_requested")
    if pack.core_mutation_allowed:
        blockers.append("core_mutation_requested")
    if not pack.evidence_refs:
        blockers.append("missing_pack_evidence_refs")
    if not pack.cases:
        blockers.append("missing_eval_cases")
    if len(pack.cases) > _MAX_CASES:
        blockers.append("too_many_eval_cases")

    case_ids = [case.case_id for case in pack.cases]
    if len(case_ids) != len(set(case_ids)):
        blockers.append("duplicate_case_id")
    for case in pack.cases:
        blockers.extend(_validate_case(pack, case))
    return sorted(set(blockers))


def run_domain_eval_pack(
    *,
    pack_path: Path | str = DEFAULT_DOMAIN_EVAL_PACK_PATH,
    profile: str = "development",
    workdir: Path,
    run_id: str | None = None,
    generated_at: str | None = None,
) -> DomainEvalRunContract:
    """Execute a domain pack through the real governed core using local services only."""

    pack = load_domain_eval_pack(pack_path)
    resolved_run_id = run_id or f"domain-eval-{uuid4().hex[:8]}"
    resolved_generated_at = generated_at or datetime.now(UTC).isoformat()
    blockers = validate_domain_eval_pack(pack)
    if blockers:
        return ObservabilityService.build_domain_eval_run(
            run_id=resolved_run_id,
            eval_pack_id=pack.eval_pack_id,
            pack_version=pack.version,
            route_name=pack.route_name,
            case_results=[],
            minimum_pass_rate=pack.minimum_pass_rate,
            evidence_refs=pack.evidence_refs,
            generated_at=resolved_generated_at,
            blockers=blockers,
        )

    orchestrator = build_orchestrator(profile, workdir)
    results = [
        _execute_case(orchestrator, pack, case, resolved_run_id) for case in pack.cases
    ]
    return orchestrator.observability_service.build_domain_eval_run(
        run_id=resolved_run_id,
        eval_pack_id=pack.eval_pack_id,
        pack_version=pack.version,
        route_name=pack.route_name,
        case_results=results,
        minimum_pass_rate=pack.minimum_pass_rate,
        evidence_refs=[*pack.evidence_refs, f"domain-eval-run://{resolved_run_id}"],
        generated_at=resolved_generated_at,
    )


def _validate_case(pack: DomainEvalPackContract, case: DomainEvalCaseContract) -> list[str]:
    blockers: list[str] = []
    prefix = f"case:{case.case_id}:"
    if fullmatch(_ID_PATTERN, case.case_id or "") is None:
        blockers.append(prefix + "invalid_case_id")
    if not case.input_text or len(case.input_text) > _MAX_INPUT_LENGTH:
        blockers.append(prefix + "invalid_input_length")
    if case.expected_route != pack.route_name:
        blockers.append(prefix + "route_mismatch")
    if not set(case.expected_canonical_domain_refs).issubset(pack.canonical_domain_refs):
        blockers.append(prefix + "domain_refs_outside_pack")
    if case.expected_workflow_profile != pack.workflow_profile:
        blockers.append(prefix + "workflow_mismatch")
    if case.expected_specialist_type != pack.specialist_type:
        blockers.append(prefix + "specialist_mismatch")
    required_lists = {
        "memory_statuses": case.allowed_memory_causality_statuses,
        "response_fragments": case.required_response_fragments,
        "required_events": case.required_events,
    }
    for label, values in required_lists.items():
        if not _clean(values):
            blockers.append(prefix + f"missing_{label}")
        if len(values) > _MAX_LIST_ITEMS:
            blockers.append(prefix + f"too_many_{label}")
    if case.minimum_response_length < 1 or case.minimum_response_length > 20_000:
        blockers.append(prefix + "invalid_minimum_response_length")
    return blockers


def _execute_case(orchestrator, pack, case, run_id):  # type: ignore[no-untyped-def]
    request_id = f"req-{run_id}-{case.case_id}"
    try:
        response = orchestrator.handle_input(
            InputContract(
                request_id=RequestId(request_id),
                session_id=SessionId(f"sess-{case.session_key}"),
                mission_id=MissionId(case.mission_key) if case.mission_key else None,
                channel=ChannelType.CHAT,
                input_type=InputType.TEXT,
                content=case.input_text,
                timestamp="2026-07-16T00:00:00Z",
                metadata={
                    "domain_eval_pack_id": pack.eval_pack_id,
                    "domain_eval_case_id": case.case_id,
                    "domain_eval_offline_only": True,
                },
            )
        )
        audit = orchestrator.observability_service.audit_flow(
            ObservabilityQuery(request_id=request_id, limit=100)
        )
    except Exception as exc:  # pragma: no cover - defensive boundary
        return DomainEvalCaseResultContract(
            eval_pack_id=pack.eval_pack_id,
            case_id=case.case_id,
            passed=False,
            checks={"execution": False},
            failures=[f"execution_error:{type(exc).__name__}"],
            observed_governance_decision=None,
            observed_route=None,
            observed_canonical_domain_refs=[],
            observed_workflow_profile=None,
            observed_specialist_types=[],
            observed_memory_causality_status="unavailable",
            response_evidence=[],
            response_length=0,
            observed_events=[],
        )

    observed_decision = response.governance_decision.decision.value
    observed_route = audit.workflow_domain_route or response.deliberative_plan.primary_route
    observed_workflow = (
        audit.workflow_profile or response.deliberative_plan.route_workflow_profile
    )
    observed_domains = sorted(set(audit.registry_domains))
    observed_specialists = sorted(
        {
            *audit.domain_specialists,
            *(item.specialist_type for item in response.specialist_invocations),
        }
    )
    normalized_response = response.response_text.casefold()
    response_evidence = [
        fragment
        for fragment in case.required_response_fragments
        if fragment.casefold() in normalized_response
    ]
    checks = {
        "governance_decision": (
            observed_decision == case.expected_decision
        ),
        "route": observed_route == case.expected_route,
        "canonical_domains": set(case.expected_canonical_domain_refs).issubset(observed_domains),
        "workflow": observed_workflow == case.expected_workflow_profile,
        "specialist": case.expected_specialist_type in observed_specialists,
        "response": (
            len(response.response_text) >= case.minimum_response_length
            and len(response_evidence) == len(case.required_response_fragments)
        ),
        "memory": audit.memory_causality_status in case.allowed_memory_causality_statuses,
        "required_events": set(case.required_events).issubset(audit.event_names),
        "trace": audit.trace_complete,
    }
    failures = [f"{name}_mismatch" for name, passed in checks.items() if not passed]
    return DomainEvalCaseResultContract(
        eval_pack_id=pack.eval_pack_id,
        case_id=case.case_id,
        passed=not failures,
        checks=checks,
        failures=failures,
        observed_governance_decision=observed_decision,
        observed_route=observed_route,
        observed_canonical_domain_refs=observed_domains,
        observed_workflow_profile=observed_workflow,
        observed_specialist_types=observed_specialists,
        observed_memory_causality_status=audit.memory_causality_status,
        response_evidence=response_evidence,
        response_length=len(response.response_text),
        observed_events=list(audit.event_names),
    )


def _clean(values: Iterable[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]
