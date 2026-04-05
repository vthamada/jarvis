"""Close the v2 sovereign alignment cut with regenerable local evidence."""
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
class CutEvidenceSummary:
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
    baseline_workflow_profile_decision: str
    candidate_workflow_profile_decision: str
    baseline_workflow_baseline_rate: float
    candidate_workflow_baseline_rate: float
    baseline_workflow_maturation_rate: float
    candidate_workflow_maturation_rate: float
    baseline_memory_causality_decision: str
    candidate_memory_causality_decision: str
    baseline_memory_causal_rate: float
    candidate_memory_causal_rate: float
    baseline_memory_attached_only_rate: float
    candidate_memory_attached_only_rate: float
    baseline_mind_domain_specialist_decision: str
    candidate_mind_domain_specialist_decision: str
    baseline_mind_domain_specialist_alignment_rate: float
    candidate_mind_domain_specialist_alignment_rate: float
    baseline_cognitive_recomposition_decision: str
    candidate_cognitive_recomposition_decision: str
    baseline_cognitive_recomposition_coherent_rate: float
    candidate_cognitive_recomposition_coherent_rate: float


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the v2 sovereign alignment cut.")
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
        help="Path to the path comparison artifact used as sovereign-cut evidence.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of recent request traces to inspect.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / ".jarvis_runtime" / "v2_sovereign_alignment_cut"),
        help="Directory where closure artifacts will be written.",
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
            item_id="v2-domain-consumers-and-specialists",
            title="consumidores canonicos de dominio acima do guided atual",
            target_class="proximo_corte_v2",
            rationale=(
                "o corte soberano alinhou registry, memoria e arbitragem; o proximo salto "
                "correto e criar consumidores reais de dominio acima do handoff guiado atual."
            ),
            dependency="registry soberano, guided specialists e axis gates ja estabilizados",
        ),
        BacklogDecision(
            item_id="v2-operational-workflow-layer",
            title="camada de workflows operacionais acima do nucleo soberano",
            target_class="proximo_corte_v2",
            rationale=(
                "o runtime ja suporta especialistas e observabilidade suficientes para abrir "
                "uma camada futura de workflows compostos sem terceirizar o nucleo."
            ),
            dependency="specialists guiados maduros e contratos observaveis estaveis",
        ),
        BacklogDecision(
            item_id="v2-governed-technology-benchmarks",
            title="benchmarks governados de AutoGPT Platform, Mastra e Mem0",
            target_class="proximo_corte_v2",
            rationale=(
                "o sistema ja tem gramatica soberana para avaliar tecnologias externas "
                "por recorte, especialmente workflow continuo e memoria multicamada."
            ),
            dependency="technology-study consolidado e evolution-lab sandbox-only",
        ),
        BacklogDecision(
            item_id="v2-release-grade-axis-baseline",
            title="promocao do baseline do v2 sempre subordinada a axis gates",
            target_class="proximo_corte_v2",
            rationale=(
                "depois deste corte, toda ampliacao do v2 deve nascer ja subordinada "
                "a gates permanentes de dominio, memoria, mente, identidade e soberania."
            ),
            dependency="engineering gate de release e artifacts por eixo regeneraveis",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-wide-computer-use",
            title="computer use amplo e operacao extensa do computador",
            target_class="manter_deferido",
            rationale=(
                "essa frente ainda amplia superficie cedo demais para um runtime que "
                "acabou de estabilizar sua soberania interna."
            ),
            dependency="camada operacional mais madura e governanca ampliada",
        ),
        BacklogDecision(
            item_id="defer-voice-and-realtime",
            title="voz e realtime como superficie oficial",
            target_class="manter_deferido",
            rationale=(
                "voz continua importante na visao, mas ainda nao move a lacuna "
                "principal do programa nesta fase."
            ),
            dependency="proximo corte do v2 consolidado e superficies mais maduras",
        ),
        BacklogDecision(
            item_id="defer-pgvector-as-foundation",
            title="pgvector como fundacao canonica obrigatoria",
            target_class="manter_deferido",
            rationale=(
                "o proximo problema real nao e trocar a fundacao do banco, e sim "
                "criar consumidores semanticos e multicamada com utilidade concreta."
            ),
            dependency="consumidores canonicos e benchmark proprio de memoria",
        ),
        BacklogDecision(
            item_id="defer-aggressive-evolution-promotion",
            title="promocao evolutiva agressiva do laboratorio para o nucleo",
            target_class="manter_deferido",
            rationale=(
                "o evolution-lab segue importante como sandbox, mas ainda nao deve "
                "promover mudanca estrutural automatica do sistema."
            ),
            dependency="memoria evolutiva formal e gates muito mais fortes",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-robust-absorbing-ecosystem",
            title="ecossistema robusto capaz de absorver o melhor do estado da arte",
            target_class="preservar_como_visao",
            rationale=(
                "essa continua sendo a ambicao correta do JARVIS, mas deve subir "
                "progressivamente sem terceirizar o cerebro do sistema."
            ),
            dependency="camada formal de absorcao tecnologica governada",
        ),
        BacklogDecision(
            item_id="vision-full-memory-ecology",
            title="ecologia completa das 11 memorias com promocao e arquivamento profundos",
            target_class="preservar_como_visao",
            rationale=(
                "o eixo de memoria amadureceu, mas a ecologia total das memorias "
                "continua acima do backlog curto do v2."
            ),
            dependency="consumidores canonicos e politicas futuras de promocao",
        ),
        BacklogDecision(
            item_id="vision-full-mind-ecology",
            title="ecologia completa das 24 mentes governando todo o runtime",
            target_class="preservar_como_visao",
            rationale=(
                "a arbitragem soberana ja existe, mas a profundidade total da ecologia "
                "de mentes continua sendo horizonte, nao backlog imediato."
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


def _comparison_label(
    comparison_summary: dict[str, object],
    *,
    key: str,
    default: str = "not_applicable",
) -> str:
    value = comparison_summary.get(key)
    return default if value is None else str(value)


def _comparison_rate(
    comparison_payload: dict[str, object],
    comparison_summary: dict[str, object],
    *,
    summary_key: str,
    scenario_key: str,
    target: str,
) -> float:
    summary_value = comparison_summary.get(summary_key)
    if summary_value is not None:
        return float(summary_value)
    scenario_results = comparison_payload.get("scenario_results", [])
    statuses = [
        item[scenario_key]
        for item in scenario_results
        if isinstance(item, dict) and item.get(scenario_key) is not None
    ]
    if not statuses:
        return 0.0
    return round(sum(1 for status in statuses if status == target) / len(statuses), 4)


def evidence_summary(
    *,
    observability_db: str,
    evolution_db: str,
    comparison_json: str,
    limit: int,
) -> CutEvidenceSummary:
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
    return CutEvidenceSummary(
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
        baseline_workflow_profile_decision=_comparison_label(
            comparison_summary,
            key="baseline_workflow_profile_decision",
        ),
        candidate_workflow_profile_decision=_comparison_label(
            comparison_summary,
            key="candidate_workflow_profile_decision",
        ),
        baseline_workflow_baseline_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_workflow_baseline_rate",
            scenario_key="baseline_workflow_profile_assessment",
            target="baseline_saudavel",
        ),
        candidate_workflow_baseline_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_workflow_baseline_rate",
            scenario_key="candidate_workflow_profile_assessment",
            target="baseline_saudavel",
        ),
        baseline_workflow_maturation_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_workflow_maturation_rate",
            scenario_key="baseline_workflow_profile_assessment",
            target="maturation_recommended",
        ),
        candidate_workflow_maturation_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_workflow_maturation_rate",
            scenario_key="candidate_workflow_profile_assessment",
            target="maturation_recommended",
        ),
        baseline_memory_causality_decision=_comparison_label(
            comparison_summary,
            key="baseline_memory_causality_decision",
        ),
        candidate_memory_causality_decision=_comparison_label(
            comparison_summary,
            key="candidate_memory_causality_decision",
        ),
        baseline_memory_causal_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_memory_causal_rate",
            scenario_key="baseline_memory_causality_assessment",
            target="causal_guidance",
        ),
        candidate_memory_causal_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_memory_causal_rate",
            scenario_key="candidate_memory_causality_assessment",
            target="causal_guidance",
        ),
        baseline_memory_attached_only_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_memory_attached_only_rate",
            scenario_key="baseline_memory_causality_assessment",
            target="attached_only",
        ),
        candidate_memory_attached_only_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_memory_attached_only_rate",
            scenario_key="candidate_memory_causality_assessment",
            target="attached_only",
        ),
        baseline_mind_domain_specialist_decision=_comparison_label(
            comparison_summary,
            key="baseline_mind_domain_specialist_decision",
        ),
        candidate_mind_domain_specialist_decision=_comparison_label(
            comparison_summary,
            key="candidate_mind_domain_specialist_decision",
        ),
        baseline_mind_domain_specialist_alignment_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_mind_domain_specialist_alignment_rate",
            scenario_key="baseline_mind_domain_specialist_assessment",
            target="aligned",
        ),
        candidate_mind_domain_specialist_alignment_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_mind_domain_specialist_alignment_rate",
            scenario_key="candidate_mind_domain_specialist_assessment",
            target="aligned",
        ),
        baseline_cognitive_recomposition_decision=_comparison_label(
            comparison_summary,
            key="baseline_cognitive_recomposition_decision",
        ),
        candidate_cognitive_recomposition_decision=_comparison_label(
            comparison_summary,
            key="candidate_cognitive_recomposition_decision",
        ),
        baseline_cognitive_recomposition_coherent_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="baseline_cognitive_recomposition_coherent_rate",
            scenario_key="baseline_cognitive_recomposition_assessment",
            target="coherent",
        ),
        candidate_cognitive_recomposition_coherent_rate=_comparison_rate(
            comparison_payload,
            comparison_summary,
            summary_key="candidate_cognitive_recomposition_coherent_rate",
            scenario_key="candidate_cognitive_recomposition_assessment",
            target="coherent",
        ),
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
        "cut_id": "v2-sovereign-alignment-cut-1",
        "decision": "complete_v2_sovereign_alignment_cut",
        "evidence_summary": asdict(evidence),
        "next_cut_scope": [asdict(item) for item in next_cut_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            (
                "o registry de dominios passou a governar o roteamento runtime "
                "e os eventos canonicos"
            ),
            (
                "o compartilhamento mediado com especialistas passou a declarar "
                "consumo por classe e politica de escrita"
            ),
            (
                "a arbitragem cognitiva passou a operar sobre mentes e dominios "
                "canonicos com identidade auditavel"
            ),
            (
                "os especialistas guiados passaram a operar acima do shadow "
                "como caminho principal das rotas promovidas"
            ),
            "o gate de release passou a exigir artefatos minimos de aderencia por eixo",
        ],
        "decision_rationale": (
            "o v2-sovereign-alignment-cut cumpriu o objetivo de transformar dominios, "
            "memorias, mentes, identidade e soberania em partes auditaveis e coerentes "
            "do runtime. o proximo passo nao e reabrir esse alinhamento, mas usa-lo como "
            "baseline para consumidores mais ricos de dominio, camada operacional mais "
            "composta e absorcao tecnologica ainda governada por sandbox e axis gates."
        ),
    }


def render_text(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        f"cut_id={payload['cut_id']}",
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
        (
            "workflow_profile="
            f"baseline_decision={evidence['baseline_workflow_profile_decision']} "
            f"candidate_decision={evidence['candidate_workflow_profile_decision']} "
            f"candidate_maturation_rate={evidence['candidate_workflow_maturation_rate']}"
        ),
        (
            "memory_causality="
            f"baseline_decision={evidence['baseline_memory_causality_decision']} "
            f"candidate_decision={evidence['candidate_memory_causality_decision']} "
            f"candidate_causal_rate={evidence['candidate_memory_causal_rate']}"
        ),
        (
            "mind_domain_specialist="
            f"baseline_decision={evidence['baseline_mind_domain_specialist_decision']} "
            f"candidate_decision={evidence['candidate_mind_domain_specialist_decision']} "
            f"candidate_alignment_rate={evidence['candidate_mind_domain_specialist_alignment_rate']}"
        ),
        (
            "cognitive_recomposition="
            f"baseline_decision={evidence['baseline_cognitive_recomposition_decision']} "
            f"candidate_decision={evidence['candidate_cognitive_recomposition_decision']} "
            f"candidate_coherent_rate={evidence['candidate_cognitive_recomposition_coherent_rate']}"
        ),
        "next_cut=" + ",".join(item["item_id"] for item in payload["next_cut_scope"]),
        "deferred=" + ",".join(item["item_id"] for item in payload["deferred_scope"]),
        "vision=" + ",".join(item["item_id"] for item in payload["vision_scope"]),
    ]
    return "\n".join(lines)


def render_markdown(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        "# Fechamento do V2 Sovereign Alignment Cut",
        "",
        f"- corte: `{payload['cut_id']}`",
        f"- decisao: `{payload['decision']}`",
        "",
        "## Evidencia consolidada",
        "",
        f"- requests auditados: `{evidence['requests_audited']}`",
        f"- requests saudaveis: `{evidence['healthy_requests']}`",
        f"- requests incompletos: `{evidence['incomplete_requests']}`",
        f"- requests com atencao requerida: `{evidence['attention_required_requests']}`",
        f"- domain alignment healthy: `{evidence['domain_alignment_healthy']}`",
        f"- mind alignment healthy: `{evidence['mind_alignment_healthy']}`",
        f"- identity alignment healthy: `{evidence['identity_alignment_healthy']}`",
        f"- memory alignment healthy: `{evidence['memory_alignment_healthy']}`",
        f"- specialist sovereignty healthy: `{evidence['sovereignty_healthy']}`",
        f"- axis gate healthy: `{evidence['axis_gate_healthy']}`",
        f"- axis gate partial: `{evidence['axis_gate_partial']}`",
        f"- axis gate attention required: `{evidence['axis_gate_attention_required']}`",
        f"- proposals recentes do evolution-lab: `{evidence['recent_evolution_proposals']}`",
        f"- decisoes recentes do evolution-lab: `{evidence['recent_evolution_decisions']}`",
        f"- veredito comparativo: `{evidence['comparison_overall_verdict']}`",
        f"- decisao comparativa: `{evidence['comparison_decision']}`",
        f"- cenarios com match: `{evidence['matched_scenarios']}`",
        f"- cenarios divergentes: `{evidence['divergent_scenarios']}`",
        f"- baseline axis adherence score: `{evidence['baseline_axis_adherence_score']}`",
        f"- candidate axis adherence score: `{evidence['candidate_axis_adherence_score']}`",
        f"- baseline axis gate pass rate: `{evidence['baseline_axis_gate_pass_rate']}`",
        f"- candidate axis gate pass rate: `{evidence['candidate_axis_gate_pass_rate']}`",
        f"- candidate runtime coverage: `{evidence['candidate_runtime_coverage']}`",
        (
            "- baseline workflow profile decision: "
            f"`{evidence['baseline_workflow_profile_decision']}`"
        ),
        (
            "- candidate workflow profile decision: "
            f"`{evidence['candidate_workflow_profile_decision']}`"
        ),
        (
            "- candidate workflow maturation rate: "
            f"`{evidence['candidate_workflow_maturation_rate']}`"
        ),
        (
            "- baseline memory causality decision: "
            f"`{evidence['baseline_memory_causality_decision']}`"
        ),
        (
            "- candidate memory causality decision: "
            f"`{evidence['candidate_memory_causality_decision']}`"
        ),
        (
            "- candidate memory causal rate: "
            f"`{evidence['candidate_memory_causal_rate']}`"
        ),
        (
            "- candidate memory attached-only rate: "
            f"`{evidence['candidate_memory_attached_only_rate']}`"
        ),
        (
            "- baseline mind-domain-specialist decision: "
            f"`{evidence['baseline_mind_domain_specialist_decision']}`"
        ),
        (
            "- candidate mind-domain-specialist decision: "
            f"`{evidence['candidate_mind_domain_specialist_decision']}`"
        ),
        (
            "- candidate mind-domain-specialist alignment rate: "
            f"`{evidence['candidate_mind_domain_specialist_alignment_rate']}`"
        ),
        (
            "- baseline cognitive recomposition decision: "
            f"`{evidence['baseline_cognitive_recomposition_decision']}`"
        ),
        (
            "- candidate cognitive recomposition decision: "
            f"`{evidence['candidate_cognitive_recomposition_decision']}`"
        ),
        (
            "- candidate cognitive recomposition coherent rate: "
            f"`{evidence['candidate_cognitive_recomposition_coherent_rate']}`"
        ),
        "",
        "## Metas atendidas",
        "",
    ]
    for item in payload["goals_met"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Entra no proximo corte do v2", ""])
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
    lines.extend(["", "## Racional da decisao", "", payload["decision_rationale"]])
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
    (output_dir / "cut_closure.json").write_text(
        dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (output_dir / "cut_closure.md").write_text(
        render_markdown(payload),
        encoding="utf-8",
    )
    if args.format == "json":
        print(dumps(payload, ensure_ascii=True, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
