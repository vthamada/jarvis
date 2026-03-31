"""Close the v2 native memory scope hardening cut with regenerable evidence."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path

from shared.contracts import SpecialistSharedMemoryContextContract, UserScopeContextContract
from shared.memory_registry import (
    DEFAULT_MEMORY_SCOPES,
    SHARED_MEMORY_CLASSES,
    organization_scope_guard_payload,
    policy_for,
)
from shared.types import MemoryClass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_native_memory_scope_hardening_cut"
DOC_OUTPUT_PATH = (
    ROOT / "docs" / "implementation" / "v2-native-memory-scope-hardening-cut-closure.md"
)


@dataclass(frozen=True)
class BacklogDecision:
    item_id: str
    title: str
    target_class: str
    rationale: str
    dependency: str


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Close the v2 native memory scope hardening cut.")
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


def recurrent_field_names() -> list[str]:
    return sorted(
        name
        for name in SpecialistSharedMemoryContextContract.__dataclass_fields__
        if name.startswith("recurrent_")
    )


def next_cut_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="repository-hygiene-and-tools-review",
            title="revisao estrutural de docs e tools antes do proximo corte",
            target_class="proximo_passo_recomendado",
            rationale=(
                "o baseline nativo ficou mais forte, mas a proxima melhoria "
                "de maior valor agora e reduzir carga documental e revisar "
                "o que permanece ativo em tools antes de abrir outra frente funcional."
            ),
            dependency=(
                "v2-native-memory-scope-hardening-cut formalmente encerrado "
                "e gate de release apontando para o fechamento correto"
            ),
        ),
        BacklogDecision(
            item_id="native-memory-followup-only-with-new-evidence",
            title="novo recorte de memoria apenas com lacuna local comprovada",
            target_class="proximo_passo_recomendado",
            rationale=(
                "o endurecimento atual resolveu o que era pressionado no baseline "
                "sem justificar absorcao externa nova. qualquer nova frente de memoria "
                "deve nascer de evidencia local."
            ),
            dependency="novo protocolo ou anomalia recorrente acima do baseline endurecido",
        ),
    ]


def deferred_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="defer-mem0-absorption",
            title="absorcao de Mem0 no baseline central",
            target_class="manter_deferido",
            rationale=(
                "Mem0 continua em absorver_depois. o recorte endureceu user scope "
                "e recorrencia de especialistas sem provar necessidade de promocao externa."
            ),
            dependency="nova evidencia local acima do baseline soberano",
        ),
        BacklogDecision(
            item_id="defer-organization-scope-rollout",
            title="promocao de organization scope para runtime principal",
            target_class="manter_deferido",
            rationale=(
                "organization scope agora esta bloqueado explicitamente no baseline "
                "e so pode reabrir com consumidor canonico soberano real."
            ),
            dependency="consumidor canonico soberano para organization scope",
        ),
    ]


def vision_scope() -> list[BacklogDecision]:
    return [
        BacklogDecision(
            item_id="vision-native-multiscope-memory",
            title="memoria nativa multicamada mais rica sem perder soberania",
            target_class="preservar_como_visao",
            rationale=(
                "o JARVIS pode evoluir para memoria mais rica por usuario, "
                "especialista e organizacao, desde que continue subordinando "
                "escrita, recovery e governanca ao nucleo."
            ),
            dependency=(
                "mais de um ciclo fechado de endurecimento nativo e evidencia "
                "comparativa local"
            ),
        )
    ]


def build_payload() -> dict[str, object]:
    organization_scope_guard = organization_scope_guard_payload()
    return {
        "cut_id": "v2-native-memory-scope-hardening-cut",
        "decision": "complete_v2_native_memory_scope_hardening_cut",
        "next_cut_recommendation": "repository-hygiene-and-tools-review",
        "decision_summary": {
            "default_recovery_scopes": len(DEFAULT_MEMORY_SCOPES),
            "specialist_shared_classes": len(SHARED_MEMORY_CLASSES),
            "user_scope_runtime_status": policy_for(MemoryClass.USER).runtime_status,
            "user_scope_contract_fields": len(UserScopeContextContract.__dataclass_fields__),
            "recurrent_context_fields": len(recurrent_field_names()),
            "organization_scope_guard_status": organization_scope_guard["status"],
            "organization_scope_reopen_signal": organization_scope_guard["reopen_signal"],
        },
        "next_cut_scope": [asdict(item) for item in next_cut_scope()],
        "deferred_scope": [asdict(item) for item in deferred_scope()],
        "vision_scope": [asdict(item) for item in vision_scope()],
        "goals_met": [
            (
                "user scope passou a ter contrato nativo, recovery default "
                "e telemetria minima no runtime"
            ),
            (
                "especialistas promovidos passaram a receber contexto "
                "recorrente nativo ainda through_core_only"
            ),
            "organization scope ficou explicitamente bloqueado sem consumidor canonico soberano",
            "o recorte terminou sem dependencia externa nova e sem reabrir Mem0 por conveniencia",
        ],
        "decision_rationale": (
            "o recorte cumpriu seu papel de endurecer os dois pontos de pressao "
            "comprovados no baseline nativo e de bloquear explicitamente a reabertura "
            "prematura de organization scope. com isso, o proximo passo mais valioso "
            "nao e abrir nova frente funcional imediatamente, e sim reduzir carga "
            "estrutural do repositorio e manter qualquer nova iniciativa de memoria "
            "condicionada a evidencia local adicional."
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
                f"default_recovery_scopes={summary['default_recovery_scopes']} "
                f"specialist_shared_classes={summary['specialist_shared_classes']} "
                f"user_scope_runtime_status={summary['user_scope_runtime_status']} "
                f"organization_scope_guard_status={summary['organization_scope_guard_status']}"
            ),
        ]
    )


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["decision_summary"]
    lines = [
        "# Fechamento do V2 Native Memory Scope Hardening Cut",
        "",
        f"- corte: `{payload['cut_id']}`",
        f"- decisao: `{payload['decision']}`",
        f"- proximo passo recomendado: `{payload['next_cut_recommendation']}`",
        "- fechador regeneravel: `tools/close_native_memory_scope_hardening_cut.py`",
        "",
        "## Evidencia consolidada",
        "",
        f"- default_recovery_scopes: `{summary['default_recovery_scopes']}`",
        f"- specialist_shared_classes: `{summary['specialist_shared_classes']}`",
        f"- user_scope_runtime_status: `{summary['user_scope_runtime_status']}`",
        f"- user_scope_contract_fields: `{summary['user_scope_contract_fields']}`",
        f"- recurrent_context_fields: `{summary['recurrent_context_fields']}`",
        f"- organization_scope_guard_status: `{summary['organization_scope_guard_status']}`",
        f"- organization_scope_reopen_signal: `{summary['organization_scope_reopen_signal']}`",
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
