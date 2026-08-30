from pathlib import Path

from tools.readiness_dashboard import (
    ACTIVE_STATUS_DOCS,
    GateRunResult,
    build_repository_readiness_report,
)

ROOT = Path(__file__).resolve().parents[2]
CLOSURE_PATH = (
    ROOT
    / "docs/implementation/core-learning-and-technology-readiness-closure-mb210.md"
)
RUNBOOK_PATH = (
    ROOT / "docs/operations/core-learning-and-technology-readiness-runbook.md"
)
MB_EVIDENCE = {
    "MB-202": "WorkflowPolicyDecisionContract",
    "MB-203": "SemanticMemoryCandidateContract",
    "MB-204": "ReviewedProceduralPlaybookContract",
    "MB-205": "DecisionOutcomeAttributionRecordContract",
    "MB-206": "WorkflowVariantEvalRunContract",
    "MB-207": "WorkflowLifecycleTransitionContract",
    "MB-208": "TechnologyRadarIntakeContract",
    "MB-209": "TechnologyExperimentPackContract",
}
PHASE_ORDER = ("GOV-007", "GOV-005", "ACT-005", "SFC-005")
AUTHORITY_FIELDS = (
    "autonomous_release_allowed",
    "execution_authorized",
    "execution_allowed",
    "tool_dispatch_allowed",
    "runtime_activation_allowed",
    "automatic_activation_allowed",
    "release_authorized",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
    "priority_mutation_allowed",
    "adapter_activation_allowed",
    "public_api_activation_allowed",
)
DEFERRED_MARKERS = (
    "voice/realtime",
    "rich UI",
    "browser automation",
    "computer use",
    "autonomous scheduler",
    "external integrations",
    "SO-001",
    "TA-004",
    "TA-006",
    "`DV` horizon",
    "`RH` horizon",
)


def _safe_longitudinal_payload() -> dict[str, object]:
    return {
        "report_id": "longitudinal-learning-report://mb210-closure-test",
        "report_status": "sustained_gain_observed",
        "regression_flags": [],
        "read_only": True,
        "promotion_authorized": False,
        "automatic_promotion_allowed": False,
        "core_mutation_allowed": False,
    }


def _matrix_rows(document: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in document.splitlines():
        if not line.startswith("| `MB-"):
            continue
        item_id = line.split("|", maxsplit=2)[1].strip().strip("`")
        rows[item_id] = line
    return rows


def test_mb210_closure_has_complete_bounded_evidence_matrix() -> None:
    closure = CLOSURE_PATH.read_text(encoding="utf-8")
    normalized_closure = " ".join(closure.split())
    rows = _matrix_rows(closure)

    assert tuple(rows) == tuple(MB_EVIDENCE)
    for item_id, contract_name in MB_EVIDENCE.items():
        assert contract_name in rows[item_id]
        assert "false" in rows[item_id]

    assert "framework substitution is rejected" in rows["MB-209"]
    assert "queue_exhausted" in closure
    assert "next_ready_item` | `null" in closure
    assert "status_drift` | `[]" in closure
    assert "separate reprioritization" in closure
    assert "does not fabricate a replacement `ready` item" in normalized_closure

    for authority_field in AUTHORITY_FIELDS:
        assert f"`{authority_field}` | `false`" in closure


def test_mb210_runbook_and_phase_decision_preserve_order_and_deferrals() -> None:
    closure = CLOSURE_PATH.read_text(encoding="utf-8")
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    decision = closure.split("## Explicit next-phase decision", maxsplit=1)[1]
    normalized_decision = " ".join(decision.split())

    indexes = [decision.index(f"`{item_id}`") for item_id in PHASE_ORDER]
    assert indexes == sorted(indexes)
    assert "Governed Action Foundation" in decision
    assert "must precede `SFC-005` and any public API surface" in normalized_decision
    assert "does not make `GOV-007`" in normalized_decision

    required_commands = (
        "test_core_learning_and_technology_readiness_closure.py -q",
        "verify_document_guardrails.py --format json",
        "readiness_dashboard.py --run-gate standard --format json --no-save",
    )
    assert all(command in runbook for command in required_commands)
    assert "backlog_status=queue_exhausted" in runbook
    assert "next_ready_item=null" in runbook
    assert "status_drift=[]" in runbook
    assert "autonomous_release_allowed=false" in runbook
    assert "does not open that phase" in runbook
    assert "separate reprioritization" in runbook

    combined_documents = closure + runbook
    assert all(marker in combined_documents for marker in DEFERRED_MARKERS)


def _write_mb210_closure_snapshot(root: Path) -> None:
    master_map = """# Implementation Master Map

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `OBS-007` | Regression dashboard | `implemented_baseline` | Keep stable | tools | none |
| `MEM-005` | Semantic memory influence | `partial_runtime` | Deepen | memory | candidate |
| `GOV-007` | Autonomy | `partial_runtime_enforced` | Enforce | policy | candidate |
| `GOV-005` | Adapter permissions | `minimum_baseline` | Scope adapters | governance | candidate |
| `ACT-005` | Local files | `planned` | Allowlist | GOV-007, GOV-005 | candidate |
| `SFC-005` | Public API | `missing` | Governed API | action foundation | later |
| `SFC-006` | Web UI | `deferred_by_phase` | Future | API | later |
| `SFC-007` | Voice/realtime | `deferred_by_phase` | Future | surface | not now |
| `ACT-006` | Browser automation | `deferred_by_phase` | Future | tools | not now |
| `ACT-007` | Computer use | `deferred_by_phase` | Future | tools | not now |
| `ACT-009` | Scheduler | `deferred_by_phase` | Future | governance | later |

### MB-210 -- Core Learning And Technology Readiness Closure

Status: closed in `MB-210`.
"""
    backlog_rows = "\n\n".join(
        f"### {item_id}\n\n- `status`: `completed`" for item_id in MB_EVIDENCE
    )
    backlog = f"""# Execution Backlog

{backlog_rows}

### MB-210

- `status`: `completed`
"""
    map_path = root / "docs/implementation/implementation-master-map.md"
    backlog_path = root / "docs/implementation/execution-backlog.md"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(master_map, encoding="utf-8")
    backlog_path.write_text(backlog, encoding="utf-8")
    for relative_path in ACTIVE_STATUS_DOCS:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "MB-210 is the latest closed item; the queue is exhausted.\n",
            encoding="utf-8",
        )


def _build_snapshot_report(
    root: Path,
    *,
    longitudinal_payload: dict[str, object],
):
    return build_repository_readiness_report(
        root=root,
        gate_result=GateRunResult(
            gate_mode="standard",
            gate_status="passed",
            test_status="passed",
            evidence_refs=["engineering-gate://standard/passed"],
        ),
        document_payload={"decision": "document_guardrails_ok"},
        longitudinal_payload=longitudinal_payload,
        generated_at="2026-08-29T12:00:00Z",
    )


def test_mb210_synthetic_readiness_closes_queue_without_authority(
    tmp_path: Path,
) -> None:
    _write_mb210_closure_snapshot(tmp_path)
    report = _build_snapshot_report(
        tmp_path,
        longitudinal_payload=_safe_longitudinal_payload(),
    )

    assert report.status == "ready_with_known_gaps"
    assert report.backlog_status == "queue_exhausted"
    assert report.next_ready_item is None
    assert report.status_drift == []
    assert report.blockers == []
    assert report.document_status == "healthy"
    assert report.gate_status == "passed"
    assert report.test_status == "passed"
    assert report.read_only is True
    assert report.longitudinal_learning_authority_safe is True
    assert report.autonomous_release_allowed is False

    capabilities = {item.capability_id: item for item in report.capability_results}
    for capability_id in (
        "SFC-005",
        "SFC-006",
        "SFC-007",
        "ACT-006",
        "ACT-007",
        "ACT-009",
    ):
        assert capabilities[capability_id].scope_status == "deferred"
        assert capabilities[capability_id].readiness_status == "deferred"


def test_mb210_synthetic_readiness_rejects_authority_bearing_evidence(
    tmp_path: Path,
) -> None:
    _write_mb210_closure_snapshot(tmp_path)
    unsafe_payload = {
        **_safe_longitudinal_payload(),
        "promotion_authorized": True,
    }
    report = _build_snapshot_report(
        tmp_path,
        longitudinal_payload=unsafe_payload,
    )

    assert report.status == "blocked"
    assert report.longitudinal_learning_authority_safe is False
    assert "longitudinal_learning_authority_violation" in report.blockers
    assert report.autonomous_release_allowed is False
