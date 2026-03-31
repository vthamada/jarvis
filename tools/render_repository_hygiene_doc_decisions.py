"""Render formal document decisions for the repository hygiene cut."""

from __future__ import annotations

from json import dumps
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_repository_hygiene_and_tools_review_cut"
OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-repository-hygiene-doc-decisions.md"


def build_payload() -> dict[str, object]:
    keep_active = [
        {
            "document": "implementation-strategy.md",
            "decision": "manter",
            "rationale": (
                "continua sendo referencia estrutural curta para a organizacao do repositorio "
                "e nao duplica o corte ativo"
            ),
        },
        {
            "document": "service-breakdown.md",
            "decision": "manter",
            "rationale": (
                "continua util para leitura de topologia tecnica e onboarding do baseline"
            ),
        },
        {
            "document": "v2-adherence-snapshot.md",
            "decision": "manter",
            "rationale": (
                "funciona como leitura transversal por eixo e ainda orienta backlog estrutural"
            ),
        },
        {
            "document": "v2-repository-hygiene-and-tools-review-cut.md",
            "decision": "manter",
            "rationale": "e o documento ativo de execucao do corte corrente",
        },
        {
            "document": "v2-repository-hygiene-inventory.md",
            "decision": "manter",
            "rationale": "e o artefato regeneravel base da revisao estrutural ativa",
        },
        {
            "document": "v2-native-memory-scope-hardening-cut-closure.md",
            "decision": "manter",
            "rationale": (
                "e o fechamento funcional mais recente e ancora a transicao para a revisao atual"
            ),
        },
    ]
    archive_candidates = [
        {
            "document": "v2-domain-consumers-and-workflows-cut.md",
            "decision": "arquivar",
            "rationale": (
                "cut funcional ja encerrado e sucedido por closure e cortes posteriores"
            ),
        },
        {
            "document": "v2-domain-consumers-and-workflows-cut-closure.md",
            "decision": "arquivar",
            "rationale": (
                "closure historico preservavel, mas nao precisa ficar na superficie principal"
            ),
        },
        {
            "document": "v2-governed-benchmark-execution-cut.md",
            "decision": "arquivar",
            "rationale": "cut funcional ja encerrado e sem papel de execucao atual",
        },
        {
            "document": "v2-governed-benchmark-execution-plan.md",
            "decision": "arquivar",
            "rationale": (
                "artefato de apoio de recorte encerrado, util como historico regeneravel"
            ),
        },
        {
            "document": "v2-governed-benchmark-scenario-specs.md",
            "decision": "arquivar",
            "rationale": (
                "scenario specs de benchmark continuam uteis, mas ja nao pertencem a area ativa"
            ),
        },
        {
            "document": "v2-governed-benchmark-matrix.md",
            "decision": "arquivar",
            "rationale": (
                "a matriz continua relevante como historico de decisao, nao como doc ativo "
                "do momento"
            ),
        },
        {
            "document": "v2-governed-benchmark-decisions.md",
            "decision": "arquivar",
            "rationale": (
                "decisao formal preservavel, mas ja sucedida por cortes posteriores"
            ),
        },
        {
            "document": "v2-governed-benchmark-execution-cut-closure.md",
            "decision": "arquivar",
            "rationale": (
                "closure historico de benchmark, sem uso operacional direto no corte atual"
            ),
        },
        {
            "document": "v2-memory-gap-evidence-cut.md",
            "decision": "arquivar",
            "rationale": (
                "cut funcional encerrado e sucedido pelo endurecimento nativo e pela revisao atual"
            ),
        },
        {
            "document": "v2-memory-gap-evidence-protocol.md",
            "decision": "arquivar",
            "rationale": (
                "protocolo de recorte encerrado, melhor mantido como historico regeneravel"
            ),
        },
        {
            "document": "v2-memory-gap-baseline-evidence.md",
            "decision": "arquivar",
            "rationale": (
                "evidencia importante, mas ja usada e sucedida pelo cut nativo subsequente"
            ),
        },
        {
            "document": "v2-memory-gap-decision.md",
            "decision": "arquivar",
            "rationale": (
                "decisao formal preservavel, porem nao precisa ocupar a superficie ativa"
            ),
        },
        {
            "document": "v2-memory-gap-evidence-cut-closure.md",
            "decision": "arquivar",
            "rationale": "closure historico de recorte encerrado",
        },
        {
            "document": "v2-native-memory-scope-hardening-cut.md",
            "decision": "arquivar",
            "rationale": (
                "ultimo cut funcional ja encerrado e sucedido por closure mais novo"
            ),
        },
        {
            "document": "v2-sovereign-alignment-cut-closure.md",
            "decision": "arquivar",
            "rationale": (
                "closure importante, mas suficientemente historico para sair da superficie ativa"
            ),
        },
    ]
    delete_candidates: list[dict[str, str]] = []
    return {
        "cut_id": "v2-repository-hygiene-and-tools-review-cut",
        "sprint_id": "sprint-2-docs-classification",
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
                "nenhum arquivo classificado como arquivar deve ser movido antes da Sprint 4 "
                "do corte"
            ),
            (
                "nenhum documento em delete candidate pode existir sem checagem previa de "
                "referencias vivas"
            ),
            (
                "closures mais recentes continuam preservadas ativas ate a limpeza final "
                "confirmar substitutos e navegacao"
            ),
        ],
        "decision_rationale": (
            "a classificacao desta sprint privilegia reducao de ruido sem perder "
            "rastreabilidade. por isso, os documentos que ainda explicam a fase atual ou a "
            "topologia do repositorio permanecem ativos, enquanto cuts, planos e evidencias "
            "de recortes ja encerrados passam a candidatos de arquivamento. nao ha delete "
            "candidate nesta fase porque todos os documentos restantes ainda possuem valor "
            "de auditoria."
        ),
    }


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        "# V2 Repository Hygiene Doc Decisions",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
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
        lines.append(f"- `{item['document']}`")
        lines.append(f"  decisao: `{item['decision']}`; racional: {item['rationale']}")
    lines.extend(["", "## Archive Candidates", ""])
    for item in payload["archive_candidates"]:
        lines.append(f"- `{item['document']}`")
        lines.append(f"  decisao: `{item['decision']}`; racional: {item['rationale']}")
    lines.extend(["", "## Delete Candidates", ""])
    if payload["delete_candidates"]:
        for item in payload["delete_candidates"]:
            lines.append(f"- `{item['document']}`")
            lines.append(f"  decisao: `{item['decision']}`; racional: {item['rationale']}")
    else:
        lines.append("- nenhum documento entra em delete candidate nesta sprint")
    lines.extend(["", "## Guardrails", ""])
    for item in payload["guardrails"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Decision Rationale", "", payload["decision_rationale"], ""])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "doc_decisions.json").write_text(
        dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"rendered={OUTPUT_PATH.relative_to(ROOT)} "
        f"classified={payload['summary']['total_classified']}"
    )


if __name__ == "__main__":
    main()

