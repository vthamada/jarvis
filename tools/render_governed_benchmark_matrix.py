"""Render the governed benchmark matrix for the active v2 cut."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps, loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = (
    ROOT / "tools" / "benchmarks" / "datasets" / "v2_governed_benchmark_candidates.json"
)
DEFAULT_JSON_OUTPUT = (
    ROOT / ".jarvis_runtime" / "governed_benchmarks" / "v2_governed_benchmark_matrix.json"
)
DEFAULT_DOC_OUTPUT = ROOT / "docs" / "implementation" / "v2-governed-benchmark-matrix.md"


@dataclass(frozen=True)
class BenchmarkCandidate:
    technology_id: str
    display_name: str
    cut_disposition: str
    expected_outcome: str
    why_it_matters: str
    benchmark_scope: str
    promotion_blocker: str


@dataclass(frozen=True)
class BenchmarkFamily:
    family_id: str
    title: str
    jarvis_gap: str
    goal: str
    candidates: list[BenchmarkCandidate]


@dataclass(frozen=True)
class GovernedBenchmarkMatrix:
    cut_id: str
    sprint_id: str
    families: list[BenchmarkFamily]


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render the governed benchmark matrix for the active v2 cut."
    )
    parser.add_argument(
        "--dataset-path",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to the governed benchmark candidate dataset.",
    )
    parser.add_argument(
        "--json-output",
        default=str(DEFAULT_JSON_OUTPUT),
        help="Path to the generated JSON artifact.",
    )
    parser.add_argument(
        "--doc-output",
        default=str(DEFAULT_DOC_OUTPUT),
        help="Path to the generated Markdown document.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    target = Path(value)
    return target if target.is_absolute() else ROOT / target


def load_matrix(dataset_path: str | Path = DEFAULT_DATASET_PATH) -> GovernedBenchmarkMatrix:
    path = _resolve_path(str(dataset_path))
    payload = loads(path.read_text(encoding="utf-8"))
    families: list[BenchmarkFamily] = []
    for item in payload["families"]:
        families.append(
            BenchmarkFamily(
                family_id=item["family_id"],
                title=item["title"],
                jarvis_gap=item["jarvis_gap"],
                goal=item["goal"],
                candidates=[BenchmarkCandidate(**candidate) for candidate in item["candidates"]],
            )
        )
    return GovernedBenchmarkMatrix(
        cut_id=payload["cut_id"],
        sprint_id=payload["sprint_id"],
        families=families,
    )


def build_payload(dataset_path: str | Path = DEFAULT_DATASET_PATH) -> dict[str, object]:
    matrix = load_matrix(dataset_path)
    family_summaries: list[dict[str, object]] = []
    candidate_totals = {
        "benchmark_now": 0,
        "reference_envelope": 0,
        "defer_outside_cut": 0,
    }
    active_candidates: list[str] = []

    for family in matrix.families:
        dispositions = {key: 0 for key in candidate_totals}
        candidates: list[dict[str, object]] = []
        for candidate in family.candidates:
            dispositions[candidate.cut_disposition] = (
                dispositions.get(candidate.cut_disposition, 0) + 1
            )
            candidate_totals[candidate.cut_disposition] = (
                candidate_totals.get(candidate.cut_disposition, 0) + 1
            )
            if candidate.cut_disposition == "benchmark_now":
                active_candidates.append(candidate.display_name)
            candidates.append(asdict(candidate))
        family_summaries.append(
            {
                "family_id": family.family_id,
                "title": family.title,
                "jarvis_gap": family.jarvis_gap,
                "goal": family.goal,
                "dispositions": dispositions,
                "candidates": candidates,
            }
        )

    return {
        "cut_id": matrix.cut_id,
        "sprint_id": matrix.sprint_id,
        "decision": "complete_sprint_3_governed_benchmarks",
        "rules": {
            "core_rule": "nenhuma tecnologia externa entra no nucleo por benchmark isolado",
            "active_cut_rule": (
                "benchmark_now significa comparar recorte governado "
                "sem promocao direta"
            ),
            "reference_rule": (
                "reference_envelope significa tecnologia util para contraste, "
                "nao para entrada imediata"
            ),
        },
        "candidate_totals": candidate_totals,
        "active_benchmark_candidates": active_candidates,
        "promotion_trigger_rules": [
            (
                "a lacuna do JARVIS precisa estar comprovada no corte ativo, "
                "sem workaround excessivo no baseline"
            ),
            (
                "o benchmark ou experimento precisa mostrar ganho real "
                "contra o baseline atual"
            ),
            (
                "o ganho precisa vir sem romper domain_registry, memory_registry, "
                "mind_registry, governanca final ou sintese soberana"
            ),
            "a absorcao precisa caber no menor recorte util e reversivel",
            (
                "HANDOFF.md e o documento do corte precisam passar a tratar "
                "a tecnologia como candidata de absorcao da fase"
            ),
        ],
        "family_summaries": family_summaries,
        "decision_rationale": (
            "a sprint 3 fecha o envelope de benchmark governado do corte ativo. "
            "AutoGPT Platform, Mastra e Mem0 entram como benchmarks pequenos e controlados; "
            "LangGraph, OpenAI Agents SDK, CrewAI, Microsoft Agent Framework, "
            "OpenClaw, Hermes Agent, Manus, Letta/MemGPT, Zep e Graphiti ficam "
            "no envelope comparativo, sem promocao oportunista."
        ),
    }


def render_text(payload: dict[str, object]) -> str:
    lines = [
        f"cut_id={payload['cut_id']}",
        f"sprint_id={payload['sprint_id']}",
        f"decision={payload['decision']}",
        "active=" + ",".join(payload["active_benchmark_candidates"]),
    ]
    for family in payload["family_summaries"]:
        dispositions = family["dispositions"]
        lines.append(
            "family="
            f"{family['family_id']} "
            f"benchmark_now={dispositions.get('benchmark_now', 0)} "
            f"reference_envelope={dispositions.get('reference_envelope', 0)} "
            f"defer_outside_cut={dispositions.get('defer_outside_cut', 0)}"
        )
    return "\n".join(lines)


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# V2 Governed Benchmark Matrix",
        "",
        f"- corte: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- decisao: `{payload['decision']}`",
        "",
        "## Regras do benchmark governado",
        "",
        f"- regra central: {payload['rules']['core_rule']}",
        f"- regra do corte ativo: {payload['rules']['active_cut_rule']}",
        f"- regra do envelope comparativo: {payload['rules']['reference_rule']}",
        "",
        "## Candidatas em benchmark agora",
        "",
    ]
    for item in payload["active_benchmark_candidates"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Quando `absorver_depois` pode subir", ""])
    for item in payload["promotion_trigger_rules"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Familias", ""])

    for family in payload["family_summaries"]:
        lines.extend(
            [
                f"### {family['title']}",
                "",
                f"- lacuna do JARVIS: {family['jarvis_gap']}",
                f"- objetivo do benchmark: {family['goal']}",
                (
                    "- distribuicao: "
                    f"benchmark_now=`{family['dispositions'].get('benchmark_now', 0)}`, "
                    f"reference_envelope=`{family['dispositions'].get('reference_envelope', 0)}`, "
                    f"defer_outside_cut=`{family['dispositions'].get('defer_outside_cut', 0)}`"
                ),
                "",
            ]
        )
        for candidate in family["candidates"]:
            lines.extend(
                [
                    f"- `{candidate['display_name']}`",
                    (
                        f"  disposition: `{candidate['cut_disposition']}`; "
                        f"expected_outcome: `{candidate['expected_outcome']}`"
                    ),
                    f"  why_it_matters: {candidate['why_it_matters']}",
                    f"  benchmark_scope: {candidate['benchmark_scope']}",
                    f"  promotion_blocker: {candidate['promotion_blocker']}",
                ]
            )
        lines.append("")

    lines.extend(["## Racional", "", payload["decision_rationale"], ""])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = build_payload(args.dataset_path)

    json_output = _resolve_path(args.json_output)
    doc_output = _resolve_path(args.doc_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    doc_output.parent.mkdir(parents=True, exist_ok=True)

    json_output.write_text(dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc_output.write_text(render_markdown(payload), encoding="utf-8")

    if args.format == "json":
        print(dumps(payload, ensure_ascii=False, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
