"""Promote internal pilot signals into sandbox-only evolution proposals."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict
from json import dumps, loads
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = [
    ROOT,
    ROOT / "evolution" / "evolution-lab" / "src",
    ROOT / "services" / "observability-service" / "src",
]

for src_dir in SRC_DIRS:
    sys_path.insert(0, str(src_dir))

from evolution_lab.service import EvolutionLabService, FlowEvaluationInput
from observability_service.service import ObservabilityService


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Create sandbox evolution proposals from pilot traces.")
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
        default=10,
        help="Maximum number of recent requests to inspect.",
    )
    parser.add_argument(
        "--comparison-json",
        help="Optional comparison artifact from tools/compare_orchestrator_paths.py.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def _evaluation_from_dict(payload: dict[str, object]) -> FlowEvaluationInput:
    return FlowEvaluationInput(
        request_id=str(payload["request_id"]),
        session_id=str(payload["session_id"]) if payload.get("session_id") else None,
        mission_id=str(payload["mission_id"]) if payload.get("mission_id") else None,
        governance_decision=(
            str(payload["governance_decision"])
            if payload.get("governance_decision") is not None
            else None
        ),
        operation_status=(
            str(payload["operation_status"])
            if payload.get("operation_status") is not None
            else None
        ),
        total_events=int(payload["total_events"]),
        duration_seconds=float(payload["duration_seconds"]),
        missing_required_events=list(payload.get("missing_required_events", [])),
        anomaly_flags=list(payload.get("anomaly_flags", [])),
        continuity_action=(
            str(payload["continuity_action"])
            if payload.get("continuity_action") is not None
            else None
        ),
        continuity_source=(
            str(payload["continuity_source"])
            if payload.get("continuity_source") is not None
            else None
        ),
        continuity_runtime_mode=(
            str(payload["continuity_runtime_mode"])
            if payload.get("continuity_runtime_mode") is not None
            else None
        ),
        registry_domains=list(payload.get("registry_domains", [])),
        shadow_specialists=list(payload.get("shadow_specialists", [])),
        domain_alignment_status=(
            str(payload["domain_alignment_status"])
            if payload.get("domain_alignment_status") is not None
            else None
        ),
        mind_alignment_status=(
            str(payload["mind_alignment_status"])
            if payload.get("mind_alignment_status") is not None
            else None
        ),
        identity_alignment_status=(
            str(payload["identity_alignment_status"])
            if payload.get("identity_alignment_status") is not None
            else None
        ),
        memory_alignment_status=(
            str(payload["memory_alignment_status"])
            if payload.get("memory_alignment_status") is not None
            else None
        ),
        specialist_sovereignty_status=(
            str(payload["specialist_sovereignty_status"])
            if payload.get("specialist_sovereignty_status") is not None
            else None
        ),
        axis_gate_status=(
            str(payload["axis_gate_status"])
            if payload.get("axis_gate_status") is not None
            else None
        ),
        workflow_profile_status=(
            str(payload["workflow_profile_status"])
            if payload.get("workflow_profile_status") is not None
            else None
        ),
        workflow_output_status=(
            str(payload["workflow_output_status"])
            if payload.get("workflow_output_status") is not None
            else None
        ),
        metacognitive_guidance_status=(
            str(payload["metacognitive_guidance_status"])
            if payload.get("metacognitive_guidance_status") is not None
            else None
        ),
        mind_disagreement_status=(
            str(payload["mind_disagreement_status"])
            if payload.get("mind_disagreement_status") is not None
            else "not_applicable"
        ),
        mind_validation_checkpoint_status=(
            str(payload["mind_validation_checkpoint_status"])
            if payload.get("mind_validation_checkpoint_status") is not None
            else "not_applicable"
        ),
        capability_decision_status=(
            str(payload["capability_decision_status"])
            if payload.get("capability_decision_status") is not None
            else "not_applicable"
        ),
        capability_decision_selected_mode=(
            str(payload["capability_decision_selected_mode"])
            if payload.get("capability_decision_selected_mode") is not None
            else None
        ),
        capability_authorization_status=(
            str(payload["capability_authorization_status"])
            if payload.get("capability_authorization_status") is not None
            else "not_applicable"
        ),
        capability_decision_tool_class=(
            str(payload["capability_decision_tool_class"])
            if payload.get("capability_decision_tool_class") is not None
            else None
        ),
        capability_decision_handoff_mode=(
            str(payload["capability_decision_handoff_mode"])
            if payload.get("capability_decision_handoff_mode") is not None
            else None
        ),
        capability_effectiveness=(
            str(payload["capability_effectiveness"])
            if payload.get("capability_effectiveness") is not None
            else "not_applicable"
        ),
        handoff_adapter_status=(
            str(payload["handoff_adapter_status"])
            if payload.get("handoff_adapter_status") is not None
            else "not_applicable"
        ),
        request_identity_status=(
            str(payload["request_identity_status"])
            if payload.get("request_identity_status") is not None
            else "not_applicable"
        ),
        mission_policy_status=(
            str(payload["mission_policy_status"])
            if payload.get("mission_policy_status") is not None
            else "not_applicable"
        ),
        request_identity_mismatch_flags=list(
            payload.get("request_identity_mismatch_flags", [])
        ),
        adaptive_intervention_status=(
            str(payload["adaptive_intervention_status"])
            if payload.get("adaptive_intervention_status") is not None
            else "not_applicable"
        ),
        adaptive_intervention_selected_action=(
            str(payload["adaptive_intervention_selected_action"])
            if payload.get("adaptive_intervention_selected_action") is not None
            else None
        ),
        adaptive_intervention_effectiveness=(
            str(payload["adaptive_intervention_effectiveness"])
            if payload.get("adaptive_intervention_effectiveness") is not None
            else "not_applicable"
        ),
        adaptive_intervention_policy_status=(
            str(payload["adaptive_intervention_policy_status"])
            if payload.get("adaptive_intervention_policy_status") is not None
            else "not_applicable"
        ),
        memory_causality_status=(
            str(payload["memory_causality_status"])
            if payload.get("memory_causality_status") is not None
            else None
        ),
        memory_maintenance_status=(
            str(payload["memory_maintenance_status"])
            if payload.get("memory_maintenance_status") is not None
            else None
        ),
        memory_maintenance_effectiveness=(
            str(payload["memory_maintenance_effectiveness"])
            if payload.get("memory_maintenance_effectiveness") is not None
            else None
        ),
        context_compaction_status=(
            str(payload["context_compaction_status"])
            if payload.get("context_compaction_status") is not None
            else None
        ),
        cross_session_recall_status=(
            str(payload["cross_session_recall_status"])
            if payload.get("cross_session_recall_status") is not None
            else None
        ),
        primary_mind=(
            str(payload["primary_mind"])
            if payload.get("primary_mind") is not None
            else None
        ),
        primary_route=(
            str(payload["primary_route"])
            if payload.get("primary_route") is not None
            else None
        ),
        dominant_tension=(
            str(payload["dominant_tension"])
            if payload.get("dominant_tension") is not None
            else None
        ),
        arbitration_source=(
            str(payload["arbitration_source"])
            if payload.get("arbitration_source") is not None
            else None
        ),
        primary_domain_driver=(
            str(payload["primary_domain_driver"])
            if payload.get("primary_domain_driver") is not None
            else None
        ),
        mind_domain_specialist_status=(
            str(payload["mind_domain_specialist_status"])
            if payload.get("mind_domain_specialist_status") is not None
            else None
        ),
        mind_domain_specialist_chain_status=(
            str(payload["mind_domain_specialist_chain_status"])
            if payload.get("mind_domain_specialist_chain_status") is not None
            else None
        ),
        mind_domain_specialist_effectiveness=(
            str(payload["mind_domain_specialist_effectiveness"])
            if payload.get("mind_domain_specialist_effectiveness") is not None
            else None
        ),
        mind_domain_specialist_mismatch_flags=list(
            payload.get("mind_domain_specialist_mismatch_flags", [])
        ),
        semantic_memory_source=(
            str(payload["semantic_memory_source"])
            if payload.get("semantic_memory_source") is not None
            else None
        ),
        procedural_memory_source=(
            str(payload["procedural_memory_source"])
            if payload.get("procedural_memory_source") is not None
            else None
        ),
        semantic_memory_lifecycle=(
            str(payload["semantic_memory_lifecycle"])
            if payload.get("semantic_memory_lifecycle") is not None
            else None
        ),
        procedural_memory_lifecycle=(
            str(payload["procedural_memory_lifecycle"])
            if payload.get("procedural_memory_lifecycle") is not None
            else None
        ),
        memory_lifecycle_status=(
            str(payload["memory_lifecycle_status"])
            if payload.get("memory_lifecycle_status") is not None
            else None
        ),
        memory_review_status=(
            str(payload["memory_review_status"])
            if payload.get("memory_review_status") is not None
            else None
        ),
        memory_corpus_status=(
            str(payload["memory_corpus_status"])
            if payload.get("memory_corpus_status") is not None
            else "not_applicable"
        ),
        memory_retention_pressure=(
            str(payload["memory_retention_pressure"])
            if payload.get("memory_retention_pressure") is not None
            else None
        ),
        workflow_checkpoint_status=(
            str(payload["workflow_checkpoint_status"])
            if payload.get("workflow_checkpoint_status") is not None
            else None
        ),
        workflow_resume_status=(
            str(payload["workflow_resume_status"])
            if payload.get("workflow_resume_status") is not None
            else None
        ),
        workflow_pending_checkpoint_count=int(
            payload.get("workflow_pending_checkpoint_count", 0)
        ),
        procedural_artifact_status=(
            str(payload["procedural_artifact_status"])
            if payload.get("procedural_artifact_status") is not None
            else None
        ),
        procedural_artifact_ref_count=int(
            payload.get("procedural_artifact_ref_count", 0)
        ),
        procedural_artifact_version=(
            int(payload["procedural_artifact_version"])
            if payload.get("procedural_artifact_version") is not None
            else None
        ),
        cognitive_recomposition_applied=bool(
            payload.get("cognitive_recomposition_applied", False)
        ),
        cognitive_recomposition_reason=(
            str(payload["cognitive_recomposition_reason"])
            if payload.get("cognitive_recomposition_reason") is not None
            else None
        ),
        cognitive_recomposition_trigger=(
            str(payload["cognitive_recomposition_trigger"])
            if payload.get("cognitive_recomposition_trigger") is not None
            else None
        ),
        continuity_trace_status=(
            str(payload["continuity_trace_status"])
            if payload.get("continuity_trace_status") is not None
            else None
        ),
        missing_continuity_signals=list(payload.get("missing_continuity_signals", [])),
        continuity_anomaly_flags=list(payload.get("continuity_anomaly_flags", [])),
    )


def resolve_path(value: str) -> Path:
    target = Path(value)
    return target if target.is_absolute() else ROOT / target


def build_payload(args: Namespace) -> dict[str, object]:
    observability = ObservabilityService(database_path=str(resolve_path(args.observability_db)))
    evolution = EvolutionLabService(database_path=str(resolve_path(args.evolution_db)))
    audits = observability.summarize_recent_requests(limit=args.limit)
    proposals = []
    for audit in audits:
        if (
            not audit.anomaly_flags
            and not audit.missing_required_events
            and audit.domain_alignment_status == "healthy"
            and audit.mind_alignment_status == "healthy"
            and audit.identity_alignment_status == "healthy"
            and audit.memory_alignment_status == "healthy"
            and audit.specialist_sovereignty_status == "healthy"
            and audit.workflow_profile_status in {None, "healthy", "not_applicable"}
            and audit.workflow_output_status in {None, "coherent", "not_applicable"}
            and audit.metacognitive_guidance_status in {None, "healthy", "not_applicable"}
            and audit.mind_disagreement_status in {None, "not_applicable", "contained"}
            and audit.mind_validation_checkpoint_status in {None, "not_applicable", "healthy"}
            and audit.adaptive_intervention_status in {None, "healthy", "not_applicable"}
            and audit.adaptive_intervention_effectiveness
            in {None, "effective", "not_applicable"}
            and audit.adaptive_intervention_policy_status
            in {None, "policy_aligned", "mandatory_override", "not_applicable"}
            and audit.memory_causality_status in {None, "causal_guidance", "not_applicable"}
            and audit.memory_maintenance_effectiveness
            in {None, "effective", "not_applicable"}
            and audit.memory_lifecycle_status in {None, "retained", "promoted", "not_applicable"}
            and audit.memory_corpus_status in {None, "stable", "not_applicable"}
            and audit.mind_domain_specialist_status in {None, "aligned", "not_applicable"}
            and audit.mind_domain_specialist_chain_status
            in {None, "aligned", "not_applicable"}
            and audit.mind_domain_specialist_effectiveness
            in {None, "effective", "not_applicable"}
            and not audit.mind_domain_specialist_mismatch_flags
        ):
            continue
        proposal = evolution.create_proposal_from_flow_evaluation(
            FlowEvaluationInput(
                request_id=audit.request_id or "unknown",
                session_id=audit.session_id,
                mission_id=audit.mission_id,
                governance_decision=audit.governance_decision,
                operation_status=audit.operation_status,
                total_events=audit.total_events,
                duration_seconds=audit.duration_seconds,
                missing_required_events=audit.missing_required_events,
                anomaly_flags=audit.anomaly_flags,
                continuity_action=audit.continuity_action,
                continuity_source=audit.continuity_source,
                continuity_runtime_mode=audit.continuity_runtime_mode,
                registry_domains=list(audit.registry_domains),
                shadow_specialists=list(audit.shadow_specialists),
                domain_alignment_status=audit.domain_alignment_status,
                mind_alignment_status=audit.mind_alignment_status,
                identity_alignment_status=audit.identity_alignment_status,
                memory_alignment_status=audit.memory_alignment_status,
                specialist_sovereignty_status=audit.specialist_sovereignty_status,
                axis_gate_status=(
                    "healthy"
                    if all(
                        status == "healthy"
                        for status in [
                            audit.domain_alignment_status,
                            audit.mind_alignment_status,
                            audit.identity_alignment_status,
                            audit.memory_alignment_status,
                            audit.specialist_sovereignty_status,
                        ]
                    )
                    else "attention_required"
                ),
                workflow_profile_status=audit.workflow_profile_status,
                workflow_output_status=audit.workflow_output_status,
                metacognitive_guidance_status=audit.metacognitive_guidance_status,
                mind_disagreement_status=audit.mind_disagreement_status,
                mind_validation_checkpoint_status=audit.mind_validation_checkpoint_status,
                request_identity_status=audit.request_identity_status,
                mission_policy_status=audit.mission_policy_status,
                request_identity_mismatch_flags=list(
                    audit.request_identity_mismatch_flags
                ),
                adaptive_intervention_status=audit.adaptive_intervention_status,
                adaptive_intervention_selected_action=(
                    audit.adaptive_intervention_selected_action
                ),
                adaptive_intervention_effectiveness=(
                    audit.adaptive_intervention_effectiveness
                ),
                adaptive_intervention_policy_status=(
                    audit.adaptive_intervention_policy_status
                ),
                memory_causality_status=audit.memory_causality_status,
                memory_maintenance_status=audit.memory_maintenance_status,
                memory_maintenance_effectiveness=audit.memory_maintenance_effectiveness,
                context_compaction_status=audit.context_compaction_status,
                cross_session_recall_status=audit.cross_session_recall_status,
                primary_mind=audit.primary_mind,
                primary_route=audit.primary_route,
                dominant_tension=audit.dominant_tension,
                arbitration_source=audit.arbitration_source,
                primary_domain_driver=audit.primary_domain_driver,
                mind_domain_specialist_status=audit.mind_domain_specialist_status,
                mind_domain_specialist_chain_status=(
                    audit.mind_domain_specialist_chain_status
                ),
                mind_domain_specialist_effectiveness=(
                    audit.mind_domain_specialist_effectiveness
                ),
                mind_domain_specialist_mismatch_flags=list(
                    audit.mind_domain_specialist_mismatch_flags
                ),
                semantic_memory_source=audit.semantic_memory_source,
                procedural_memory_source=audit.procedural_memory_source,
                semantic_memory_lifecycle=audit.semantic_memory_lifecycle,
                procedural_memory_lifecycle=audit.procedural_memory_lifecycle,
                memory_lifecycle_status=audit.memory_lifecycle_status,
                memory_review_status=audit.memory_review_status,
                memory_corpus_status=audit.memory_corpus_status,
                memory_retention_pressure=audit.memory_retention_pressure,
                cognitive_recomposition_applied=audit.cognitive_recomposition_applied,
                cognitive_recomposition_reason=audit.cognitive_recomposition_reason,
                cognitive_recomposition_trigger=audit.cognitive_recomposition_trigger,
                continuity_trace_status=audit.continuity_trace_status,
                missing_continuity_signals=audit.missing_continuity_signals,
                continuity_anomaly_flags=audit.continuity_anomaly_flags,
                workflow_checkpoint_status=audit.workflow_checkpoint_status,
                workflow_resume_status=audit.workflow_resume_status,
                workflow_pending_checkpoint_count=audit.workflow_pending_checkpoint_count,
                procedural_artifact_status=audit.procedural_artifact_status,
                procedural_artifact_ref_count=len(audit.procedural_artifact_refs),
                procedural_artifact_version=audit.procedural_artifact_version,
            ),
            target_scope="orchestrator-service",
        )
        proposals.append(asdict(proposal))

    comparisons = []
    if args.comparison_json:
        payload = loads(resolve_path(args.comparison_json).read_text(encoding="utf-8"))
        for item in payload.get("scenario_results", []):
            candidate = item.get("candidate")
            if candidate is None:
                continue
            baseline_eval = _evaluation_from_dict(item["baseline"])
            candidate_eval = _evaluation_from_dict(candidate)
            proposal = evolution.create_proposal_from_flow_evaluation(
                baseline_eval,
                target_scope="orchestrator-service",
                strategy_name="manual_variants",
            )
            comparison = evolution.compare_flow_evaluations(
                proposal,
                baseline_label=f"baseline:{item['scenario_id']}",
                candidate_label=f"langgraph:{item['scenario_id']}",
                baseline=baseline_eval,
                candidate=candidate_eval,
                governance_refs=["policy://sandbox/manual-review"],
                notes=[
                    f"comparison_scenario={item['scenario_id']}",
                    (
                        "workflow_profile="
                        f"{item.get('baseline_workflow_profile_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_profile_assessment', 'n/a')}"
                    ),
                    (
                        "workflow_output="
                        f"{item.get('baseline_workflow_output_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_output_assessment', 'n/a')}"
                    ),
                    (
                        "metacognitive_guidance="
                        f"{item.get('baseline_metacognitive_guidance_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_metacognitive_guidance_assessment', 'n/a')}"
                    ),
                    (
                        "mind_disagreement="
                        f"{item.get('baseline_mind_disagreement_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_disagreement_assessment', 'n/a')}"
                    ),
                    (
                        "memory_causality="
                        f"{item.get('baseline_memory_causality_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_memory_causality_assessment', 'n/a')}"
                    ),
                    (
                        "adaptive_intervention_policy="
                        f"{item.get('baseline_adaptive_intervention_policy_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_adaptive_intervention_policy_assessment', 'n/a')}"
                    ),
                    (
                        "request_identity="
                        f"{item.get('baseline_request_identity_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_request_identity_assessment', 'n/a')}"
                    ),
                    (
                        "mission_policy="
                        f"{item.get('baseline_mission_policy_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mission_policy_assessment', 'n/a')}"
                    ),
                    (
                        "memory_lifecycle="
                        f"{item.get('baseline_memory_lifecycle_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_memory_lifecycle_assessment', 'n/a')}"
                    ),
                    (
                        "memory_corpus="
                        f"{item.get('baseline_memory_corpus_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_memory_corpus_assessment', 'n/a')}"
                    ),
                    (
                        "workflow_checkpoint="
                        f"{item.get('baseline_workflow_checkpoint_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_checkpoint_assessment', 'n/a')}"
                    ),
                    (
                        "workflow_resume="
                        f"{item.get('baseline_workflow_resume_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_resume_assessment', 'n/a')}"
                    ),
                    (
                        "procedural_artifact="
                        f"{item.get('baseline_procedural_artifact_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_procedural_artifact_assessment', 'n/a')}"
                    ),
                    (
                        "mind_domain_specialist="
                        f"{item.get('baseline_mind_domain_specialist_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_domain_specialist_assessment', 'n/a')}"
                    ),
                    (
                        "mind_domain_specialist_chain="
                        f"{item.get('baseline_mind_domain_specialist_chain_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_domain_specialist_chain_assessment', 'n/a')}"
                    ),
                    (
                        "mind_domain_specialist_effectiveness="
                        f"{item.get(
                            'baseline_mind_domain_specialist_effectiveness_assessment',
                            'n/a',
                        )}"
                        "->"
                        f"{item.get(
                            'candidate_mind_domain_specialist_effectiveness_assessment',
                            'n/a',
                        )}"
                    ),
                    (
                        "mind_domain_specialist_mismatch="
                        f"{item.get('baseline_mind_domain_specialist_mismatch_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_domain_specialist_mismatch_assessment', 'n/a')}"
                    ),
                    (
                        "cognitive_recomposition="
                        f"{item.get('baseline_cognitive_recomposition_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_cognitive_recomposition_assessment', 'n/a')}"
                    ),
                ],
            )
            comparisons.append(
                {
                    "scenario_id": item["scenario_id"],
                    "baseline_workflow_profile_assessment": item.get(
                        "baseline_workflow_profile_assessment"
                    ),
                    "candidate_workflow_profile_assessment": item.get(
                        "candidate_workflow_profile_assessment"
                    ),
                    "baseline_workflow_output_assessment": item.get(
                        "baseline_workflow_output_assessment"
                    ),
                    "candidate_workflow_output_assessment": item.get(
                        "candidate_workflow_output_assessment"
                    ),
                    "baseline_metacognitive_guidance_assessment": item.get(
                        "baseline_metacognitive_guidance_assessment"
                    ),
                    "candidate_metacognitive_guidance_assessment": item.get(
                        "candidate_metacognitive_guidance_assessment"
                    ),
                    "baseline_mind_disagreement_assessment": item.get(
                        "baseline_mind_disagreement_assessment"
                    ),
                    "candidate_mind_disagreement_assessment": item.get(
                        "candidate_mind_disagreement_assessment"
                    ),
                    "baseline_capability_decision_assessment": item.get(
                        "baseline_capability_decision_assessment"
                    ),
                    "candidate_capability_decision_assessment": item.get(
                        "candidate_capability_decision_assessment"
                    ),
                    "baseline_capability_effectiveness_assessment": item.get(
                        "baseline_capability_effectiveness_assessment"
                    ),
                    "candidate_capability_effectiveness_assessment": item.get(
                        "candidate_capability_effectiveness_assessment"
                    ),
                    "baseline_handoff_adapter_assessment": item.get(
                        "baseline_handoff_adapter_assessment"
                    ),
                    "candidate_handoff_adapter_assessment": item.get(
                        "candidate_handoff_adapter_assessment"
                    ),
                    "baseline_memory_causality_assessment": item.get(
                        "baseline_memory_causality_assessment"
                    ),
                    "candidate_memory_causality_assessment": item.get(
                        "candidate_memory_causality_assessment"
                    ),
                    "baseline_adaptive_intervention_policy_assessment": item.get(
                        "baseline_adaptive_intervention_policy_assessment"
                    ),
                    "candidate_adaptive_intervention_policy_assessment": item.get(
                        "candidate_adaptive_intervention_policy_assessment"
                    ),
                    "baseline_memory_lifecycle_assessment": item.get(
                        "baseline_memory_lifecycle_assessment"
                    ),
                    "candidate_memory_lifecycle_assessment": item.get(
                        "candidate_memory_lifecycle_assessment"
                    ),
                    "baseline_memory_corpus_assessment": item.get(
                        "baseline_memory_corpus_assessment"
                    ),
                    "candidate_memory_corpus_assessment": item.get(
                        "candidate_memory_corpus_assessment"
                    ),
                    "baseline_workflow_checkpoint_assessment": item.get(
                        "baseline_workflow_checkpoint_assessment"
                    ),
                    "candidate_workflow_checkpoint_assessment": item.get(
                        "candidate_workflow_checkpoint_assessment"
                    ),
                    "baseline_workflow_resume_assessment": item.get(
                        "baseline_workflow_resume_assessment"
                    ),
                    "candidate_workflow_resume_assessment": item.get(
                        "candidate_workflow_resume_assessment"
                    ),
                    "baseline_procedural_artifact_assessment": item.get(
                        "baseline_procedural_artifact_assessment"
                    ),
                    "candidate_procedural_artifact_assessment": item.get(
                        "candidate_procedural_artifact_assessment"
                    ),
                    "baseline_mind_domain_specialist_assessment": item.get(
                        "baseline_mind_domain_specialist_assessment"
                    ),
                    "candidate_mind_domain_specialist_assessment": item.get(
                        "candidate_mind_domain_specialist_assessment"
                    ),
                    "baseline_mind_domain_specialist_chain_assessment": item.get(
                        "baseline_mind_domain_specialist_chain_assessment"
                    ),
                    "candidate_mind_domain_specialist_chain_assessment": item.get(
                        "candidate_mind_domain_specialist_chain_assessment"
                    ),
                    "baseline_mind_domain_specialist_effectiveness_assessment": item.get(
                        "baseline_mind_domain_specialist_effectiveness_assessment"
                    ),
                    "candidate_mind_domain_specialist_effectiveness_assessment": item.get(
                        "candidate_mind_domain_specialist_effectiveness_assessment"
                    ),
                    "baseline_mind_domain_specialist_mismatch_assessment": item.get(
                        "baseline_mind_domain_specialist_mismatch_assessment"
                    ),
                    "candidate_mind_domain_specialist_mismatch_assessment": item.get(
                        "candidate_mind_domain_specialist_mismatch_assessment"
                    ),
                    "baseline_cognitive_recomposition_assessment": item.get(
                        "baseline_cognitive_recomposition_assessment"
                    ),
                    "candidate_cognitive_recomposition_assessment": item.get(
                        "candidate_cognitive_recomposition_assessment"
                    ),
                    "proposal": asdict(comparison.proposal),
                    "decision": asdict(comparison.decision),
                    "metric_deltas": comparison.metric_deltas,
                }
            )

    return {
        "recent_trace_proposals": proposals,
        "comparison_decisions": comparisons,
    }


def render_text(payload: dict[str, object]) -> str:
    lines = [
        f"recent_trace_proposals={len(payload['recent_trace_proposals'])}",
        f"comparison_decisions={len(payload['comparison_decisions'])}",
    ]
    for item in payload["comparison_decisions"]:
        lines.append(
            " ".join(
                [
                    f"scenario_id={item['scenario_id']}",
                    f"decision={item['decision']['decision']}",
                    (
                        "workflow_profile="
                        f"{item.get('baseline_workflow_profile_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_profile_assessment', 'n/a')}"
                    ),
                    (
                        "workflow_output="
                        f"{item.get('baseline_workflow_output_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_output_assessment', 'n/a')}"
                    ),
                    (
                        "metacognitive_guidance="
                        f"{item.get('baseline_metacognitive_guidance_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_metacognitive_guidance_assessment', 'n/a')}"
                    ),
                    (
                        "mind_disagreement="
                        f"{item.get('baseline_mind_disagreement_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_disagreement_assessment', 'n/a')}"
                    ),
                    (
                        "capability_decision="
                        f"{item.get('baseline_capability_decision_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_capability_decision_assessment', 'n/a')}"
                    ),
                    (
                        "capability_effectiveness="
                        f"{item.get('baseline_capability_effectiveness_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_capability_effectiveness_assessment', 'n/a')}"
                    ),
                    (
                        "handoff_adapter="
                        f"{item.get('baseline_handoff_adapter_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_handoff_adapter_assessment', 'n/a')}"
                    ),
                    (
                        "memory_causality="
                        f"{item.get('baseline_memory_causality_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_memory_causality_assessment', 'n/a')}"
                    ),
                    (
                        "adaptive_intervention_policy="
                        f"{item.get('baseline_adaptive_intervention_policy_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_adaptive_intervention_policy_assessment', 'n/a')}"
                    ),
                    (
                        "request_identity="
                        f"{item.get('baseline_request_identity_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_request_identity_assessment', 'n/a')}"
                    ),
                    (
                        "mission_policy="
                        f"{item.get('baseline_mission_policy_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mission_policy_assessment', 'n/a')}"
                    ),
                    (
                        "memory_lifecycle="
                        f"{item.get('baseline_memory_lifecycle_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_memory_lifecycle_assessment', 'n/a')}"
                    ),
                    (
                        "memory_corpus="
                        f"{item.get('baseline_memory_corpus_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_memory_corpus_assessment', 'n/a')}"
                    ),
                    (
                        "workflow_checkpoint="
                        f"{item.get('baseline_workflow_checkpoint_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_checkpoint_assessment', 'n/a')}"
                    ),
                    (
                        "workflow_resume="
                        f"{item.get('baseline_workflow_resume_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_workflow_resume_assessment', 'n/a')}"
                    ),
                    (
                        "procedural_artifact="
                        f"{item.get('baseline_procedural_artifact_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_procedural_artifact_assessment', 'n/a')}"
                    ),
                    (
                        "mind_domain_specialist="
                        f"{item.get('baseline_mind_domain_specialist_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_domain_specialist_assessment', 'n/a')}"
                    ),
                    (
                        "mind_domain_specialist_chain="
                        f"{item.get('baseline_mind_domain_specialist_chain_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_domain_specialist_chain_assessment', 'n/a')}"
                    ),
                    (
                        "mind_domain_specialist_effectiveness="
                        f"{item.get(
                            'baseline_mind_domain_specialist_effectiveness_assessment',
                            'n/a',
                        )}"
                        "->"
                        f"{item.get(
                            'candidate_mind_domain_specialist_effectiveness_assessment',
                            'n/a',
                        )}"
                    ),
                    (
                        "mind_domain_specialist_mismatch="
                        f"{item.get('baseline_mind_domain_specialist_mismatch_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_mind_domain_specialist_mismatch_assessment', 'n/a')}"
                    ),
                    (
                        "cognitive_recomposition="
                        f"{item.get('baseline_cognitive_recomposition_assessment', 'n/a')}"
                        "->"
                        f"{item.get('candidate_cognitive_recomposition_assessment', 'n/a')}"
                    ),
                    f"rollback_plan_ref={item['decision']['rollback_plan_ref']}",
                ]
            )
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    if args.format == "json":
        print(dumps(payload, ensure_ascii=True, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
