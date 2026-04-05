from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from tools.verify_document_guardrails import build_payload

TEST_RUNTIME_ROOT = Path(".test_runtime") / "document_guardrails"


@contextmanager
def scratch_document_root():
    root = TEST_RUNTIME_ROOT / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        rmtree(root, ignore_errors=True)


def test_verify_document_guardrails_reports_success_for_repository() -> None:
    payload = build_payload()

    assert payload["decision"] == "document_guardrails_ok"
    assert payload["summary"]["documents_failed"] == 0
    changelog = next(
        document for document in payload["documents"] if document["path"] == "CHANGELOG.md"
    )
    assert changelog["status"] == "ok"
    assert changelog["dated_sections_found"] >= 15
    assert changelog["dated_headings_non_increasing"] is True
    assert changelog["history_anchor_present"] is True


def test_verify_document_guardrails_detects_identity_and_history_loss(
) -> None:
    with scratch_document_root() as tmp_path:
        (tmp_path / "CHANGELOG.md").write_text(
            "\n".join(
                [
                    "# Programa ate V3",
                    "",
                    "## 2026-04-01 - Replace everything",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_path / "HANDOFF.md").write_text(
            "\n".join(
                [
                    "# HANDOFF",
                    "",
                    "## Metadata",
                    "",
                    "### Foco operacional atual",
                    "",
                    "## Meta atual",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_path / "documento_mestre_jarvis.md").write_text(
            "\n".join(
                [
                    "# Documento-Mestre do JARVIS",
                    "",
                    "## 1. Finalidade do documento",
                    "",
                    "## 2. Defini",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        roadmap_dir = tmp_path / "docs" / "roadmap"
        roadmap_dir.mkdir(parents=True)
        (roadmap_dir / "programa-ate-v3.md").write_text(
            "\n".join(
                [
                    "# Programa ate V3",
                    "",
                    "## 1. Objetivo",
                    "",
                    "## 2. Estado de partida real",
                    "",
                    "## 3. Eixos oficiais de evolucao",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        implementation_dir = tmp_path / "docs" / "implementation"
        implementation_dir.mkdir(parents=True)
        (implementation_dir / "v2-adherence-snapshot.md").write_text(
            "\n".join(
                [
                    "# V2 Adherence Snapshot",
                    "",
                    "## 1. Objetivo",
                    "",
                    "## 2. Fotografia atual",
                    "",
                    "## 3. Leitura por eixo",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_payload(root=tmp_path)

    assert payload["decision"] == "document_guardrails_failed"
    assert payload["summary"]["documents_failed"] == 1
    changelog = next(
        document for document in payload["documents"] if document["path"] == "CHANGELOG.md"
    )
    assert changelog["status"] == "identity_drift"
    assert changelog["actual_heading"] == "# Programa ate V3"

def test_verify_document_guardrails_detects_date_order_regression() -> None:
    with scratch_document_root() as tmp_path:
        (tmp_path / "CHANGELOG.md").write_text(
            "\n".join(
                [
                    "# CHANGELOG",
                    "",
                    "## 2026-03-31",
                    "",
                    "## 2026-03-31",
                    "",
                    "## 2026-03-30",
                    "",
                    "## 2026-03-29",
                    "",
                    "## 2026-03-28",
                    "",
                    "## 2026-03-27",
                    "",
                    "## 2026-03-26",
                    "",
                    "## 2026-03-25",
                    "",
                    "## 2026-03-24",
                    "",
                    "## 2026-03-23",
                    "",
                    "## 2026-03-22",
                    "",
                    "## 2026-03-21",
                    "",
                    "## 2026-03-18",
                    "",
                    "## 2026-03-17",
                    "",
                    "## 2026-03-16",
                    "",
                    "## 2026-03-20",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_path / "HANDOFF.md").write_text(
            "\n".join(
                [
                    "# HANDOFF",
                    "",
                    "## Metadata",
                    "",
                    "### Foco operacional atual",
                    "",
                    "## Meta atual",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_path / "documento_mestre_jarvis.md").write_text(
            "\n".join(
                [
                    "# Documento-Mestre do JARVIS",
                    "",
                    "## 1. Finalidade do documento",
                    "",
                    "## 2. Defini",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        roadmap_dir = tmp_path / "docs" / "roadmap"
        roadmap_dir.mkdir(parents=True)
        (roadmap_dir / "programa-ate-v3.md").write_text(
            "\n".join(
                [
                    "# Programa ate V3",
                    "",
                    "## 1. Objetivo",
                    "",
                    "## 2. Estado de partida real",
                    "",
                    "## 3. Eixos oficiais de evolucao",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        implementation_dir = tmp_path / "docs" / "implementation"
        implementation_dir.mkdir(parents=True)
        (implementation_dir / "v2-adherence-snapshot.md").write_text(
            "\n".join(
                [
                    "# V2 Adherence Snapshot",
                    "",
                    "## 1. Objetivo",
                    "",
                    "## 2. Fotografia atual",
                    "",
                    "## 3. Leitura por eixo",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_payload(root=tmp_path)

    assert payload["decision"] == "document_guardrails_failed"
    changelog = next(
        document for document in payload["documents"] if document["path"] == "CHANGELOG.md"
    )
    assert changelog["status"] == "date_order_regressed"
    assert changelog["dated_headings_non_increasing"] is False
