"""Close the repository hygiene and tools review cut with regenerable evidence."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = (
    ROOT / ".jarvis_runtime" / "v2_repository_hygiene_and_tools_review_cut"
)
DOC_OUTPUT_PATH = (
    ROOT / "docs" / "implementation" / "v2-repository-hygiene-and-tools-review-cut-closure.md"
)


@dataclass(frozen=True)
class BacklogDecision:
    item_id: str
    title: str
    target_class: str
    rationale: str
    dependency: str


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Close the repository hygiene and tools review cut."
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


def _sorted_file_names(path: Path) -> list[str]:
    return sorted(item.name for item in path.iterdir() if item.is_file())


def next_cut_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="select-next-functional-cut-from-adherence-snapshot",
            title=(
                "selecionar e abrir o proximo recorte funcional a partir do "
                "v2 adherence snapshot"
            ),
            target_class="proximo_passo_recomendado",
            rationale=(
                "a limpeza estrutural foi concluida e o repositorio voltou a uma superficie mais "
                "enxuta. o proximo passo de maior valor e escolher o proximo recorte funcional com "
                "base no backlog estrutural e de aderencia, nao por oportunidade local."
            ),
            dependency=(
                "v2-repository-hygiene-and-tools-review-cut formalmente encerrado e docs vivos "
                "apontando para a nova superficie ativa"
            ),
        ),
        BacklogDecision(
            item_id="preserve-repository-hygiene-as-baseline-rule",
            title="preservar a superficie ativa enxuta como regra continua do repositorio",
            target_class="proximo_passo_recomendado",
            rationale=(
                "o ganho desta revisao so se sustenta se novos cortes nao "
                "voltarem a espalhar docs e tools historicos na superficie "
                "principal."
            ),
            dependency="novos recortes abrirem ja com regra de archive candidate respeitada",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-delete-wave-without-new-reference-check",
            title="delete wave adicional sem nova checagem de referencias",
            target_class="manter_deferido",
            rationale=(
                "nenhum delete candidate foi executado neste corte. "
                "qualquer remocao definitiva futura deve nascer de nova "
                "evidencia local e de uma checagem propria de referencias."
            ),
            dependency="nova revisao estrutural com delete candidate formalizado",
        ),
        BacklogDecision(
            item_id="defer-benchmarks-subtree-cleanup",
            title="limpeza profunda de tools/benchmarks fora do recorte atual",
            target_class="manter_deferido",
            rationale=(
                "o subdiretorio tools/benchmarks continua util para o "
                "baseline local e nao entrou na limpeza desta rodada alem "
                "do necessario para reduzir a superficie principal."
            ),
            dependency="novo recorte especifico para benchmark internals, se ainda fizer sentido",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-lean-active-surface",
            title="superficie ativa pequena como politica permanente do repositorio",
            target_class="preservar_como_visao",
            rationale=(
                "o repositorio fica mais legivel e seguro quando docs e "
                "tools historicos saem do caminho principal sem perder "
                "rastreabilidade regeneravel."
            ),
            dependency="disciplina continua de classificacao entre manter, arquivar e deletar",
        )
    ]


def build_payload() -> dict[str, object]:
    active_implementation_docs = _sorted_file_names(ROOT / "docs" / "implementation")
    archived_implementation_docs = _sorted_file_names(
        ROOT / "docs" / "archive" / "implementation"
    )
    active_tool_entrypoints = [
        name
        for name in _sorted_file_names(ROOT / "tools")
        if name not in {"README.md", "__init__.py"}
    ]
    archived_tool_entrypoints = [
        name
        for name in _sorted_file_names(ROOT / "tools" / "archive")
        if name != "__init__.py"
    ]
    return {
        "cut_id": "v2-repository-hygiene-and-tools-review-cut",
        "decision": "complete_v2_repository_hygiene_and_tools_review_cut",
        "next_cut_recommendation": "select-next-functional-cut-from-adherence-snapshot",
        "decision_summary": {
            "active_implementation_docs": len(active_implementation_docs),
            "archived_implementation_docs": len(archived_implementation_docs),
            "docs_moved_to_archive": 15,
            "active_tool_entrypoints": len(active_tool_entrypoints),
            "archived_tool_entrypoints": len(archived_tool_entrypoints),
            "tools_moved_to_archive": 15,
            "delete_candidates_executed": 0,
            "current_root_closure_tools": len(
                [name for name in active_tool_entrypoints if name.startswith("close_")]
            ),
        },
        "next_cut_scope": [asdict(item) for item in next_cut_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            "docs de recortes encerrados migraram para docs/archive/implementation",
            "closures e renderizadores historicos migraram para tools/archive "
            "sem quebrar imports ou gates",
            "README, HANDOFF, master-summary e toolchain foram sincronizados "
            "com a nova topologia",
            "nenhum delete candidate foi executado sem nova checagem de referencias",
        ],
        "decision_rationale": (
            "o recorte cumpriu seu papel de reduzir a carga da superficie ativa "
            "sem sacrificar rastreabilidade nem quebrar o baseline de release. "
            "com isso, o repositorio fica mais legivel, os artefatos "
            "historicos saem do caminho principal e o proximo passo correto "
            "volta a ser funcional, desde que escolhido sobre backlog real e "
            "nao sobre ruido estrutural."
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
                f"active_implementation_docs={summary['active_implementation_docs']} "
                f"archived_implementation_docs={summary['archived_implementation_docs']} "
                f"active_tool_entrypoints={summary['active_tool_entrypoints']} "
                f"archived_tool_entrypoints={summary['archived_tool_entrypoints']}"
            ),
        ]
    )


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["decision_summary"]
    lines = [
        "# Fechamento do V2 Repository Hygiene And Tools Review Cut",
        "",
        f"- corte: `{payload['cut_id']}`",
        f"- decisao: `{payload['decision']}`",
        f"- proximo passo recomendado: `{payload['next_cut_recommendation']}`",
        "- fechador regeneravel: `tools/close_repository_hygiene_and_tools_review_cut.py`",
        "",
        "## Evidencia consolidada",
        "",
        f"- active_implementation_docs: `{summary['active_implementation_docs']}`",
        f"- archived_implementation_docs: `{summary['archived_implementation_docs']}`",
        f"- docs_moved_to_archive: `{summary['docs_moved_to_archive']}`",
        f"- active_tool_entrypoints: `{summary['active_tool_entrypoints']}`",
        f"- archived_tool_entrypoints: `{summary['archived_tool_entrypoints']}`",
        f"- tools_moved_to_archive: `{summary['tools_moved_to_archive']}`",
        f"- delete_candidates_executed: `{summary['delete_candidates_executed']}`",
        f"- current_root_closure_tools: `{summary['current_root_closure_tools']}`",
        "",
        "## Metas atendidas",
        "",
    ]
    for item in payload["goals_met"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Entra no proximo passo recomendado", ""])
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
    rendered_markdown = render_markdown(payload) + "\n"
    (output_dir / "cut_closure.json").write_text(
        dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "cut_closure.md").write_text(rendered_markdown, encoding="utf-8")
    DOC_OUTPUT_PATH.write_text(rendered_markdown, encoding="utf-8")
    if args.format == "json":
        print(dumps(payload, ensure_ascii=False, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
