"""Verify identity and minimum preservation of critical project documents."""

from __future__ import annotations

import re
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from json import dumps
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATE_HEADING_PATTERN = re.compile(r"^## \d{4}-\d{2}-\d{2}$", re.MULTILINE)


@dataclass(frozen=True)
class DocumentGuardrailSpec:
    path: str
    required_heading: str
    required_markers: tuple[str, ...]
    minimum_dated_sections: int | None = None
    required_history_anchor: str | None = None


DOCUMENT_SPECS = (
    DocumentGuardrailSpec(
        path="CHANGELOG.md",
        required_heading="# CHANGELOG",
        required_markers=("## 2026-03-16", "## 2026-03-31"),
        minimum_dated_sections=15,
        required_history_anchor="## 2026-03-16",
    ),
    DocumentGuardrailSpec(
        path="HANDOFF.md",
        required_heading="# HANDOFF",
        required_markers=(
            "## Metadata",
            "### Foco operacional atual",
            "## Meta atual",
        ),
    ),
    DocumentGuardrailSpec(
        path="documento_mestre_jarvis.md",
        required_heading="# Documento-Mestre do JARVIS",
        required_markers=(
            "## 1. Finalidade do documento",
            "## 2. Defini",
        ),
    ),
    DocumentGuardrailSpec(
        path="docs/roadmap/programa-ate-v3.md",
        required_heading="# Programa ate V3",
        required_markers=(
            "## 1. Objetivo",
            "## 2. Estado de partida real",
            "## 3. Eixos oficiais de evolucao",
        ),
    ),
    DocumentGuardrailSpec(
        path="docs/implementation/v2-adherence-snapshot.md",
        required_heading="# V2 Adherence Snapshot",
        required_markers=(
            "## 1. Objetivo",
            "## 2. Fotografia atual",
            "## 3. Leitura por eixo",
        ),
    ),
)


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Verify identity and historical floor of critical project documents."
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _dated_headings_are_non_increasing(text: str) -> bool:
    headings = DATE_HEADING_PATTERN.findall(text)
    return headings == sorted(headings, reverse=True)


def _build_document_result(
    spec: DocumentGuardrailSpec,
    *,
    root: Path,
) -> dict[str, object]:
    path = root / spec.path
    if not path.exists():
        return {
            "path": spec.path,
            "status": "missing",
            "required_heading": spec.required_heading,
            "actual_heading": "",
            "missing_markers": list(spec.required_markers),
            "minimum_dated_sections": spec.minimum_dated_sections,
            "dated_sections_found": 0,
            "required_history_anchor": spec.required_history_anchor,
            "history_anchor_present": False,
        }

    text = _read_text(path)
    actual_heading = _first_non_empty_line(text)
    missing_markers = [marker for marker in spec.required_markers if marker not in text]
    dated_sections_found = len(DATE_HEADING_PATTERN.findall(text))
    dated_headings_non_increasing = _dated_headings_are_non_increasing(text)
    history_anchor_present = (
        True if spec.required_history_anchor is None else spec.required_history_anchor in text
    )

    status = "ok"
    if actual_heading != spec.required_heading:
        status = "identity_drift"
    elif missing_markers:
        status = "structure_drift"
    elif (
        spec.minimum_dated_sections is not None
        and dated_sections_found < spec.minimum_dated_sections
    ):
        status = "history_floor_regressed"
    elif spec.minimum_dated_sections is not None and not dated_headings_non_increasing:
        status = "date_order_regressed"
    elif not history_anchor_present:
        status = "history_anchor_missing"

    return {
        "path": spec.path,
        "status": status,
        "required_heading": spec.required_heading,
        "actual_heading": actual_heading,
        "missing_markers": missing_markers,
        "minimum_dated_sections": spec.minimum_dated_sections,
        "dated_sections_found": dated_sections_found,
        "dated_headings_non_increasing": dated_headings_non_increasing,
        "required_history_anchor": spec.required_history_anchor,
        "history_anchor_present": history_anchor_present,
    }


def build_payload(*, root: Path = ROOT) -> dict[str, object]:
    documents = [_build_document_result(spec, root=root) for spec in DOCUMENT_SPECS]
    failed_documents = [document for document in documents if document["status"] != "ok"]
    return {
        "decision": (
            "document_guardrails_ok"
            if not failed_documents
            else "document_guardrails_failed"
        ),
        "summary": {
            "documents_checked": len(documents),
            "documents_failed": len(failed_documents),
        },
        "documents": documents,
    }


def render_text(payload: dict[str, object]) -> str:
    lines = [
        f"decision={payload['decision']}",
        f"documents_checked={payload['summary']['documents_checked']}",
        f"documents_failed={payload['summary']['documents_failed']}",
    ]
    for document in payload["documents"]:
        lines.append(
            (
                f"{document['path']} status={document['status']} "
                f"heading={document['actual_heading'] or '<empty>'}"
            )
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = build_payload()
    if args.format == "json":
        print(dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(payload))
    if payload["decision"] != "document_guardrails_ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
