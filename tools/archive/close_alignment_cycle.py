"""Close the v2 alignment cycle and emit the next master-aligned cut for v2."""
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
    mind_alignment_healthy: int
    mind_alignment_partial: int
    mind_alignment_incomplete: int
    mind_alignment_attention_required: int
    identity_alignment_healthy: int
    identity_alignment_partial: int
    identity_alignment_incomplete: int
    identity_alignment_attention_required: int
    memory_alignment_healthy: int
    memory_alignment_partial: int
    memory_alignment_incomplete: int
    memory_alignment_attention_required: int
    sovereignty_healthy: int
    sovereignty_incomplete: int
    sovereignty_attention_required: int
    axis_gate_healthy: int
    axis_gate_partial: int
    axis_gate_attention_required: int
    recent_evolution_proposals: int
    recent_evolution_decisions: int
    comparison_overall_verdict: str
    comparison_decision: str
    matched_scenarios: int
    divergent_scenarios: int
    baseline_axis_adherence_score: float
    candidate_axis_adherence_score: float
    baseline_axis_gate_pass_rate: float
    candidate_axis_gate_pass_rate: float
    candidate_runtime_coverage: float


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the v2 alignment cycle.")
    parser.add_argument(
        "--observability-db",
        default=str(
            ROOT / ".jarvis_runtime" / "path_comparison_v2" / "baseline" / "observability.db"
        ),
        help="Path to the observability database used as alignment evidence.",
    )
    parser.add_argument(
        "--evolution-db",
        default=str(ROOT / ".jarvis_runtime" / "evolution.db"),
        help="Path to the local evolution database.",
    )
    parser.add_argument(
        "--comparison-json",
        default=str(ROOT / ".jarvis_runtime" / "path_comparison_v2" / "path_comparison.json"),
        help="Path to the path comparison artifact used as alignment evidence.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of recent request traces to inspect.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / ".jarvis_runtime" / "v2_alignment_cycle"),
        help="Directory where cycle closure artifacts will be written.",
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
            item_id="v2-domain-specialists-beyond-shadow",
            title="especialistas de dominio acima do shadow mode",
            target_class="proximo_corte_v2",
            rationale=(
                "o alinhamento fortaleceu os eixos soberanos; o passo seguinte e abrir "
                "especialistas por dominio real sem perder a voz unica do nucleo."
            ),
            dependency="registry de dominios soberano e gates por eixo ja ativos",
        ),
        BacklogDecision(
            item_id="v2-semantic-memory-consumers",
            title="consumidores canonicos de memoria relacional e semantica",
            target_class="proximo_corte_v2",
            rationale=(
                "agora que a politica por classe de memoria e auditavel, o proximo salto "
                "correto e criar consumidores reais acima do handoff atual."
            ),
            dependency="memory_registry soberano e specialist shared memory maduros",
        ),
        BacklogDecision(
            item_id="v2-governed-technology-absorption",
            title="absorcao tecnologica sandbox-only guiada pelos registries soberanos",
            target_class="proximo_corte_v2",
            rationale=(
                "o nucleo ja tem gramatica suficiente para absorver valor do ecossistema "
                "sem virar colagem, desde que a promocao continue experimental e auditavel."
            ),
            dependency="technology-study, evolution-lab e axis gates como regra de promocao",
        ),
        BacklogDecision(
            item_id="v2-axis-gated-promotion",
            title="promocao do proximo corte usando aderencia por eixo como gate obrigatorio",
            target_class="proximo_corte_v2",
            rationale=(
                "a Sprint 5 abriu a medicao por eixo; depois do fechamento da Sprint 6, "
                "todo novo recorte do v2 deve nascer ja subordinado a esses gates."
            ),
            dependency="close_alignment_cycle e comparacao local regeneravel",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-wide-computer-use",
            title="computer use amplo e operacao extensa do computador",
            target_class="manter_deferido",
            rationale=(
                "essa frente amplia superficie cedo demais para um nucleo que acabou "
                "de fechar o alinhamento dos eixos soberanos."
            ),
            dependency="especialistas de dominio maduros e governanca ampliada",
        ),
        BacklogDecision(
            item_id="defer-voice-and-realtime",
            title="voz e realtime como superficie oficial",
            target_class="manter_deferido",
            rationale=(
                "voz continua importante na visao, mas ainda nao move a principal "
                "lacuna do sistema nesta fase."
            ),
            dependency="nucleo mais amplo e observabilidade de superficies maduras",
        ),
        BacklogDecision(
            item_id="defer-pgvector-as-foundation",
            title="pgvector como fundacao canonica obrigatoria",
            target_class="manter_deferido",
            rationale=(
                "a proxima necessidade real ainda e consumidor de memoria, nao "
                "troca de fundacao por banco vetorial."
            ),
            dependency="consumidor semantico canonico e benchmark proprio de retrieval",
        ),
        BacklogDecision(
            item_id="defer-aggressive-autoevolution",
            title="autoevolucao promotiva agressiva no nucleo",
            target_class="manter_deferido",
            rationale=(
                "o evolution-lab segue util como sandbox, mas promover mudanca estrutural "
                "automatica ainda seria cedo demais."
            ),
            dependency="memoria evolutiva formal e gates muito mais fortes",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-robust-ecosystem",
            title="ecossistema robusto que absorve o melhor do estado da arte",
            target_class="preservar_como_visao",
            rationale=(
                "essa continua sendo a ambicao correta do JARVIS, mas so deve subir "
                "como camada institucional quando o nucleo mantiver soberania plena."
            ),
            dependency="camada formal de absorcao tecnologica governada",
        ),
        BacklogDecision(
            item_id="vision-full-memory-ecology",
            title="sistema vivo pleno das 11 memorias com promocao e arquivamento profundos",
            target_class="preservar_como_visao",
            rationale=(
                "o eixo de memoria evoluiu bastante, mas a ecologia completa ainda "
                "fica acima do corte profissional imediato."
            ),
            dependency="consumidores canonicos e politicas de promocao futuras",
        ),
        BacklogDecision(
            item_id="vision-full-mind-ecology",
            title="ecologia completa das 24 mentes governando todo o runtime",
            target_class="preservar_como_visao",
            rationale=(
                "a arbitragem soberana ja entrou, mas a profundidade total da ecologia "
                "de mentes continua sendo horizonte, nao backlog curto."
            ),
            dependency="ciclos posteriores do v2 e do v3",
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
                "baseline_axis_gate_pass_rate": 0.0,
                "candidate_axis_gate_pass_rate": 0.0,
                "candidate_runtime_coverage": 0.0,
                "decision": "artifact_missing",
            },
            "scenario_results": [],
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


def _gate_pass_rate(
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
    statuses = [
        item[scenario_key]
        for item in scenario_results
        if isinstance(item, dict) and item.get(scenario_key) is not None
    ]
    if not statuses:
        return 0.0
    return round(sum(1 for status in statuses if status == "healthy") / len(statuses), 4)


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
        mind_alignment_healthy=count_status("mind_alignment_status", "healthy"),
        mind_alignment_partial=count_status("mind_alignment_status", "partial"),
        mind_alignment_incomplete=count_status("mind_alignment_status", "incomplete"),
        mind_alignment_attention_required=count_status(
            "mind_alignment_status",
            "attention_required",
        ),
        identity_alignment_healthy=count_status("identity_alignment_status", "healthy"),
        identity_alignment_partial=count_status("identity_alignment_status", "partial"),
        identity_alignment_incomplete=count_status(
            "identity_alignment_status",
            "incomplete",
        ),
        identity_alignment_attention_required=count_status(
            "identity_alignment_status",
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
        axis_gate_healthy=sum(
            1
            for audit in audits
            if all(
                status == "healthy"
                for status in (
                    audit.domain_alignment_status,
                    audit.mind_alignment_status,
                    audit.identity_alignment_status,
                    audit.memory_alignment_status,
                    audit.specialist_sovereignty_status,
                )
            )
        ),
        axis_gate_partial=sum(
            1
            for audit in audits
            if (
                any(
                    status == "partial"
                    for status in (
                        audit.domain_alignment_status,
                        audit.mind_alignment_status,
                        audit.identity_alignment_status,
                        audit.memory_alignment_status,
                        audit.specialist_sovereignty_status,
                    )
                )
                and not any(
                    status in {"attention_required", "incomplete"}
                    for status in (
                        audit.domain_alignment_status,
                        audit.mind_alignment_status,
                        audit.identity_alignment_status,
                        audit.memory_alignment_status,
                        audit.specialist_sovereignty_status,
                    )
                )
            )
        ),
        axis_gate_attention_required=sum(
            1
            for audit in audits
            if any(
                status in {"attention_required", "incomplete"}
                for status in (
                    audit.domain_alignment_status,
                    audit.mind_alignment_status,
                    audit.identity_alignment_status,
                    audit.memory_alignment_status,
                    audit.specialist_sovereignty_status,
                )
            )
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
        baseline_axis_gate_pass_rate=_gate_pass_rate(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_axis_gate_pass_rate",
            scenario_key="baseline_axis_gate_status",
        ),
        candidate_axis_gate_pass_rate=_gate_pass_rate(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_axis_gate_pass_rate",
            scenario_key="candidate_axis_gate_status",
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
        "cycle_id": "v2-alignment-cycle-1",
        "decision": "close_v2_alignment_cycle_and_open_next_v2_cut",
        "evidence_summary": asdict(evidence),
        "next_cut_scope": [asdict(item) for item in next_cut_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            (
                "dominios, memorias, mentes e identidade passaram a operar como "
                "eixos auditaveis do runtime"
            ),
            "os cinco eixos ja entram em piloto, comparacao local e sandbox evolutivo",
            (
                "o ciclo deixou de medir apenas utilidade local e passou a fechar "
                "por aderencia ao mestre"
            ),
            (
                "o nucleo ficou mais preparado para absorcao tecnologica disciplinada "
                "sem perder soberania"
            ),
        ],
        "decision_rationale": (
            "o v2-alignment-cycle cumpriu o objetivo de alinhar o runtime aos eixos "
            "soberanos do Documento-Mestre sem ampliar superficies cedo demais. "
            "o proximo passo correto continua dentro do v2, mas troca o foco de "
            "alinhamento estrutural por expansao governada sobre esses eixos, com "
            "especialistas de dominio mais maduros, consumidores reais de memoria "
            "mais rica e absorcao tecnologica ainda restrita ao sandbox e a gates formais."
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
            f"mind_healthy={evidence['mind_alignment_healthy']} "
            f"identity_healthy={evidence['identity_alignment_healthy']} "
            f"memory_healthy={evidence['memory_alignment_healthy']} "
            f"sovereignty_healthy={evidence['sovereignty_healthy']} "
            f"axis_gate_healthy={evidence['axis_gate_healthy']}"
        ),
        (
            "comparison="
            f"overall_verdict={evidence['comparison_overall_verdict']} "
            f"decision={evidence['comparison_decision']} "
            f"matched={evidence['matched_scenarios']} "
            f"divergent={evidence['divergent_scenarios']} "
            f"candidate_axis_adherence={evidence['candidate_axis_adherence_score']} "
            f"candidate_axis_gate_pass_rate={evidence['candidate_axis_gate_pass_rate']}"
        ),
        "next_cut=" + ",".join(item["item_id"] for item in payload["next_cut_scope"]),
        "deferred=" + ",".join(item["item_id"] for item in payload["deferred_scope"]),
        "vision=" + ",".join(item["item_id"] for item in payload["vision_scope"]),
    ]
    return "\n".join(lines)


def render_markdown(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        "# Fechamento do V2 Alignment Cycle",
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
        f"- mind alignment healthy: `{evidence['mind_alignment_healthy']}`",
        f"- mind alignment partial: `{evidence['mind_alignment_partial']}`",
        f"- mind alignment incomplete: `{evidence['mind_alignment_incomplete']}`",
        (
            "- mind alignment attention required: "
            f"`{evidence['mind_alignment_attention_required']}`"
        ),
        f"- identity alignment healthy: `{evidence['identity_alignment_healthy']}`",
        f"- identity alignment partial: `{evidence['identity_alignment_partial']}`",
        (
            "- identity alignment incomplete: "
            f"`{evidence['identity_alignment_incomplete']}`"
        ),
        (
            "- identity alignment attention required: "
            f"`{evidence['identity_alignment_attention_required']}`"
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
        f"- axis gate healthy: `{evidence['axis_gate_healthy']}`",
        f"- axis gate partial: `{evidence['axis_gate_partial']}`",
        f"- axis gate attention required: `{evidence['axis_gate_attention_required']}`",
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
        (
            "- baseline axis gate pass rate: "
            f"`{evidence['baseline_axis_gate_pass_rate']}`"
        ),
        (
            "- candidate axis gate pass rate: "
            f"`{evidence['candidate_axis_gate_pass_rate']}`"
        ),
        f"- candidate runtime coverage: `{evidence['candidate_runtime_coverage']}`",
        "",
        "## Entra no proximo corte do v2",
        "",
    ]
    for item in payload["next_cut_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependencia: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(["", "## Fica fora do corte imediato", ""])
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


