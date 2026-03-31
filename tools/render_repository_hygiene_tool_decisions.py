"""Render formal tool decisions for the repository hygiene cut."""

from __future__ import annotations

from json import dumps
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_repository_hygiene_and_tools_review_cut"
OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-repository-hygiene-tool-decisions.md"


def build_payload() -> dict[str, object]:
    keep_active = [
        {
            "tool": "check_mojibake.py",
            "decision": "manter",
            "rationale": (
                "continua sendo validacao basica de hygiene e encoding do repositorio"
            ),
        },
        {
            "tool": "engineering_gate.py",
            "decision": "manter",
            "rationale": "e o gate central do baseline e nao pode sair da superficie ativa",
        },
        {
            "tool": "fix_mojibake.py",
            "decision": "manter",
            "rationale": (
                "segue util como ferramenta de reparo controlado "
                "quando houver contaminacao real"
            ),
        },
        {
            "tool": "go_live_internal_checklist.py",
            "decision": "manter",
            "rationale": (
                "permanece no baseline de validacao operacional e readiness local"
            ),
        },
        {
            "tool": "validate_baseline.py",
            "decision": "manter",
            "rationale": "continua como validacao executavel do baseline oficial",
        },
        {
            "tool": "verify_active_cut_baseline.py",
            "decision": "manter",
            "rationale": (
                "ainda ancora o estado release-grade do ultimo recorte funcional fechado"
            ),
        },
        {
            "tool": "verify_axis_artifacts.py",
            "decision": "manter",
            "rationale": (
                "continua como verificador de coerencia minima "
                "entre artefatos vivos do programa"
            ),
        },
        {
            "tool": "compare_orchestrator_paths.py",
            "decision": "manter",
            "rationale": (
                "segue util para comparacao operacional entre baseline e fluxo opcional"
            ),
        },
        {
            "tool": "evolution_from_pilot.py",
            "decision": "manter",
            "rationale": (
                "continua traduzindo sinais do piloto em propostas sandbox-only"
            ),
        },
        {
            "tool": "internal_pilot_report.py",
            "decision": "manter",
            "rationale": (
                "permanece como leitura curta das evidencias recentes do piloto"
            ),
        },
        {
            "tool": "internal_pilot_support.py",
            "decision": "manter",
            "rationale": (
                "continua fornecendo agregacao de suporte ao piloto e comparadores"
            ),
        },
        {
            "tool": "operational_artifacts.py",
            "decision": "manter",
            "rationale": (
                "permanece util na persistencia e leitura "
                "de artefatos operacionais locais"
            ),
        },
        {
            "tool": "run_internal_pilot.py",
            "decision": "manter",
            "rationale": "segue como entrypoint executavel do internal pilot oficial",
        },
        {
            "tool": "render_repository_hygiene_inventory.py",
            "decision": "manter",
            "rationale": (
                "e o renderizador base do corte ativo de higiene do repositorio"
            ),
        },
        {
            "tool": "render_repository_hygiene_doc_decisions.py",
            "decision": "manter",
            "rationale": (
                "e o artefato regeneravel que ancora a classificacao dos docs ativos"
            ),
        },
        {
            "tool": "render_repository_hygiene_tool_decisions.py",
            "decision": "manter",
            "rationale": (
                "passa a registrar de forma regeneravel a classificacao "
                "dos entrypoints de tools"
            ),
        },
        {
            "tool": "close_native_memory_scope_hardening_cut.py",
            "decision": "manter",
            "rationale": (
                "closure funcional mais recente ainda ancora a transicao "
                "para o corte estrutural atual"
            ),
        },
    ]
    archive_candidates = [
        {
            "tool": "close_alignment_cycle.py",
            "decision": "arquivar",
            "rationale": (
                "fecha ciclo historico ja encerrado e fora do caminho critico atual"
            ),
        },
        {
            "tool": "close_continuity_cycle.py",
            "decision": "arquivar",
            "rationale": (
                "closure historico do pos-v1, preservavel "
                "sem ficar na superficie principal"
            ),
        },
        {
            "tool": "close_domain_consumers_and_workflows_cut.py",
            "decision": "arquivar",
            "rationale": (
                "closure de recorte funcional encerrado "
                "e ja sucedido por cortes posteriores"
            ),
        },
        {
            "tool": "close_governed_benchmark_execution_cut.py",
            "decision": "arquivar",
            "rationale": (
                "closure de benchmark encerrado, relevante como historico "
                "mas nao como tooling ativo"
            ),
        },
        {
            "tool": "close_memory_gap_evidence_cut.py",
            "decision": "arquivar",
            "rationale": (
                "closure de recorte encerrado, preservavel "
                "sem permanecer na area viva"
            ),
        },
        {
            "tool": "close_sovereign_alignment_cut.py",
            "decision": "arquivar",
            "rationale": (
                "closure importante do corte soberano, mas hoje ja e historico"
            ),
        },
        {
            "tool": "close_specialization_cycle.py",
            "decision": "arquivar",
            "rationale": (
                "closure historico de especializacao, fora do recorte operacional atual"
            ),
        },
        {
            "tool": "close_stateful_runtime_cycle.py",
            "decision": "arquivar",
            "rationale": (
                "closure historico do ciclo stateful, preservavel como auditoria"
            ),
        },
        {
            "tool": "render_governed_benchmark_decisions.py",
            "decision": "arquivar",
            "rationale": "renderizador de artefato fechado do benchmark governado",
        },
        {
            "tool": "render_governed_benchmark_execution_plan.py",
            "decision": "arquivar",
            "rationale": (
                "artefato regeneravel de recorte encerrado, "
                "nao mais parte da superficie ativa"
            ),
        },
        {
            "tool": "render_governed_benchmark_matrix.py",
            "decision": "arquivar",
            "rationale": (
                "matriz historica do benchmark, preservavel "
                "sem continuar no topo do tooling vivo"
            ),
        },
        {
            "tool": "render_governed_benchmark_scenario_specs.py",
            "decision": "arquivar",
            "rationale": (
                "scenario specs de benchmark pertencem ao historico regeneravel "
                "do recorte encerrado"
            ),
        },
        {
            "tool": "render_memory_gap_baseline_evidence.py",
            "decision": "arquivar",
            "rationale": (
                "evidencia de lacuna de memoria ja usada "
                "e sucedida pelo endurecimento nativo"
            ),
        },
        {
            "tool": "render_memory_gap_decision.py",
            "decision": "arquivar",
            "rationale": (
                "decisao formal de recorte encerrado, relevante para auditoria "
                "e nao para uso diario"
            ),
        },
        {
            "tool": "render_memory_gap_evidence_protocol.py",
            "decision": "arquivar",
            "rationale": (
                "protocolo regeneravel de recorte encerrado, "
                "fora da superficie ativa atual"
            ),
        },
    ]
    delete_candidates: list[dict[str, str]] = []
    return {
        "cut_id": "v2-repository-hygiene-and-tools-review-cut",
        "sprint_id": "sprint-3-tools-classification",
        "scope_note": (
            "esta sprint classifica os entrypoints da raiz de tools. "
            "internals de tools/benchmarks permanecem fora da limpeza imediata "
            "por ainda sustentarem benchmark local e validacao auxiliar"
        ),
        "summary": {
            "keep_active": len(keep_active),
            "archive_candidates": len(archive_candidates),
            "delete_candidates": len(delete_candidates),
            "total_classified": (
                len(keep_active) + len(archive_candidates) + len(delete_candidates)
            ),
        },
        "keep_active": keep_active,
        "archive_candidates": archive_candidates,
        "delete_candidates": delete_candidates,
        "guardrails": [
            (
                "nenhuma ferramenta exigida por engineering_gate ou verify_axis_artifacts "
                "entra em archive ou delete sem substituto explicito"
            ),
            (
                "closures e renderizadores de recortes fechados so migram de fato "
                "na Sprint 4, apos checagem de referencias vivas"
            ),
            (
                "nenhuma ferramenta entra em delete candidate nesta sprint porque o foco "
                "ainda e reduzir ruido sem perder auditabilidade"
            ),
        ],
        "decision_rationale": (
            "a classificacao desta sprint separa tooling realmente vivo do baseline atual "
            "do tooling regeneravel historico. permanecem ativos os gates, verificadores, "
            "ferramentas do piloto, artefatos do corte de higiene e o ultimo closure funcional. "
            "renderizadores e closures de recortes ja encerrados passam a archive candidate. "
            "nao ha delete candidate nesta fase porque a limpeza segura ainda depende da Sprint 4 "
            "e da checagem final de referencias."
        ),
    }


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        "# V2 Repository Hygiene Tool Decisions",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- scope_note: {payload['scope_note']}",
        "",
        "## Summary",
        "",
        f"- keep_active: `{summary['keep_active']}`",
        f"- archive_candidates: `{summary['archive_candidates']}`",
        f"- delete_candidates: `{summary['delete_candidates']}`",
        f"- total_classified: `{summary['total_classified']}`",
        "",
        "## Keep Active",
        "",
    ]
    for item in payload["keep_active"]:
        lines.append(f"- `{item['tool']}`")
        lines.append(f"  decisao: `{item['decision']}`; racional: {item['rationale']}")
    lines.extend(["", "## Archive Candidates", ""])
    for item in payload["archive_candidates"]:
        lines.append(f"- `{item['tool']}`")
        lines.append(f"  decisao: `{item['decision']}`; racional: {item['rationale']}")
    lines.extend(["", "## Delete Candidates", ""])
    if payload["delete_candidates"]:
        for item in payload["delete_candidates"]:
            lines.append(f"- `{item['tool']}`")
            lines.append(f"  decisao: `{item['decision']}`; racional: {item['rationale']}")
    else:
        lines.append("- nenhuma ferramenta entra em delete candidate nesta sprint")
    lines.extend(["", "## Guardrails", ""])
    for item in payload["guardrails"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Decision Rationale", "", payload["decision_rationale"], ""])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "tool_decisions.json").write_text(
        dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"rendered={OUTPUT_PATH.relative_to(ROOT)} "
        f"classified={payload['summary']['total_classified']}"
    )


if __name__ == "__main__":
    main()
