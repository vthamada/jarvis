"""Close the v2 domain consumers and workflows cut with regenerable evidence."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path

from tools.verify_active_cut_baseline import build_payload as build_baseline_payload

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_domain_consumers_and_workflows_cut"


@dataclass(frozen=True)
class BacklogDecision:
    item_id: str
    title: str
    target_class: str
    rationale: str
    dependency: str


@dataclass(frozen=True)
class CutEvidenceSummary:
    active_routes: int
    active_routes_with_workflows: int
    promoted_routes: int
    promoted_routes_with_consumer_contract: int
    promoted_routes_with_specialist_contract: int
    benchmark_now_candidates: int
    reference_envelope_candidates: int
    promotion_trigger_rules: int
    baseline_decision: str


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Close the v2 domain consumers and workflows cut."
    )
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


def next_cut_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="v2-workflow-orchestration-benchmark-execution",
            title="execucao sandbox de benchmarks de workflow orchestration",
            target_class="proximo_corte_v2",
            rationale=(
                "o baseline atual ja estabilizou contratos, consumidores e workflows; "
                "o proximo passo correto e comparar `Mastra` contra o envelope atual sem "
                "reabrir o nucleo soberano."
            ),
            dependency="baseline release-grade e matriz governada de benchmark ja fechados",
        ),
        BacklogDecision(
            item_id="v2-continuous-operational-agent-benchmarks",
            title="execucao sandbox de benchmarks de agentes operacionais continuos",
            target_class="proximo_corte_v2",
            rationale=(
                "`AutoGPT Platform` so deve subir ou cair por evidencia de sandbox ligada a "
                "triggers, blocos e automacao continua acima do runtime atual."
            ),
            dependency="workflows compostos auditaveis e comparacao protegida por axis gates",
        ),
        BacklogDecision(
            item_id="v2-multilayer-memory-benchmark-execution",
            title="execucao sandbox de benchmarks de memoria multicamada",
            target_class="proximo_corte_v2",
            rationale=(
                "`Mem0` e o envelope `Letta / MemGPT`, `Zep` e `Graphiti` precisam ser "
                "avaliados sobre lacunas reais de memoria, e nao por apelo abstrato."
            ),
            dependency="memoria canonica atual preservada e benchmark_now ja definido",
        ),
        BacklogDecision(
            item_id="v2-absorption-decision-gates",
            title="decisao formal de absorcao, referencia ou rejeicao por tecnologia",
            target_class="proximo_corte_v2",
            rationale=(
                "o proximo recorte deve fechar cada benchmark_now com saida disciplinada: "
                "`usar como referencia`, `absorver depois` ou `rejeitar`."
            ),
            dependency="evidencia comparativa gerada por sandbox e release gate preservado",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-direct-promotion-to-core",
            title="promocao direta de benchmark para o nucleo",
            target_class="manter_deferido",
            rationale=(
                "o baseline ficou forte exatamente por nao promover tecnologia externa sem "
                "recorte minimo e evidencia suficiente."
            ),
            dependency="ciclo posterior com evidencia clara de absorcao",
        ),
        BacklogDecision(
            item_id="defer-broad-computer-use-and-voice",
            title="computer use amplo, voz e realtime como superficie principal",
            target_class="manter_deferido",
            rationale=(
                "essas superficies continuam fora da lacuna principal enquanto o programa "
                "ainda consolida benchmark governado e memoria multicamada."
            ),
            dependency="runtime operacional mais maduro e governanca ampliada",
        ),
        BacklogDecision(
            item_id="defer-memory-foundation-replacement",
            title="substituicao da memoria canonica por framework externo",
            target_class="manter_deferido",
            rationale=(
                "o proximo recorte compara capacidades, nao substitui a fundacao soberana "
                "de memoria do sistema."
            ),
            dependency="evidencia de ganho estrutural muito superior ao baseline atual",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-governed-technology-absorption-layer",
            title="camada formal de absorcao tecnologica governada",
            target_class="preservar_como_visao",
            rationale=(
                "a direcao correta continua sendo um JARVIS capaz de estudar, comparar e "
                "absorver tecnologia por recorte, sem terceirizar o cerebro do sistema."
            ),
            dependency="mais de um recorte fechado de benchmark com saida disciplinada",
        ),
        BacklogDecision(
            item_id="vision-robust-absorbing-ecosystem",
            title="ecossistema robusto capaz de absorver o melhor do estado da arte",
            target_class="preservar_como_visao",
            rationale=(
                "essa visao segue valida, mas precisa continuar subordinada a soberania, "
                "gates de eixo e experimentacao reversivel."
            ),
            dependency="camada de benchmark governado transformada em capacidade permanente",
        ),
    ]


def build_payload() -> dict[str, object]:
    baseline_payload = build_baseline_payload()
    summary = baseline_payload["summary"]
    evidence = CutEvidenceSummary(
        active_routes=int(summary["active_routes"]),
        active_routes_with_workflows=int(summary["active_routes_with_workflows"]),
        promoted_routes=int(summary["promoted_routes"]),
        promoted_routes_with_consumer_contract=int(
            summary["promoted_routes_with_consumer_contract"]
        ),
        promoted_routes_with_specialist_contract=int(
            summary["promoted_routes_with_specialist_contract"]
        ),
        benchmark_now_candidates=int(summary["benchmark_now_candidates"]),
        reference_envelope_candidates=int(summary["reference_envelope_candidates"]),
        promotion_trigger_rules=int(summary["promotion_trigger_rules"]),
        baseline_decision=str(baseline_payload["decision"]),
    )
    decision = "complete_v2_domain_consumers_and_workflows_cut"
    if evidence.baseline_decision != "baseline_release_ready":
        decision = "hold_v2_domain_consumers_and_workflows_cut"

    return {
        "cut_id": "v2-domain-consumers-and-workflows-cut",
        "decision": decision,
        "next_cut_recommendation": "v2-governed-benchmark-execution-cut",
        "evidence_summary": asdict(evidence),
        "next_cut_scope": [asdict(item) for item in next_cut_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            (
                "rotas promovidas passaram a carregar consumidores canonicos "
                "acima do guided atual"
            ),
            (
                "workflows compostos passaram a operar com checkpoints, decisao "
                "e observabilidade auditavel"
            ),
            "benchmark governado virou artefato regeneravel em vez de pesquisa solta",
            (
                "o baseline do corte passou a ser verificavel em modo release-grade "
                "antes de qualquer proximo recorte"
            ),
        ],
        "decision_rationale": (
            "o corte cumpriu o objetivo de transformar consumidores canonicos, workflows "
            "operacionais e benchmark governado em baseline coerente. o proximo passo nao "
            "e criar mais runtime local neste mesmo corte, mas executar benchmarks sandbox "
            "sobre o envelope ja definido e classificar cada tecnologia por evidencia."
        ),
    }


def render_text(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    return "\n".join(
        [
            f"cut_id={payload['cut_id']}",
            f"decision={payload['decision']}",
            f"next_cut_recommendation={payload['next_cut_recommendation']}",
            (
                "baseline="
                f"decision={evidence['baseline_decision']} "
                f"active_routes={evidence['active_routes']} "
                f"workflow_ready={evidence['active_routes_with_workflows']} "
                f"promoted_routes={evidence['promoted_routes']}"
            ),
            (
                "benchmarks="
                f"benchmark_now={evidence['benchmark_now_candidates']} "
                f"reference_envelope={evidence['reference_envelope_candidates']} "
                f"promotion_rules={evidence['promotion_trigger_rules']}"
            ),
        ]
    )


def render_markdown(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        "# Fechamento do V2 Domain Consumers and Workflows Cut",
        "",
        f"- corte: `{payload['cut_id']}`",
        f"- decisao: `{payload['decision']}`",
        f"- proximo recorte recomendado: `{payload['next_cut_recommendation']}`",
        "",
        "## Evidencia consolidada",
        "",
        f"- baseline decision: `{evidence['baseline_decision']}`",
        f"- active routes: `{evidence['active_routes']}`",
        f"- active routes with workflows: `{evidence['active_routes_with_workflows']}`",
        f"- promoted routes: `{evidence['promoted_routes']}`",
        (
            "- promoted routes with consumer contract: "
            f"`{evidence['promoted_routes_with_consumer_contract']}`"
        ),
        (
            "- promoted routes with specialist contract: "
            f"`{evidence['promoted_routes_with_specialist_contract']}`"
        ),
        f"- benchmark_now candidates: `{evidence['benchmark_now_candidates']}`",
        (
            "- reference_envelope candidates: "
            f"`{evidence['reference_envelope_candidates']}`"
        ),
        f"- promotion trigger rules: `{evidence['promotion_trigger_rules']}`",
        "",
        "## Metas atendidas",
        "",
    ]
    for item in payload["goals_met"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Entra no proximo recorte do v2", ""])
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
