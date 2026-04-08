"""Memory registry derived from the Documento-Mestre."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from shared.types import MemoryClass


@dataclass(frozen=True)
class MemoryPolicy:
    memory_class: MemoryClass
    display_name: str
    stability: str
    sensitivity: str
    runtime_status: str
    retrieval_default: bool = False
    specialist_shared: bool = False
    domain_linked: bool = False
    retrieval_priority: int = 0
    sharing_priority: int = 0
    sharing_mode: str | None = None
    write_policy: str | None = None


@dataclass(frozen=True)
class WorkflowMemoryPolicy:
    workflow_profile: str | None
    reasoning_semantic_enabled: bool = True
    reasoning_procedural_enabled: bool = True
    specialist_semantic_enabled: bool = True
    specialist_procedural_enabled: bool = True


@dataclass(frozen=True)
class MemoryLifecycleDecision:
    semantic_lifecycle: str | None
    procedural_lifecycle: str | None
    semantic_memory_state: str | None
    procedural_memory_state: str | None
    lifecycle_status: str
    review_status: str
    consolidation_status: str
    fixation_status: str
    archive_status: str


@dataclass(frozen=True)
class GuidedMemoryDecision:
    reasoning_classes: tuple[MemoryClass, ...]
    specialist_classes: tuple[MemoryClass, ...]
    semantic_source: str | None
    procedural_source: str | None
    semantic_effects: tuple[str, ...]
    procedural_effects: tuple[str, ...]
    semantic_lifecycle: str | None
    procedural_lifecycle: str | None
    semantic_memory_state: str | None
    procedural_memory_state: str | None
    lifecycle_status: str
    review_status: str
    consolidation_status: str
    fixation_status: str
    archive_status: str


@dataclass(frozen=True)
class MemoryCorpusTelemetry:
    corpus_status: str
    retention_pressure: str
    summary: dict[str, int]


@dataclass(frozen=True)
class ProceduralArtifactDecision:
    eligible: bool
    artifact_status: str
    artifact_kind: str
    reuse_scope: str
    versioning_mode: str
    through_core_only: bool


@dataclass(frozen=True)
class ContextWindowPolicy:
    requested_limit: int
    live_turn_limit: int
    continuity_hint_limit: int
    user_hint_limit: int
    mission_hint_limit: int
    plan_hint_limit: int
    compaction_status: str
    cross_session_recall_status: str


DEFAULT_WORKFLOW_MEMORY_POLICY = WorkflowMemoryPolicy(workflow_profile=None)

WORKFLOW_MEMORY_POLICIES: dict[str, WorkflowMemoryPolicy] = {
    "strategic_direction_workflow": WorkflowMemoryPolicy(
        workflow_profile="strategic_direction_workflow",
        specialist_procedural_enabled=False,
    ),
    "structured_analysis_workflow": WorkflowMemoryPolicy(
        workflow_profile="structured_analysis_workflow",
        specialist_procedural_enabled=False,
    ),
    "governance_boundary_workflow": WorkflowMemoryPolicy(
        workflow_profile="governance_boundary_workflow",
        specialist_procedural_enabled=False,
    ),
    "decision_risk_workflow": WorkflowMemoryPolicy(
        workflow_profile="decision_risk_workflow",
        specialist_procedural_enabled=False,
    ),
    "software_change_workflow": WorkflowMemoryPolicy(
        workflow_profile="software_change_workflow",
    ),
    "operational_readiness_workflow": WorkflowMemoryPolicy(
        workflow_profile="operational_readiness_workflow",
    ),
}


MEMORY_REGISTRY: dict[MemoryClass, MemoryPolicy] = {
    MemoryClass.IDENTITY: MemoryPolicy(
        memory_class=MemoryClass.IDENTITY,
        display_name="Memoria de identidade",
        stability="muito_alta",
        sensitivity="critica",
        runtime_status="tipado_documentado",
    ),
    MemoryClass.NORMATIVE: MemoryPolicy(
        memory_class=MemoryClass.NORMATIVE,
        display_name="Memoria normativa",
        stability="muito_alta",
        sensitivity="critica",
        runtime_status="tipado_documentado",
    ),
    MemoryClass.USER: MemoryPolicy(
        memory_class=MemoryClass.USER,
        display_name="Memoria do usuario",
        stability="alta",
        sensitivity="elevada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        retrieval_priority=95,
    ),
    MemoryClass.RELATIONAL: MemoryPolicy(
        memory_class=MemoryClass.RELATIONAL,
        display_name="Memoria social e relacional",
        stability="media",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=90,
        sharing_priority=90,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.CONTEXTUAL: MemoryPolicy(
        memory_class=MemoryClass.CONTEXTUAL,
        display_name="Memoria contextual",
        stability="baixa",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=60,
        sharing_priority=60,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.EPISODIC: MemoryPolicy(
        memory_class=MemoryClass.EPISODIC,
        display_name="Memoria episodica",
        stability="media",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=70,
        sharing_priority=70,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.SEMANTIC: MemoryPolicy(
        memory_class=MemoryClass.SEMANTIC,
        display_name="Memoria semantica",
        stability="alta",
        sensitivity="baixa",
        runtime_status="runtime_partial",
        specialist_shared=True,
        domain_linked=True,
        retrieval_priority=50,
        sharing_priority=50,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.PROCEDURAL: MemoryPolicy(
        memory_class=MemoryClass.PROCEDURAL,
        display_name="Memoria procedural",
        stability="alta",
        sensitivity="baixa",
        runtime_status="runtime_partial",
        specialist_shared=True,
        retrieval_priority=40,
        sharing_priority=40,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.MISSION: MemoryPolicy(
        memory_class=MemoryClass.MISSION,
        display_name="Memoria de projetos e missoes",
        stability="alta",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=100,
        sharing_priority=100,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.DOMAIN: MemoryPolicy(
        memory_class=MemoryClass.DOMAIN,
        display_name="Memoria de dominio",
        stability="alta",
        sensitivity="baixa",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        domain_linked=True,
        retrieval_priority=80,
        sharing_priority=80,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.EVOLUTIONARY: MemoryPolicy(
        memory_class=MemoryClass.EVOLUTIONARY,
        display_name="Memoria evolutiva",
        stability="media",
        sensitivity="moderada",
        runtime_status="tipado_documentado",
    ),
}


def policy_for(memory_class: MemoryClass) -> MemoryPolicy:
    """Return the canonical policy for a memory class."""

    return MEMORY_REGISTRY[memory_class]


def default_memory_scopes() -> list[MemoryClass]:
    """Return default recovery scopes ordered by runtime priority."""

    return sorted(
        (
            memory_class
            for memory_class, policy in MEMORY_REGISTRY.items()
            if policy.retrieval_default
        ),
        key=lambda memory_class: (
            -MEMORY_REGISTRY[memory_class].retrieval_priority,
            memory_class.value,
        ),
    )


def specialist_shared_memory_classes() -> list[MemoryClass]:
    """Return specialist-shareable classes ordered by runtime priority."""

    return sorted(
        (
            memory_class
            for memory_class, policy in MEMORY_REGISTRY.items()
            if policy.specialist_shared
        ),
        key=lambda memory_class: (
            -MEMORY_REGISTRY[memory_class].sharing_priority,
            memory_class.value,
        ),
    )


def workflow_memory_policy(workflow_profile: str | None) -> WorkflowMemoryPolicy:
    """Return the sovereign memory visibility policy for a workflow profile."""

    if workflow_profile is None:
        return DEFAULT_WORKFLOW_MEMORY_POLICY
    return WORKFLOW_MEMORY_POLICIES.get(workflow_profile, DEFAULT_WORKFLOW_MEMORY_POLICY)


def guided_optional_memory_classes(
    *,
    semantic_evidence: bool,
    procedural_evidence: bool,
    domain_compatible: bool,
    workflow_profile: str | None = None,
) -> list[MemoryClass]:
    """Return the optional classes that a guided route may expose."""

    policy = workflow_memory_policy(workflow_profile)
    classes: list[MemoryClass] = []
    if domain_compatible and semantic_evidence and policy.reasoning_semantic_enabled:
        classes.append(MemoryClass.SEMANTIC)
    if domain_compatible and procedural_evidence and policy.reasoning_procedural_enabled:
        classes.append(MemoryClass.PROCEDURAL)
    return classes


def guided_reasoning_memory_classes(
    *,
    semantic_evidence: bool,
    procedural_evidence: bool,
    domain_compatible: bool,
    workflow_profile: str | None = None,
) -> list[MemoryClass]:
    """Return the optional guided-memory classes visible to planning and synthesis."""

    return guided_optional_memory_classes(
        semantic_evidence=semantic_evidence,
        procedural_evidence=procedural_evidence,
        domain_compatible=domain_compatible,
        workflow_profile=workflow_profile,
    )


def guided_specialist_memory_classes(
    *,
    semantic_evidence: bool,
    procedural_evidence: bool,
    domain_compatible: bool,
    workflow_profile: str | None = None,
) -> list[MemoryClass]:
    """Return the specialist-visible classes for a guided route packet."""

    policy = workflow_memory_policy(workflow_profile)
    classes = [
        memory_class
        for memory_class in specialist_shared_memory_classes()
        if memory_class not in {MemoryClass.SEMANTIC, MemoryClass.PROCEDURAL}
    ]
    optional_classes = guided_reasoning_memory_classes(
        semantic_evidence=semantic_evidence,
        procedural_evidence=procedural_evidence,
        domain_compatible=domain_compatible,
        workflow_profile=workflow_profile,
    )
    if MemoryClass.SEMANTIC in optional_classes and policy.specialist_semantic_enabled:
        classes.append(MemoryClass.SEMANTIC)
    if MemoryClass.PROCEDURAL in optional_classes and policy.specialist_procedural_enabled:
        classes.append(MemoryClass.PROCEDURAL)
    return classes


def memory_lifecycle_decision(
    *,
    semantic_sources: Sequence[str],
    procedural_sources: Sequence[str],
    continuity_source: str | None = None,
) -> MemoryLifecycleDecision:
    """Return the sovereign lifecycle classification for guided memory usage."""

    semantic_lifecycle = _memory_lifecycle_label(
        sources=semantic_sources,
        continuity_source=continuity_source,
    )
    procedural_lifecycle = _memory_lifecycle_label(
        sources=procedural_sources,
        continuity_source=continuity_source,
    )
    labels = [label for label in (semantic_lifecycle, procedural_lifecycle) if label]
    if not labels:
        lifecycle_status = "not_applicable"
    elif "aging" in labels:
        lifecycle_status = "review_recommended"
    elif "retained" in labels:
        lifecycle_status = "retained"
    elif "promoted" in labels:
        lifecycle_status = "promoted"
    else:
        lifecycle_status = "emerging"
    if "aging" in labels:
        review_status = "review_recommended"
    elif "consolidating" in labels:
        review_status = "monitor"
    elif labels:
        review_status = "stable"
    else:
        review_status = "not_needed"
    lifecycle_support = memory_lifecycle_support_signals(
        semantic_lifecycle=semantic_lifecycle,
        procedural_lifecycle=procedural_lifecycle,
    )
    return MemoryLifecycleDecision(
        semantic_lifecycle=semantic_lifecycle,
        procedural_lifecycle=procedural_lifecycle,
        semantic_memory_state=lifecycle_support["semantic_memory_state"],
        procedural_memory_state=lifecycle_support["procedural_memory_state"],
        lifecycle_status=lifecycle_status,
        review_status=review_status,
        consolidation_status=lifecycle_support["consolidation_status"],
        fixation_status=lifecycle_support["fixation_status"],
        archive_status=lifecycle_support["archive_status"],
    )


def guided_memory_decision(
    *,
    semantic_sources: Sequence[str],
    procedural_sources: Sequence[str],
    domain_compatible: bool,
    workflow_profile: str | None = None,
    continuity_source: str | None = None,
) -> GuidedMemoryDecision:
    """Resolve the sovereign guided-memory decision for reasoning and specialist use."""

    reasoning_classes = tuple(
        guided_reasoning_memory_classes(
            semantic_evidence=bool(semantic_sources),
            procedural_evidence=bool(procedural_sources),
            domain_compatible=domain_compatible,
            workflow_profile=workflow_profile,
        )
    )
    specialist_classes = tuple(
        guided_specialist_memory_classes(
            semantic_evidence=bool(semantic_sources),
            procedural_evidence=bool(procedural_sources),
            domain_compatible=domain_compatible,
            workflow_profile=workflow_profile,
        )
    )
    lifecycle = memory_lifecycle_decision(
        semantic_sources=semantic_sources,
        procedural_sources=procedural_sources,
        continuity_source=continuity_source,
    )
    semantic_source = (
        _preferred_memory_source(semantic_sources, continuity_source)
        if MemoryClass.SEMANTIC in reasoning_classes
        else None
    )
    procedural_source = (
        _preferred_memory_source(procedural_sources, continuity_source)
        if MemoryClass.PROCEDURAL in reasoning_classes
        else None
    )
    semantic_effects = _memory_effects_for_source(
        semantic_source,
        primary_effect="framing",
    )
    procedural_effects = _memory_effects_for_source(
        procedural_source,
        primary_effect="next_action",
    )
    return GuidedMemoryDecision(
        reasoning_classes=reasoning_classes,
        specialist_classes=specialist_classes,
        semantic_source=semantic_source,
        procedural_source=procedural_source,
        semantic_effects=tuple(semantic_effects),
        procedural_effects=tuple(procedural_effects),
        semantic_lifecycle=lifecycle.semantic_lifecycle,
        procedural_lifecycle=lifecycle.procedural_lifecycle,
        semantic_memory_state=lifecycle.semantic_memory_state,
        procedural_memory_state=lifecycle.procedural_memory_state,
        lifecycle_status=lifecycle.lifecycle_status,
        review_status=lifecycle.review_status,
        consolidation_status=lifecycle.consolidation_status,
        fixation_status=lifecycle.fixation_status,
        archive_status=lifecycle.archive_status,
    )


def memory_corpus_telemetry(
    *,
    user_scope_records: int,
    mission_state_records: int,
    specialist_context_records: int,
    semantic_records: int,
    procedural_records: int,
    retained_records: int,
    promoted_records: int,
    aging_records: int,
    review_recommended_records: int,
    fixed_records: int,
    operational_records: int,
    archivable_records: int,
    consolidating_records: int,
) -> MemoryCorpusTelemetry:
    """Classify memory corpus pressure without introducing a new storage layer."""

    total_guided_records = semantic_records + procedural_records
    if (
        review_recommended_records >= 3
        or aging_records >= 3
        or archivable_records >= 3
        or total_guided_records >= 18
    ):
        retention_pressure = "high"
    elif (
        review_recommended_records >= 1
        or aging_records >= 1
        or archivable_records >= 1
        or total_guided_records >= 9
    ):
        retention_pressure = "moderate"
    else:
        retention_pressure = "low"

    if retention_pressure == "high":
        corpus_status = "review_recommended"
    elif retention_pressure == "moderate":
        corpus_status = "monitor"
    else:
        corpus_status = "stable"

    return MemoryCorpusTelemetry(
        corpus_status=corpus_status,
        retention_pressure=retention_pressure,
        summary={
            "user_scope_records": user_scope_records,
            "mission_state_records": mission_state_records,
            "specialist_context_records": specialist_context_records,
            "semantic_records": semantic_records,
            "procedural_records": procedural_records,
            "retained_records": retained_records,
            "promoted_records": promoted_records,
            "aging_records": aging_records,
            "review_recommended_records": review_recommended_records,
            "fixed_records": fixed_records,
            "operational_records": operational_records,
            "archivable_records": archivable_records,
            "consolidating_records": consolidating_records,
        },
    )


def context_window_policy(
    *,
    requested_limit: int,
    user_scope_status: str | None,
    interaction_count: int,
    has_session_continuity: bool,
    has_related_mission: bool,
    has_mission_context: bool,
) -> ContextWindowPolicy:
    """Return the sovereign policy for live context compaction and recall."""

    normalized_limit = max(1, requested_limit)
    has_user_scope = user_scope_status not in {None, "not_applicable"}
    recall_active = (
        user_scope_status == "recoverable"
        or has_session_continuity
        or has_related_mission
    )
    recall_seeded = has_user_scope or has_mission_context or interaction_count > 0

    if recall_active:
        return ContextWindowPolicy(
            requested_limit=normalized_limit,
            live_turn_limit=min(2, normalized_limit),
            continuity_hint_limit=7,
            user_hint_limit=max(6, normalized_limit),
            mission_hint_limit=9,
            plan_hint_limit=5,
            compaction_status="compressed_live_context",
            cross_session_recall_status="active",
        )
    if recall_seeded:
        return ContextWindowPolicy(
            requested_limit=normalized_limit,
            live_turn_limit=min(2, normalized_limit),
            continuity_hint_limit=6,
            user_hint_limit=max(5, normalized_limit),
            mission_hint_limit=8,
            plan_hint_limit=4,
            compaction_status="seeded_live_context",
            cross_session_recall_status="seeded",
        )
    return ContextWindowPolicy(
        requested_limit=normalized_limit,
        live_turn_limit=min(3, normalized_limit),
        continuity_hint_limit=3,
        user_hint_limit=normalized_limit,
        mission_hint_limit=6,
        plan_hint_limit=2,
        compaction_status="minimal_live_context",
        cross_session_recall_status="not_applicable",
    )


def default_priority_rules() -> list[str]:
    """Expose the runtime ordering rules implied by the registry."""

    ordered = ">".join(memory_class.value for memory_class in default_memory_scopes())
    return [
        f"default_recovery_order={ordered}",
        "mission_and_user_memory_before_recent_context",
        "domain_memory_requires_runtime_domain_link",
        "user_memory_recovers_when_user_id_is_available",
        "identity_and_normative_memory_are_not_default_recovery_scopes",
        "organization_scope_blocked_without_canonical_consumer",
    ]


def organization_scope_guard_payload() -> dict[str, str]:
    """Return the baseline guardrail that keeps organization scope out of runtime."""

    return {
        "status": "no_go_without_canonical_consumer",
        "reason": "baseline_keeps_organization_scope_out_until_a_sovereign_consumer_exists",
        "reopen_signal": "canonical_consumer_required_for_reopen",
    }


def specialist_memory_policy_payload(
    memory_classes: Iterable[MemoryClass],
) -> dict[str, dict[str, object]]:
    """Serialize specialist-facing policy metadata by memory class."""

    payload: dict[str, dict[str, object]] = {}
    for memory_class in memory_classes:
        policy = MEMORY_REGISTRY[memory_class]
        payload[memory_class.value] = {
            "runtime_status": policy.runtime_status,
            "stability": policy.stability,
            "sensitivity": policy.sensitivity,
            "specialist_shared": policy.specialist_shared,
            "domain_linked": policy.domain_linked,
            "sharing_mode": policy.sharing_mode,
            "write_policy": policy.write_policy,
        }
    return payload


DEFAULT_MEMORY_SCOPES: list[MemoryClass] = default_memory_scopes()

SHARED_MEMORY_CLASSES: list[MemoryClass] = specialist_shared_memory_classes()


def memory_lifecycle_support_signals(
    *,
    semantic_lifecycle: str | None,
    procedural_lifecycle: str | None,
) -> dict[str, str | None]:
    """Return explicit lifecycle support signals without changing canonical labels."""

    semantic_memory_state = _memory_state_for_lifecycle(semantic_lifecycle)
    procedural_memory_state = _memory_state_for_lifecycle(procedural_lifecycle)
    labels = [label for label in (semantic_lifecycle, procedural_lifecycle) if label]
    if not labels:
        consolidation_status = "not_applicable"
        fixation_status = "not_applicable"
        archive_status = "not_applicable"
    else:
        if any(label == "aging" for label in labels):
            consolidation_status = "revisit_before_reuse"
        elif any(label == "consolidating" for label in labels):
            consolidation_status = "in_progress"
        else:
            consolidation_status = "consolidated"
        fixation_status = (
            "fixed" if any(label == "retained" for label in labels) else "not_fixed"
        )
        archive_status = (
            "archive_candidate"
            if any(label == "aging" for label in labels)
            else "active_memory"
        )
    return {
        "semantic_memory_state": semantic_memory_state,
        "procedural_memory_state": procedural_memory_state,
        "consolidation_status": consolidation_status,
        "fixation_status": fixation_status,
        "archive_status": archive_status,
    }


def procedural_artifact_decision(
    *,
    workflow_profile: str | None,
    procedural_lifecycle: str | None,
    procedural_memory_state: str | None,
    memory_review_status: str | None,
) -> ProceduralArtifactDecision:
    """Return whether guided procedural memory may become a reusable core artifact."""

    if not workflow_profile or not procedural_lifecycle or not procedural_memory_state:
        return ProceduralArtifactDecision(
            eligible=False,
            artifact_status="not_applicable",
            artifact_kind="workflow_procedure",
            reuse_scope="through_core_only",
            versioning_mode="increment_on_contract_shift",
            through_core_only=True,
        )
    if memory_review_status == "attention_required":
        return ProceduralArtifactDecision(
            eligible=False,
            artifact_status="blocked",
            artifact_kind="workflow_procedure",
            reuse_scope="through_core_only",
            versioning_mode="increment_on_contract_shift",
            through_core_only=True,
        )
    if procedural_memory_state == "fixed":
        artifact_status = "reusable"
    elif procedural_memory_state == "operational":
        artifact_status = "candidate"
    elif procedural_memory_state == "archivable":
        artifact_status = "archivable"
    else:
        artifact_status = "not_applicable"
    return ProceduralArtifactDecision(
        eligible=artifact_status in {"candidate", "reusable", "archivable"},
        artifact_status=artifact_status,
        artifact_kind="workflow_procedure",
        reuse_scope="through_core_only",
        versioning_mode="increment_on_contract_shift",
        through_core_only=True,
    )


def _preferred_memory_source(
    sources: Sequence[str],
    continuity_source: str | None,
) -> str | None:
    normalized: list[str] = []
    for item in sources:
        if item and item not in normalized:
            normalized.append(item)
    if not normalized:
        return None
    preferred_order: list[str] = []
    if continuity_source:
        preferred_order.append(continuity_source)
    preferred_order.extend(
        [
            "related_mission",
            "active_mission",
            "user_scope",
            "recurrent_specialist",
            "fresh_request",
        ]
    )
    for candidate in preferred_order:
        if candidate in normalized:
            return candidate
    return normalized[0]


def _memory_effects_for_source(
    source: str | None,
    *,
    primary_effect: str,
) -> list[str]:
    if source is None:
        return []
    effects = [primary_effect]
    if source != "fresh_request":
        effects.append("continuity")
    return effects


def _memory_lifecycle_label(
    *,
    sources: Sequence[str],
    continuity_source: str | None,
) -> str | None:
    normalized = {item for item in sources if item}
    if not normalized:
        return None
    cross_context = bool(
        normalized.intersection({"related_mission", "user_scope", "recurrent_specialist"})
    )
    active_context = "active_mission" in normalized
    if continuity_source == "fresh_request" and (cross_context or active_context):
        return "aging"
    if cross_context and active_context:
        return "retained"
    if cross_context:
        return "promoted"
    return "consolidating"


def _memory_state_for_lifecycle(label: str | None) -> str | None:
    if label == "retained":
        return "fixed"
    if label in {"promoted", "consolidating"}:
        return "operational"
    if label == "aging":
        return "archivable"
    return None
