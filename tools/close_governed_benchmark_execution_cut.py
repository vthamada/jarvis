"""Close the v2 governed benchmark execution cut with regenerable evidence."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from collections import Counter
from dataclasses import asdict, dataclass
from json import dumps, loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_governed_benchmark_execution_cut"
DECISIONS_DATASET = (
    ROOT / "tools" / "benchmarks" / "datasets" / "v2_governed_benchmark_decisions.json"
)


@dataclass(frozen=True)
class BacklogDecision:
    item_id: str
    title: str
    target_class: str
    rationale: str
    dependency: str


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the v2 governed benchmark execution cut.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the cut-closure artifacts will be written.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def load_decisions() -> list[dict[str, object]]:
    dataset = loads(DECISIONS_DATASET.read_text(encoding="utf-8"))
    return list(dataset["decisions"])


def next_cut_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="v2-memory-gap-evidence-cut",
            title="recorte de evidencia para lacunas reais de memoria multicamada",
            target_class="proximo_corte_recomendado",
            rationale=(
                "Mem0 foi a unica tecnologia classificada como `absorver_depois`, entao o "
                "proximo recorte so faz sentido se provar antes a lacuna real do baseline atual."
            ),
            dependency=(
                "memory-service atual estabilizado e sinais de reabertura "
                "realmente presentes"
            ),
        ),
        BacklogDecision(
            item_id="v2-native-memory-gap-measurement",
            title="medicao explicita de limites da modelagem atual de memoria",
            target_class="proximo_corte_recomendado",
            rationale=(
                "antes de absorver qualquer camada externa, o JARVIS precisa demonstrar onde a "
                "separacao entre conversa, sessao, usuario e memoria compartilhada ja nao basta."
            ),
            dependency=(
                "evidencia de carga, consumo canonico e recuperacao insuficiente "
                "no baseline"
            ),
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-mastra-adoption",
            title="adocao de Mastra no runtime principal",
            target_class="manter_deferido",
            rationale=(
                "Mastra ficou como `usar_como_referencia`; o ganho atual e orientar workflow, nao "
                "justificar dependencia central nova."
            ),
            dependency="lacuna comprovada de suspend/resume e checkpoints acima do baseline atual",
        ),
        BacklogDecision(
            item_id="defer-autogpt-operational-layer",
            title="promocao de AutoGPT Platform como camada operacional oficial",
            target_class="manter_deferido",
            rationale=(
                "AutoGPT Platform ainda serve melhor como referencia de blocos, "
                "triggers e webhooks do que como parte do baseline atual."
            ),
            dependency="abertura formal de uma camada canonica de automacao continua",
        ),
        BacklogDecision(
            item_id="defer-direct-external-core-promotion",
            title="promocao direta de tecnologia externa para o nucleo",
            target_class="manter_deferido",
            rationale=(
                "o corte fechou justamente para evitar que benchmark governado vire absorcao "
                "oportunista sem evidencias suficientes."
            ),
            dependency="novo recorte formalmente aberto e sinais de reabertura satisfeitos",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-governed-technology-absorption-capability",
            title="capacidade permanente de absorcao tecnologica governada",
            target_class="preservar_como_visao",
            rationale=(
                "o benchmark governado deve evoluir para capacidade institucional do JARVIS, nao "
                "para experimentacao solta."
            ),
            dependency="mais de um ciclo fechado com evidencia comparativa e decisoes consistentes",
        )
    ]


def build_payload() -> dict[str, object]:
    decisions = load_decisions()
    counts = Counter(str(item["final_decision"]) for item in decisions)
    return {
        "cut_id": "v2-governed-benchmark-execution-cut",
        "decision": "complete_v2_governed_benchmark_execution_cut",
        "next_cut_recommendation": "v2-memory-gap-evidence-cut",
        "decision_summary": {
            "benchmark_now_count": len(decisions),
            "usar_como_referencia": counts.get("usar_como_referencia", 0),
            "absorver_depois": counts.get("absorver_depois", 0),
            "rejeitar": counts.get("rejeitar", 0),
        },
        "next_cut_scope": [asdict(item) for item in next_cut_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            "benchmark_now virou plano, scenario specs e decisao formal regeneravel",
            "Mastra e AutoGPT Platform ficaram formalmente retidos como referencia",
            "Mem0 ficou formalmente classificada como absorcao futura condicionada",
            "o corte terminou sem abrir dependencia central nova no nucleo",
        ],
        "decision_rationale": (
            "o recorte cumpriu seu papel de transformar benchmark governado em "
            "decisao disciplinada. o unico candidato de reabertura futura imediata "
            "e `Mem0`, mas apenas se um recorte posterior provar a lacuna real do "
            "baseline atual de memoria multicamada."
        ),
    }


def render_text(payload: dict[str, object]) -> str:
    summary = payload["decision_summary"]
    return "\n".join(
        [
            f"cut_id={payload['cut_id']}",
            f"decision={payload['decision']}",
            f"next_cut_recommendation={payload['next_cut_recommendation']}",
            (
                "decisions="
                f"benchmark_now={summary['benchmark_now_count']} "
                f"usar_como_referencia={summary['usar_como_referencia']} "
                f"absorver_depois={summary['absorver_depois']} "
                f"rejeitar={summary['rejeitar']}"
            ),
        ]
    )


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["decision_summary"]
    lines = [
        "# Fechamento do V2 Governed Benchmark Execution Cut",
        "",
        f"- corte: `{payload['cut_id']}`",
        f"- decisao: `{payload['decision']}`",
        f"- proximo recorte recomendado: `{payload['next_cut_recommendation']}`",
        "",
        "## Evidencia consolidada",
        "",
        f"- benchmark_now_count: `{summary['benchmark_now_count']}`",
        f"- usar_como_referencia: `{summary['usar_como_referencia']}`",
        f"- absorver_depois: `{summary['absorver_depois']}`",
        f"- rejeitar: `{summary['rejeitar']}`",
        "",
        "## Metas atendidas",
        "",
    ]
    for item in payload["goals_met"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Entra no proximo recorte recomendado", ""])
    for item in payload["next_cut_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependencia: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(["", "## Fica fora do recorte imediato", ""])
    for item in payload["deferred_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependencia: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(["", "## Preservar como visao", ""])
    for item in payload["vision_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependencia: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(["", "## Racional da decisao", "", payload["decision_rationale"], ""])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    (output_dir / "cut_closure.json").write_text(
        dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "cut_closure.md").write_text(
        render_markdown(payload) + "\n",
        encoding="utf-8",
    )
    if args.format == "json":
        print(dumps(payload, ensure_ascii=False, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
