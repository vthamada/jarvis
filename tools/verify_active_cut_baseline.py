"""Verify the release-grade baseline of the active v2 cut."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path

from shared.domain_registry import PROMOTED_SPECIALIST_ROUTES, RUNTIME_ROUTE_REGISTRY
from tools.archive.render_governed_benchmark_matrix import build_payload as build_benchmark_payload

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


def build_payload() -> dict[str, object]:
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
    )
    decision = "baseline_release_ready"
    if any(
        value > 0
        for value in (
            summary.active_routes_missing_workflows,
            summary.promoted_routes_missing_consumer_contract,
            summary.promoted_routes_missing_specialist_contract,
        )
    ) or summary.benchmark_now_candidates == 0 or summary.promotion_trigger_rules < 5:
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
