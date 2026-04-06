"""Verify the release-grade baseline of the active v2 cut."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path

from shared.domain_registry import PROMOTED_SPECIALIST_ROUTES, RUNTIME_ROUTE_REGISTRY
from tools.archive.render_governed_benchmark_matrix import build_payload as build_benchmark_payload
from tools.internal_pilot_support import (
    PilotExecutionResult,
    default_pilot_scenarios,
    run_pilot_scenarios,
    runtime_dir,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_domain_consumers_and_workflows_cut"


@dataclass(frozen=True)
class ActiveCutBaselineSummary:
    active_routes: int
    active_routes_with_workflows: int
    active_routes_missing_workflows: int
    promoted_routes: int
    promoted_routes_with_consumer_contract: int
    promoted_routes_missing_consumer_contract: int
    promoted_routes_with_specialist_contract: int
    promoted_routes_missing_specialist_contract: int
    benchmark_now_candidates: int
    reference_envelope_candidates: int
    promotion_trigger_rules: int
    targeted_pilot_scenarios: int
    targeted_route_expectations: int
    targeted_route_matches: int
    targeted_workflow_expectations: int
    targeted_workflow_matches: int
    promoted_routes_covered_by_pilot: int
    promoted_routes_missing_pilot_coverage: int
    promoted_workflow_profiles_covered_by_pilot: int
    promoted_workflow_profiles_missing_pilot_coverage: int
    memory_causality_target_scenarios: int
    memory_causality_ready_scenarios: int
    mind_domain_specialist_target_scenarios: int
    mind_domain_specialist_ready_scenarios: int
    dominant_tension_target_scenarios: int
    dominant_tension_ready_scenarios: int
    cognitive_recomposition_target_scenarios: int
    cognitive_recomposition_ready_scenarios: int
    specialist_subflow_target_scenarios: int
    specialist_subflow_ready_scenarios: int
    mission_runtime_state_target_scenarios: int
    mission_runtime_state_ready_scenarios: int


def _promoted_workflow_profiles() -> set[str]:
    return {
        entry.workflow_profile
        for route_name, entry in RUNTIME_ROUTE_REGISTRY.items()
        if route_name in PROMOTED_SPECIALIST_ROUTES and entry.workflow_profile
    }


def _collect_targeted_pilot_results() -> list[PilotExecutionResult]:
    scenarios = [
        scenario
        for scenario in default_pilot_scenarios()
        if (
            scenario.expected_route is not None
            or scenario.expected_workflow_profile is not None
            or scenario.coverage_tags
        )
    ]
    return run_pilot_scenarios(
        profile="development",
        workdir=runtime_dir("active-cut-baseline"),
        scenarios=scenarios,
        path_name="baseline",
    )


def _build_targeted_pilot_summary(
    pilot_results: list[PilotExecutionResult],
) -> tuple[dict[str, object], list[str]]:
    promoted_routes = set(PROMOTED_SPECIALIST_ROUTES)
    promoted_workflow_profiles = _promoted_workflow_profiles()
    route_expectations = [item for item in pilot_results if item.expected_route is not None]
    workflow_expectations = [
        item for item in pilot_results if item.expected_workflow_profile is not None
    ]
    matched_routes = {
        item.expected_route
        for item in route_expectations
        if item.route_matches_expectation and item.expected_route is not None
    }
    matched_workflows = {
        item.expected_workflow_profile
        for item in workflow_expectations
        if (
            item.workflow_profile_matches_expectation
            and item.expected_workflow_profile is not None
        )
    }
    memory_causality_targets = [
        item for item in pilot_results if "memory_causality" in item.coverage_tags
    ]
    mind_domain_specialist_targets = [
        item for item in pilot_results if "mind_domain_specialist" in item.coverage_tags
    ]
    dominant_tension_targets = [
        item for item in pilot_results if "dominant_tension" in item.coverage_tags
    ]
    cognitive_recomposition_targets = [
        item for item in pilot_results if "cognitive_recomposition" in item.coverage_tags
    ]
    specialist_subflow_targets = [
        item for item in pilot_results if "specialist_subflow" in item.coverage_tags
    ]
    mission_runtime_state_targets = [
        item for item in pilot_results if "mission_runtime_state" in item.coverage_tags
    ]
    missing_routes = sorted(promoted_routes - matched_routes)
    missing_workflow_profiles = sorted(promoted_workflow_profiles - matched_workflows)
    return (
        {
            "targeted_pilot_scenarios": len(pilot_results),
            "targeted_route_expectations": len(route_expectations),
            "targeted_route_matches": sum(
                1 for item in route_expectations if item.route_matches_expectation
            ),
            "targeted_workflow_expectations": len(workflow_expectations),
            "targeted_workflow_matches": sum(
                1
                for item in workflow_expectations
                if item.workflow_profile_matches_expectation
            ),
            "promoted_routes_covered_by_pilot": len(matched_routes),
            "promoted_routes_missing_pilot_coverage": len(missing_routes),
            "promoted_workflow_profiles_covered_by_pilot": len(matched_workflows),
            "promoted_workflow_profiles_missing_pilot_coverage": len(
                missing_workflow_profiles
            ),
            "memory_causality_target_scenarios": len(memory_causality_targets),
            "memory_causality_ready_scenarios": sum(
                1
                for item in memory_causality_targets
                if item.memory_causality_status == "causal_guidance"
            ),
            "mind_domain_specialist_target_scenarios": len(
                mind_domain_specialist_targets
            ),
            "mind_domain_specialist_ready_scenarios": sum(
                1
                for item in mind_domain_specialist_targets
                if (
                    item.mind_domain_specialist_status == "aligned"
                    and item.primary_domain_driver is not None
                )
            ),
            "dominant_tension_target_scenarios": len(dominant_tension_targets),
            "dominant_tension_ready_scenarios": sum(
                1
                for item in dominant_tension_targets
                if item.dominant_tension is not None and item.arbitration_source is not None
            ),
            "cognitive_recomposition_target_scenarios": len(
                cognitive_recomposition_targets
            ),
            "cognitive_recomposition_ready_scenarios": sum(
                1
                for item in cognitive_recomposition_targets
                if (
                    item.cognitive_recomposition_applied
                    and item.cognitive_recomposition_reason is not None
                    and item.cognitive_recomposition_trigger is not None
                )
            ),
            "specialist_subflow_target_scenarios": len(specialist_subflow_targets),
            "specialist_subflow_ready_scenarios": sum(
                1
                for item in specialist_subflow_targets
                if item.specialist_subflow_status in {"healthy", "contained"}
            ),
            "mission_runtime_state_target_scenarios": len(mission_runtime_state_targets),
            "mission_runtime_state_ready_scenarios": sum(
                1
                for item in mission_runtime_state_targets
                if item.mission_runtime_state_status == "healthy"
            ),
        },
        [
            (
                "missing promoted routes in targeted pilot coverage: "
                f"{', '.join(missing_routes) if missing_routes else 'none'}"
            ),
            (
                "missing promoted workflow profiles in targeted pilot coverage: "
                f"{', '.join(missing_workflow_profiles) if missing_workflow_profiles else 'none'}"
            ),
        ],
    )


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Verify the active v2 domain consumers/workflows baseline."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the release-baseline artifacts will be written.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def build_payload(
    *,
    pilot_results: list[PilotExecutionResult] | None = None,
) -> dict[str, object]:
    active_routes = {
        name: entry
        for name, entry in RUNTIME_ROUTE_REGISTRY.items()
        if entry.maturity in {"active_registry", "active_specialist"}
    }
    active_routes_with_workflows = 0
    promoted_routes_with_consumer_contract = 0
    promoted_routes_with_specialist_contract = 0

    for route_name, entry in active_routes.items():
        if (
            entry.workflow_profile
            and entry.workflow_steps
            and entry.workflow_checkpoints
            and entry.workflow_decision_points
        ):
            active_routes_with_workflows += 1
        if route_name in PROMOTED_SPECIALIST_ROUTES:
            if (
                entry.consumer_profile
                and entry.consumer_objective
                and entry.expected_deliverables
                and entry.telemetry_focus
            ):
                promoted_routes_with_consumer_contract += 1
            if (
                entry.linked_specialist_type
                and entry.specialist_mode in {"guided", "active"}
            ):
                promoted_routes_with_specialist_contract += 1

    benchmark_payload = build_benchmark_payload()
    focused_pilot_results = (
        pilot_results if pilot_results is not None else _collect_targeted_pilot_results()
    )
    pilot_summary, pilot_notes = _build_targeted_pilot_summary(focused_pilot_results)
    candidate_totals = benchmark_payload["candidate_totals"]
    summary = ActiveCutBaselineSummary(
        active_routes=len(active_routes),
        active_routes_with_workflows=active_routes_with_workflows,
        active_routes_missing_workflows=len(active_routes) - active_routes_with_workflows,
        promoted_routes=len(PROMOTED_SPECIALIST_ROUTES),
        promoted_routes_with_consumer_contract=promoted_routes_with_consumer_contract,
        promoted_routes_missing_consumer_contract=(
            len(PROMOTED_SPECIALIST_ROUTES) - promoted_routes_with_consumer_contract
        ),
        promoted_routes_with_specialist_contract=promoted_routes_with_specialist_contract,
        promoted_routes_missing_specialist_contract=(
            len(PROMOTED_SPECIALIST_ROUTES) - promoted_routes_with_specialist_contract
        ),
        benchmark_now_candidates=int(candidate_totals["benchmark_now"]),
        reference_envelope_candidates=int(candidate_totals["reference_envelope"]),
        promotion_trigger_rules=len(benchmark_payload["promotion_trigger_rules"]),
        targeted_pilot_scenarios=int(pilot_summary["targeted_pilot_scenarios"]),
        targeted_route_expectations=int(pilot_summary["targeted_route_expectations"]),
        targeted_route_matches=int(pilot_summary["targeted_route_matches"]),
        targeted_workflow_expectations=int(
            pilot_summary["targeted_workflow_expectations"]
        ),
        targeted_workflow_matches=int(pilot_summary["targeted_workflow_matches"]),
        promoted_routes_covered_by_pilot=int(
            pilot_summary["promoted_routes_covered_by_pilot"]
        ),
        promoted_routes_missing_pilot_coverage=int(
            pilot_summary["promoted_routes_missing_pilot_coverage"]
        ),
        promoted_workflow_profiles_covered_by_pilot=int(
            pilot_summary["promoted_workflow_profiles_covered_by_pilot"]
        ),
        promoted_workflow_profiles_missing_pilot_coverage=int(
            pilot_summary["promoted_workflow_profiles_missing_pilot_coverage"]
        ),
        memory_causality_target_scenarios=int(
            pilot_summary["memory_causality_target_scenarios"]
        ),
        memory_causality_ready_scenarios=int(
            pilot_summary["memory_causality_ready_scenarios"]
        ),
        mind_domain_specialist_target_scenarios=int(
            pilot_summary["mind_domain_specialist_target_scenarios"]
        ),
        mind_domain_specialist_ready_scenarios=int(
            pilot_summary["mind_domain_specialist_ready_scenarios"]
        ),
        dominant_tension_target_scenarios=int(
            pilot_summary["dominant_tension_target_scenarios"]
        ),
        dominant_tension_ready_scenarios=int(
            pilot_summary["dominant_tension_ready_scenarios"]
        ),
        cognitive_recomposition_target_scenarios=int(
            pilot_summary["cognitive_recomposition_target_scenarios"]
        ),
        cognitive_recomposition_ready_scenarios=int(
            pilot_summary["cognitive_recomposition_ready_scenarios"]
        ),
        specialist_subflow_target_scenarios=int(
            pilot_summary["specialist_subflow_target_scenarios"]
        ),
        specialist_subflow_ready_scenarios=int(
            pilot_summary["specialist_subflow_ready_scenarios"]
        ),
        mission_runtime_state_target_scenarios=int(
            pilot_summary["mission_runtime_state_target_scenarios"]
        ),
        mission_runtime_state_ready_scenarios=int(
            pilot_summary["mission_runtime_state_ready_scenarios"]
        ),
    )
    decision = "baseline_release_ready"
    if any(
        value > 0
        for value in (
            summary.active_routes_missing_workflows,
            summary.promoted_routes_missing_consumer_contract,
            summary.promoted_routes_missing_specialist_contract,
            summary.promoted_routes_missing_pilot_coverage,
            summary.promoted_workflow_profiles_missing_pilot_coverage,
        )
    ) or (
        summary.benchmark_now_candidates == 0
        or summary.promotion_trigger_rules < 5
        or summary.memory_causality_ready_scenarios == 0
        or summary.mind_domain_specialist_ready_scenarios == 0
        or summary.dominant_tension_ready_scenarios == 0
        or summary.cognitive_recomposition_ready_scenarios == 0
        or summary.specialist_subflow_ready_scenarios == 0
        or summary.mission_runtime_state_ready_scenarios == 0
    ):
        decision = "baseline_requires_iteration"

    return {
        "cut_id": "v2-domain-consumers-and-workflows-cut",
        "decision": decision,
        "summary": asdict(summary),
        "notes": [
            (
                "todas as rotas runtime ativas precisam carregar workflow minimo "
                "para o baseline release-grade"
            ),
            (
                "todas as rotas promovidas precisam manter contrato de consumo "
                "e especialista coerentes"
            ),
            (
                "a matriz de benchmark governado precisa continuar presente "
                "com candidatas benchmark_now e regras de promocao"
            ),
            (
                "o piloto focado precisa cobrir todas as rotas promovidas e todos "
                "os workflow profiles promovidos"
            ),
            (
                "o baseline ativo precisa manter pelo menos um cenario deliberado "
                "de memoria causal e um de recomposicao cognitiva"
            ),
            (
                "o baseline ativo precisa manter pelo menos um cenario deliberado "
                "de alinhamento mente->dominio->especialista e um de tensao dominante"
            ),
            (
                "o baseline ativo precisa manter pelo menos um cenario deliberado "
                "de subfluxo explicito de especialistas e um de mission runtime state"
            ),
            *pilot_notes,
        ],
    }


def render_text(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    return "\n".join(
        [
            f"cut_id={payload['cut_id']}",
            f"decision={payload['decision']}",
            (
                "routes="
                f"active={summary['active_routes']} "
                f"workflow_ready={summary['active_routes_with_workflows']} "
                f"workflow_missing={summary['active_routes_missing_workflows']}"
            ),
            (
                "promoted="
                f"routes={summary['promoted_routes']} "
                f"consumer_ready={summary['promoted_routes_with_consumer_contract']} "
                f"consumer_missing={summary['promoted_routes_missing_consumer_contract']} "
                f"specialist_ready={summary['promoted_routes_with_specialist_contract']} "
                f"specialist_missing={summary['promoted_routes_missing_specialist_contract']}"
            ),
            (
                "benchmarks="
                f"benchmark_now={summary['benchmark_now_candidates']} "
                f"reference_envelope={summary['reference_envelope_candidates']} "
                f"promotion_rules={summary['promotion_trigger_rules']}"
            ),
            (
                "pilot="
                f"scenarios={summary['targeted_pilot_scenarios']} "
                f"route_matches={summary['targeted_route_matches']}/"
                f"{summary['targeted_route_expectations']} "
                f"workflow_matches={summary['targeted_workflow_matches']}/"
                f"{summary['targeted_workflow_expectations']}"
            ),
            (
                "signals="
                f"memory_causality_ready={summary['memory_causality_ready_scenarios']}/"
                f"{summary['memory_causality_target_scenarios']} "
                "mind_domain_specialist_ready="
                f"{summary['mind_domain_specialist_ready_scenarios']}/"
                f"{summary['mind_domain_specialist_target_scenarios']} "
                "dominant_tension_ready="
                f"{summary['dominant_tension_ready_scenarios']}/"
                f"{summary['dominant_tension_target_scenarios']} "
                "specialist_subflow_ready="
                f"{summary['specialist_subflow_ready_scenarios']}/"
                f"{summary['specialist_subflow_target_scenarios']} "
                "mission_runtime_state_ready="
                f"{summary['mission_runtime_state_ready_scenarios']}/"
                f"{summary['mission_runtime_state_target_scenarios']} "
                "cognitive_recomposition_ready="
                f"{summary['cognitive_recomposition_ready_scenarios']}/"
                f"{summary['cognitive_recomposition_target_scenarios']}"
            ),
        ]
    )


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        "# Active V2 Cut Release Baseline",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- decision: `{payload['decision']}`",
        "",
        "## Summary",
        "",
        f"- active routes: `{summary['active_routes']}`",
        f"- active routes with workflows: `{summary['active_routes_with_workflows']}`",
        f"- active routes missing workflows: `{summary['active_routes_missing_workflows']}`",
        f"- promoted routes: `{summary['promoted_routes']}`",
        (
            "- promoted routes with consumer contract: "
            f"`{summary['promoted_routes_with_consumer_contract']}`"
        ),
        (
            "- promoted routes missing consumer contract: "
            f"`{summary['promoted_routes_missing_consumer_contract']}`"
        ),
        (
            "- promoted routes with specialist contract: "
            f"`{summary['promoted_routes_with_specialist_contract']}`"
        ),
        (
            "- promoted routes missing specialist contract: "
            f"`{summary['promoted_routes_missing_specialist_contract']}`"
        ),
        f"- benchmark_now candidates: `{summary['benchmark_now_candidates']}`",
        (
            "- reference_envelope candidates: "
            f"`{summary['reference_envelope_candidates']}`"
        ),
        f"- promotion trigger rules: `{summary['promotion_trigger_rules']}`",
        f"- targeted pilot scenarios: `{summary['targeted_pilot_scenarios']}`",
        (
            "- targeted pilot route matches: "
            f"`{summary['targeted_route_matches']}`/"
            f"`{summary['targeted_route_expectations']}`"
        ),
        (
            "- targeted pilot workflow matches: "
            f"`{summary['targeted_workflow_matches']}`/"
            f"`{summary['targeted_workflow_expectations']}`"
        ),
        (
            "- promoted routes covered by pilot: "
            f"`{summary['promoted_routes_covered_by_pilot']}`"
        ),
        (
            "- promoted routes missing pilot coverage: "
            f"`{summary['promoted_routes_missing_pilot_coverage']}`"
        ),
        (
            "- promoted workflow profiles covered by pilot: "
            f"`{summary['promoted_workflow_profiles_covered_by_pilot']}`"
        ),
        (
            "- promoted workflow profiles missing pilot coverage: "
            f"`{summary['promoted_workflow_profiles_missing_pilot_coverage']}`"
        ),
        (
            "- memory causality scenarios ready: "
            f"`{summary['memory_causality_ready_scenarios']}`/"
            f"`{summary['memory_causality_target_scenarios']}`"
        ),
        (
            "- mind-domain-specialist scenarios ready: "
            f"`{summary['mind_domain_specialist_ready_scenarios']}`/"
            f"`{summary['mind_domain_specialist_target_scenarios']}`"
        ),
        (
            "- dominant tension scenarios ready: "
            f"`{summary['dominant_tension_ready_scenarios']}`/"
            f"`{summary['dominant_tension_target_scenarios']}`"
        ),
        (
            "- specialist subflow scenarios ready: "
            f"`{summary['specialist_subflow_ready_scenarios']}`/"
            f"`{summary['specialist_subflow_target_scenarios']}`"
        ),
        (
            "- mission runtime state scenarios ready: "
            f"`{summary['mission_runtime_state_ready_scenarios']}`/"
            f"`{summary['mission_runtime_state_target_scenarios']}`"
        ),
        (
            "- cognitive recomposition scenarios ready: "
            f"`{summary['cognitive_recomposition_ready_scenarios']}`/"
            f"`{summary['cognitive_recomposition_target_scenarios']}`"
        ),
        "",
        "## Notes",
        "",
    ]
    for note in payload["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = build_payload()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "release_baseline.json").write_text(
        dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "release_baseline.md").write_text(
        render_markdown(payload) + "\n",
        encoding="utf-8",
    )
    if args.format == "json":
        print(dumps(payload, ensure_ascii=False, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
