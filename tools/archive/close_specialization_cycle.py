"""Close the first specialization cycle and emit the master-oriented cut for v2."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps, loads
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIRS = [
    ROOT,
    ROOT / "services" / "observability-service" / "src",
    ROOT / "evolution" / "evolution-lab" / "src",
]

for src_dir in SRC_DIRS:
    sys_path.insert(0, str(src_dir))

from evolution_lab.service import EvolutionLabService
from observability_service.service import ObservabilityService


@dataclass(frozen=True)
class BacklogDecision:
    item_id: str
    title: str
    target_class: str
    rationale: str
    dependency: str


@dataclass(frozen=True)
class CycleEvidenceSummary:
    requests_audited: int
    healthy_requests: int
    incomplete_requests: int
    attention_required_requests: int
    domain_alignment_healthy: int
    domain_alignment_partial: int
    domain_alignment_incomplete: int
    domain_alignment_attention_required: int
    memory_alignment_healthy: int
    memory_alignment_partial: int
    memory_alignment_incomplete: int
    memory_alignment_attention_required: int
    sovereignty_healthy: int
    sovereignty_incomplete: int
    sovereignty_attention_required: int
    recent_evolution_proposals: int
    recent_evolution_decisions: int
    comparison_overall_verdict: str
    comparison_decision: str
    matched_scenarios: int
    divergent_scenarios: int
    baseline_axis_adherence_score: float
    candidate_axis_adherence_score: float
    candidate_runtime_coverage: float


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the first specialization cycle.")
    parser.add_argument(
        "--observability-db",
        default=str(ROOT / ".jarvis_runtime" / "observability.db"),
        help="Path to the local observability database.",
    )
    parser.add_argument(
        "--evolution-db",
        default=str(ROOT / ".jarvis_runtime" / "evolution.db"),
        help="Path to the local evolution database.",
    )
    parser.add_argument(
        "--comparison-json",
        default=str(ROOT / ".jarvis_runtime" / "path_comparison_v2" / "path_comparison.json"),
        help="Path to the path comparison artifact used as specialization evidence.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of recent request traces to inspect.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / ".jarvis_runtime" / "specialization_cycle"),
        help="Directory where cycle closure artifacts will be written.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def correct_now_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="alignment-domain-sovereignty",
            title="dominios como fonte soberana de roteamento e ativacao",
            target_class="corrigir_agora",
            rationale=(
                "o mapa canonico ja existe no registry, mas o runtime ainda depende de subset "
                "e heuristica local em parte do roteamento."
            ),
            dependency="domain_registry.json, knowledge-service e specialist-engine",
        ),
        BacklogDecision(
            item_id="alignment-memory-policies",
            title="politicas operacionais por classe de memoria",
            target_class="corrigir_agora",
            rationale=(
                "o registry de memorias ja existe, mas o runtime ainda concentra "
                "quase tudo em continuidade, missao e relacional."
            ),
            dependency="memory_registry.py, memory-service e governance-service",
        ),
        BacklogDecision(
            item_id="alignment-mind-arbitration",
            title="composicao e arbitragem soberana entre mentes",
            target_class="corrigir_agora",
            rationale=(
                "o registry de mentes ja existe, mas ainda nao governa a arbitragem "
                "de runtime com profundidade suficiente."
            ),
            dependency="mind_registry.py, cognitive-engine e planning-engine",
        ),
        BacklogDecision(
            item_id="alignment-identity-audit",
            title="criterios auditaveis de identidade e unidade do nucleo",
            target_class="corrigir_agora",
            rationale=(
                "o mestre exige identidade unificada e auditavel; o runtime ainda "
                "nao mede esse eixo como classe propria de aderencia."
            ),
            dependency="synthesis-engine, governance-service e observability-service",
        ),
        BacklogDecision(
            item_id="alignment-axis-gates",
            title="gates de sprint por eixo do Documento-Mestre",
            target_class="corrigir_agora",
            rationale=(
                "a proxima rodada do v2 precisa fechar o ciclo pela otica do mestre, "
                "e nao apenas por ampliacao local de especialistas."
            ),
            dependency="matriz de aderencia, sprint cycle e tooling de fechamento",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-wide-tool-layer",
            title="tool layer ampla e operacao computacional extensa",
            target_class="manter_deferido",
            rationale=(
                "essa frente amplia superficie antes de a aderencia entre dominios, "
                "memorias e mentes estar madura no runtime."
            ),
            dependency="segundo corte do v2 estabilizado",
        ),
        BacklogDecision(
            item_id="defer-voice-surface",
            title="voz e realtime como superficie oficial",
            target_class="manter_deferido",
            rationale=(
                "voz amplia interface, mas nao fecha a lacuna principal do mestre no "
                "momento atual."
            ),
            dependency="nucleo especialista mais maduro e governado",
        ),
        BacklogDecision(
            item_id="defer-pgvector-foundation",
            title="memoria profunda com pgvector como fundacao obrigatoria",
            target_class="manter_deferido",
            rationale=(
                "o problema atual nao e falta de banco vetorial; e soberania de "
                "politica de memoria no runtime."
            ),
            dependency="memoria de dominio e semantica com consumidores reais",
        ),
        BacklogDecision(
            item_id="defer-evolution-promotion",
            title="promocao evolutiva ampla do laboratorio para o nucleo",
            target_class="manter_deferido",
            rationale=(
                "o evolution-lab segue util como sandbox, mas ainda nao deve promover "
                "mudanca estrutural automatica do sistema."
            ),
            dependency="gates evolutivos muito mais fortes",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-full-domain-maturity",
            title="todos os dominios do mestre operando com maturidade plena ao mesmo tempo",
            target_class="preservar_como_visao",
            rationale=(
                "o mapa completo deve existir no sistema, mas sua maturacao plena "
                "acontece progressivamente por fase e por utilidade real."
            ),
            dependency="ciclos futuros do v2 e v3",
        ),
        BacklogDecision(
            item_id="vision-full-mind-ecology",
            title="ecologia completa das 24 mentes com arbitragem profunda em todo o runtime",
            target_class="preservar_como_visao",
            rationale=(
                "essa e uma direcao canonicamente correta, mas ainda acima do corte "
                "profissional do ciclo atual."
            ),
            dependency="maturidade de composicao cognitiva em fases futuras",
        ),
        BacklogDecision(
            item_id="vision-full-memory-system",
            title="sistema vivo completo das 11 memorias com promocao e arquivamento plenos",
            target_class="preservar_como_visao",
            rationale=(
                "o runtime deve caminhar nessa direcao, mas sem fingir que o ciclo "
                "atual consegue materializar a plenitude inteira de uma vez."
            ),
            dependency="politicas de memoria maduras em ciclos futuros",
        ),
    ]


def resolve_path(value: str) -> Path:
    target = Path(value)
    return target if target.is_absolute() else ROOT / target


def load_comparison_summary(comparison_json: str) -> dict[str, object]:
    comparison_path = resolve_path(comparison_json)
    if not comparison_path.exists():
        return {
            "overall_verdict": "unavailable",
            "comparison_summary": {
                "matched_scenarios": 0,
                "divergent_scenarios": 0,
                "baseline_axis_adherence_score": 0.0,
                "candidate_axis_adherence_score": 0.0,
                "candidate_runtime_coverage": 0.0,
                "decision": "artifact_missing",
            },
        }
    return loads(comparison_path.read_text(encoding="utf-8"))


def _summary_score(
    comparison_payload: dict[str, object],
    comparison_summary: dict[str, object],
    *,
    summary_key: str,
    scenario_key: str,
) -> float:
    summary_value = comparison_summary.get(summary_key)
    if summary_value is not None:
        return float(summary_value)
    scenario_results = comparison_payload.get("scenario_results", [])
    if not scenario_results:
        return 0.0
    values = [
        float(item[scenario_key])
        for item in scenario_results
        if isinstance(item, dict) and item.get(scenario_key) is not None
    ]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def evidence_summary(
    *,
    observability_db: str,
    evolution_db: str,
    comparison_json: str,
    limit: int,
) -> CycleEvidenceSummary:
    observability = ObservabilityService(database_path=observability_db)
    evolution = EvolutionLabService(database_path=evolution_db)
    audits = observability.summarize_recent_requests(limit=limit)
    healthy_requests = sum(1 for audit in audits if audit.trace_complete)
    incomplete_requests = sum(
        1
        for audit in audits
        if (
            not audit.trace_complete
            and not audit.anomaly_flags
            and not audit.continuity_anomaly_flags
        )
    )
    attention_required_requests = len(audits) - healthy_requests - incomplete_requests

    def count_status(attribute: str, value: str) -> int:
        return sum(1 for audit in audits if getattr(audit, attribute) == value)

    comparison_payload = load_comparison_summary(comparison_json)
    comparison_summary = comparison_payload["comparison_summary"]
    return CycleEvidenceSummary(
        requests_audited=len(audits),
        healthy_requests=healthy_requests,
        incomplete_requests=incomplete_requests,
        attention_required_requests=attention_required_requests,
        domain_alignment_healthy=count_status("domain_alignment_status", "healthy"),
        domain_alignment_partial=count_status("domain_alignment_status", "partial"),
        domain_alignment_incomplete=count_status("domain_alignment_status", "incomplete"),
        domain_alignment_attention_required=count_status(
            "domain_alignment_status",
            "attention_required",
        ),
        memory_alignment_healthy=count_status("memory_alignment_status", "healthy"),
        memory_alignment_partial=count_status("memory_alignment_status", "partial"),
        memory_alignment_incomplete=count_status("memory_alignment_status", "incomplete"),
        memory_alignment_attention_required=count_status(
            "memory_alignment_status",
            "attention_required",
        ),
        sovereignty_healthy=count_status("specialist_sovereignty_status", "healthy"),
        sovereignty_incomplete=count_status("specialist_sovereignty_status", "incomplete"),
        sovereignty_attention_required=count_status(
            "specialist_sovereignty_status",
            "attention_required",
        ),
        recent_evolution_proposals=len(evolution.list_recent_proposals(limit=limit)),
        recent_evolution_decisions=len(evolution.list_recent_decisions(limit=limit)),
        comparison_overall_verdict=str(comparison_payload["overall_verdict"]),
        comparison_decision=str(comparison_summary["decision"]),
        matched_scenarios=int(comparison_summary["matched_scenarios"]),
        divergent_scenarios=int(comparison_summary["divergent_scenarios"]),
        baseline_axis_adherence_score=_summary_score(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_axis_adherence_score",
            scenario_key="baseline_axis_adherence_score",
        ),
        candidate_axis_adherence_score=_summary_score(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_axis_adherence_score",
            scenario_key="candidate_axis_adherence_score",
        ),
        candidate_runtime_coverage=float(comparison_summary["candidate_runtime_coverage"]),
    )


def build_payload(
    *,
    observability_db: str,
    evolution_db: str,
    comparison_json: str,
    limit: int,
) -> dict[str, object]:
    evidence = evidence_summary(
        observability_db=observability_db,
        evolution_db=evolution_db,
        comparison_json=comparison_json,
        limit=limit,
    )
    return {
        "cycle_id": "v2-cycle-1",
        "decision": "open_v2_alignment_cycle",
        "evidence_summary": asdict(evidence),
        "correct_now_scope": [asdict(item) for item in correct_now_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            "especialistas subordinados operam sem quebrar a soberania do nucleo",
            "memoria relacional compartilhada mediada pelo nucleo entrou no runtime",
            "o mapa canonico de dominios passou a existir no registry do sistema",
            (
                "registries formais de mentes e memorias foram abertos como base "
                "do runtime progressivo"
            ),
            "evals e observabilidade passaram a medir aderencia do recorte aos eixos do mestre",
        ],
        "decision_rationale": (
            "o primeiro corte do v2 cumpriu o salto inicial rumo a especializacao "
            "subordinada, memoria compartilhada e aderencia observavel ao mestre. "
            "o proximo ciclo correto continua dentro do v2, mas deixa de ser "
            "expansao de especialistas por si so e passa a ser alinhamento "
            "soberano de dominios, memorias e mentes ao runtime do sistema."
        ),
    }


def render_text(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        f"cycle_id={payload['cycle_id']}",
        f"decision={payload['decision']}",
        (
            "requests="
            f"{evidence['requests_audited']} "
            f"healthy={evidence['healthy_requests']} "
            f"incomplete={evidence['incomplete_requests']} "
            f"attention_required={evidence['attention_required_requests']}"
        ),
        (
            "alignment="
            f"domain_healthy={evidence['domain_alignment_healthy']} "
            f"domain_partial={evidence['domain_alignment_partial']} "
            f"memory_healthy={evidence['memory_alignment_healthy']} "
            f"memory_partial={evidence['memory_alignment_partial']} "
            f"sovereignty_healthy={evidence['sovereignty_healthy']}"
        ),
        (
            "comparison="
            f"overall_verdict={evidence['comparison_overall_verdict']} "
            f"decision={evidence['comparison_decision']} "
            f"matched={evidence['matched_scenarios']} "
            f"divergent={evidence['divergent_scenarios']} "
            f"candidate_axis_adherence={evidence['candidate_axis_adherence_score']}"
        ),
        "correct_now=" + ",".join(item["item_id"] for item in payload["correct_now_scope"]),
        "deferred=" + ",".join(item["item_id"] for item in payload["deferred_scope"]),
        "vision=" + ",".join(item["item_id"] for item in payload["vision_scope"]),
    ]
    return "\n".join(lines)


def render_markdown(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        "# Fechamento do Primeiro Corte do V2",
        "",
        f"- ciclo: `{payload['cycle_id']}`",
        f"- decisao: `{payload['decision']}`",
        "",
        "## Evidencia consolidada",
        "",
        f"- requests auditados: `{evidence['requests_audited']}`",
        f"- requests saudaveis: `{evidence['healthy_requests']}`",
        f"- requests incompletos: `{evidence['incomplete_requests']}`",
        f"- requests com atencao requerida: `{evidence['attention_required_requests']}`",
        f"- domain alignment healthy: `{evidence['domain_alignment_healthy']}`",
        f"- domain alignment partial: `{evidence['domain_alignment_partial']}`",
        f"- domain alignment incomplete: `{evidence['domain_alignment_incomplete']}`",
        (
            "- domain alignment attention required: "
            f"`{evidence['domain_alignment_attention_required']}`"
        ),
        f"- memory alignment healthy: `{evidence['memory_alignment_healthy']}`",
        f"- memory alignment partial: `{evidence['memory_alignment_partial']}`",
        f"- memory alignment incomplete: `{evidence['memory_alignment_incomplete']}`",
        (
            "- memory alignment attention required: "
            f"`{evidence['memory_alignment_attention_required']}`"
        ),
        f"- specialist sovereignty healthy: `{evidence['sovereignty_healthy']}`",
        f"- specialist sovereignty incomplete: `{evidence['sovereignty_incomplete']}`",
        (
            "- specialist sovereignty attention required: "
            f"`{evidence['sovereignty_attention_required']}`"
        ),
        f"- proposals recentes do evolution-lab: `{evidence['recent_evolution_proposals']}`",
        f"- decisoes recentes do evolution-lab: `{evidence['recent_evolution_decisions']}`",
        f"- veredito comparativo: `{evidence['comparison_overall_verdict']}`",
        f"- decisao comparativa: `{evidence['comparison_decision']}`",
        f"- cenarios comparados com match: `{evidence['matched_scenarios']}`",
        f"- cenarios divergentes: `{evidence['divergent_scenarios']}`",
        (
            "- baseline axis adherence score: "
            f"`{evidence['baseline_axis_adherence_score']}`"
        ),
        (
            "- candidate axis adherence score: "
            f"`{evidence['candidate_axis_adherence_score']}`"
        ),
        f"- candidate runtime coverage: `{evidence['candidate_runtime_coverage']}`",
        "",
        "## Corrigir agora",
        "",
    ]
    for item in payload["correct_now_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependencia: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(["", "## Manter deferido", ""])
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
    lines.extend(
        [
            "",
            "## Racional da decisao",
            "",
            payload["decision_rationale"],
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(
        observability_db=str(resolve_path(args.observability_db)),
        evolution_db=str(resolve_path(args.evolution_db)),
        comparison_json=str(resolve_path(args.comparison_json)),
        limit=args.limit,
    )
    (output_dir / "cycle_closure.json").write_text(
        dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (output_dir / "cycle_closure.md").write_text(
        render_markdown(payload),
        encoding="utf-8",
    )
    if args.format == "json":
        print(dumps(payload, ensure_ascii=True, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
