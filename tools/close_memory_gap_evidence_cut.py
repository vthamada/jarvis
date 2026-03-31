"""Close the v2 memory gap evidence cut with regenerable evidence."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps, loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_memory_gap_evidence_cut"
DECISION_DATASET = ROOT / "tools" / "benchmarks" / "datasets" / "v2_memory_gap_decision.json"
DOC_OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-memory-gap-evidence-cut-closure.md"
EVIDENCE_DATASET = (
    ROOT / "tools" / "benchmarks" / "datasets" / "v2_memory_gap_baseline_scope_rules.json"
)


@dataclass(frozen=True)
class BacklogDecision:
    item_id: str
    title: str
    target_class: str
    rationale: str
    dependency: str


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the v2 memory gap evidence cut.")
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


def load_decision_dataset() -> dict[str, object]:
    return loads(DECISION_DATASET.read_text(encoding="utf-8-sig"))


def load_evidence_dataset() -> dict[str, object]:
    return loads(EVIDENCE_DATASET.read_text(encoding="utf-8-sig"))


def next_cut_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="v2-native-memory-scope-hardening-cut",
            title="endurecimento nativo de user scope e shared specialist scope",
            target_class="proximo_corte_recomendado",
            rationale=(
                "a evidencia provou lacuna parcial em user scope e shared specialist scope, "
                "mas ainda nao justificou absorcao externa. o proximo corte correto e endurecer "
                "essas camadas no proprio baseline soberano."
            ),
            dependency=(
                "memory gap cut formalmente encerrado e backlog traduzido para contratos e "
                "runtime nativos"
            ),
        ),
        BacklogDecision(
            item_id="v2-user-scope-runtime-contracts",
            title="contratos e leitura runtime mais ricos para user scope",
            target_class="proximo_corte_recomendado",
            rationale=(
                "o user scope apareceu como tipado e rastreado, mas ainda nao como memoria runtime "
                "rica comparavel a session e mission continuity."
            ),
            dependency="consumer canonico e escrita mediada pelo nucleo",
        ),
        BacklogDecision(
            item_id="v2-recurrent-specialist-context-hardening",
            title="endurecimento do contexto recorrente para especialistas promovidos",
            target_class="proximo_corte_recomendado",
            rationale=(
                "specialist_shared_memory hoje cobre handoff, mas ainda nao prova um escopo mais "
                "forte por agente ou participante recorrente."
            ),
            dependency="medicao de reentrada recorrente no runtime atual",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-mem0-absorption",
            title="absorcao de Mem0 no baseline central",
            target_class="manter_deferido",
            rationale=(
                "o recorte fechou em `manter_fechado`; `Mem0` continua candidata condicional e "
                "nao entra no baseline sem nova evidencia soberana."
            ),
            dependency="novo recorte formal com lacuna comprovada acima do baseline endurecido",
        ),
        BacklogDecision(
            item_id="defer-organization-scope-rollout",
            title="promocao de organization scope para runtime principal",
            target_class="manter_deferido",
            rationale=(
                "organization scope permaneceu forma futura e ainda nao apareceu como necessidade "
                "operacional comprovada no runtime atual."
            ),
            dependency="consumidor canonico soberano acima de user e session",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-multilayer-memory-without-core-loss",
            title="memoria multicamada mais rica sem perda de soberania do nucleo",
            target_class="preservar_como_visao",
            rationale=(
                "o sistema pode ganhar mais camadas de memoria no futuro, mas essa evolucao deve "
                "continuar subordinada a registry, governanca e escrita mediada pelo nucleo."
            ),
            dependency="mais de um ciclo fechado de endurecimento nativo e nova evidencia local",
        )
    ]


def build_payload() -> dict[str, object]:
    decision = load_decision_dataset()
    evidence = load_evidence_dataset()
    scopes = list(evidence["scopes"])
    scope_totals = {
        "scope_count": len(scopes),
        "implemented": sum(
            1 for scope in scopes if scope["status_when_rules_match"] == "implemented"
        ),
        "partial_gap_candidates": sum(
            1
            for scope in scopes
            if scope["gap_read_when_rules_match"] == "partial_gap_supported"
        ),
        "future_shape_only": sum(
            1
            for scope in scopes
            if scope["gap_read_when_rules_match"] == "not_proven_gap"
        ),
    }
    return {
        "cut_id": "v2-memory-gap-evidence-cut",
        "decision": "complete_v2_memory_gap_evidence_cut",
        "next_cut_recommendation": "v2-native-memory-scope-hardening-cut",
        "decision_summary": {
            "final_decision": decision["final_decision"],
            "mem0_status": decision["mem0_status"],
            **scope_totals,
        },
        "next_cut_scope": [asdict(item) for item in next_cut_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            (
                "a hipotese de memory gap virou protocolo, evidencia local e decisao "
                "formal regeneravel"
            ),
            (
                "o recorte provou que a lacuna atual e parcial e nao suficiente para "
                "reabrir absorcao externa"
            ),
            "Mem0 permaneceu em absorver_depois sem promover dependencia central nova",
            "o proximo passo ficou traduzido para endurecimento nativo do baseline",
        ],
        "decision_rationale": (
            "o recorte cumpriu seu papel de quebrar a hipotese de memoria multicamada em "
            "evidencia soberana. a leitura final e que existe pressao parcial sobre user "
            "scope e shared specialist scope, mas ainda nao uma falha estrutural que "
            "justifique absorcao externa imediata. por isso, o caminho correto e endurecer "
            "primeiro o baseline nativo antes de qualquer reabertura para Mem0."
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
                "summary="
                f"final_decision={summary['final_decision']} "
                f"mem0_status={summary['mem0_status']} "
                f"scope_count={summary['scope_count']} "
                f"partial_gap_candidates={summary['partial_gap_candidates']}"
            ),
        ]
    )


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["decision_summary"]
    lines = [
        "# Fechamento do V2 Memory Gap Evidence Cut",
        "",
        f"- corte: `{payload['cut_id']}`",
        f"- decisao: `{payload['decision']}`",
        f"- proximo recorte recomendado: `{payload['next_cut_recommendation']}`",
        "",
        "## Evidencia consolidada",
        "",
        f"- final_decision: `{summary['final_decision']}`",
        f"- mem0_status: `{summary['mem0_status']}`",
        f"- scope_count: `{summary['scope_count']}`",
        f"- implemented: `{summary['implemented']}`",
        f"- partial_gap_candidates: `{summary['partial_gap_candidates']}`",
        f"- future_shape_only: `{summary['future_shape_only']}`",
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
    rendered_markdown = render_markdown(payload) + "\n"
    (output_dir / "cut_closure.md").write_text(
        rendered_markdown,
        encoding="utf-8",
    )
    DOC_OUTPUT_PATH.write_text(rendered_markdown, encoding="utf-8")
    if args.format == "json":
        print(dumps(payload, ensure_ascii=False, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
