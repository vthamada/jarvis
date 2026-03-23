"""Close the first v1.5 cycle and emit a formal cut toward v2."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps, loads
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent
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
    target_phase: str
    rationale: str
    dependency: str


@dataclass(frozen=True)
class CycleEvidenceSummary:
    requests_audited: int
    healthy_requests: int
    incomplete_requests: int
    attention_required_requests: int
    continuity_traces_healthy: int
    continuity_traces_incomplete: int
    continuity_traces_attention_required: int
    recent_evolution_proposals: int
    recent_evolution_decisions: int
    langgraph_status: str
    comparison_overall_verdict: str
    comparison_decision: str
    matched_scenarios: int
    divergent_scenarios: int
    baseline_expectation_score: float
    candidate_expectation_score: float
    candidate_runtime_coverage: float


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the first v1.5 cycle.")
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
        default=str(ROOT / ".jarvis_runtime" / "path-comparison" / "path_comparison.json"),
        help="Path to the path comparison artifact used as runtime evidence.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of recent request traces to inspect.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / ".jarvis_runtime" / "v1_5_cycle"),
        help="Directory where cycle closure artifacts will be written.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def v2_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="v2-specialist-runtime-contracts",
            title="contratos e runtime inicial de especialistas subordinados",
            target_phase="v2",
            rationale=(
                "o v1.5 estabilizou checkpoint, replay, pausa e subfluxo stateful; "
                "o proximo salto correto e abrir a fronteira de convocacao segura "
                "de especialistas sem fragmentar o nucleo."
            ),
            dependency="runtime stateful governado do v1.5 e observabilidade comparativa madura",
        ),
        BacklogDecision(
            item_id="v2-specialist-routing",
            title="selecao governada de especialistas e handoff interno",
            target_phase="v2",
            rationale=(
                "a continuidade profunda ja decide direcao entre sessao, missao e conflito; "
                "o proximo nivel e decidir quando e como um especialista deve ser convocado."
            ),
            dependency="contratos de especialistas e trilha observavel de handoff interno",
        ),
        BacklogDecision(
            item_id="v2-relational-memory",
            title="memoria relacional compartilhada entre nucleo e especialistas",
            target_phase="v2",
            rationale=(
                "o ciclo atual resolveu continuidade stateful; o v2 precisa ampliar "
                "contexto compartilhado e relacoes persistentes acima da sessao."
            ),
            dependency="estudo dirigido de Hermes, Graphiti e Zep com consumidor real no nucleo",
        ),
        BacklogDecision(
            item_id="v2-first-specialist-shadow-mode",
            title="primeiro especialista subordinado em shadow mode",
            target_phase="v2",
            rationale=(
                "a estrategia correta agora e validar o primeiro especialista como extensao "
                "observavel e governada do nucleo, antes de qualquer ecossistema amplo."
            ),
            dependency=(
                "routing governado, memoria relacional minima e contratos "
                "de saida estruturada"
            ),
        ),
        BacklogDecision(
            item_id="v2-specialist-evals",
            title="evals e governanca de convocacao de especialistas",
            target_phase="v2",
            rationale=(
                "o v1.5 fechou evals de continuidade; o v2 deve herdar essa disciplina "
                "para comparar invocacao, utilidade e risco de especialistas."
            ),
            dependency="internal pilot, compare_orchestrator_paths e evolution-lab endurecidos",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="later-computer-use-wide",
            title="computer use amplo e operacao extensa do computador",
            target_phase="deferir_apos_primeiro_ciclo_v2",
            rationale=(
                "essa frente amplia superficie e risco operacional antes de o modelo "
                "de especialistas subordinados estar maduro."
            ),
            dependency="especialistas, governanca e observabilidade de v2 consolidados",
        ),
        BacklogDecision(
            item_id="later-voice-runtime",
            title="voz e realtime como superficie oficial",
            target_phase="deferir_apos_primeiro_ciclo_v2",
            rationale=(
                "voz amplia interface, nao resolve a lacuna principal do proximo ciclo "
                "e deve entrar com o nucleo especialista mais maduro."
            ),
            dependency="v2 estabilizado e runtime governado mais amplo",
        ),
        BacklogDecision(
            item_id="later-pgvector-baseline",
            title="memoria semantica profunda com pgvector como base canonica",
            target_phase="deferir_apos_primeiro_ciclo_v2",
            rationale=(
                "memoria relacional e consumidor canonico precisam nascer primeiro; "
                "pgvector nao deve entrar como fundacao antes disso."
            ),
            dependency="memoria relacional do v2 e benchmark proprio de retrieval",
        ),
        BacklogDecision(
            item_id="later-operational-assistant-wide",
            title="assistencia operacional ampla e workflows pessoais",
            target_phase="deferir_apos_primeiro_ciclo_v2",
            rationale=(
                "essa camada depende de especialistas, memoria mais rica e governanca "
                "de superficie ampliada, ainda fora do corte imediato."
            ),
            dependency="primeiro ciclo do v2 concluido com especialistas subordinados uteis",
        ),
        BacklogDecision(
            item_id="later-aggressive-autoevolution",
            title="autoevolucao promotiva e mudanca estrutural agressiva",
            target_phase="laboratorio_futuro",
            rationale=(
                "o evolution-lab continua sandbox-only; promover mudanca automatica do "
                "nucleo segue fora do corte profissional do sistema."
            ),
            dependency="gates de laboratorio muito mais fortes e benchmark repetivel",
        ),
    ]


def load_comparison_summary(comparison_json: str) -> dict[str, object]:
    comparison_path = resolve_path(comparison_json)
    if not comparison_path.exists():
        return {
            "langgraph_status": "missing_artifact",
            "overall_verdict": "unavailable",
            "comparison_summary": {
                "scenario_count": 0,
                "matched_scenarios": 0,
                "divergent_scenarios": 0,
                "baseline_expectation_score": 0.0,
                "candidate_expectation_score": 0.0,
                "candidate_runtime_coverage": 0.0,
                "decision": "artifact_missing",
            },
        }
    return loads(comparison_path.read_text(encoding="utf-8"))


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
    continuity_healthy = sum(
        1 for audit in audits if audit.continuity_trace_status == "healthy"
    )
    continuity_incomplete = sum(
        1 for audit in audits if audit.continuity_trace_status == "incomplete"
    )
    continuity_attention = sum(
        1 for audit in audits if audit.continuity_trace_status == "attention_required"
    )
    comparison_payload = load_comparison_summary(comparison_json)
    comparison_summary = comparison_payload["comparison_summary"]
    return CycleEvidenceSummary(
        requests_audited=len(audits),
        healthy_requests=healthy_requests,
        incomplete_requests=incomplete_requests,
        attention_required_requests=attention_required_requests,
        continuity_traces_healthy=continuity_healthy,
        continuity_traces_incomplete=continuity_incomplete,
        continuity_traces_attention_required=continuity_attention,
        recent_evolution_proposals=len(evolution.list_recent_proposals(limit=limit)),
        recent_evolution_decisions=len(evolution.list_recent_decisions(limit=limit)),
        langgraph_status=str(comparison_payload["langgraph_status"]),
        comparison_overall_verdict=str(comparison_payload["overall_verdict"]),
        comparison_decision=str(comparison_summary["decision"]),
        matched_scenarios=int(comparison_summary["matched_scenarios"]),
        divergent_scenarios=int(comparison_summary["divergent_scenarios"]),
        baseline_expectation_score=float(comparison_summary["baseline_expectation_score"]),
        candidate_expectation_score=float(comparison_summary["candidate_expectation_score"]),
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
        "cycle_id": "v1-5-cycle-1",
        "decision": "promote_to_v2",
        "evidence_summary": asdict(evidence),
        "v2_scope": [asdict(item) for item in v2_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "goals_met": [
            "checkpoint, replay e pausa governada da continuidade operam como runtime recuperavel",
            "subfluxo stateful de LangGraph foi absorvido parcialmente sem reescrever o nucleo",
            (
                "evals comparativas do runtime fecharam com evidencia de equivalencia "
                "e coverage integral do recorte absorvido"
            ),
            (
                "observabilidade, piloto e evolution-lab passaram a carregar sinais "
                "especificos do runtime de continuidade"
            ),
        ],
        "decision_rationale": (
            "o v1.5 cumpriu o primeiro salto estrutural acima do baseline do v1. "
            "o proximo ciclo correto e abrir o v2 com especializacao controlada, "
            "memoria relacional mais rica e convocacao subordinada de especialistas, "
            "sem antecipar superficies amplas ou mudancas agressivas de autonomia."
        ),
    }


def render_text(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        f"cycle_id={payload['cycle_id']}",
        f"decision={payload['decision']}",
        (
            "evidence="
            f"requests={evidence['requests_audited']} "
            f"healthy={evidence['healthy_requests']} "
            f"incomplete={evidence['incomplete_requests']} "
            f"attention_required={evidence['attention_required_requests']} "
            f"continuity_healthy={evidence['continuity_traces_healthy']} "
            f"continuity_incomplete={evidence['continuity_traces_incomplete']} "
            f"continuity_attention={evidence['continuity_traces_attention_required']}"
        ),
        (
            "comparison="
            f"langgraph_status={evidence['langgraph_status']} "
            f"overall_verdict={evidence['comparison_overall_verdict']} "
            f"decision={evidence['comparison_decision']} "
            f"matched={evidence['matched_scenarios']} "
            f"divergent={evidence['divergent_scenarios']} "
            f"candidate_runtime_coverage={evidence['candidate_runtime_coverage']}"
        ),
        "v2_scope=" + ",".join(item["item_id"] for item in payload["v2_scope"]),
        "deferred_scope=" + ",".join(item["item_id"] for item in payload["deferred_scope"]),
    ]
    return "\n".join(lines)


def render_markdown(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        "# Fechamento do Ciclo V1.5",
        "",
        f"- ciclo: `{payload['cycle_id']}`",
        f"- decisão: `{payload['decision']}`",
        "",
        "## Evidência consolidada",
        "",
        f"- requests auditados: `{evidence['requests_audited']}`",
        f"- requests saudáveis: `{evidence['healthy_requests']}`",
        f"- requests incompletos: `{evidence['incomplete_requests']}`",
        f"- requests com atenção requerida: `{evidence['attention_required_requests']}`",
        f"- trilhas de continuidade saudáveis: `{evidence['continuity_traces_healthy']}`",
        f"- trilhas de continuidade incompletas: `{evidence['continuity_traces_incomplete']}`",
        (
            "- trilhas de continuidade com atenção requerida: "
            f"`{evidence['continuity_traces_attention_required']}`"
        ),
        f"- proposals recentes do evolution-lab: `{evidence['recent_evolution_proposals']}`",
        f"- decisões recentes do evolution-lab: `{evidence['recent_evolution_decisions']}`",
        f"- status do runtime LangGraph: `{evidence['langgraph_status']}`",
        f"- veredito comparativo: `{evidence['comparison_overall_verdict']}`",
        f"- decisão comparativa: `{evidence['comparison_decision']}`",
        f"- cenários comparados com match: `{evidence['matched_scenarios']}`",
        f"- cenários divergentes: `{evidence['divergent_scenarios']}`",
        f"- score esperado do baseline: `{evidence['baseline_expectation_score']}`",
        f"- score esperado da candidata: `{evidence['candidate_expectation_score']}`",
        f"- cobertura do runtime absorvido: `{evidence['candidate_runtime_coverage']}`",
        "",
        "## Entra no primeiro ciclo do v2",
        "",
    ]
    for item in payload["v2_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependência: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(["", "## Fica fora do corte imediato", ""])
    for item in payload["deferred_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependência: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Racional da decisão",
            "",
            payload["decision_rationale"],
        ]
    )
    return "\n".join(lines)


def resolve_path(value: str) -> Path:
    target = Path(value)
    return target if target.is_absolute() else ROOT / target


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
