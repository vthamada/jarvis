"""Close the first post-v1 cycle and emit a formal cut between v1.5 and v2."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
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


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the first post-v1 cycle.")
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
        "--limit",
        type=int,
        default=20,
        help="Maximum number of recent request traces to inspect.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / ".jarvis_runtime" / "post_v1_cycle"),
        help="Directory where cycle closure artifacts will be written.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def v1_5_backlog() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="v15-runtime-checkpoints",
            title="checkpoint e replay governados da continuidade",
            target_phase="v1.5",
            rationale=(
                "e o menor salto estrutural capaz de transformar continuidade profunda em "
                "runtime stateful recuperavel, sem abrir ainda especializacao ampla."
            ),
            dependency="base funcional das Sprints 1 a 5 e fluxo opcional de LangGraph",
        ),
        BacklogDecision(
            item_id="v15-hitl-pauses",
            title="pausas HITL em conflitos de continuidade",
            target_phase="v1.5",
            rationale=(
                "continuidade ja ficou funcional e observavel; o passo seguinte e permitir "
                "pausa governada antes de retomadas sensiveis."
            ),
            dependency="governanca atual e trilha de continuidade auditavel",
        ),
        BacklogDecision(
            item_id="v15-langgraph-partial-absorption",
            title="absorcao parcial de LangGraph no subfluxo de continuidade",
            target_phase="v1.5",
            rationale=(
                "o estudo e a trilha opcional ja apontam encaixe em checkpoint, replay e "
                "stateful execution sem reescrever o nucleo inteiro."
            ),
            dependency="benchmark comparativo baseline vs langgraph_flow",
        ),
        BacklogDecision(
            item_id="v15-continuity-evals",
            title="evals operacionais da continuidade profunda",
            target_phase="v1.5",
            rationale=(
                "o ciclo atual criou auditoria e sinais; o proximo precisa transformar isso "
                "em avaliacao repetivel de runtime e recuperacao."
            ),
            dependency="observabilidade e internal pilot report endurecidos na Sprint 5",
        ),
    ]


def v2_backlog() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="v2-specialists",
            title="especialistas subordinados maduros por dominio",
            target_phase="v2",
            rationale=(
                "especializacao ampla ainda depende de runtime mais stateful e de memoria "
                "mais profunda do que o corte atual comporta."
            ),
            dependency="v1.5 consolidado e governanca de subfluxos madura",
        ),
        BacklogDecision(
            item_id="v2-deep-memory",
            title="memoria semantica profunda com pgvector e retrieval mais rico",
            target_phase="v2",
            rationale=(
                "o ciclo atual resolveu continuidade acima da missao; memoria semantica "
                "profunda ainda precisa consumidor canonico e benchmark proprio."
            ),
            dependency="fechamento do runtime stateful de v1.5",
        ),
        BacklogDecision(
            item_id="v2-computer-use",
            title="computer use governado e operacao ampla do computador",
            target_phase="v2",
            rationale=(
                "essa camada amplia risco e superficie operacional antes da consolidacao "
                "do nucleo cognitivo do v1.5."
            ),
            dependency="governanca reforcada e trilha operacional madura",
        ),
        BacklogDecision(
            item_id="v2-voice-runtime",
            title="voz e realtime como superficie oficial",
            target_phase="v2",
            rationale=(
                "voz amplia interface, nao resolve a lacuna principal do ciclo atual, e "
                "deve entrar com nucleo stateful mais maduro."
            ),
            dependency="v1.5 estavel e runtime governado ja consolidado",
        ),
        BacklogDecision(
            item_id="v2-operational-assistant",
            title="assistencia operacional ampla e workflows pessoais",
            target_phase="v2",
            rationale=(
                "camada operacional ampla depende de memoria mais rica, especialistas e "
                "governanca mais madura do que o salto imediato."
            ),
            dependency="especialistas e memoria profunda de v2",
        ),
    ]


def evidence_summary(
    *,
    observability_db: str,
    evolution_db: str,
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
    )


def build_payload(
    *,
    observability_db: str,
    evolution_db: str,
    limit: int,
) -> dict[str, object]:
    evidence = evidence_summary(
        observability_db=observability_db,
        evolution_db=evolution_db,
        limit=limit,
    )
    return {
        "cycle_id": "post-v1-cycle-1",
        "decision": "promote_to_v1_5",
        "evidence_summary": asdict(evidence),
        "v1_5_scope": [asdict(item) for item in v1_5_backlog()],
        "v2_scope": [asdict(item) for item in v2_backlog()],
        "goals_met": [
            "continuidade profunda funcional acima da missao atual",
            "decisao explicita entre continuar, encerrar, reformular e retomar",
            "sintese e memoria coerentes com continuidade da sessao",
            "trilha observavel e comparavel da continuidade",
        ],
        "decision_rationale": (
            "o primeiro ciclo pos-v1 fechou a base de continuidade profunda. "
            "o proximo salto correto e um runtime stateful governado de v1.5, "
            "nao uma ampliacao prematura para especializacao ampla de v2."
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
        "v1_5_scope=" + ",".join(item["item_id"] for item in payload["v1_5_scope"]),
        "v2_scope=" + ",".join(item["item_id"] for item in payload["v2_scope"]),
    ]
    return "\n".join(lines)


def render_markdown(payload: dict[str, object]) -> str:
    evidence = payload["evidence_summary"]
    lines = [
        "# Fechamento do Ciclo Pós-v1",
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
        "",
        "## Entra em v1.5",
        "",
    ]
    for item in payload["v1_5_scope"]:
        lines.extend(
            [
                f"- `{item['title']}`",
                f"  id: `{item['item_id']}`; dependencia: `{item['dependency']}`",
                f"  racional: {item['rationale']}",
            ]
        )
    lines.extend(["", "## Fica para v2", ""])
    for item in payload["v2_scope"]:
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
