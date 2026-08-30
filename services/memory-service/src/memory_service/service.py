"""Persistent memory service backed by canonical contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from hashlib import sha256
from os import getenv
from re import fullmatch
from uuid import uuid4

from memory_service.repository import (
    SessionContinuitySnapshot,
    StoredContinuityCheckpoint,
    StoredContinuityPauseResolution,
    StoredExperienceReflection,
    StoredMemoryLifecycleReviewDecision,
    StoredProceduralPlaybookCandidate,
    StoredReviewedLearningGuidance,
    StoredReviewedProceduralPlaybook,
    StoredSkillCandidate,
    StoredSpecialistSharedMemory,
    StoredTurn,
    StoredUserScopeSnapshot,
    StoredWorkflowLifecycleTransition,
    build_memory_repository,
    continuity_checkpoint_to_contract,
)
from shared.artifact_physical_saga import (
    require_valid_artifact_physical_apply_plan,
    require_valid_artifact_physical_canonical_commit_receipt,
    require_valid_artifact_physical_rollback_plan,
    require_valid_local_text_physical_state_attestation,
    saga_state_from_event,
    seal_artifact_physical_canonical_commit_receipt,
    seal_artifact_physical_lineage,
    seal_artifact_physical_outbox_delivery,
    seal_artifact_physical_outbox_item,
    seal_artifact_physical_saga_event,
    seal_physical_artifact_version,
)
from shared.artifact_policy import (
    canonical_artifact_states_from_mission,
    validate_artifact_lineage,
    validate_artifact_transition,
    validate_artifact_version,
)
from shared.contracts import (
    WORK_ITEM_PRIORITY_LEVELS,
    ArtifactLifecycleStateContract,
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalCanonicalCommitReceiptContract,
    ArtifactPhysicalLineageContract,
    ArtifactPhysicalOutboxDeliveryContract,
    ArtifactPhysicalOutboxItemContract,
    ArtifactPhysicalRollbackPlanContract,
    ArtifactPhysicalSagaEventContract,
    ArtifactPhysicalSagaStateContract,
    ContinuityCheckpointContract,
    ContinuityPauseContract,
    ContinuityReplayContract,
    DecisionOutcomeAttributionRecordContract,
    DeliberativePlanContract,
    EcosystemOperationalStateContract,
    ExperienceRecordContract,
    InputContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
    LocalTextRollbackReceipt,
    LongHorizonGoalStrategyContract,
    MemoryInfluencePolicyDecisionContract,
    MemoryInfluenceSignalContract,
    MemoryLifecycleCandidateContract,
    MemoryLifecycleGovernanceAssessmentContract,
    MemoryLifecycleReviewDecisionContract,
    MemoryRecordContract,
    MemoryRecoveryContract,
    MissionContinuityCandidateContract,
    MissionContinuityContextContract,
    MissionStateContract,
    OpenLoopResumePlanContract,
    OpenLoopStateContract,
    OperationDispatchContract,
    OperationResultContract,
    OperatorFeedbackContract,
    PhysicalArtifactVersionContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    RecurringPatternReportContract,
    ReviewedLearningGuidanceContract,
    ReviewedProceduralPlaybookContract,
    SemanticMemoryCandidateContract,
    SkillCandidateContract,
    SpecialistContributionContract,
    SpecialistSharedMemoryContextContract,
    UserScopeContextContract,
    WorkflowLifecycleGovernanceAssessmentContract,
    WorkflowLifecycleTransitionContract,
    WorkItemStateContract,
)
from shared.decision_attribution import (
    decision_attribution_fingerprint,
    validate_decision_attribution_record,
)
from shared.domain_registry import (
    primary_route_payload,
    specialist_eligible_route,
    specialist_route_payload,
)
from shared.local_text_rollback_permissions import (
    require_valid_local_text_mutation_receipt,
    require_valid_local_text_rollback_receipt,
)
from shared.memory_influence_policy import (
    evaluate_memory_influence_policy,
    semantic_memory_freshness_status,
)
from shared.memory_registry import (
    DEFAULT_MEMORY_SCOPES,
    SHARED_MEMORY_CLASSES,
    context_window_policy,
    default_priority_rules,
    ecosystem_continuity_policy,
    guided_memory_decision,
    memory_corpus_telemetry,
    memory_lifecycle_runtime_policy,
    memory_lifecycle_support_signals,
    memory_maintenance_decision,
    organization_scope_guard_payload,
    procedural_artifact_decision,
    specialist_memory_policy_payload,
)
from shared.open_loop_policy import canonical_open_loop_states_from_mission
from shared.recurring_patterns import build_recurring_pattern_report
from shared.specialist_registry import (
    canonical_specialist_type,
    legacy_specialist_type,
    normalize_specialist_types,
)
from shared.types import (
    MemoryClass,
    MemoryQueryId,
    MemoryRecordId,
    MissionId,
    MissionStatus,
    OperationStatus,
    PermissionDecision,
    RecoveryType,
    RequestId,
    RiskLevel,
    SessionId,
    TimeWindow,
)
from shared.versioning import parse_canonical_semver
from shared.work_item_policy import (
    canonical_work_items_from_mission,
    refresh_work_item_blocking_states,
    validate_work_item_graph,
)
from shared.workflow_lifecycle import (
    validate_workflow_lifecycle_governance_assessment,
    validate_workflow_lifecycle_transition,
    workflow_lifecycle_artifact_fingerprint,
    workflow_lifecycle_transition_fingerprint,
)


@dataclass
class MemoryRecoveryResult:
    """Structured result for contextual recovery."""

    recovery_contract: MemoryRecoveryContract
    user_hints: list[str]
    session_context: list[str]
    mission_hints: list[str]
    plan_hints: list[str]
    organization_scope_status: str
    organization_scope_reason: str
    organization_scope_reopen_signal: str
    continuity_context: MissionContinuityContextContract | None = None
    user_scope_context: UserScopeContextContract | None = None
    semantic_memory_candidates: list[SemanticMemoryCandidateContract] = field(default_factory=list)

    @property
    def recovered_items(self) -> list[str]:
        return [*self.user_hints, *self.session_context, *self.mission_hints, *self.plan_hints]


@dataclass
class MemoryRecordResult:
    """Structured result for memory recording."""

    record_contract: MemoryRecordContract
    organization_scope_status: str
    organization_scope_reason: str
    organization_scope_reopen_signal: str
    user_scope_context: UserScopeContextContract | None = None
    procedural_artifact_status: str | None = None
    procedural_artifact_refs: list[str] = field(default_factory=list)
    procedural_artifact_version: int | None = None
    procedural_artifact_summary: str | None = None


@dataclass(frozen=True)
class SurfaceContinuityState:
    linked_surface_ids: list[str] = field(default_factory=list)
    active_surface_id: str | None = None
    last_surface_id: str | None = None
    surface_continuity_status: str | None = None
    surface_identity_conflict_flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectObjectiveContinuityState:
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None


@dataclass(frozen=True)
class OperatorFeedbackMemoryResult:
    feedback: OperatorFeedbackContract
    record: StoredExperienceReflection


class WorkflowLifecycleIntegrityError(RuntimeError):
    """Signal that a persisted lifecycle binding exists but cannot be trusted."""


class MemoryService:
    """Handles contextual continuity with persistent episodic and mission memory."""

    name = "memory-service"
    _MEMORY_REVIEW_ACTIONS = {
        "approve": "approved",
        "reject": "rejected",
        "needs_review": "needs_review",
        "rollback": "rolled_back",
    }

    def __init__(
        self,
        database_url: str | None = None,
        *,
        reviewed_procedural_playbook_verifier: (
            Callable[[ReviewedProceduralPlaybookContract], bool] | None
        ) = None,
        workflow_lifecycle_transition_verifier: (
            Callable[[WorkflowLifecycleTransitionContract], bool] | None
        ) = None,
        artifact_physical_mutation_verifier: (
            Callable[
                [LocalTextMutationReceipt, LocalTextPhysicalStateAttestationContract],
                bool,
            ]
            | None
        ) = None,
        artifact_physical_rollback_verifier: (
            Callable[
                [LocalTextRollbackReceipt, LocalTextPhysicalStateAttestationContract],
                bool,
            ]
            | None
        ) = None,
    ) -> None:
        configured_url = database_url or getenv("DATABASE_URL")
        self.repository = build_memory_repository(configured_url)
        self._reviewed_procedural_playbook_verifier = reviewed_procedural_playbook_verifier
        self._workflow_lifecycle_transition_verifier = workflow_lifecycle_transition_verifier
        self._artifact_physical_mutation_verifier = artifact_physical_mutation_verifier
        self._artifact_physical_rollback_verifier = artifact_physical_rollback_verifier

    def _verified_reviewed_procedural_playbook(
        self,
        playbook: ReviewedProceduralPlaybookContract,
    ) -> bool:
        verifier = self._reviewed_procedural_playbook_verifier
        if verifier is None:
            return False
        try:
            return bool(verifier(playbook))
        except (TypeError, ValueError, RuntimeError):
            return False

    def _verified_workflow_lifecycle_transition(
        self,
        transition: WorkflowLifecycleTransitionContract,
    ) -> bool:
        verifier = self._workflow_lifecycle_transition_verifier
        if verifier is None:
            return False
        try:
            return bool(verifier(transition))
        except (TypeError, ValueError, RuntimeError):
            return False

    def record_experience_reflection(
        self,
        *,
        experience: ExperienceRecordContract,
        reflection: PostTaskReflectionContract,
    ) -> StoredExperienceReflection:
        """Persist a bounded post-task experience/reflection pair."""

        blockers = list(reflection.blockers)
        if experience.automatic_promotion_allowed or reflection.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if experience.core_mutation_allowed or reflection.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if not experience.evidence_refs and not reflection.evidence_refs:
            blockers.append("evidence_required")
        sanitized_reflection = replace(
            reflection,
            blockers=self._merge_unique_strings(blockers, []),
            human_review_required=True,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )
        sanitized_experience = replace(
            experience,
            human_review_required=True,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
            reusable_memory_status=(
                "blocked"
                if "evidence_required" in sanitized_reflection.blockers
                else experience.reusable_memory_status
            ),
        )
        record = StoredExperienceReflection(
            experience=sanitized_experience,
            reflection=sanitized_reflection,
        )
        self._assert_experience_identity_is_immutable(sanitized_experience)
        self.repository.record_experience_reflection(record)
        self._assert_experience_was_persisted_exactly(sanitized_experience)
        return record

    def record_experience(
        self,
        *,
        experience: ExperienceRecordContract,
    ) -> StoredExperienceReflection:
        """Persist a bounded post-task experience before reflection exists."""

        reusable_status = experience.reusable_memory_status
        failure_modes = list(experience.failure_modes)
        if experience.automatic_promotion_allowed:
            failure_modes.append("automatic_promotion_not_allowed")
        if experience.core_mutation_allowed:
            failure_modes.append("core_mutation_not_allowed")
        if not experience.evidence_refs:
            failure_modes.append("evidence_required")
            reusable_status = "blocked"
        sanitized_experience = replace(
            experience,
            failure_modes=self._merge_unique_strings(failure_modes, []),
            human_review_required=True,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
            reusable_memory_status=reusable_status,
        )
        record = StoredExperienceReflection(experience=sanitized_experience)
        self._assert_experience_identity_is_immutable(sanitized_experience)
        self.repository.record_experience(sanitized_experience)
        self._assert_experience_was_persisted_exactly(sanitized_experience)
        return record

    def _assert_experience_identity_is_immutable(
        self,
        experience: ExperienceRecordContract,
    ) -> None:
        existing = self.repository.fetch_experience_reflection(experience.experience_id)
        if existing is not None:
            allowed_enrichment = replace(
                experience,
                user_feedback=existing.experience.user_feedback,
                evidence_refs=list(existing.experience.evidence_refs),
                signal_refs=list(existing.experience.signal_refs),
            )
            if existing.experience != allowed_enrichment:
                raise ValueError("experience identity is immutable")

    def _assert_experience_was_persisted_exactly(
        self,
        experience: ExperienceRecordContract,
    ) -> None:
        stored = self.repository.fetch_experience_reflection(experience.experience_id)
        if stored is None or stored.experience != experience:
            raise ValueError("experience identity is immutable")

    def list_experience_reflections(
        self,
        *,
        mission_id: str | None = None,
        workflow_profile: str | None = None,
        limit: int = 20,
    ) -> list[StoredExperienceReflection]:
        """Return recent bounded experience/reflection records."""

        return self.repository.list_experience_reflections(
            mission_id=mission_id,
            workflow_profile=workflow_profile,
            limit=max(1, limit),
        )

    def get_experience_reflection(
        self,
        experience_id: str,
    ) -> StoredExperienceReflection | None:
        """Return one canonical experience/reflection pair."""

        return self.repository.fetch_experience_reflection(experience_id)

    def build_recurring_pattern_report(
        self,
        *,
        report_id: str | None = None,
        workflow_profile: str | None = None,
        route: str | None = None,
        domain: str | None = None,
        minimum_occurrences: int = 2,
        max_records: int = 100,
        max_patterns: int = 20,
        generated_at: str | None = None,
    ) -> RecurringPatternReportContract:
        """Build read-only recurrence evidence from canonical learning memory."""

        records = self.list_experience_reflections(
            workflow_profile=workflow_profile,
            limit=max_records + 1,
        )
        resolved_at = generated_at or datetime.now(UTC).isoformat()
        return build_recurring_pattern_report(
            report_id=report_id or f"recurring-pattern-report://{uuid4().hex[:12]}",
            experiences=[record.experience for record in records],
            reflections=[record.reflection for record in records if record.reflection is not None],
            minimum_occurrences=minimum_occurrences,
            generated_at=resolved_at,
            workflow_profile=workflow_profile,
            route=route,
            domain=domain,
            max_records=max_records,
            max_patterns=max_patterns,
        )

    def record_operator_feedback(
        self,
        feedback: OperatorFeedbackContract,
    ) -> OperatorFeedbackMemoryResult:
        """Attach explicit bounded operator feedback to canonical learning memory."""

        record = self.get_experience_reflection(feedback.experience_id)
        if record is None:
            raise ValueError("operator feedback requires an existing experience")
        if str(record.experience.mission_id) != str(feedback.mission_id):
            raise ValueError("operator feedback mission does not match experience")
        if record.reflection is None:
            raise ValueError("operator feedback requires an existing reflection")
        if feedback.assessment not in {
            "helpful",
            "partially_helpful",
            "not_helpful",
            "correction",
        }:
            raise ValueError("unsupported operator feedback assessment")
        if feedback.rating is not None and (
            isinstance(feedback.rating, bool) or feedback.rating < 1 or feedback.rating > 5
        ):
            raise ValueError("operator feedback rating must be between 1 and 5")
        if feedback.assessment == "correction" and not feedback.correction:
            raise ValueError("correction feedback requires correction text")
        if not feedback.operator_ref or len(feedback.operator_ref) > 160:
            raise ValueError("operator feedback requires a bounded operator_ref")
        if len(feedback.evidence_refs) > 20 or any(
            not item or len(item) > 200 for item in feedback.evidence_refs
        ):
            raise ValueError("operator feedback evidence_refs must be bounded")
        if feedback.automatic_promotion_allowed or feedback.core_mutation_allowed:
            raise ValueError("operator feedback cannot authorize autonomous mutation")
        if feedback.memory_write_mode != "through_core_only":
            raise ValueError("operator feedback must write through the sovereign core")

        safe_feedback = replace(
            feedback,
            comment=self._bounded_operator_feedback_text(feedback.comment, 1000),
            correction=self._bounded_operator_feedback_text(feedback.correction, 1000),
            next_expectation=self._bounded_operator_feedback_text(
                feedback.next_expectation,
                500,
            ),
            evidence_refs=self._merge_unique_strings(feedback.evidence_refs, []),
            feedback_status="recorded_bounded",
            evolution_review_status="needs_review",
            memory_write_mode="through_core_only",
            human_review_required=True,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )
        feedback_summary = self._operator_feedback_summary(safe_feedback)
        feedback_signals = [
            safe_feedback.feedback_id,
            f"operator-feedback://assessment/{safe_feedback.assessment}",
        ]
        if safe_feedback.rating is not None:
            feedback_signals.append(f"operator-feedback://rating/{safe_feedback.rating}")

        for _attempt in range(16):
            if record is None:
                raise ValueError("operator feedback requires an existing experience")
            if str(record.experience.mission_id) != str(safe_feedback.mission_id):
                raise ValueError("operator feedback mission does not match experience")
            if record.reflection is None:
                raise ValueError("operator feedback requires an existing reflection")
            prior_feedback = record.experience.user_feedback or ""
            combined_feedback = " | ".join(
                item for item in (prior_feedback, feedback_summary) if item
            )[-2000:]
            evidence_refs = self._merge_unique_strings(
                record.experience.evidence_refs,
                [safe_feedback.feedback_id],
                safe_feedback.evidence_refs,
            )
            updated_experience = replace(
                record.experience,
                user_feedback=combined_feedback,
                evidence_refs=evidence_refs,
                signal_refs=self._merge_unique_strings(
                    record.experience.signal_refs,
                    feedback_signals,
                ),
                human_review_required=True,
                automatic_promotion_allowed=False,
                core_mutation_allowed=False,
            )
            updated_reflection = replace(
                record.reflection,
                evidence_refs=evidence_refs,
                proposed_tests=self._merge_unique_strings(
                    record.reflection.proposed_tests,
                    ["evaluate_decision_against_explicit_operator_feedback"],
                ),
                human_review_required=True,
                automatic_promotion_allowed=False,
                core_mutation_allowed=False,
            )
            replacement = StoredExperienceReflection(
                experience=updated_experience,
                reflection=updated_reflection,
            )
            if self.repository.compare_and_swap_operator_feedback(
                expected=record,
                replacement=replacement,
            ):
                persisted = self.get_experience_reflection(safe_feedback.experience_id)
                if persisted is None:
                    raise RuntimeError("operator feedback persistence disappeared")
                return OperatorFeedbackMemoryResult(
                    feedback=safe_feedback,
                    record=persisted,
                )
            record = self.get_experience_reflection(safe_feedback.experience_id)
        raise RuntimeError("operator feedback contention limit exceeded")

    def record_reviewed_learning_guidance(
        self,
        guidance: ReviewedLearningGuidanceContract,
    ) -> StoredReviewedLearningGuidance:
        """Persist human-reviewed learning guidance with safety invariants."""

        if guidance.automatic_promotion_allowed:
            raise ValueError("reviewed learning guidance cannot allow autopromotion")
        if guidance.core_mutation_allowed:
            raise ValueError("reviewed learning guidance cannot mutate the core")
        if not guidance.evidence_refs:
            raise ValueError("reviewed learning guidance requires evidence_refs")
        if not guidance.rollback_plan_ref:
            raise ValueError("reviewed learning guidance requires rollback_plan_ref")
        safe_guidance = replace(
            guidance,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
            evidence_refs=self._merge_unique_strings(guidance.evidence_refs, []),
            allowed_usage=self._merge_unique_strings(guidance.allowed_usage, []),
        )
        record = StoredReviewedLearningGuidance(guidance=safe_guidance)
        self.repository.record_reviewed_learning_guidance(record)
        return record

    def list_reviewed_learning_guidance(
        self,
        *,
        route: str | None = None,
        workflow_profile: str | None = None,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[StoredReviewedLearningGuidance]:
        """Return recent human-reviewed learning guidance."""

        return self.repository.list_reviewed_learning_guidance(
            route=route,
            workflow_profile=workflow_profile,
            domain=domain,
            limit=max(1, limit),
        )

    def list_memory_lifecycle_review_queue(
        self,
        *,
        maintenance_action: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
        generated_at: str | None = None,
    ) -> list[MemoryLifecycleCandidateContract]:
        """Derive a human-only maintenance queue from canonical memory signals."""

        safe_generated_at = generated_at or self.now()
        corpus = self.repository.summarize_memory_corpus()
        candidates: list[MemoryLifecycleCandidateContract] = []
        if corpus.consolidating_records > 0:
            evidence_refs = [
                f"memory-telemetry://consolidating-records/{corpus.consolidating_records}",
            ]
            candidates.append(
                self._memory_lifecycle_candidate(
                    maintenance_action="consolidate",
                    target_scope="semantic_procedural_corpus",
                    target_refs=["memory-corpus://semantic-procedural/consolidating"],
                    reason=(
                        f"{corpus.consolidating_records} memory record(s) remain in "
                        "consolidating lifecycle state"
                    ),
                    evidence_refs=evidence_refs,
                    rollback_plan_ref=(
                        "rollback://memory-lifecycle/consolidation/restore-corpus-snapshot"
                    ),
                    generated_at=safe_generated_at,
                )
            )
        if corpus.archivable_records > 0:
            evidence_refs = [
                f"memory-telemetry://archivable-records/{corpus.archivable_records}",
            ]
            candidates.append(
                self._memory_lifecycle_candidate(
                    maintenance_action="archive",
                    target_scope="semantic_procedural_corpus",
                    target_refs=["memory-corpus://semantic-procedural/archivable"],
                    reason=(
                        f"{corpus.archivable_records} memory record(s) are archive "
                        "candidates and require human disposition"
                    ),
                    evidence_refs=evidence_refs,
                    rollback_plan_ref=(
                        "rollback://memory-lifecycle/archive/restore-indexed-records"
                    ),
                    generated_at=safe_generated_at,
                )
            )

        for record in self.repository.list_reviewed_learning_guidance(limit=200):
            guidance = record.guidance
            if not guidance.expires_at or not self._timestamp_reached(
                guidance.expires_at,
                safe_generated_at,
            ):
                continue
            candidates.append(
                self._memory_lifecycle_candidate(
                    maintenance_action="expire",
                    target_scope="reviewed_learning_guidance",
                    target_refs=[guidance.guidance_id],
                    reason=(
                        "reviewed learning guidance reached its bounded validity window "
                        f"at {guidance.expires_at}"
                    ),
                    evidence_refs=self._merge_unique_strings(
                        guidance.evidence_refs,
                        [f"memory-expiration://{guidance.expires_at}"],
                    ),
                    rollback_plan_ref=(
                        guidance.rollback_plan_ref
                        or f"rollback://reviewed-learning/{guidance.guidance_id}"
                    ),
                    generated_at=safe_generated_at,
                )
            )

        latest_by_candidate: dict[str, MemoryLifecycleReviewDecisionContract] = {}
        for record in self.repository.list_memory_lifecycle_review_decisions(limit=500):
            latest_by_candidate.setdefault(record.decision.candidate_id, record.decision)
        reviewed_candidates = [
            self._candidate_with_review(candidate, latest_by_candidate.get(candidate.candidate_id))
            for candidate in candidates
        ]
        if maintenance_action:
            reviewed_candidates = [
                candidate
                for candidate in reviewed_candidates
                if candidate.maintenance_action == maintenance_action
            ]
        if review_status:
            reviewed_candidates = [
                candidate
                for candidate in reviewed_candidates
                if candidate.review_status == review_status
            ]
        reviewed_candidates.sort(
            key=lambda item: (
                {"archive": 0, "expire": 1, "consolidate": 2}.get(
                    item.maintenance_action,
                    9,
                ),
                item.candidate_id,
            )
        )
        return reviewed_candidates[: max(1, min(limit, 200))]

    def get_memory_lifecycle_candidate(
        self,
        candidate_id: str,
        *,
        generated_at: str | None = None,
    ) -> MemoryLifecycleCandidateContract | None:
        """Return one currently evidenced maintenance candidate."""

        return next(
            (
                candidate
                for candidate in self.list_memory_lifecycle_review_queue(
                    limit=200,
                    generated_at=generated_at,
                )
                if candidate.candidate_id == candidate_id
            ),
            None,
        )

    def record_memory_lifecycle_review_decision(
        self,
        *,
        candidate_id: str,
        decision_action: str,
        operator_ref: str,
        evidence_refs: list[str],
        rollback_plan_ref: str | None,
        review_notes: list[str],
        governance_assessment: MemoryLifecycleGovernanceAssessmentContract,
    ) -> MemoryLifecycleReviewDecisionContract:
        """Persist a governed human decision without executing memory maintenance."""

        normalized_action = decision_action.replace("-", "_")
        if normalized_action not in self._MEMORY_REVIEW_ACTIONS:
            raise ValueError(f"unsupported memory lifecycle review action: {decision_action}")
        candidate = self.get_memory_lifecycle_candidate(
            candidate_id,
            generated_at=governance_assessment.timestamp,
        )
        if candidate is None:
            raise ValueError(f"unknown memory lifecycle candidate: {candidate_id}")
        if governance_assessment.status != "governed" or governance_assessment.blockers:
            raise ValueError("memory lifecycle review requires a governed assessment")
        if governance_assessment.candidate_id != candidate.candidate_id:
            raise ValueError("memory lifecycle governance candidate mismatch")
        if governance_assessment.maintenance_action != candidate.maintenance_action:
            raise ValueError("memory lifecycle governance action mismatch")
        if governance_assessment.decision_action != normalized_action:
            raise ValueError("memory lifecycle governance decision mismatch")
        if (
            not governance_assessment.human_review_required
            or governance_assessment.execution_authorized
            or governance_assessment.automatic_execution_allowed
            or governance_assessment.core_mutation_allowed
        ):
            raise ValueError("memory lifecycle governance cannot authorize mutation")
        required_policy_refs = {
            "policy://memory-lifecycle/human-review-required",
            "policy://memory-lifecycle/no-autonomous-maintenance",
            "policy://memory-lifecycle/separate-execution-step",
        }
        if not required_policy_refs.issubset(governance_assessment.policy_refs):
            raise ValueError("memory lifecycle governance policy trace required")
        if normalized_action in {"approve", "rollback"} and not evidence_refs:
            raise ValueError("memory lifecycle review evidence required")
        if normalized_action in {"approve", "rollback"} and not rollback_plan_ref:
            raise ValueError("memory lifecycle rollback plan required")
        if not self._bounded_memory_review_ref(operator_ref):
            raise ValueError("bounded memory lifecycle operator ref required")
        if rollback_plan_ref and not self._bounded_memory_review_ref(rollback_plan_ref):
            raise ValueError("bounded memory lifecycle rollback ref required")
        if any(not self._bounded_memory_review_ref(ref) for ref in evidence_refs):
            raise ValueError("bounded memory lifecycle evidence refs required")
        previous_decisions = self.repository.list_memory_lifecycle_review_decisions(
            candidate_id=candidate.candidate_id,
            limit=1,
        )
        if normalized_action == "rollback" and (
            not previous_decisions or previous_decisions[0].decision.review_status != "approved"
        ):
            raise ValueError("approved memory lifecycle review required before rollback")

        review_timestamp = self.now()
        review_identity = sha256(f"{candidate_id}|{review_timestamp}".encode()).hexdigest()[:16]
        decision = MemoryLifecycleReviewDecisionContract(
            review_decision_id=(f"memory-lifecycle-review://{review_identity}"),
            candidate_id=candidate.candidate_id,
            maintenance_action=candidate.maintenance_action,
            decision_action=normalized_action,
            review_status=self._MEMORY_REVIEW_ACTIONS[normalized_action],
            operator_ref=operator_ref,
            evidence_refs=self._merge_unique_strings(evidence_refs, []),
            rollback_plan_ref=rollback_plan_ref or candidate.rollback_plan_ref,
            governance_assessment_id=governance_assessment.assessment_id,
            timestamp=review_timestamp,
            review_notes=self._merge_unique_strings(review_notes, []),
            execution_authorized=False,
            automatic_execution_allowed=False,
            core_mutation_allowed=False,
        )
        self.repository.record_memory_lifecycle_review_decision(
            StoredMemoryLifecycleReviewDecision(decision=decision)
        )
        return decision

    def list_memory_lifecycle_review_decisions(
        self,
        *,
        candidate_id: str | None = None,
        limit: int = 20,
    ) -> list[StoredMemoryLifecycleReviewDecision]:
        """Return persisted human review history for memory maintenance."""

        return self.repository.list_memory_lifecycle_review_decisions(
            candidate_id=candidate_id,
            limit=max(1, min(limit, 200)),
        )

    @staticmethod
    def evaluate_influence_policy(
        *,
        decision_id: str,
        signals: list[MemoryInfluenceSignalContract],
        route: str | None,
        workflow_profile: str | None,
        domain: str | None,
        generated_at: str,
    ) -> MemoryInfluencePolicyDecisionContract:
        """Apply the shared read-only policy without creating another store."""

        return evaluate_memory_influence_policy(
            decision_id=decision_id,
            signals=signals,
            route=route,
            workflow_profile=workflow_profile,
            domain=domain,
            generated_at=generated_at,
        )

    def record_procedural_playbook_candidate(
        self,
        candidate: ProceduralPlaybookCandidateContract,
    ) -> StoredProceduralPlaybookCandidate:
        """Persist a bounded procedural playbook candidate for human review."""

        blockers = list(candidate.blockers)
        if candidate.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if candidate.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if not candidate.evidence_refs:
            blockers.append("evidence_required")
        if not candidate.rollback_plan_ref:
            blockers.append("rollback_plan_required")
        if not candidate.bounded_steps:
            blockers.append("bounded_steps_required")
        review_status = (
            "needs_review"
            if blockers or candidate.review_status not in {"candidate", "needs_review"}
            else candidate.review_status
        )
        safe_candidate = replace(
            candidate,
            bounded_steps=self._merge_unique_strings(candidate.bounded_steps, [])[:8],
            evidence_refs=self._merge_unique_strings(candidate.evidence_refs, []),
            source_artifact_refs=self._merge_unique_strings(
                candidate.source_artifact_refs,
                [],
            ),
            source_reflection_refs=self._merge_unique_strings(
                candidate.source_reflection_refs,
                [],
            ),
            proposed_tests=self._merge_unique_strings(candidate.proposed_tests, []),
            review_status=review_status,
            blockers=self._merge_unique_strings(blockers, []),
            human_review_required=True,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
            memory_write_mode="through_core_only",
        )
        record = StoredProceduralPlaybookCandidate(candidate=safe_candidate)
        self.repository.record_procedural_playbook_candidate(record)
        return record

    def list_procedural_playbook_candidates(
        self,
        *,
        workflow_profile: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredProceduralPlaybookCandidate]:
        """Return recent bounded procedural playbook candidates."""

        return self.repository.list_procedural_playbook_candidates(
            workflow_profile=workflow_profile,
            review_status=review_status,
            limit=max(1, limit),
        )

    def record_reviewed_procedural_playbook(
        self,
        playbook: ReviewedProceduralPlaybookContract,
    ) -> StoredReviewedProceduralPlaybook:
        """Persist immutable reviewed guidance without granting execution authority."""

        if not self._verified_reviewed_procedural_playbook(playbook):
            raise ValueError(
                "reviewed procedural playbook requires persisted evolution verification"
            )

        if parse_canonical_semver(playbook.version) is None:
            raise ValueError("reviewed procedural playbook requires numeric semver")
        if playbook.review_status != "approved":
            raise ValueError("new reviewed procedural playbook must be approved")
        identity_and_scope = {
            "playbook_id": playbook.playbook_id,
            "source_candidate_id": playbook.source_candidate_id,
            "source_review_decision_id": playbook.source_review_decision_id,
            "evolution_proposal_id": str(playbook.evolution_proposal_id),
            "procedure_name": playbook.procedure_name,
            "route": playbook.route,
            "workflow_profile": playbook.workflow_profile,
            "domain": playbook.domain,
            "rollback_plan_ref": playbook.rollback_plan_ref,
            "timestamp": playbook.timestamp,
        }
        if any(
            not str(value).strip() or len(str(value)) > 500 for value in identity_and_scope.values()
        ):
            raise ValueError("reviewed procedural playbook scope is incomplete")
        if len(f"{playbook.playbook_id}@{playbook.version}") > 240 or any(
            len(str(identity_and_scope[field_name])) > 240
            for field_name in (
                "source_candidate_id",
                "source_review_decision_id",
                "evolution_proposal_id",
                "rollback_plan_ref",
            )
        ):
            raise ValueError("reviewed procedural playbook refs must be bounded")
        if (
            not playbook.bounded_steps
            or len(playbook.bounded_steps) > 8
            or any(
                not isinstance(step, str) or not step.strip() or len(step) > 500
                for step in playbook.bounded_steps
            )
        ):
            raise ValueError("reviewed procedural playbook steps must be bounded")
        if (
            not playbook.evidence_refs
            or len(playbook.evidence_refs) > 20
            or any(
                not isinstance(ref, str) or not ref.strip() or len(ref) > 240
                for ref in playbook.evidence_refs
            )
        ):
            raise ValueError("reviewed procedural playbook evidence is invalid")
        if any(not isinstance(value, str) for value in playbook.allowed_usage) or set(
            playbook.allowed_usage
        ) != {"planning_context"}:
            raise ValueError("reviewed procedural playbook is planning guidance only")
        if (
            not playbook.read_only
            or not playbook.human_review_required
            or playbook.execution_allowed
            or playbook.tool_dispatch_allowed
            or playbook.memory_write_mode != "read_only"
            or playbook.automatic_promotion_allowed
            or playbook.core_mutation_allowed
        ):
            raise ValueError("reviewed procedural playbook cannot claim authority")
        safe_playbook = replace(
            playbook,
            bounded_steps=self._merge_unique_strings(playbook.bounded_steps, [])[:8],
            allowed_usage=self._merge_unique_strings(playbook.allowed_usage, []),
            evidence_refs=self._merge_unique_strings(playbook.evidence_refs, []),
            revoked_at=None,
            revocation_ref=None,
            read_only=True,
            human_review_required=True,
            execution_allowed=False,
            tool_dispatch_allowed=False,
            memory_write_mode="read_only",
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )
        existing = self.repository.fetch_reviewed_procedural_playbook(
            safe_playbook.playbook_id,
            safe_playbook.version,
        )
        if existing is not None and existing.playbook != safe_playbook:
            raise ValueError("reviewed procedural playbook version is immutable")
        record = StoredReviewedProceduralPlaybook(playbook=safe_playbook)
        if existing is None:
            inserted = self.repository._insert_reviewed_procedural_playbook(record)
            if inserted:
                return record
            existing = self.repository.fetch_reviewed_procedural_playbook(
                safe_playbook.playbook_id,
                safe_playbook.version,
            )
        if existing is None or existing.playbook != safe_playbook:
            raise ValueError("reviewed procedural playbook version is immutable")
        return existing

    def revoke_reviewed_procedural_playbook(
        self,
        *,
        playbook_id: str,
        version: str,
        revocation_ref: str,
        revoked_at: str,
    ) -> StoredReviewedProceduralPlaybook:
        """Revoke causal eligibility while preserving the reviewed artifact."""

        record = self.repository.fetch_reviewed_procedural_playbook(
            playbook_id,
            version,
        )
        if record is None:
            raise ValueError("unknown reviewed procedural playbook")
        if not self._verified_reviewed_procedural_playbook(record.playbook):
            raise ValueError(
                "reviewed procedural playbook requires persisted evolution verification"
            )
        if not revocation_ref or len(revocation_ref) > 240:
            raise ValueError("revocation requires a bounded human decision ref")
        if not revoked_at or len(revoked_at) > 100:
            raise ValueError("revocation requires a bounded timestamp")
        if record.playbook.review_status == "revoked":
            if record.playbook.revocation_ref != revocation_ref:
                raise ValueError("playbook version already revoked by another decision")
            return record
        revoked = replace(
            record.playbook,
            review_status="revoked",
            evidence_refs=self._merge_unique_strings(
                [revocation_ref],
                record.playbook.evidence_refs,
            )[:20],
            revoked_at=revoked_at,
            revocation_ref=revocation_ref,
            execution_allowed=False,
            tool_dispatch_allowed=False,
        )
        revoked_record = StoredReviewedProceduralPlaybook(playbook=revoked)
        if self.repository._transition_reviewed_procedural_playbook_to_revoked(revoked_record):
            return revoked_record
        winner = self.repository.fetch_reviewed_procedural_playbook(
            playbook_id,
            version,
        )
        if (
            winner is not None
            and winner.playbook.review_status == "revoked"
            and winner.playbook.revocation_ref == revocation_ref
        ):
            return winner
        raise ValueError("playbook version was revoked by another decision")

    def list_reviewed_procedural_playbooks(
        self,
        *,
        workflow_profile: str | None = None,
        route: str | None = None,
        domain: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredReviewedProceduralPlaybook]:
        """Return reviewed and revoked guidance for governed policy evaluation."""

        requested_limit = max(1, min(limit, 100))
        page_size = max(20, requested_limit)
        verified_records: list[StoredReviewedProceduralPlaybook] = []
        offset = 0
        while len(verified_records) < requested_limit:
            page = self.repository.list_reviewed_procedural_playbooks(
                workflow_profile=workflow_profile,
                route=route,
                domain=domain,
                review_status=review_status,
                limit=page_size,
                offset=offset,
            )
            if not page:
                break
            verified_records.extend(
                record
                for record in page
                if self._verified_reviewed_procedural_playbook(record.playbook)
            )
            offset += len(page)
            if len(page) < page_size:
                break
        return verified_records[:requested_limit]

    @staticmethod
    def _validate_decision_outcome_attribution(
        record: DecisionOutcomeAttributionRecordContract,
    ) -> None:
        validate_decision_attribution_record(record)
        required_refs = (
            ("attribution_record_id", record.attribution_record_id),
            ("request_id", record.request_id),
            ("session_id", record.session_id),
            ("observed_at", record.observed_at),
            ("governance_decision_ref", record.governance_decision_ref),
            ("governance_decision_status", record.governance_decision_status),
        )
        for field_name, value in required_refs:
            if not str(value).strip() or len(str(value)) > 500:
                raise ValueError(f"{field_name} must be present and bounded")
        for field_name in ("mission_id", "workflow_profile", "route"):
            value = getattr(record, field_name)
            if value is not None and (not str(value).strip() or len(str(value)) > 500):
                raise ValueError(f"{field_name} must be bounded when present")
        if (
            not record.read_only
            or not record.immutable
            or not record.human_review_required
            or record.memory_write_allowed
            or record.execution_allowed
            or record.tool_dispatch_allowed
            or record.promotion_authorized
            or record.automatic_promotion_allowed
            or record.core_mutation_allowed
            or record.causal_effect_proven
        ):
            raise ValueError("decision outcome attribution cannot claim authority")
        if record.causality_scope != "runtime_declared_participation_only":
            raise ValueError("decision outcome attribution causality scope is invalid")
        if record.gain_claim_status != "not_established_without_comparator":
            raise ValueError("decision outcome attribution cannot claim unmeasured gain")
        decision_attribution_fingerprint(record)

    def record_decision_outcome_attribution(
        self,
        record: DecisionOutcomeAttributionRecordContract,
    ) -> DecisionOutcomeAttributionRecordContract:
        """Append one immutable outcome attribution, idempotently by both ids."""

        self._validate_decision_outcome_attribution(record)
        expected_fingerprint = decision_attribution_fingerprint(record)

        def exact_match(
            existing: DecisionOutcomeAttributionRecordContract | None,
        ) -> bool:
            return (
                existing is not None
                and existing == record
                and decision_attribution_fingerprint(existing) == expected_fingerprint
            )

        existing_by_id = self.repository.fetch_decision_outcome_attribution(
            attribution_record_id=record.attribution_record_id
        )
        existing_by_request = self.repository.fetch_decision_outcome_attribution(
            request_id=str(record.request_id)
        )
        if existing_by_id is not None or existing_by_request is not None:
            if exact_match(existing_by_id) and exact_match(existing_by_request):
                self._validate_decision_outcome_storage_links(record)
                return record
            raise ValueError("decision outcome attribution identity is immutable")

        self._validate_decision_outcome_storage_links(record)

        if self.repository._insert_decision_outcome_attribution(record):
            return record

        winner_by_id = self.repository.fetch_decision_outcome_attribution(
            attribution_record_id=record.attribution_record_id
        )
        winner_by_request = self.repository.fetch_decision_outcome_attribution(
            request_id=str(record.request_id)
        )
        if exact_match(winner_by_id) and exact_match(winner_by_request):
            self._validate_decision_outcome_storage_links(record)
            return record
        raise ValueError("decision outcome attribution identity is immutable")

    def _validate_decision_outcome_storage_links(
        self,
        record: DecisionOutcomeAttributionRecordContract,
    ) -> None:
        runtime_claim = self.repository.fetch_runtime_request_claim(str(record.request_id))
        if runtime_claim is None:
            raise ValueError("decision outcome attribution requires a runtime request claim")
        if runtime_claim.session_id != str(record.session_id):
            raise ValueError(
                "decision outcome attribution session does not match runtime request claim"
            )
        stored_experience = self.repository.fetch_experience_reflection(str(record.experience_id))
        if stored_experience is None:
            raise ValueError("decision outcome attribution requires a persisted experience")
        experience = stored_experience.experience
        if (
            experience.experience_id != record.experience_id
            or experience.mission_id != record.mission_id
            or experience.workflow_profile != record.workflow_profile
            or experience.route != record.route
            or experience.outcome_status != record.outcome_status
            or experience.timestamp != record.observed_at
        ):
            raise ValueError("decision outcome attribution does not match persisted experience")

    def claim_runtime_request(
        self,
        *,
        request_id: str,
        session_id: str,
        claimed_at: str,
    ) -> bool:
        """Atomically reserve a request identity before any runtime side effect."""

        for field_name, value in (
            ("request_id", request_id),
            ("session_id", session_id),
            ("claimed_at", claimed_at),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{field_name} must be present and canonical")
            if len(value) > 500:
                raise ValueError(f"{field_name} must be bounded")
        return self.repository._claim_runtime_request(
            request_id=request_id,
            session_id=session_id,
            claimed_at=claimed_at,
        )

    def get_decision_outcome_attribution(
        self,
        *,
        attribution_record_id: str | None = None,
        request_id: str | None = None,
    ) -> DecisionOutcomeAttributionRecordContract | None:
        """Load one verified attribution by exactly one canonical identity."""

        if (attribution_record_id is None) == (request_id is None):
            raise ValueError("exactly one attribution identity is required")
        identity = attribution_record_id if attribution_record_id is not None else request_id
        if identity is None or not identity.strip() or len(identity) > 500:
            raise ValueError("attribution identity must be present and bounded")
        record = self.repository.fetch_decision_outcome_attribution(
            attribution_record_id=attribution_record_id,
            request_id=request_id,
        )
        if record is not None:
            self._validate_decision_outcome_attribution(record)
            self._validate_decision_outcome_storage_links(record)
        return record

    def list_decision_outcome_attributions(
        self,
        *,
        request_id: str | None = None,
        mission_id: str | None = None,
        workflow_profile: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DecisionOutcomeAttributionRecordContract]:
        """List verified attribution records after applying storage scope filters."""

        for field_name, value in (
            ("request_id", request_id),
            ("mission_id", mission_id),
            ("workflow_profile", workflow_profile),
        ):
            if value is not None and (not value.strip() or len(value) > 500):
                raise ValueError(f"{field_name} must be bounded when present")
        requested_limit = max(1, min(limit, 100))
        requested_offset = max(0, offset)
        storage_offset = 0
        valid_records_seen = 0
        verified_records: list[DecisionOutcomeAttributionRecordContract] = []
        while len(verified_records) < requested_limit:
            try:
                page = self.repository.list_decision_outcome_attributions(
                    request_id=request_id,
                    mission_id=mission_id,
                    workflow_profile=workflow_profile,
                    limit=1,
                    offset=storage_offset,
                )
            except ValueError:
                storage_offset += 1
                continue
            if not page:
                break
            storage_offset += 1
            record = page[0]
            try:
                self._validate_decision_outcome_attribution(record)
                self._validate_decision_outcome_storage_links(record)
            except ValueError:
                continue
            if valid_records_seen < requested_offset:
                valid_records_seen += 1
                continue
            verified_records.append(record)
        return verified_records

    @staticmethod
    def _validate_workflow_lifecycle_scope(*, workflow_profile: str, route: str) -> None:
        for field_name, value in (
            ("workflow_profile", workflow_profile),
            ("route", route),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                raise ValueError(f"{field_name} must be present and bounded")

    def _load_validated_workflow_lifecycle_chain(
        self,
        *,
        workflow_profile: str,
        route: str,
        through_revision: int | None = None,
    ) -> list[StoredWorkflowLifecycleTransition]:
        """Rebuild one chain from genesis so callers never trust an isolated tail."""

        if through_revision is not None:
            if through_revision < 1:
                return []
            target_revision = through_revision
        else:
            latest = self.repository.fetch_latest_workflow_lifecycle_transition(
                workflow_profile=workflow_profile,
                route=route,
            )
            if latest is None:
                return []
            target_revision = latest.transition.revision
        chain: list[StoredWorkflowLifecycleTransition] = []
        current: WorkflowLifecycleTransitionContract | None = None
        for revision in range(1, target_revision + 1):
            stored = self.repository.fetch_workflow_lifecycle_transition(
                workflow_profile=workflow_profile,
                route=route,
                revision=revision,
            )
            if stored is None:
                return []
            if not self._verified_workflow_lifecycle_transition(stored.transition):
                return []
            transition_failures = validate_workflow_lifecycle_transition(
                stored.transition,
                current_transition=current,
            )
            assessment_failures = validate_workflow_lifecycle_governance_assessment(
                stored.governance_assessment,
                transition=stored.transition,
                current_transition=current,
            )
            if transition_failures or assessment_failures:
                return []
            if (
                stored.transition_fingerprint
                != workflow_lifecycle_transition_fingerprint(stored.transition)
                or stored.governance_assessment_fingerprint
                != workflow_lifecycle_artifact_fingerprint(stored.governance_assessment)
            ):
                return []
            chain.append(stored)
            current = stored.transition
        return chain

    def record_workflow_lifecycle_transition(
        self,
        transition: WorkflowLifecycleTransitionContract,
        governance_assessment: WorkflowLifecycleGovernanceAssessmentContract,
    ) -> WorkflowLifecycleTransitionContract:
        """Append one exact, human-authorized transition through canonical memory."""

        self._validate_workflow_lifecycle_scope(
            workflow_profile=transition.workflow_profile,
            route=transition.route,
        )
        existing_by_id = self.repository.fetch_workflow_lifecycle_transition(
            transition_id=transition.transition_id
        )
        existing_by_revision = self.repository.fetch_workflow_lifecycle_transition(
            workflow_profile=transition.workflow_profile,
            route=transition.route,
            revision=transition.revision,
        )
        if existing_by_id is not None or existing_by_revision is not None:
            if (
                existing_by_id is not None
                and existing_by_revision is not None
                and existing_by_id == existing_by_revision
                and existing_by_id.transition == transition
                and existing_by_id.governance_assessment == governance_assessment
                and self._load_validated_workflow_lifecycle_chain(
                    workflow_profile=transition.workflow_profile,
                    route=transition.route,
                    through_revision=transition.revision,
                )
            ):
                return transition
            raise ValueError("workflow lifecycle transition identity is immutable")

        if not self._verified_workflow_lifecycle_transition(transition):
            raise ValueError(
                "workflow lifecycle transition requires a verified persisted release bundle"
            )

        current_chain = self._load_validated_workflow_lifecycle_chain(
            workflow_profile=transition.workflow_profile,
            route=transition.route,
        )
        current = current_chain[-1].transition if current_chain else None
        transition_failures = validate_workflow_lifecycle_transition(
            transition,
            current_transition=current,
        )
        assessment_failures = validate_workflow_lifecycle_governance_assessment(
            governance_assessment,
            transition=transition,
            current_transition=current,
        )
        if transition_failures:
            raise ValueError(
                "workflow lifecycle transition is invalid: " + "; ".join(transition_failures)
            )
        if assessment_failures:
            raise ValueError(
                "workflow lifecycle governance assessment is invalid: "
                + "; ".join(assessment_failures)
            )
        if (
            governance_assessment.status != "approved"
            or not governance_assessment.human_authorization_verified
            or not governance_assessment.transition_recording_authorized
        ):
            raise ValueError(
                "workflow lifecycle transition requires approved governance authorization"
            )
        stored = StoredWorkflowLifecycleTransition(
            transition=transition,
            governance_assessment=governance_assessment,
            transition_fingerprint=workflow_lifecycle_transition_fingerprint(transition),
            governance_assessment_fingerprint=workflow_lifecycle_artifact_fingerprint(
                governance_assessment
            ),
        )
        if self.repository._insert_workflow_lifecycle_transition(stored):
            return transition

        winner_by_id = self.repository.fetch_workflow_lifecycle_transition(
            transition_id=transition.transition_id
        )
        winner_by_revision = self.repository.fetch_workflow_lifecycle_transition(
            workflow_profile=transition.workflow_profile,
            route=transition.route,
            revision=transition.revision,
        )
        if (
            winner_by_id is not None
            and winner_by_revision is not None
            and winner_by_id == winner_by_revision == stored
            and self._load_validated_workflow_lifecycle_chain(
                workflow_profile=transition.workflow_profile,
                route=transition.route,
                through_revision=transition.revision,
            )
        ):
            return transition
        raise ValueError("workflow lifecycle transition lost compare-and-swap")

    def get_active_workflow_lifecycle(
        self,
        *,
        workflow_profile: str,
        route: str,
    ) -> WorkflowLifecycleTransitionContract | None:
        """Return the active tail only after validating every link from genesis."""

        self._validate_workflow_lifecycle_scope(
            workflow_profile=workflow_profile,
            route=route,
        )
        latest = self.repository.fetch_latest_workflow_lifecycle_transition(
            workflow_profile=workflow_profile,
            route=route,
        )
        if latest is None:
            return None
        chain = self._load_validated_workflow_lifecycle_chain(
            workflow_profile=workflow_profile,
            route=route,
            through_revision=latest.transition.revision,
        )
        if not chain or chain[-1] != latest:
            raise WorkflowLifecycleIntegrityError("workflow_lifecycle_persisted_chain_rejected")
        return chain[-1].transition

    def list_workflow_lifecycle_transitions(
        self,
        *,
        workflow_profile: str | None = None,
        route: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WorkflowLifecycleTransitionContract]:
        """List verified transitions in stable scope order, newest revision first."""

        for field_name, value in (
            ("workflow_profile", workflow_profile),
            ("route", route),
        ):
            if value is not None and (not value.strip() or len(value) > 500):
                raise ValueError(f"{field_name} must be bounded when present")
        requested_limit = max(1, min(limit, 100))
        requested_offset = max(0, offset)
        storage_offset = 0
        valid_records_seen = 0
        verified: list[WorkflowLifecycleTransitionContract] = []
        while len(verified) < requested_limit:
            page = self.repository.list_workflow_lifecycle_transitions(
                workflow_profile=workflow_profile,
                route=route,
                limit=1,
                offset=storage_offset,
            )
            if not page:
                break
            storage_offset += 1
            stored = page[0]
            chain = self._load_validated_workflow_lifecycle_chain(
                workflow_profile=stored.transition.workflow_profile,
                route=stored.transition.route,
                through_revision=stored.transition.revision,
            )
            if not chain or chain[-1] != stored:
                continue
            if valid_records_seen < requested_offset:
                valid_records_seen += 1
                continue
            verified.append(stored.transition)
        return verified

    def record_skill_candidate(
        self,
        candidate: SkillCandidateContract,
    ) -> StoredSkillCandidate:
        """Register one immutable inactive skill candidate through canonical memory."""

        for field_name, value in (
            ("skill_candidate_id", candidate.skill_candidate_id),
            ("skill_id", candidate.skill_id),
            ("skill_name", candidate.skill_name),
        ):
            if not value or len(value) > 200:
                raise ValueError(f"{field_name} must be present and bounded")
        if fullmatch(r"\d+\.\d+\.\d+", candidate.version) is None:
            raise ValueError("skill candidate version must use numeric semver")
        try:
            risk_level = RiskLevel(str(candidate.risk_level))
        except ValueError as exc:
            raise ValueError("skill candidate risk_level is invalid") from exc

        blockers = list(candidate.blockers)
        bounded_fields = {
            "inputs": self._bounded_skill_values(candidate.inputs, "inputs", blockers),
            "outputs": self._bounded_skill_values(candidate.outputs, "outputs", blockers),
            "allowed_tools": self._bounded_skill_values(
                candidate.allowed_tools,
                "allowed_tools",
                blockers,
            ),
            "bounded_instructions": self._bounded_skill_values(
                candidate.bounded_instructions,
                "bounded_instructions",
                blockers,
                max_items=12,
                item_limit=500,
            ),
            "evidence_refs": self._bounded_skill_values(
                candidate.evidence_refs,
                "evidence_refs",
                blockers,
                item_limit=240,
            ),
            "source_pattern_refs": self._bounded_skill_values(
                candidate.source_pattern_refs,
                "source_pattern_refs",
                blockers,
                item_limit=240,
            ),
            "failure_modes": self._bounded_skill_values(
                candidate.failure_modes,
                "failure_modes",
                blockers,
            ),
            "proposed_tests": self._bounded_skill_values(
                candidate.proposed_tests,
                "proposed_tests",
                blockers,
                item_limit=500,
            ),
        }
        for required_field in (
            "workflow_profile",
            "domain",
            "specialist_type",
            "rollback_plan_ref",
        ):
            value = str(getattr(candidate, required_field) or "").strip()
            if not value or len(value) > 240:
                blockers.append(f"{required_field}_required_and_bounded")
        for required_list in (
            "inputs",
            "outputs",
            "bounded_instructions",
            "evidence_refs",
            "source_pattern_refs",
            "failure_modes",
            "proposed_tests",
        ):
            if not bounded_fields[required_list]:
                blockers.append(f"{required_list}_required")
        if any(
            item.strip().lower() in {"*", "all", "any", "unrestricted"}
            for item in bounded_fields["allowed_tools"]
        ):
            blockers.append("allowed_tools_must_be_explicit")
        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            blockers.append("high_risk_candidate_requires_explicit_sandbox_review")
        if candidate.registry_status != "candidate_inactive":
            blockers.append("registry_status_forced_inactive")
        if candidate.review_status != "needs_review":
            blockers.append("human_review_required_before_status_change")
        if candidate.activation_status != "inactive":
            blockers.append("activation_status_forced_inactive")
        if not candidate.sandbox_required:
            blockers.append("sandbox_required")
        if candidate.automatic_activation_allowed:
            blockers.append("automatic_activation_not_allowed")
        if candidate.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if candidate.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if candidate.memory_write_mode != "through_core_only":
            blockers.append("memory_write_must_use_sovereign_core")

        safe_candidate = replace(
            candidate,
            risk_level=risk_level,
            **bounded_fields,
            registry_status="candidate_inactive",
            review_status="needs_review",
            activation_status="inactive",
            blockers=self._merge_unique_strings(blockers, []),
            sandbox_required=True,
            human_review_required=True,
            automatic_activation_allowed=False,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
            memory_write_mode="through_core_only",
        )
        existing = self.repository.fetch_skill_candidate(safe_candidate.skill_candidate_id)
        if existing is not None:
            if existing.candidate == safe_candidate:
                return existing
            raise ValueError("registered skill candidate versions are immutable")
        version_matches = self.repository.list_skill_candidates(
            skill_id=safe_candidate.skill_id,
            version=safe_candidate.version,
            limit=1,
        )
        if version_matches:
            raise ValueError("skill_id and version already belong to another candidate")

        record = StoredSkillCandidate(candidate=safe_candidate)
        self.repository.record_skill_candidate(record)
        return record

    def get_skill_candidate(
        self,
        skill_candidate_id: str,
    ) -> StoredSkillCandidate | None:
        """Return one inactive candidate without changing registry state."""

        return self.repository.fetch_skill_candidate(skill_candidate_id)

    def list_skill_candidates(
        self,
        *,
        skill_id: str | None = None,
        version: str | None = None,
        domain: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredSkillCandidate]:
        """Return bounded inactive candidates from the canonical registry."""

        return self.repository.list_skill_candidates(
            skill_id=skill_id,
            version=version,
            domain=domain,
            review_status=review_status,
            limit=max(1, min(limit, 100)),
        )

    def recover_for_input(self, contract: InputContract) -> MemoryRecoveryResult:
        """Recover contextual, episodic, and mission hints for the current session."""

        recovery_contract = MemoryRecoveryContract(
            memory_query_id=MemoryQueryId(f"mem-query-{uuid4().hex[:8]}"),
            recovery_type=RecoveryType.CONTEXTUAL,
            session_id=contract.session_id,
            requested_scopes=list(DEFAULT_MEMORY_SCOPES),
            priority_rules=default_priority_rules(),
            context_window=TimeWindow(label="current-session"),
            mission_id=contract.mission_id,
            user_id=contract.user_id,
            max_items=4,
            sensitivity_ceiling=RiskLevel.MODERATE,
        )
        (
            user_hints,
            session_context,
            mission_hints,
            plan_hints,
            continuity_context,
            user_scope_context,
        ) = self._compose_recovered_items(contract, recovery_contract.max_items or 4)
        organization_scope_guard = organization_scope_guard_payload()
        return MemoryRecoveryResult(
            recovery_contract=recovery_contract,
            user_hints=user_hints,
            session_context=session_context,
            mission_hints=mission_hints,
            plan_hints=plan_hints,
            organization_scope_status=organization_scope_guard["status"],
            organization_scope_reason=organization_scope_guard["reason"],
            organization_scope_reopen_signal=organization_scope_guard["reopen_signal"],
            continuity_context=continuity_context,
            user_scope_context=user_scope_context,
            semantic_memory_candidates=self._recover_semantic_memory_candidates(
                contract=contract,
                continuity_context=continuity_context,
            ),
        )

    def _recover_semantic_memory_candidates(
        self,
        *,
        contract: InputContract,
        continuity_context: MissionContinuityContextContract | None,
    ) -> list[SemanticMemoryCandidateContract]:
        candidates: list[SemanticMemoryCandidateContract] = []
        if contract.mission_id:
            active_state = self.repository.fetch_mission_state(str(contract.mission_id))
            active_score = 0.9
            if continuity_context is not None:
                active_score = continuity_context.active_priority_score or 0.65
            candidate = self._semantic_candidate_from_mission_state(
                state=active_state,
                source_kind="active_mission",
                generated_at=str(contract.timestamp),
                relevance_score=active_score,
                relevance_reason="active_mission_id_match",
            )
            if candidate is not None:
                candidates.append(candidate)

        if continuity_context is not None:
            for related in continuity_context.related_candidates[:2]:
                state = self.repository.fetch_mission_state(str(related.mission_id))
                candidate = self._semantic_candidate_from_mission_state(
                    state=state,
                    source_kind="related_mission",
                    generated_at=str(contract.timestamp),
                    relevance_score=related.priority_score,
                    relevance_reason=related.continuity_reason,
                )
                if candidate is not None and all(
                    existing.anchor_ref != candidate.anchor_ref for existing in candidates
                ):
                    candidates.append(candidate)
        return sorted(
            candidates,
            key=lambda candidate: (-candidate.relevance_score, candidate.anchor_ref),
        )[:4]

    @staticmethod
    def _semantic_candidate_from_mission_state(
        *,
        state: MissionStateContract | None,
        source_kind: str,
        generated_at: str,
        relevance_score: float,
        relevance_reason: str,
    ) -> SemanticMemoryCandidateContract | None:
        if state is None or not (state.semantic_brief or state.semantic_focus):
            return None
        summary = state.semantic_brief or (
            f"objective={state.mission_goal}; focus={','.join(state.semantic_focus[:4])}"
        )
        observed_at = str(state.updated_at)
        freshness = semantic_memory_freshness_status(observed_at, generated_at)
        digest = sha256(
            f"{state.mission_id}\x00{observed_at}\x00{summary}".encode("utf-8")
        ).hexdigest()[:16]
        lifecycle_status = (
            "retained"
            if freshness == "current"
            else "aging"
            if freshness == "aging"
            else "expired"
            if freshness == "stale"
            else "review_recommended"
        )
        return SemanticMemoryCandidateContract(
            anchor_ref=f"memory://mission/{state.mission_id}/semantic",
            source_kind=source_kind,
            summary=summary[:1000],
            evidence_refs=[
                f"mission-state://{state.mission_id}/semantic/{digest}",
                f"mission-state-updated://{state.mission_id}/{observed_at}",
            ],
            observed_at=observed_at,
            freshness_status=freshness,
            relevance_score=max(0.0, min(float(relevance_score), 1.0)),
            relevance_reason=relevance_reason[:500],
            domain_hints=list(dict.fromkeys(state.semantic_focus))[:8],
            lifecycle_status=lifecycle_status,
        )

    def record_turn(
        self,
        contract: InputContract,
        intent: str,
        response_text: str,
        *,
        deliberative_plan: DeliberativePlanContract | None = None,
        specialist_contributions: list[SpecialistContributionContract] | None = None,
        governance_decision: PermissionDecision | None = None,
        operation_dispatch: OperationDispatchContract | None = None,
        operation_result: OperationResultContract | None = None,
    ) -> MemoryRecordResult:
        """Persist a minimal episodic entry and refresh contextual continuity."""

        specialist_contributions = specialist_contributions or []
        accepted = governance_decision not in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }
        ecosystem_state = self._resolve_ecosystem_state(
            contract,
            operation_dispatch=operation_dispatch,
            operation_result=operation_result,
        )
        surface_state = self._resolve_surface_continuity_state(
            contract,
            operation_dispatch=operation_dispatch,
            operation_result=operation_result,
        )
        objective_state = self._resolve_project_objective_state(
            contract,
            operation_dispatch=operation_dispatch,
            operation_result=operation_result,
            ecosystem_state=ecosystem_state,
        )
        open_loops = self._extract_open_loops(deliberative_plan, specialist_contributions)
        decision_frame = self._decision_frame(deliberative_plan)
        dominant_goal = deliberative_plan.goal if deliberative_plan else contract.content
        record_contract = MemoryRecordContract(
            memory_record_id=MemoryRecordId(f"mem-record-{uuid4().hex[:8]}"),
            record_type="interaction_turn",
            source_service=self.name,
            payload={
                "request_content": contract.content,
                "intent": intent,
                "response_text": response_text,
                "dominant_goal": dominant_goal,
                "decision_frame": decision_frame,
                "governance_decision": governance_decision.value if governance_decision else None,
                "open_loops": open_loops,
                "plan_summary": deliberative_plan.plan_summary if deliberative_plan else None,
                "plan_steps": deliberative_plan.steps if deliberative_plan else [],
                "recommended_task_type": (
                    deliberative_plan.recommended_task_type if deliberative_plan else None
                ),
                "requires_human_validation": (
                    deliberative_plan.requires_human_validation if deliberative_plan else False
                ),
                "tensions_considered": (
                    deliberative_plan.tensions_considered if deliberative_plan else []
                ),
                "specialist_hints": (
                    deliberative_plan.specialist_hints if deliberative_plan else []
                ),
                "specialist_resolution_summary": (
                    deliberative_plan.specialist_resolution_summary if deliberative_plan else None
                ),
                "specialist_summary": (
                    " | ".join(
                        contribution.recommendation for contribution in specialist_contributions
                    )
                    if specialist_contributions
                    else None
                ),
                "specialist_types": [
                    contribution.specialist_type for contribution in specialist_contributions
                ],
                "ecosystem_state_status": (
                    ecosystem_state.ecosystem_state_status if ecosystem_state else None
                ),
                "active_work_items": (
                    list(ecosystem_state.active_work_items) if ecosystem_state else []
                ),
                "active_artifact_refs": (
                    list(ecosystem_state.active_artifact_refs) if ecosystem_state else []
                ),
                "open_checkpoint_refs": (
                    list(ecosystem_state.open_checkpoint_refs) if ecosystem_state else []
                ),
                "surface_presence": (
                    list(ecosystem_state.surface_presence) if ecosystem_state else []
                ),
                "ecosystem_state_summary": (
                    ecosystem_state.state_summary if ecosystem_state else None
                ),
                "linked_surface_ids": list(surface_state.linked_surface_ids),
                "active_surface_id": surface_state.active_surface_id,
                "last_surface_id": surface_state.last_surface_id,
                "surface_continuity_status": surface_state.surface_continuity_status,
                "surface_identity_conflict_flags": list(
                    surface_state.surface_identity_conflict_flags
                ),
                "project_ref": objective_state.project_ref,
                "objective_ref": objective_state.objective_ref,
                "work_item_refs": list(objective_state.work_item_refs),
                "checkpoint_refs": list(objective_state.checkpoint_refs),
                "artifact_refs": list(objective_state.artifact_refs),
                "objective_status": objective_state.objective_status,
                "next_action_ref": objective_state.next_action_ref,
            },
            timestamp=self.now(),
            session_id=contract.session_id,
            mission_id=contract.mission_id,
            user_id=contract.user_id,
            proposed_memory_class=MemoryClass.EPISODIC,
            sensitivity_hint=RiskLevel.LOW,
            promotion_candidate=False,
        )
        self.repository.record_turn(
            StoredTurn(
                session_id=str(contract.session_id),
                mission_id=str(contract.mission_id) if contract.mission_id else None,
                user_id=contract.user_id,
                request_content=contract.content,
                intent=intent,
                response_text=response_text,
                timestamp=record_contract.timestamp,
                plan_summary=deliberative_plan.plan_summary if deliberative_plan else None,
                plan_steps=list(deliberative_plan.steps) if deliberative_plan else [],
                recommended_task_type=(
                    deliberative_plan.recommended_task_type if deliberative_plan else None
                ),
            )
        )
        continuity_snapshot = self._build_session_continuity_snapshot(
            contract,
            deliberative_plan=deliberative_plan,
            governance_decision=governance_decision,
            ecosystem_state=ecosystem_state,
            surface_state=surface_state,
            objective_state=objective_state,
        )
        if continuity_snapshot is not None:
            self.repository.upsert_session_continuity(continuity_snapshot)
            self.repository.upsert_continuity_checkpoint(
                self._build_continuity_checkpoint(
                    contract,
                    deliberative_plan=deliberative_plan,
                    governance_decision=governance_decision,
                    continuity_snapshot=continuity_snapshot,
                    ecosystem_state=ecosystem_state,
                    surface_state=surface_state,
                    objective_state=objective_state,
                )
            )
        if contract.mission_id:
            mission_state, procedural_artifact = self._build_mission_state(
                contract,
                record_contract.memory_record_id,
                intent,
                deliberative_plan,
                open_loops=open_loops,
                decision_frame=decision_frame,
                governance_decision=governance_decision,
                ecosystem_state=ecosystem_state,
                surface_state=surface_state,
                objective_state=objective_state,
            )
            if mission_state is not None:
                self.repository.upsert_mission_state(mission_state)
        else:
            mission_state = None
            procedural_artifact = self._build_procedural_artifact(
                contract,
                deliberative_plan=deliberative_plan if accepted else None,
                previous_artifacts=[],
            )
        user_scope_context: UserScopeContextContract | None = None
        if contract.user_id:
            user_scope_snapshot = self._build_user_scope_snapshot(
                contract,
                intent=intent,
                deliberative_plan=deliberative_plan,
                governance_decision=governance_decision,
            )
            if user_scope_snapshot is not None:
                self.repository.upsert_user_scope_snapshot(user_scope_snapshot)
                user_scope_context = self._user_scope_contract_from_snapshot(user_scope_snapshot)
        organization_scope_guard = organization_scope_guard_payload()
        return MemoryRecordResult(
            record_contract=record_contract,
            organization_scope_status=organization_scope_guard["status"],
            organization_scope_reason=organization_scope_guard["reason"],
            organization_scope_reopen_signal=organization_scope_guard["reopen_signal"],
            user_scope_context=user_scope_context,
            procedural_artifact_status=(
                str(procedural_artifact.get("artifact_status"))
                if procedural_artifact is not None
                and procedural_artifact.get("artifact_status") is not None
                else None
            ),
            procedural_artifact_refs=(
                [str(procedural_artifact.get("artifact_ref"))]
                if procedural_artifact is not None
                and procedural_artifact.get("artifact_ref") is not None
                else []
            ),
            procedural_artifact_version=(
                int(procedural_artifact.get("version"))
                if procedural_artifact is not None
                and procedural_artifact.get("version") is not None
                else None
            ),
            procedural_artifact_summary=(
                str(procedural_artifact.get("summary"))
                if procedural_artifact is not None
                and procedural_artifact.get("summary") is not None
                else None
            ),
        )

    def get_mission_state(self, mission_id: str) -> MissionStateContract | None:
        """Expose the latest mission snapshot for validation and orchestration."""

        return self.repository.fetch_mission_state(mission_id)

    def list_mission_states(
        self,
        *,
        limit: int = 20,
        include_closed: bool = False,
    ) -> list[MissionStateContract]:
        """Expose recent canonical mission states without deriving new state."""

        return self.repository.list_mission_states(
            limit=max(1, min(limit, 200)),
            include_closed=include_closed,
        )

    def build_long_horizon_goal_strategy(
        self,
        mission_id: str,
    ) -> LongHorizonGoalStrategyContract | None:
        """Derive a read-only long-horizon strategy from canonical mission state."""

        mission_state = self.repository.fetch_mission_state(mission_id)
        if mission_state is None:
            return None

        milestone_refs = self._merge_unique_strings(
            list(mission_state.work_item_refs),
            list(mission_state.checkpoint_refs),
        )[:8]
        risk_refs = self._merge_unique_strings(
            [f"open_loop:{item}" for item in mission_state.open_loops],
            (
                [f"objective_status:{mission_state.objective_status}"]
                if mission_state.objective_status
                in {"blocked", "paused", "requires_operator_decision"}
                else []
            ),
        )[:6]
        memory_anchor_refs = self._merge_unique_strings(
            list(mission_state.related_memories),
            [f"semantic_focus:{item}" for item in mission_state.semantic_focus],
            ([f"project_ref:{mission_state.project_ref}"] if mission_state.project_ref else []),
            (
                [f"objective_ref:{mission_state.objective_ref}"]
                if mission_state.objective_ref
                else []
            ),
        )[:8]
        evidence_refs = self._merge_unique_strings(
            list(mission_state.artifact_refs),
            list(mission_state.active_artifact_refs),
            list(mission_state.checkpoint_refs),
            list(mission_state.open_checkpoint_refs),
        )[:8]
        generated_from_state_refs = self._merge_unique_strings(
            [f"mission:{mission_state.mission_id}"],
            ([f"objective:{mission_state.objective_ref}"] if mission_state.objective_ref else []),
            milestone_refs,
            evidence_refs,
        )[:10]
        strategy_status = self._long_horizon_strategy_status(
            mission_state=mission_state,
            milestone_refs=milestone_refs,
            memory_anchor_refs=memory_anchor_refs,
            evidence_refs=evidence_refs,
        )
        strategy_summary = self._long_horizon_strategy_summary(
            mission_state=mission_state,
            strategy_status=strategy_status,
            milestone_refs=milestone_refs,
            risk_refs=risk_refs,
        )
        return LongHorizonGoalStrategyContract(
            mission_id=MissionId(mission_id),
            strategy_status=strategy_status,
            strategy_summary=strategy_summary,
            milestone_refs=milestone_refs,
            risk_refs=risk_refs,
            memory_anchor_refs=memory_anchor_refs,
            next_action_ref=mission_state.next_action_ref,
            evidence_refs=evidence_refs,
            generated_from_state_refs=generated_from_state_refs,
        )

    def transition_objective_state(
        self,
        *,
        mission_id: str,
        objective_status: str,
        mission_status: MissionStatus,
        transition_ref: str,
        next_action_ref: str | None = None,
    ) -> MissionStateContract | None:
        """Persist a bounded operator transition over the canonical mission state."""

        current = self.repository.fetch_mission_state(mission_id)
        if current is None:
            return None

        checkpoint_refs = [
            *list(current.checkpoint_refs),
            transition_ref,
        ][-5:]
        checkpoints = [
            *list(current.checkpoints),
            f"objective_transition:{transition_ref}",
        ][-5:]
        updated = replace(
            current,
            mission_status=mission_status,
            checkpoints=checkpoints,
            checkpoint_refs=checkpoint_refs,
            objective_status=objective_status,
            next_action_ref=next_action_ref,
            active_work_items=(
                [] if mission_status == MissionStatus.COMPLETED else current.active_work_items
            ),
            open_checkpoint_refs=(
                [] if mission_status == MissionStatus.COMPLETED else current.open_checkpoint_refs
            ),
            updated_at=self.now(),
        )
        self.repository.upsert_mission_state(updated)
        return updated

    def resume_open_loop_state(
        self,
        *,
        mission_id: str,
        open_loop_ref: str,
        plan: OpenLoopResumePlanContract,
        expected_updated_at: str,
        checkpoint_ref: str,
    ) -> MissionStateContract | None:
        """Record an explicit resume without executing the selected next action."""

        current = self.repository.fetch_mission_state(mission_id)
        if current is None:
            return None
        if current.updated_at != expected_updated_at:
            raise ValueError("mission state changed after resume revalidation")
        if (
            current.mission_status != MissionStatus.ACTIVE
            or (current.objective_status or "active") != "active"
        ):
            raise ValueError("mission objective is not active for open loop resume")

        open_loop_states = list(current.open_loop_states)
        selected = next(
            (item for item in open_loop_states if item.open_loop_ref == open_loop_ref),
            None,
        )
        if selected is None:
            selected = next(
                (
                    item
                    for item in canonical_open_loop_states_from_mission(current)
                    if item.open_loop_ref == open_loop_ref
                ),
                None,
            )
            if selected is not None:
                open_loop_states.append(selected)
        if selected is None or selected.loop_status != "open":
            raise ValueError("open loop is missing or no longer eligible")
        if plan.open_loop_ref != open_loop_ref or str(plan.mission_id) != mission_id:
            raise ValueError("open loop resume plan identity mismatch")
        if plan.selected_work_item_ref:
            executable_refs = {
                item.work_item_ref
                for item in refresh_work_item_blocking_states(
                    canonical_work_items_from_mission(current)
                )
                if item.work_item_status == "active" and item.blocking_state == "ready"
            }
            if plan.selected_work_item_ref not in executable_refs:
                raise ValueError("selected work item is no longer executable")

        now = self.now()
        updated_loop = OpenLoopStateContract(
            open_loop_ref=selected.open_loop_ref,
            mission_id=current.mission_id,
            loop_summary=selected.loop_summary,
            loop_status="resumed",
            source_work_item_ref=plan.selected_work_item_ref,
            selected_at=now,
            resumed_at=now,
            next_action_ref=plan.next_action_ref,
            next_action_summary=plan.next_action_summary,
            evidence_refs=list(plan.evidence_refs),
            checkpoint_refs=[*selected.checkpoint_refs, checkpoint_ref][-20:],
        )
        open_loop_states = [
            updated_loop if item.open_loop_ref == open_loop_ref else item
            for item in open_loop_states
        ]
        updated = replace(
            current,
            open_loops=[item for item in current.open_loops if item != selected.loop_summary],
            open_loop_states=open_loop_states,
            next_action_ref=plan.next_action_ref,
            checkpoints=[*current.checkpoints, f"open_loop_resume:{checkpoint_ref}"][-5:],
            checkpoint_refs=[*current.checkpoint_refs, checkpoint_ref][-5:],
            updated_at=now,
        )
        self.repository.upsert_mission_state(updated)
        return updated

    def transition_work_item_state(
        self,
        *,
        mission_id: str,
        work_item_ref: str,
        work_item_status: str,
        transition_ref: str,
        next_action_ref: str | None = None,
        transition: str | None = None,
        dependency_refs: list[str] | None = None,
        priority_level: str | None = None,
        blocker_refs: list[str] | None = None,
    ) -> MissionStateContract | None:
        """Persist a bounded work item transition in the canonical mission state."""

        current = self.repository.fetch_mission_state(mission_id)
        if current is None:
            return None

        transition_name = transition or self._work_item_transition_from_ref(transition_ref)
        work_items = canonical_work_items_from_mission(current)
        existing = next(
            (item for item in work_items if item.work_item_ref == work_item_ref),
            None,
        )
        effective_dependency_refs = (
            list(dependency_refs)
            if dependency_refs is not None
            else list(existing.dependency_refs)
            if existing
            else []
        )
        effective_priority = priority_level or (existing.priority_level if existing else "p2")
        if effective_priority not in WORK_ITEM_PRIORITY_LEVELS:
            raise ValueError("invalid work item priority")
        graph_errors = validate_work_item_graph(
            work_items,
            work_item_ref=work_item_ref,
            dependency_refs=effective_dependency_refs,
        )
        if graph_errors:
            raise ValueError("invalid work item dependency graph: " + ",".join(graph_errors))
        effective_blocker_refs = (
            []
            if transition_name == "resume"
            else list(blocker_refs)
            if blocker_refs is not None
            else list(existing.blocker_refs)
            if existing
            else []
        )
        item_checkpoint_refs = [
            *(list(existing.checkpoint_refs) if existing else []),
            transition_ref,
        ][-20:]
        updated_item = WorkItemStateContract(
            work_item_ref=work_item_ref,
            work_item_status=work_item_status,
            mission_id=current.mission_id,
            transition=transition_name,
            next_action_ref=(
                next_action_ref
                if next_action_ref is not None
                else existing.next_action_ref
                if existing
                else None
            ),
            dependency_refs=effective_dependency_refs,
            priority_level=effective_priority,
            blocker_refs=effective_blocker_refs,
            checkpoint_refs=item_checkpoint_refs,
        )
        if existing is None:
            work_items.append(updated_item)
        else:
            work_items = [
                updated_item if item.work_item_ref == work_item_ref else item for item in work_items
            ]
        work_items = refresh_work_item_blocking_states(work_items)
        structured_refs = {item.work_item_ref for item in work_items}
        work_item_refs = self._merge_unique_strings(
            list(current.work_item_refs),
            [item.work_item_ref for item in work_items],
        )
        active_work_items = [
            item_ref for item_ref in current.active_work_items if item_ref not in structured_refs
        ] + [item.work_item_ref for item in work_items if item.work_item_status == "active"]
        active_work_items = self._merge_unique_strings(active_work_items)
        checkpoint_refs = [
            *list(current.checkpoint_refs),
            transition_ref,
        ][-5:]
        checkpoints = [
            *list(current.checkpoints),
            f"work_item_transition:{transition_ref}",
        ][-5:]
        updated = replace(
            current,
            checkpoints=checkpoints,
            checkpoint_refs=checkpoint_refs,
            work_item_refs=work_item_refs,
            work_items=work_items,
            active_work_items=active_work_items,
            next_action_ref=next_action_ref or current.next_action_ref,
            updated_at=self.now(),
        )
        self.repository.upsert_mission_state(updated)
        return updated

    @staticmethod
    def _work_item_transition_from_ref(transition_ref: str) -> str:
        parts = transition_ref.split(":", 2)
        return parts[1] if len(parts) > 1 else "update"

    @staticmethod
    def _artifact_physical_event(
        *,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
        phase: str,
        occurred_at: str,
        previous: ArtifactPhysicalSagaEventContract | None,
        mutation_receipt_fingerprint: str | None = None,
        rollback_receipt_fingerprint: str | None = None,
        physical_state_attestation_fingerprint: str | None = None,
    ) -> ArtifactPhysicalSagaEventContract:
        sequence = 1 if previous is None else previous.sequence + 1
        event = ArtifactPhysicalSagaEventContract(
            event_id=f"{plan.saga_id}:event:{sequence}:{phase}",
            saga_id=plan.saga_id,
            purpose=plan.purpose,
            phase=phase,
            sequence=sequence,
            plan_fingerprint=plan.plan_fingerprint,
            physical_operation_id=plan.physical_operation_id,
            occurred_at=occurred_at,
            previous_event_fingerprint=(None if previous is None else previous.event_fingerprint),
            mutation_receipt_fingerprint=mutation_receipt_fingerprint,
            rollback_receipt_fingerprint=rollback_receipt_fingerprint,
            physical_state_attestation_fingerprint=(physical_state_attestation_fingerprint),
            event_fingerprint="",
        )
        return seal_artifact_physical_saga_event(event)

    def _require_artifact_physical_plan_scope(
        self,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
    ) -> None:
        mission = self.repository.fetch_mission_state(str(plan.mission_id))
        if mission is None:
            raise KeyError("unknown mission for artifact physical saga")
        if str(plan.owner_mission_id) != str(mission.mission_id):
            raise ValueError("artifact_physical_owner_mission_mismatch")
        if plan.objective_ref != mission.objective_ref:
            raise ValueError("artifact_physical_objective_scope_mismatch")
        if mission.mission_status != MissionStatus.ACTIVE:
            raise ValueError("artifact_physical_mission_not_active")
        work_item = next(
            (item for item in mission.work_items if item.work_item_ref == plan.work_item_ref),
            None,
        )
        if (
            work_item is None
            or str(work_item.mission_id) != str(mission.mission_id)
            or work_item.work_item_status != "active"
            or work_item.blocking_state != "ready"
        ):
            raise ValueError("artifact_physical_work_item_scope_mismatch")

    def reserve_artifact_physical_apply(
        self,
        plan: ArtifactPhysicalApplyPlanContract,
    ) -> ArtifactPhysicalSagaStateContract:
        require_valid_artifact_physical_apply_plan(plan)
        existing = self.repository.fetch_artifact_physical_saga_plan(plan.saga_id)
        if existing is not None:
            if existing != plan:
                raise ValueError("artifact_physical_saga_reservation_collision")
            return self.get_artifact_physical_saga(plan.saga_id)
        self._require_artifact_physical_plan_scope(plan)
        if (
            plan.transition == "register"
            and self.repository.is_local_text_resource_physically_bound(plan.resource_ref)
        ):
            raise ValueError("artifact_physical_resource_already_bound")
        if self.repository.fetch_physical_artifact_version(artifact_ref=plan.artifact_ref):
            raise ValueError("artifact_physical_artifact_ref_already_bound")
        current = self.repository.fetch_artifact_physical_lineage(
            mission_id=str(plan.mission_id),
            lineage_root_ref=plan.lineage_root_ref,
        )
        if plan.transition == "register":
            if current is not None or plan.expected_lineage_revision != 0:
                raise ValueError("artifact_physical_apply_lineage_cas_failed")
            mission = self.repository.fetch_mission_state(str(plan.mission_id))
            assert mission is not None
            if any(item.artifact_ref == plan.artifact_ref for item in mission.artifact_states):
                raise ValueError("artifact_physical_register_ref_not_free")
        elif (
            current is None
            or current.revision != plan.expected_lineage_revision
            or current.active_artifact_ref != plan.supersedes_artifact_ref
        ):
            # Legacy logical heads are intentionally not bootstrapped implicitly.
            raise ValueError("artifact_physical_replace_requires_normalized_head")
        else:
            predecessor = self.repository.fetch_physical_artifact_version(
                artifact_ref=current.active_artifact_ref
            )
            latest = self.repository.fetch_latest_physical_artifact_version_for_lineage(
                mission_id=str(plan.mission_id),
                lineage_root_ref=plan.lineage_root_ref,
            )
            if (
                predecessor is None
                or latest is None
                or predecessor.artifact_ref != plan.supersedes_artifact_ref
                or latest.artifact_version + 1 != plan.artifact_version
                or str(predecessor.mission_id) != str(plan.mission_id)
                or predecessor.lineage_root_ref != plan.lineage_root_ref
                or predecessor.resource_ref != plan.resource_ref
                or predecessor.root_alias != plan.root_alias
                or predecessor.desired_content_sha256 != plan.before_content_sha256
                or predecessor.root_config_fingerprint != plan.root_config_fingerprint
                or predecessor.transaction_policy_version != plan.transaction_policy_version
                or predecessor.transaction_backend_version != plan.transaction_backend_version
                or predecessor.adapter_backend_version != plan.adapter_backend_version
            ):
                raise ValueError("artifact_physical_replace_predecessor_mismatch")
        genesis = self._artifact_physical_event(
            plan=plan,
            phase="reserved",
            occurred_at=plan.created_at,
            previous=None,
        )
        self.repository.reserve_artifact_physical_saga(plan, genesis)
        return self.get_artifact_physical_saga(plan.saga_id)

    def reserve_artifact_physical_rollback(
        self,
        plan: ArtifactPhysicalRollbackPlanContract,
    ) -> ArtifactPhysicalSagaStateContract:
        require_valid_artifact_physical_rollback_plan(plan)
        existing = self.repository.fetch_artifact_physical_saga_plan(plan.saga_id)
        if existing is not None:
            if existing != plan:
                raise ValueError("artifact_physical_saga_reservation_collision")
            return self.get_artifact_physical_saga(plan.saga_id)
        self._require_artifact_physical_plan_scope(plan)
        source_plan = self.get_artifact_physical_apply_plan(plan.source_apply_saga_id)
        source_state = self.get_artifact_physical_saga(plan.source_apply_saga_id)
        if (
            source_plan.artifact_ref != plan.active_artifact_ref
            or source_plan.artifact_version != plan.active_artifact_version
            or str(source_plan.owner_mission_id) != str(plan.owner_mission_id)
            or source_plan.objective_ref != plan.objective_ref
            or source_plan.work_item_ref != plan.work_item_ref
            or source_plan.physical_operation_id != plan.mutation_operation_id
            or source_plan.resource_ref != plan.resource_ref
            or source_plan.root_alias != plan.root_alias
            or str(source_plan.mission_id) != str(plan.mission_id)
            or source_plan.lineage_root_ref != plan.lineage_root_ref
        ):
            raise ValueError("artifact_physical_rollback_source_plan_mismatch")
        source_version = self.repository.fetch_physical_artifact_version(
            artifact_ref=plan.active_artifact_ref
        )
        if plan.rollback_mode == "canonical_rollback":
            if source_state.phase != "completed":
                raise ValueError("artifact_physical_rollback_source_not_completed")
            if source_version is None:
                raise ValueError("artifact_physical_rollback_source_missing")
            if plan.restored_artifact_ref is None:
                raise ValueError("artifact_physical_rollback_restored_version_required")
            restored_version = self.repository.fetch_physical_artifact_version(
                artifact_ref=plan.restored_artifact_ref
            )
            if (
                source_version.artifact_version != plan.active_artifact_version
                or str(source_version.mission_id) != str(plan.mission_id)
                or str(source_version.owner_mission_id) != str(plan.owner_mission_id)
                or source_version.objective_ref != plan.objective_ref
                or source_version.work_item_ref != plan.work_item_ref
                or source_version.lineage_root_ref != plan.lineage_root_ref
                or source_version.resource_ref != plan.resource_ref
                or source_version.root_alias != plan.root_alias
                or source_version.physical_operation_id != plan.mutation_operation_id
                or source_version.mutation_receipt_fingerprint != plan.mutation_receipt_fingerprint
                or source_version.desired_content_sha256 != plan.expected_current_sha256
                or source_version.before_content_sha256 != plan.restored_content_sha256
                or restored_version is None
                or restored_version.artifact_version != plan.restored_artifact_version
                or str(restored_version.mission_id) != str(plan.mission_id)
                or str(restored_version.owner_mission_id) != str(plan.owner_mission_id)
                or restored_version.lineage_root_ref != plan.lineage_root_ref
                or restored_version.resource_ref != plan.resource_ref
                or restored_version.root_alias != plan.root_alias
                or source_version.supersedes_artifact_ref != restored_version.artifact_ref
                or restored_version.desired_content_sha256 != plan.restored_content_sha256
            ):
                raise ValueError("artifact_physical_rollback_version_binding_mismatch")
        else:
            if (
                source_state.phase
                not in {"effect_dispatched", "physical_applied", "compensation_required"}
                or source_version is not None
                or source_plan.before_content_sha256 != plan.restored_content_sha256
                or source_plan.desired_content_sha256 != plan.expected_current_sha256
                or source_plan.supersedes_artifact_ref != plan.restored_artifact_ref
            ):
                raise ValueError("artifact_physical_compensation_source_mismatch")
            if plan.restored_artifact_ref is None:
                if (
                    source_plan.transition != "register"
                    or plan.restored_artifact_version is not None
                    or plan.expected_lineage_revision != 0
                ):
                    raise ValueError("artifact_physical_compensation_restore_mismatch")
            else:
                restored_version = self.repository.fetch_physical_artifact_version(
                    artifact_ref=plan.restored_artifact_ref
                )
                if (
                    source_plan.transition != "replace"
                    or restored_version is None
                    or plan.restored_artifact_version is None
                    or restored_version.artifact_version != plan.restored_artifact_version
                    or str(restored_version.mission_id) != str(plan.mission_id)
                    or str(restored_version.owner_mission_id) != str(plan.owner_mission_id)
                    or restored_version.objective_ref != plan.objective_ref
                    or restored_version.work_item_ref != plan.work_item_ref
                    or restored_version.lineage_root_ref != plan.lineage_root_ref
                    or restored_version.resource_ref != plan.resource_ref
                    or restored_version.root_alias != plan.root_alias
                    or restored_version.desired_content_sha256 != plan.restored_content_sha256
                    or source_plan.before_content_sha256 != restored_version.desired_content_sha256
                ):
                    raise ValueError("artifact_physical_compensation_restore_mismatch")
        current = self.repository.fetch_artifact_physical_lineage(
            mission_id=str(plan.mission_id),
            lineage_root_ref=plan.lineage_root_ref,
        )
        if plan.rollback_mode == "canonical_rollback":
            if (
                current is None
                or current.revision != plan.expected_lineage_revision
                or current.active_artifact_ref != plan.active_artifact_ref
            ):
                raise ValueError("artifact_physical_rollback_lineage_cas_failed")
        elif (
            (current is None) != (plan.expected_lineage_revision == 0)
            or current is not None
            and (
                current.revision != plan.expected_lineage_revision
                or current.active_artifact_ref != plan.restored_artifact_ref
            )
        ):
            raise ValueError("artifact_physical_compensation_lineage_cas_failed")
        genesis = self._artifact_physical_event(
            plan=plan,
            phase="rollback_reserved",
            occurred_at=plan.created_at,
            previous=None,
            mutation_receipt_fingerprint=plan.mutation_receipt_fingerprint,
        )
        self.repository.reserve_artifact_physical_saga(plan, genesis)
        return self.get_artifact_physical_saga(plan.saga_id)

    def get_artifact_physical_apply_plan(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalApplyPlanContract:
        plan = self.repository.fetch_artifact_physical_saga_plan(saga_id)
        if not isinstance(plan, ArtifactPhysicalApplyPlanContract):
            raise KeyError("unknown artifact physical apply saga")
        require_valid_artifact_physical_apply_plan(plan)
        return plan

    def get_artifact_physical_rollback_plan(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalRollbackPlanContract:
        plan = self.repository.fetch_artifact_physical_saga_plan(saga_id)
        if not isinstance(plan, ArtifactPhysicalRollbackPlanContract):
            raise KeyError("unknown artifact physical rollback saga")
        require_valid_artifact_physical_rollback_plan(plan)
        return plan

    def get_artifact_physical_saga(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalSagaStateContract:
        plan = self.repository.fetch_artifact_physical_saga_plan(saga_id)
        if plan is None:
            raise KeyError("unknown artifact physical saga")
        events = self.repository.list_artifact_physical_saga_events(saga_id)
        if not events:
            raise ValueError("artifact physical saga has no checkpoints")
        return saga_state_from_event(
            events[-1],
            plan=plan,
            previous_event=events[-2] if len(events) > 1 else None,
        )

    def _advance_artifact_physical_saga(
        self,
        *,
        saga_id: str,
        phase: str,
        occurred_at: str,
        purpose: str,
    ) -> ArtifactPhysicalSagaStateContract:
        plan = self.repository.fetch_artifact_physical_saga_plan(saga_id)
        if plan is None or plan.purpose != purpose:
            raise KeyError(f"unknown artifact physical {purpose} saga")
        allowed = (
            {"effect_dispatched", "failed", "reconciliation_required"}
            if purpose == "apply"
            else {"rollback_effect_dispatched", "failed", "reconciliation_required"}
        )
        if phase not in allowed:
            raise ValueError("physical and canonical checkpoints require atomic commit API")
        if phase in {"effect_dispatched", "rollback_effect_dispatched"}:
            self._require_artifact_physical_plan_scope(plan)
        events = self.repository.list_artifact_physical_saga_events(saga_id)
        previous = events[-1]
        event = self._artifact_physical_event(
            plan=plan,
            phase=phase,
            occurred_at=occurred_at,
            previous=previous,
            mutation_receipt_fingerprint=previous.mutation_receipt_fingerprint,
            rollback_receipt_fingerprint=previous.rollback_receipt_fingerprint,
            physical_state_attestation_fingerprint=(
                previous.physical_state_attestation_fingerprint
            ),
        )
        self.repository.append_artifact_physical_saga_event(event)
        return self.get_artifact_physical_saga(saga_id)

    def advance_artifact_physical_apply(
        self,
        saga_id: str,
        *,
        phase: str,
        occurred_at: str,
    ) -> ArtifactPhysicalSagaStateContract:
        return self._advance_artifact_physical_saga(
            saga_id=saga_id,
            phase=phase,
            occurred_at=occurred_at,
            purpose="apply",
        )

    def advance_artifact_physical_rollback(
        self,
        saga_id: str,
        *,
        phase: str,
        occurred_at: str,
    ) -> ArtifactPhysicalSagaStateContract:
        return self._advance_artifact_physical_saga(
            saga_id=saga_id,
            phase=phase,
            occurred_at=occurred_at,
            purpose="rollback",
        )

    def _require_verified_mutation(
        self,
        receipt: LocalTextMutationReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> None:
        require_valid_local_text_mutation_receipt(receipt)
        require_valid_local_text_physical_state_attestation(attestation)
        verifier = self._artifact_physical_mutation_verifier
        if verifier is None:
            raise ValueError("artifact_physical_mutation_verifier_required")
        try:
            verified = verifier(receipt, attestation) is True
        except (TypeError, ValueError, RuntimeError):
            verified = False
        if not verified:
            raise ValueError("artifact_physical_mutation_receipt_not_verified")

    def _require_verified_rollback(
        self,
        receipt: LocalTextRollbackReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> None:
        require_valid_local_text_rollback_receipt(receipt)
        require_valid_local_text_physical_state_attestation(attestation)
        verifier = self._artifact_physical_rollback_verifier
        if verifier is None:
            raise ValueError("artifact_physical_rollback_verifier_required")
        try:
            verified = verifier(receipt, attestation) is True
        except (TypeError, ValueError, RuntimeError):
            verified = False
        if not verified:
            raise ValueError("artifact_physical_rollback_receipt_not_verified")

    def commit_artifact_physical_apply(
        self,
        saga_id: str,
        *,
        receipt: LocalTextMutationReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        plan = self.get_artifact_physical_apply_plan(saga_id)
        self._require_verified_mutation(receipt, attestation)
        if (
            receipt.operation_id != plan.physical_operation_id
            or receipt.resource_ref != plan.resource_ref
            or receipt.preflight_fingerprint != plan.preflight_fingerprint
            or receipt.root_config_fingerprint != plan.root_config_fingerprint
            or receipt.before_content_sha256 != plan.before_content_sha256
            or receipt.desired_content_sha256 != plan.desired_content_sha256
            or receipt.mutation_status != "applied"
            or attestation.purpose != "mutation_current"
            or attestation.receipt_fingerprint != receipt.receipt_fingerprint
            or attestation.mutation_operation_id != receipt.operation_id
            or attestation.rollback_operation_id is not None
            or attestation.resource_ref != plan.resource_ref
            or attestation.root_alias != plan.root_alias
            or attestation.root_config_fingerprint != plan.root_config_fingerprint
            or attestation.physical_state != "applied"
            or attestation.observed_content_sha256 != plan.desired_content_sha256
            or attestation.journal_event_fingerprint != receipt.applied_event_fingerprint
            or attestation.transaction_policy_version != plan.transaction_policy_version
            or attestation.transaction_backend_version != plan.transaction_backend_version
        ):
            raise ValueError("artifact_physical_apply_physical_binding_mismatch")
        stored_commit = self.repository.fetch_artifact_physical_commit_receipt(saga_id)
        if stored_commit is not None:
            if (
                stored_commit.mutation_receipt_fingerprint != receipt.receipt_fingerprint
                or stored_commit.physical_state_attestation_fingerprint
                != attestation.attestation_fingerprint
            ):
                raise ValueError("artifact_physical_apply_idempotency_mismatch")
            return stored_commit
        events = self.repository.list_artifact_physical_saga_events(saga_id)
        if not events or events[-1].phase != "effect_dispatched":
            raise ValueError("artifact_physical_apply_not_ready_for_commit")
        physical_event = self._artifact_physical_event(
            plan=plan,
            phase="physical_applied",
            occurred_at=attestation.verified_at,
            previous=events[-1],
            mutation_receipt_fingerprint=receipt.receipt_fingerprint,
            physical_state_attestation_fingerprint=attestation.attestation_fingerprint,
        )
        canonical_event = self._artifact_physical_event(
            plan=plan,
            phase="canonical_committed",
            occurred_at=attestation.verified_at,
            previous=physical_event,
            mutation_receipt_fingerprint=receipt.receipt_fingerprint,
            physical_state_attestation_fingerprint=attestation.attestation_fingerprint,
        )
        version = seal_physical_artifact_version(
            PhysicalArtifactVersionContract(
                mission_id=plan.mission_id,
                artifact_ref=plan.artifact_ref,
                artifact_version=plan.artifact_version,
                owner_mission_id=plan.owner_mission_id,
                objective_ref=plan.objective_ref,
                work_item_ref=plan.work_item_ref,
                lineage_root_ref=plan.lineage_root_ref,
                supersedes_artifact_ref=plan.supersedes_artifact_ref,
                physical_operation_id=plan.physical_operation_id,
                mutation_receipt_fingerprint=receipt.receipt_fingerprint,
                resource_ref=plan.resource_ref,
                root_alias=plan.root_alias,
                preflight_fingerprint=plan.preflight_fingerprint,
                root_config_fingerprint=plan.root_config_fingerprint,
                preflight_policy_version=plan.preflight_policy_version,
                transaction_policy_version=plan.transaction_policy_version,
                transaction_backend_version=plan.transaction_backend_version,
                adapter_backend_version=plan.adapter_backend_version,
                before_content_sha256=plan.before_content_sha256,
                desired_content_sha256=plan.desired_content_sha256,
                rollback_plan_ref=plan.rollback_plan_ref,
                physical_state_attestation_fingerprint=(attestation.attestation_fingerprint),
                canonical_saga_id=plan.saga_id,
                canonicalized_at=attestation.verified_at,
                version_fingerprint="",
            )
        )
        lineage = seal_artifact_physical_lineage(
            ArtifactPhysicalLineageContract(
                mission_id=plan.mission_id,
                lineage_root_ref=plan.lineage_root_ref,
                revision=plan.expected_lineage_revision + 1,
                active_artifact_ref=plan.artifact_ref,
                last_saga_id=plan.saga_id,
                last_event_fingerprint=canonical_event.event_fingerprint,
                updated_at=attestation.verified_at,
                lineage_fingerprint="",
            )
        )
        outbox = seal_artifact_physical_outbox_item(
            ArtifactPhysicalOutboxItemContract(
                outbox_id=f"{plan.saga_id}:outbox:canonical",
                saga_id=plan.saga_id,
                purpose="apply",
                event_name="artifact_lifecycle_state_changed",
                mission_id=plan.mission_id,
                artifact_ref=plan.artifact_ref,
                lineage_root_ref=plan.lineage_root_ref,
                canonical_event_fingerprint=canonical_event.event_fingerprint,
                created_at=attestation.verified_at,
                outbox_fingerprint="",
            )
        )
        commit = seal_artifact_physical_canonical_commit_receipt(
            ArtifactPhysicalCanonicalCommitReceiptContract(
                commit_id=f"{plan.saga_id}:canonical-commit",
                purpose="apply",
                saga_id=plan.saga_id,
                plan_fingerprint=plan.plan_fingerprint,
                mission_id=plan.mission_id,
                artifact_ref=plan.artifact_ref,
                artifact_version=plan.artifact_version,
                lineage_root_ref=plan.lineage_root_ref,
                lineage_revision=lineage.revision,
                physical_operation_id=plan.physical_operation_id,
                resource_ref=plan.resource_ref,
                root_alias=plan.root_alias,
                mutation_receipt_fingerprint=receipt.receipt_fingerprint,
                rollback_receipt_fingerprint=None,
                physical_state_attestation_fingerprint=(attestation.attestation_fingerprint),
                canonical_event_fingerprint=canonical_event.event_fingerprint,
                committed_at=attestation.verified_at,
                commit_fingerprint="",
            )
        )
        self.repository.commit_artifact_physical_apply(
            physical_event=physical_event,
            canonical_event=canonical_event,
            version=version,
            lineage=lineage,
            attestation=attestation,
            outbox=outbox,
            commit_receipt=commit,
        )
        stored = self.repository.fetch_artifact_physical_commit_receipt(saga_id)
        if stored != commit:
            raise ValueError("artifact_physical_apply_commit_not_persisted_exactly")
        return stored

    def commit_artifact_physical_rollback(
        self,
        saga_id: str,
        *,
        receipt: LocalTextRollbackReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        plan = self.get_artifact_physical_rollback_plan(saga_id)
        self._require_verified_rollback(receipt, attestation)
        source = self.get_artifact_physical_apply_plan(plan.source_apply_saga_id)
        if (
            receipt.operation_id != plan.physical_operation_id
            or receipt.mutation_operation_id != plan.mutation_operation_id
            or receipt.mutation_receipt_fingerprint != plan.mutation_receipt_fingerprint
            or receipt.resource_ref != plan.resource_ref
            or receipt.restored_content_sha256 != plan.restored_content_sha256
            or attestation.purpose != "rollback_current"
            or attestation.receipt_fingerprint != receipt.rollback_receipt_fingerprint
            or attestation.mutation_operation_id != plan.mutation_operation_id
            or attestation.rollback_operation_id != plan.physical_operation_id
            or attestation.resource_ref != plan.resource_ref
            or attestation.root_alias != plan.root_alias
            or attestation.root_config_fingerprint != source.root_config_fingerprint
            or attestation.physical_state not in {"restored", "absent"}
            or attestation.observed_content_sha256 != plan.restored_content_sha256
            or attestation.journal_event_fingerprint != receipt.rolled_back_event_fingerprint
            or attestation.transaction_policy_version != source.transaction_policy_version
            or attestation.transaction_backend_version != source.transaction_backend_version
        ):
            raise ValueError("artifact_physical_rollback_physical_binding_mismatch")
        stored_commit = self.repository.fetch_artifact_physical_commit_receipt(saga_id)
        if stored_commit is not None:
            if (
                stored_commit.rollback_receipt_fingerprint != receipt.rollback_receipt_fingerprint
                or stored_commit.physical_state_attestation_fingerprint
                != attestation.attestation_fingerprint
            ):
                raise ValueError("artifact_physical_rollback_idempotency_mismatch")
            return stored_commit
        events = self.repository.list_artifact_physical_saga_events(saga_id)
        if not events or events[-1].phase != "rollback_effect_dispatched":
            raise ValueError("artifact_physical_rollback_not_ready_for_commit")
        physical_event = self._artifact_physical_event(
            plan=plan,
            phase="physically_rolled_back",
            occurred_at=attestation.verified_at,
            previous=events[-1],
            mutation_receipt_fingerprint=plan.mutation_receipt_fingerprint,
            rollback_receipt_fingerprint=receipt.rollback_receipt_fingerprint,
            physical_state_attestation_fingerprint=attestation.attestation_fingerprint,
        )
        terminal_phase = (
            "canonical_rolled_back"
            if plan.rollback_mode == "canonical_rollback"
            else "compensation_committed"
        )
        canonical_event = self._artifact_physical_event(
            plan=plan,
            phase=terminal_phase,
            occurred_at=attestation.verified_at,
            previous=physical_event,
            mutation_receipt_fingerprint=plan.mutation_receipt_fingerprint,
            rollback_receipt_fingerprint=receipt.rollback_receipt_fingerprint,
            physical_state_attestation_fingerprint=attestation.attestation_fingerprint,
        )
        lineage: ArtifactPhysicalLineageContract | None = None
        if plan.rollback_mode == "canonical_rollback":
            lineage = seal_artifact_physical_lineage(
                ArtifactPhysicalLineageContract(
                    mission_id=plan.mission_id,
                    lineage_root_ref=plan.lineage_root_ref,
                    revision=plan.expected_lineage_revision + 1,
                    active_artifact_ref=plan.restored_artifact_ref,
                    last_saga_id=plan.saga_id,
                    last_event_fingerprint=canonical_event.event_fingerprint,
                    updated_at=attestation.verified_at,
                    lineage_fingerprint="",
                )
            )
        artifact_ref = (
            plan.restored_artifact_ref if plan.rollback_mode == "canonical_rollback" else None
        )
        artifact_version = (
            plan.restored_artifact_version if plan.rollback_mode == "canonical_rollback" else None
        )
        outbox = seal_artifact_physical_outbox_item(
            ArtifactPhysicalOutboxItemContract(
                outbox_id=f"{plan.saga_id}:outbox:canonical",
                saga_id=plan.saga_id,
                purpose="rollback",
                event_name=(
                    "artifact_lifecycle_state_changed"
                    if plan.rollback_mode == "canonical_rollback"
                    else "artifact_physical_apply_compensated"
                ),
                mission_id=plan.mission_id,
                artifact_ref=(artifact_ref or plan.active_artifact_ref),
                lineage_root_ref=plan.lineage_root_ref,
                canonical_event_fingerprint=canonical_event.event_fingerprint,
                created_at=attestation.verified_at,
                outbox_fingerprint="",
            )
        )
        commit = seal_artifact_physical_canonical_commit_receipt(
            ArtifactPhysicalCanonicalCommitReceiptContract(
                commit_id=f"{plan.saga_id}:canonical-commit",
                purpose="rollback",
                saga_id=plan.saga_id,
                plan_fingerprint=plan.plan_fingerprint,
                mission_id=plan.mission_id,
                artifact_ref=artifact_ref,
                artifact_version=artifact_version,
                lineage_root_ref=plan.lineage_root_ref,
                lineage_revision=(
                    lineage.revision if lineage is not None else plan.expected_lineage_revision
                ),
                physical_operation_id=plan.physical_operation_id,
                resource_ref=plan.resource_ref,
                root_alias=plan.root_alias,
                mutation_receipt_fingerprint=plan.mutation_receipt_fingerprint,
                rollback_receipt_fingerprint=receipt.rollback_receipt_fingerprint,
                physical_state_attestation_fingerprint=(attestation.attestation_fingerprint),
                canonical_event_fingerprint=canonical_event.event_fingerprint,
                committed_at=attestation.verified_at,
                commit_fingerprint="",
            )
        )
        source_compensated_event = None
        if plan.rollback_mode == "precanonical_compensation":
            source_events = self.repository.list_artifact_physical_saga_events(
                plan.source_apply_saga_id
            )
            if not source_events:
                raise ValueError("artifact_physical_compensation_source_missing")
            source_compensated_event = self._artifact_physical_event(
                plan=source,
                phase="compensated",
                occurred_at=attestation.verified_at,
                previous=source_events[-1],
                mutation_receipt_fingerprint=plan.mutation_receipt_fingerprint,
                rollback_receipt_fingerprint=receipt.rollback_receipt_fingerprint,
                physical_state_attestation_fingerprint=(attestation.attestation_fingerprint),
            )
        self.repository.commit_artifact_physical_rollback(
            physical_event=physical_event,
            canonical_event=canonical_event,
            lineage=lineage,
            attestation=attestation,
            outbox=outbox,
            commit_receipt=commit,
            source_compensated_event=source_compensated_event,
        )
        stored = self.repository.fetch_artifact_physical_commit_receipt(saga_id)
        if stored != commit:
            raise ValueError("artifact_physical_rollback_commit_not_persisted_exactly")
        return stored

    def get_artifact_physical_version(
        self,
        artifact_ref: str,
    ) -> PhysicalArtifactVersionContract | None:
        return self.repository.fetch_physical_artifact_version(artifact_ref=artifact_ref)

    def get_artifact_physical_lineage(
        self,
        mission_id: str,
        lineage_root_ref: str,
    ) -> ArtifactPhysicalLineageContract | None:
        return self.repository.fetch_artifact_physical_lineage(
            mission_id=mission_id,
            lineage_root_ref=lineage_root_ref,
        )

    def verify_artifact_physical_canonical_commit_receipt(
        self,
        receipt: ArtifactPhysicalCanonicalCommitReceiptContract,
    ) -> bool:
        try:
            require_valid_artifact_physical_canonical_commit_receipt(receipt)
            stored = self.repository.fetch_artifact_physical_commit_receipt(receipt.saga_id)
            return stored == receipt
        except (KeyError, TypeError, ValueError, RuntimeError):
            return False

    def get_artifact_physical_canonical_commit_receipt(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract | None:
        return self.repository.fetch_artifact_physical_commit_receipt(saga_id)

    def get_artifact_physical_outbox_for_saga(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalOutboxItemContract | None:
        return self.repository.fetch_artifact_physical_outbox_for_saga(saga_id)

    def list_pending_artifact_physical_outbox(
        self,
        *,
        limit: int = 20,
    ) -> list[ArtifactPhysicalOutboxItemContract]:
        return self.repository.list_pending_artifact_physical_outbox(limit=limit)

    def mark_artifact_physical_outbox_published(
        self,
        outbox_id: str,
        *,
        publisher_ref: str,
        published_at: str,
    ) -> ArtifactPhysicalOutboxDeliveryContract:
        item = self.repository.fetch_artifact_physical_outbox(outbox_id)
        if item is None:
            raise KeyError("unknown artifact physical outbox item")
        existing = self.repository.fetch_artifact_physical_outbox_delivery(outbox_id)
        if existing is not None:
            if existing.publisher_ref != publisher_ref:
                raise ValueError("artifact_physical_outbox_delivery_collision")
            return existing
        plan = self.repository.fetch_artifact_physical_saga_plan(item.saga_id)
        if plan is None:
            raise ValueError("artifact physical outbox has no saga plan")
        events = self.repository.list_artifact_physical_saga_events(item.saga_id)
        if not events:
            raise ValueError("artifact physical outbox has no saga checkpoints")
        previous = events[-1]
        completion = self._artifact_physical_event(
            plan=plan,
            phase="completed",
            occurred_at=published_at,
            previous=previous,
            mutation_receipt_fingerprint=previous.mutation_receipt_fingerprint,
            rollback_receipt_fingerprint=previous.rollback_receipt_fingerprint,
            physical_state_attestation_fingerprint=(
                previous.physical_state_attestation_fingerprint
            ),
        )
        delivery = seal_artifact_physical_outbox_delivery(
            ArtifactPhysicalOutboxDeliveryContract(
                delivery_id=f"{outbox_id}:delivery",
                outbox_id=outbox_id,
                publisher_ref=publisher_ref,
                published_at=published_at,
                delivery_fingerprint="",
            )
        )
        self.repository.record_artifact_physical_outbox_delivery(
            delivery,
            completion,
        )
        stored = self.repository.fetch_artifact_physical_outbox_delivery(outbox_id)
        if stored != delivery:
            raise ValueError("artifact_physical_delivery_not_persisted_exactly")
        return stored

    def authorize_artifact_physical_effect(
        self,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
        *,
        resource_ref: str,
        mutation_receipt_fingerprint: str | None = None,
    ) -> bool:
        try:
            stored = self.repository.fetch_artifact_physical_saga_plan(plan.saga_id)
            if stored != plan or plan.resource_ref != resource_ref:
                return False
            state = self.get_artifact_physical_saga(plan.saga_id)
            expected_phase = (
                "effect_dispatched"
                if isinstance(plan, ArtifactPhysicalApplyPlanContract)
                else "rollback_effect_dispatched"
            )
            if state.phase != expected_phase:
                return False
            if isinstance(plan, ArtifactPhysicalRollbackPlanContract):
                if mutation_receipt_fingerprint != plan.mutation_receipt_fingerprint:
                    return False
            elif mutation_receipt_fingerprint is not None:
                return False
            current = self.repository.fetch_artifact_physical_lineage(
                mission_id=str(plan.mission_id),
                lineage_root_ref=plan.lineage_root_ref,
            )
            if plan.expected_lineage_revision == 0:
                return current is None
            if isinstance(plan, ArtifactPhysicalApplyPlanContract):
                expected_active = plan.supersedes_artifact_ref
            elif plan.rollback_mode == "canonical_rollback":
                expected_active = plan.active_artifact_ref
            else:
                expected_active = plan.restored_artifact_ref
            return (
                current is not None
                and current.revision == plan.expected_lineage_revision
                and current.active_artifact_ref == expected_active
            )
        except (KeyError, TypeError, ValueError, RuntimeError):
            return False

    def is_local_text_resource_physically_bound(self, resource_ref: str) -> bool:
        return self.repository.is_local_text_resource_physically_bound(resource_ref)

    def transition_artifact_lifecycle_state(
        self,
        *,
        mission_id: str,
        artifact_ref: str,
        artifact_status: str,
        transition_ref: str,
        transition: str | None = None,
        artifact_version: int | None = None,
        work_item_ref: str | None = None,
        replacement_artifact_ref: str | None = None,
        rollback_plan_ref: str | None = None,
    ) -> MissionStateContract | None:
        """Persist a governed artifact version transition in canonical mission state."""

        current = self.repository.fetch_mission_state(mission_id)
        if current is None:
            return None

        physical_refs = [artifact_ref]
        if replacement_artifact_ref is not None:
            physical_refs.append(replacement_artifact_ref)
        if any(
            self.repository.fetch_physical_artifact_version(artifact_ref=ref) is not None
            for ref in physical_refs
        ):
            raise ValueError("physical_artifact_lifecycle_requires_saga")

        transition_name = transition or self._artifact_transition_from_ref(transition_ref)
        expected_status = "archived" if transition_name == "archive" else "active"
        if artifact_status != expected_status:
            raise ValueError("artifact status does not match lifecycle transition")
        artifact_states = list(current.artifact_states)
        if not any(item.artifact_ref == artifact_ref for item in artifact_states):
            artifact_states.extend(
                item
                for item in canonical_artifact_states_from_mission(current)
                if item.artifact_ref == artifact_ref
            )
        existing = next(
            (item for item in artifact_states if item.artifact_ref == artifact_ref),
            None,
        )
        transition_error = validate_artifact_transition(
            current_status=existing.artifact_status if existing else None,
            requested_transition=transition_name,
        )
        if transition_error:
            raise ValueError(f"invalid artifact transition: {transition_error}")
        version_error = validate_artifact_version(
            requested_transition=transition_name,
            requested_version=artifact_version,
            current_version=existing.artifact_version if existing else None,
        )
        if version_error:
            raise ValueError(f"invalid artifact version: {version_error}")
        lineage_errors = validate_artifact_lineage(
            artifact_states,
            artifact_ref=artifact_ref,
            replacement_artifact_ref=(
                replacement_artifact_ref if transition_name == "replace" else None
            ),
        )
        if lineage_errors:
            raise ValueError("invalid artifact lineage: " + ",".join(lineage_errors))

        canonical_work_item_refs = {
            item.work_item_ref for item in canonical_work_items_from_mission(current)
        }
        effective_work_item_ref = work_item_ref or (existing.work_item_ref if existing else None)
        if not effective_work_item_ref or effective_work_item_ref not in canonical_work_item_refs:
            raise ValueError("artifact source work item must belong to the mission")
        if transition_name == "replace" and (not replacement_artifact_ref or not rollback_plan_ref):
            raise ValueError("artifact replacement requires replacement and rollback refs")
        if transition_name == "rollback" and (
            existing is None or not existing.replacement_artifact_ref or not rollback_plan_ref
        ):
            raise ValueError("artifact rollback requires canonical successor and rollback ref")

        now = self.now()
        checkpoint_refs = [
            *(list(existing.checkpoint_refs) if existing else []),
            transition_ref,
        ][-20:]
        if transition_name == "register":
            artifact_states.append(
                ArtifactLifecycleStateContract(
                    artifact_ref=artifact_ref,
                    artifact_status="active",
                    mission_id=current.mission_id,
                    transition=transition_name,
                    artifact_version=artifact_version,
                    owner_mission_id=current.mission_id,
                    objective_ref=current.objective_ref,
                    work_item_ref=effective_work_item_ref,
                    lineage_root_ref=artifact_ref,
                    rollback_plan_ref=rollback_plan_ref,
                    created_at=now,
                    updated_at=now,
                    checkpoint_refs=checkpoint_refs,
                )
            )
        elif transition_name == "replace":
            assert existing is not None and replacement_artifact_ref is not None
            updated_existing = replace(
                existing,
                artifact_status="superseded",
                transition=transition_name,
                replacement_artifact_ref=replacement_artifact_ref,
                updated_at=now,
                checkpoint_refs=checkpoint_refs,
            )
            replacement_state = ArtifactLifecycleStateContract(
                artifact_ref=replacement_artifact_ref,
                artifact_status="active",
                mission_id=current.mission_id,
                transition=transition_name,
                artifact_version=artifact_version,
                owner_mission_id=existing.owner_mission_id or current.mission_id,
                objective_ref=existing.objective_ref or current.objective_ref,
                work_item_ref=effective_work_item_ref,
                lineage_root_ref=existing.lineage_root_ref or existing.artifact_ref,
                supersedes_artifact_ref=existing.artifact_ref,
                rollback_plan_ref=rollback_plan_ref,
                created_at=now,
                updated_at=now,
                checkpoint_refs=[transition_ref],
            )
            artifact_states = [
                updated_existing if item.artifact_ref == artifact_ref else item
                for item in artifact_states
            ]
            artifact_states.append(replacement_state)
        elif transition_name == "rollback":
            assert existing is not None and existing.replacement_artifact_ref is not None
            successor = next(
                (
                    item
                    for item in artifact_states
                    if item.artifact_ref == existing.replacement_artifact_ref
                ),
                None,
            )
            if successor is None or successor.artifact_status != "active":
                raise ValueError("artifact rollback successor must be active")
            artifact_states = [
                replace(
                    item,
                    artifact_status="active",
                    transition=transition_name,
                    updated_at=now,
                    checkpoint_refs=checkpoint_refs,
                )
                if item.artifact_ref == artifact_ref
                else replace(
                    item,
                    artifact_status="rolled_back",
                    transition=transition_name,
                    updated_at=now,
                    checkpoint_refs=[*item.checkpoint_refs, transition_ref][-20:],
                )
                if item.artifact_ref == successor.artifact_ref
                else item
                for item in artifact_states
            ]
        else:
            assert existing is not None
            artifact_states = [
                replace(
                    item,
                    artifact_status=artifact_status,
                    transition=transition_name,
                    updated_at=now,
                    checkpoint_refs=checkpoint_refs,
                )
                if item.artifact_ref == artifact_ref
                else item
                for item in artifact_states
            ]

        artifact_refs = self._merge_unique_strings(
            list(current.artifact_refs),
            [item.artifact_ref for item in artifact_states],
        )
        structured_refs = {item.artifact_ref for item in artifact_states}
        active_artifact_refs = [
            item for item in current.active_artifact_refs if item not in structured_refs
        ] + [item.artifact_ref for item in artifact_states if item.artifact_status == "active"]
        active_artifact_refs = self._merge_unique_strings(active_artifact_refs)
        mission_checkpoint_refs = [
            *list(current.checkpoint_refs),
            transition_ref,
        ][-5:]
        checkpoints = [
            *list(current.checkpoints),
            f"artifact_lifecycle_transition:{transition_ref}",
        ][-5:]
        updated = replace(
            current,
            checkpoints=checkpoints,
            checkpoint_refs=mission_checkpoint_refs,
            artifact_refs=artifact_refs,
            artifact_states=artifact_states,
            active_artifact_refs=active_artifact_refs,
            updated_at=now,
        )
        self.repository.upsert_mission_state(updated)
        return updated

    @staticmethod
    def _artifact_transition_from_ref(transition_ref: str) -> str:
        parts = transition_ref.split(":", 2)
        return parts[1] if len(parts) > 1 else "register"

    def get_session_continuity_checkpoint(
        self,
        session_id: str,
    ) -> ContinuityCheckpointContract | None:
        """Expose the latest recoverable continuity checkpoint for a session."""

        checkpoint = self.repository.fetch_continuity_checkpoint(session_id)
        if checkpoint is None:
            return None
        return continuity_checkpoint_to_contract(checkpoint)

    def get_session_continuity_replay(
        self,
        session_id: str,
    ) -> ContinuityReplayContract | None:
        """Build the latest replay-ready continuity state for a session."""

        checkpoint = self.repository.fetch_continuity_checkpoint(session_id)
        if checkpoint is None:
            return None
        continuity_snapshot = self.repository.fetch_session_continuity(session_id)
        mission_id = checkpoint.mission_id or (
            continuity_snapshot.anchor_mission_id if continuity_snapshot else None
        )
        mission_state = self.repository.fetch_mission_state(mission_id) if mission_id else None
        return self._build_continuity_replay(
            checkpoint=checkpoint,
            continuity_snapshot=continuity_snapshot,
            mission_state=mission_state,
        )

    def get_session_continuity_pause(
        self,
        session_id: str,
    ) -> ContinuityPauseContract | None:
        """Expose the active governed pause for a session, when one exists."""

        replay = self.get_session_continuity_replay(session_id)
        if replay is None or not replay.requires_manual_resume:
            return None
        resolution = self.repository.fetch_continuity_pause_resolution(session_id)
        return self._build_continuity_pause(
            replay=replay,
            resolution=resolution,
        )

    def resolve_session_continuity_pause(
        self,
        session_id: str,
        *,
        approved: bool,
        resolved_by: str,
        resolution_note: str,
        checkpoint_id: str | None = None,
    ) -> ContinuityPauseContract | None:
        """Resolve a governed continuity pause and persist the manual decision."""

        checkpoint = self.repository.fetch_continuity_checkpoint(session_id)
        if checkpoint is None:
            return None
        if checkpoint_id is not None and checkpoint.checkpoint_id != checkpoint_id:
            return None
        resolution = StoredContinuityPauseResolution(
            session_id=session_id,
            checkpoint_id=checkpoint.checkpoint_id,
            resolution_status="approved" if approved else "rejected",
            resolved_by=resolved_by,
            resolution_note=resolution_note,
            resolved_at=self.now(),
        )
        self.repository.upsert_continuity_pause_resolution(resolution)
        updated_checkpoint = StoredContinuityCheckpoint(
            checkpoint_id=checkpoint.checkpoint_id,
            session_id=checkpoint.session_id,
            continuity_action=checkpoint.continuity_action,
            checkpoint_status="ready" if approved else "closed",
            checkpoint_summary=checkpoint.checkpoint_summary,
            updated_at=self.now(),
            mission_id=checkpoint.mission_id,
            continuity_source=checkpoint.continuity_source,
            target_mission_id=checkpoint.target_mission_id,
            target_goal=checkpoint.target_goal,
            origin_request_id=checkpoint.origin_request_id,
            replay_summary=self._append_pause_resolution_summary(
                checkpoint.replay_summary,
                resolution,
            ),
            ecosystem_state_status=checkpoint.ecosystem_state_status,
            active_work_items=list(checkpoint.active_work_items),
            active_artifact_refs=list(checkpoint.active_artifact_refs),
            open_checkpoint_refs=list(checkpoint.open_checkpoint_refs),
            surface_presence=list(checkpoint.surface_presence),
            ecosystem_state_summary=checkpoint.ecosystem_state_summary,
            project_ref=checkpoint.project_ref,
            objective_ref=checkpoint.objective_ref,
            work_item_refs=list(checkpoint.work_item_refs),
            checkpoint_refs=list(checkpoint.checkpoint_refs),
            artifact_refs=list(checkpoint.artifact_refs),
            objective_status=checkpoint.objective_status,
            next_action_ref=checkpoint.next_action_ref,
            linked_surface_ids=list(checkpoint.linked_surface_ids),
            active_surface_id=checkpoint.active_surface_id,
            last_surface_id=checkpoint.last_surface_id,
            surface_continuity_status=checkpoint.surface_continuity_status,
            surface_identity_conflict_flags=list(checkpoint.surface_identity_conflict_flags),
        )
        self.repository.upsert_continuity_checkpoint(updated_checkpoint)
        replay = self.get_session_continuity_replay(session_id)
        if replay is None:
            return None
        return self._build_continuity_pause(replay=replay, resolution=resolution)

    def prepare_specialist_shared_memory(
        self,
        *,
        session_id: str,
        specialist_hints: list[str],
        active_domains: list[str] | None = None,
        mission_id: str | None = None,
        continuity_context: MissionContinuityContextContract | None = None,
        user_id: str | None = None,
    ) -> dict[str, SpecialistSharedMemoryContextContract]:
        """Build and persist the current core-mediated shared memory for specialists."""

        if not specialist_hints:
            return {}
        mission_state = self.repository.fetch_mission_state(mission_id) if mission_id else None
        continuity_snapshot = self.repository.fetch_session_continuity(session_id)
        related_states = self._resolve_related_states(
            session_id=session_id,
            mission_id=mission_id,
            continuity_context=continuity_context,
        )
        continuity_mode = (
            continuity_snapshot.continuity_mode
            if continuity_snapshot
            else (continuity_context.recommended_action or "continuar")
            if continuity_context
            else "continuar"
        )
        normalized_hints = normalize_specialist_types(specialist_hints)
        contexts: dict[str, SpecialistSharedMemoryContextContract] = {}
        for specialist_hint in normalized_hints:
            previous_context = (
                self.repository.fetch_latest_specialist_shared_memory_for_user(
                    user_id=user_id,
                    specialist_type=specialist_hint,
                    exclude_session_id=session_id,
                )
                if user_id
                else None
            )
            context = self._build_specialist_shared_memory_context(
                specialist_type=specialist_hint,
                continuity_mode=continuity_mode,
                mission_state=mission_state,
                related_states=related_states,
                active_domains=active_domains or [],
                user_id=user_id,
                previous_context=previous_context,
            )
            contexts[specialist_hint] = context
            self.repository.upsert_specialist_shared_memory(
                StoredSpecialistSharedMemory(
                    session_id=session_id,
                    specialist_type=context.specialist_type,
                    sharing_mode=context.sharing_mode,
                    continuity_mode=context.continuity_mode,
                    shared_memory_brief=context.shared_memory_brief,
                    write_policy=context.write_policy,
                    user_id=user_id,
                    source_mission_id=str(context.source_mission_id)
                    if context.source_mission_id
                    else None,
                    source_mission_goal=context.source_mission_goal,
                    consumer_mode=context.consumer_mode,
                    mission_context_brief=context.mission_context_brief,
                    domain_context_brief=context.domain_context_brief,
                    continuity_context_brief=context.continuity_context_brief,
                    consumer_profile=context.consumer_profile,
                    consumer_objective=context.consumer_objective,
                    expected_deliverables=list(context.expected_deliverables),
                    telemetry_focus=list(context.telemetry_focus),
                    related_mission_ids=[str(item) for item in context.related_mission_ids],
                    memory_refs=list(context.memory_refs),
                    memory_class_policies=dict(context.memory_class_policies),
                    consumed_memory_classes=list(context.consumed_memory_classes),
                    memory_write_policies=dict(context.memory_write_policies),
                    semantic_focus=list(context.semantic_focus),
                    open_loops=list(context.open_loops),
                    last_recommendation=context.last_recommendation,
                    semantic_memory_lifecycle=context.semantic_memory_lifecycle,
                    procedural_memory_lifecycle=context.procedural_memory_lifecycle,
                    memory_lifecycle_status=context.memory_lifecycle_status,
                    memory_review_status=context.memory_review_status,
                    procedural_artifact_status=context.procedural_artifact_status,
                    procedural_artifact_refs=list(context.procedural_artifact_refs),
                    procedural_artifact_version=context.procedural_artifact_version,
                    procedural_artifact_summary=context.procedural_artifact_summary,
                    domain_mission_link_reason=context.domain_mission_link_reason,
                    recurrent_context_status=context.recurrent_context_status,
                    recurrent_interaction_count=context.recurrent_interaction_count,
                    recurrent_context_brief=context.recurrent_context_brief,
                    recurrent_domain_focus=list(context.recurrent_domain_focus),
                    recurrent_memory_refs=list(context.recurrent_memory_refs),
                    recurrent_continuity_modes=list(context.recurrent_continuity_modes),
                    updated_at=self.now(),
                )
            )
        return contexts

    def get_specialist_shared_memory(
        self,
        *,
        session_id: str,
        specialist_type: str,
    ) -> SpecialistSharedMemoryContextContract | None:
        """Expose persisted specialist-facing shared memory for validation and handoff."""

        canonical = canonical_specialist_type(specialist_type)
        context = self.repository.fetch_specialist_shared_memory(
            session_id=session_id,
            specialist_type=canonical,
        )
        if context is None:
            legacy = legacy_specialist_type(canonical)
            if legacy != canonical:
                context = self.repository.fetch_specialist_shared_memory(
                    session_id=session_id,
                    specialist_type=legacy,
                )
        if context is not None:
            context.specialist_type = canonical
        return context

    def _resolve_ecosystem_state(
        self,
        contract: InputContract,
        *,
        operation_dispatch: OperationDispatchContract | None,
        operation_result: OperationResultContract | None,
    ) -> EcosystemOperationalStateContract | None:
        if operation_dispatch is None and operation_result is None:
            return None
        active_work_items = self._merge_unique_strings(
            operation_result.active_work_items if operation_result else [],
            operation_dispatch.active_work_items if operation_dispatch else [],
        )
        active_artifact_refs = self._merge_unique_strings(
            operation_result.active_artifact_refs if operation_result else [],
            operation_dispatch.active_artifact_refs if operation_dispatch else [],
        )
        open_checkpoint_refs = self._merge_unique_strings(
            operation_result.open_checkpoint_refs if operation_result else [],
            operation_dispatch.open_checkpoint_refs if operation_dispatch else [],
        )
        surface_presence = self._merge_unique_strings(
            operation_result.surface_presence if operation_result else [],
            operation_dispatch.surface_presence if operation_dispatch else [],
        )
        if not surface_presence:
            surface_presence = [
                f"surface:{contract.channel.value}",
                f"session:{contract.session_id}",
            ]
            if contract.mission_id:
                surface_presence.append(f"mission:{contract.mission_id}")
        policy = ecosystem_continuity_policy(
            ecosystem_state_status=(
                operation_result.ecosystem_state_status
                if operation_result and operation_result.ecosystem_state_status is not None
                else operation_dispatch.ecosystem_state_status
                if operation_dispatch
                else None
            ),
            active_work_items=active_work_items,
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=surface_presence,
        )
        if not policy.should_persist:
            return None
        summary = (
            operation_result.ecosystem_state_summary
            if operation_result and operation_result.ecosystem_state_summary is not None
            else operation_dispatch.ecosystem_state_summary
            if operation_dispatch and operation_dispatch.ecosystem_state_summary is not None
            else self._ecosystem_state_summary(
                active_work_items=active_work_items,
                active_artifact_refs=active_artifact_refs,
                open_checkpoint_refs=open_checkpoint_refs,
                surface_presence=surface_presence,
            )
        )
        return EcosystemOperationalStateContract(
            ecosystem_state_status=policy.ecosystem_state_status,
            active_work_items=active_work_items,
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=surface_presence,
            state_summary=summary,
        )

    def _resolve_surface_continuity_state(
        self,
        contract: InputContract,
        *,
        operation_dispatch: OperationDispatchContract | None,
        operation_result: OperationResultContract | None,
    ) -> SurfaceContinuityState:
        active_surface_id = self._first_text(
            getattr(operation_result, "surface_id", None),
            getattr(operation_dispatch, "surface_id", None),
            contract.surface_id,
            f"surface:{contract.channel.value}",
        )
        linked_surface_ids = self._merge_unique_strings(
            [active_surface_id] if active_surface_id else [],
            [getattr(operation_dispatch, "surface_id", None)],
            [getattr(operation_result, "surface_id", None)],
        )
        surface_continuity_status = self._first_text(
            getattr(operation_result, "surface_continuity_status", None),
            getattr(operation_dispatch, "surface_continuity_status", None),
            contract.surface_continuity_status,
        )
        canonical_refs = self._merge_unique_strings(
            [contract.canonical_user_ref],
            [getattr(operation_dispatch, "canonical_user_ref", None)],
            [getattr(operation_result, "canonical_user_ref", None)],
        )
        operator_refs = self._merge_unique_strings(
            [contract.operator_identity_ref],
            [getattr(operation_dispatch, "operator_identity_ref", None)],
            [getattr(operation_result, "operator_identity_ref", None)],
        )
        conflict_flags: list[str] = []
        if not active_surface_id:
            conflict_flags.append("surface_id_missing")
        if len(canonical_refs) > 1:
            conflict_flags.append("canonical_user_ref_mismatch")
        if len(operator_refs) > 1:
            conflict_flags.append("operator_identity_ref_mismatch")
        if surface_continuity_status == "surface_identity_conflict":
            conflict_flags.append("surface_identity_conflict_status")
        if conflict_flags and surface_continuity_status != "surface_identity_conflict":
            surface_continuity_status = "surface_identity_conflict"
        return SurfaceContinuityState(
            linked_surface_ids=linked_surface_ids,
            active_surface_id=active_surface_id,
            last_surface_id=active_surface_id,
            surface_continuity_status=surface_continuity_status or "single_surface",
            surface_identity_conflict_flags=conflict_flags,
        )

    def _resolve_project_objective_state(
        self,
        contract: InputContract,
        *,
        operation_dispatch: OperationDispatchContract | None,
        operation_result: OperationResultContract | None,
        ecosystem_state: EcosystemOperationalStateContract | None,
    ) -> ProjectObjectiveContinuityState:
        mission_ref = str(contract.mission_id) if contract.mission_id else None
        project_ref = self._first_text(
            getattr(operation_result, "project_ref", None),
            getattr(operation_dispatch, "project_ref", None),
            contract.project_ref,
            f"project://{mission_ref}" if mission_ref else None,
        )
        objective_ref = self._first_text(
            getattr(operation_result, "objective_ref", None),
            getattr(operation_dispatch, "objective_ref", None),
            contract.objective_ref,
            f"objective://{mission_ref}" if mission_ref else None,
        )
        work_item_refs = self._merge_unique_strings(
            getattr(operation_result, "work_item_refs", []),
            getattr(operation_dispatch, "work_item_refs", []),
            contract.work_item_refs,
            ecosystem_state.active_work_items if ecosystem_state else [],
        )
        checkpoint_refs = self._merge_unique_strings(
            getattr(operation_result, "checkpoint_refs", []),
            getattr(operation_dispatch, "checkpoint_refs", []),
            contract.checkpoint_refs,
            ecosystem_state.open_checkpoint_refs if ecosystem_state else [],
        )
        artifact_refs = self._merge_unique_strings(
            getattr(operation_result, "artifact_refs", []),
            getattr(operation_dispatch, "artifact_refs", []),
            contract.artifact_refs,
            ecosystem_state.active_artifact_refs if ecosystem_state else [],
        )
        objective_status = self._first_text(
            getattr(operation_result, "objective_status", None),
            "completed"
            if operation_result is not None and operation_result.status == OperationStatus.COMPLETED
            else None,
            getattr(operation_dispatch, "objective_status", None),
            contract.objective_status,
        )
        next_action_ref = self._first_text(
            getattr(operation_result, "next_action_ref", None),
            getattr(operation_dispatch, "next_action_ref", None),
            contract.next_action_ref,
            self._next_action_from_checkpoint_refs(checkpoint_refs),
        )
        return ProjectObjectiveContinuityState(
            project_ref=project_ref,
            objective_ref=objective_ref,
            work_item_refs=work_item_refs,
            checkpoint_refs=checkpoint_refs,
            artifact_refs=artifact_refs,
            objective_status=objective_status,
            next_action_ref=next_action_ref,
        )

    @staticmethod
    def _next_action_from_checkpoint_refs(checkpoint_refs: list[str]) -> str | None:
        if not checkpoint_refs:
            return None
        first = checkpoint_refs[0]
        parts = first.split(":")
        if len(parts) >= 2 and parts[0] == "workflow_checkpoint":
            return f"next_action:{parts[1]}"
        return f"next_action:{first}"

    @staticmethod
    def _first_text(*items: object | None) -> str | None:
        for item in items:
            if item is None:
                continue
            value = str(item).strip()
            if value:
                return value
        return None

    def _compose_recovered_items(
        self,
        contract: InputContract,
        limit: int,
    ) -> tuple[
        list[str],
        list[str],
        list[str],
        list[str],
        MissionContinuityContextContract | None,
        UserScopeContextContract | None,
    ]:
        user_hints: list[str] = []
        session_context: list[str] = []
        continuity_hints: list[str] = []
        mission_hints: list[str] = []
        plan_hints: list[str] = []
        continuity_context: MissionContinuityContextContract | None = None
        user_scope_context: UserScopeContextContract | None = None
        mission_state: MissionStateContract | None = None
        latest_artifact: dict[str, object] | None = None
        if contract.user_id:
            user_scope_context = self.repository.fetch_user_scope_snapshot(contract.user_id)
            if user_scope_context is None:
                user_scope_context = self._tracked_only_user_scope_context(contract.user_id)
            user_hints.append(f"user_scope_status={user_scope_context.context_status}")
            user_hints.append(
                f"user_scope_interaction_count={user_scope_context.interaction_count}"
            )
            if user_scope_context.user_context_brief:
                user_hints.append(f"user_context_brief={user_scope_context.user_context_brief}")
            if user_scope_context.recent_intents:
                user_hints.append(
                    f"user_recent_intents={','.join(user_scope_context.recent_intents[:3])}"
                )
            if user_scope_context.recent_domain_focus:
                user_hints.append(
                    f"user_domain_focus={','.join(user_scope_context.recent_domain_focus[:3])}"
                )
            if user_scope_context.active_mission_ids:
                user_hints.append(
                    f"user_active_missions={','.join(user_scope_context.active_mission_ids[:3])}"
                )
            if user_scope_context.last_recommended_task_type:
                user_hints.append(
                    "user_last_recommended_task_type="
                    f"{user_scope_context.last_recommended_task_type}"
                )
            if user_scope_context.continuity_preference:
                user_hints.append(
                    f"user_continuity_preference={user_scope_context.continuity_preference}"
                )
        summary = self.repository.fetch_context_summary(str(contract.session_id))
        if summary:
            session_context.append(f"context_summary={summary}")
        turns = self.repository.fetch_recent_turns(str(contract.session_id), max(limit, 3))
        for turn in turns:
            session_context.append(
                "user="
                f"{turn.request_content} | intent={turn.intent} | "
                f"response={turn.response_text}"
            )
            if turn.plan_summary:
                plan_hints.append(f"prior_plan={turn.plan_summary}")
            if turn.plan_steps:
                plan_hints.append(f"prior_steps={' ; '.join(turn.plan_steps[:3])}")
        session_continuity = self.repository.fetch_session_continuity(str(contract.session_id))
        if session_continuity:
            continuity_hints.append(
                f"session_continuity_brief={session_continuity.continuity_brief}"
            )
            continuity_hints.append(f"session_continuity_mode={session_continuity.continuity_mode}")
            if session_continuity.ecosystem_state_status:
                continuity_hints.append(
                    f"ecosystem_state_status={session_continuity.ecosystem_state_status}"
                )
            if session_continuity.ecosystem_state_summary:
                continuity_hints.append(
                    f"ecosystem_state_summary={session_continuity.ecosystem_state_summary}"
                )
            if session_continuity.active_work_items:
                continuity_hints.append(
                    "ecosystem_active_work_items="
                    f"{';'.join(session_continuity.active_work_items[:3])}"
                )
            if session_continuity.active_artifact_refs:
                continuity_hints.append(
                    "ecosystem_active_artifact_refs="
                    f"{';'.join(session_continuity.active_artifact_refs[:3])}"
                )
            if session_continuity.open_checkpoint_refs:
                continuity_hints.append(
                    "ecosystem_open_checkpoint_refs="
                    f"{';'.join(session_continuity.open_checkpoint_refs[:3])}"
                )
            if session_continuity.surface_presence:
                continuity_hints.append(
                    "ecosystem_surface_presence="
                    f"{';'.join(session_continuity.surface_presence[:3])}"
                )
            if session_continuity.linked_surface_ids:
                continuity_hints.append(
                    f"linked_surface_ids={';'.join(session_continuity.linked_surface_ids[:3])}"
                )
            if session_continuity.active_surface_id:
                continuity_hints.append(f"active_surface_id={session_continuity.active_surface_id}")
            if session_continuity.last_surface_id:
                continuity_hints.append(f"last_surface_id={session_continuity.last_surface_id}")
            if session_continuity.surface_continuity_status:
                continuity_hints.append(
                    f"surface_continuity_status={session_continuity.surface_continuity_status}"
                )
            if session_continuity.surface_identity_conflict_flags:
                continuity_hints.append(
                    "surface_identity_conflict_flags="
                    f"{';'.join(session_continuity.surface_identity_conflict_flags[:3])}"
                )
            if session_continuity.project_ref:
                continuity_hints.append(f"project_ref={session_continuity.project_ref}")
            if session_continuity.objective_ref:
                continuity_hints.append(f"objective_ref={session_continuity.objective_ref}")
            if session_continuity.objective_status:
                continuity_hints.append(f"objective_status={session_continuity.objective_status}")
            if session_continuity.work_item_refs:
                continuity_hints.append(
                    f"work_item_refs={','.join(session_continuity.work_item_refs[:3])}"
                )
            if session_continuity.checkpoint_refs:
                continuity_hints.append(
                    f"checkpoint_refs={','.join(session_continuity.checkpoint_refs[:3])}"
                )
            if session_continuity.artifact_refs:
                continuity_hints.append(
                    f"artifact_refs={','.join(session_continuity.artifact_refs[:3])}"
                )
            if session_continuity.next_action_ref:
                continuity_hints.append(f"next_action_ref={session_continuity.next_action_ref}")
            if session_continuity.anchor_mission_id:
                continuity_hints.append(
                    f"session_anchor_mission_id={session_continuity.anchor_mission_id}"
                )
            if session_continuity.anchor_goal:
                continuity_hints.append(f"session_anchor_goal={session_continuity.anchor_goal}")
            if session_continuity.related_mission_id:
                continuity_hints.append(
                    f"session_related_mission_id={session_continuity.related_mission_id}"
                )
            if session_continuity.related_goal:
                continuity_hints.append(f"session_related_goal={session_continuity.related_goal}")
        continuity_checkpoint = self.repository.fetch_continuity_checkpoint(
            str(contract.session_id)
        )
        if continuity_checkpoint:
            continuity_hints.append(
                f"continuity_checkpoint_id={continuity_checkpoint.checkpoint_id}"
            )
            continuity_hints.append(
                f"continuity_checkpoint_status={continuity_checkpoint.checkpoint_status}"
            )
            continuity_hints.append(
                f"continuity_checkpoint_action={continuity_checkpoint.continuity_action}"
            )
            continuity_hints.append(
                f"continuity_checkpoint_summary={continuity_checkpoint.checkpoint_summary}"
            )
            if continuity_checkpoint.origin_request_id:
                continuity_hints.append(
                    f"continuity_checkpoint_origin={continuity_checkpoint.origin_request_id}"
                )
            if continuity_checkpoint.replay_summary:
                continuity_hints.append(
                    f"continuity_replay_summary={continuity_checkpoint.replay_summary}"
                )
            if continuity_checkpoint.open_checkpoint_refs:
                continuity_hints.append(
                    "continuity_open_checkpoint_refs="
                    f"{';'.join(continuity_checkpoint.open_checkpoint_refs[:3])}"
                )
            if continuity_checkpoint.active_surface_id:
                continuity_hints.append(
                    f"continuity_active_surface_id={continuity_checkpoint.active_surface_id}"
                )
            if continuity_checkpoint.surface_identity_conflict_flags:
                continuity_hints.append(
                    "continuity_surface_identity_conflict_flags="
                    f"{';'.join(continuity_checkpoint.surface_identity_conflict_flags[:3])}"
                )
            if continuity_checkpoint.objective_status:
                continuity_hints.append(
                    f"continuity_objective_status={continuity_checkpoint.objective_status}"
                )
            if continuity_checkpoint.next_action_ref:
                continuity_hints.append(
                    f"continuity_next_action_ref={continuity_checkpoint.next_action_ref}"
                )
        continuity_replay = self.get_session_continuity_replay(str(contract.session_id))
        if continuity_replay:
            continuity_hints.append(f"continuity_replay_status={continuity_replay.replay_status}")
            continuity_hints.append(f"continuity_recovery_mode={continuity_replay.recovery_mode}")
            continuity_hints.append(f"continuity_resume_point={continuity_replay.resume_point}")
            if continuity_replay.ecosystem_state_status:
                continuity_hints.append(
                    f"continuity_ecosystem_state_status={continuity_replay.ecosystem_state_status}"
                )
            if continuity_replay.surface_continuity_status:
                continuity_hints.append(
                    "continuity_surface_continuity_status="
                    f"{continuity_replay.surface_continuity_status}"
                )
            if continuity_replay.objective_status:
                continuity_hints.append(
                    f"continuity_objective_status={continuity_replay.objective_status}"
                )
        continuity_pause = self.get_session_continuity_pause(str(contract.session_id))
        if continuity_pause:
            continuity_hints.append(f"continuity_pause_status={continuity_pause.pause_status}")
            continuity_hints.append(f"continuity_pause_reason={continuity_pause.pause_reason}")
        if contract.mission_id:
            mission_state = self.repository.fetch_mission_state(str(contract.mission_id))
            if mission_state:
                if mission_state.identity_continuity_brief:
                    mission_hints.append(
                        f"identity_continuity_brief={mission_state.identity_continuity_brief}"
                    )
                if mission_state.open_loops:
                    mission_hints.append(f"open_loops={';'.join(mission_state.open_loops[:3])}")
                if mission_state.semantic_brief:
                    mission_hints.append(f"mission_semantic_brief={mission_state.semantic_brief}")
                mission_hints.append(f"mission_goal={mission_state.mission_goal}")
                if mission_state.active_surface_id:
                    mission_hints.append(
                        f"mission_active_surface_id={mission_state.active_surface_id}"
                    )
                if mission_state.ecosystem_state_status:
                    mission_hints.append(
                        f"mission_ecosystem_state_status={mission_state.ecosystem_state_status}"
                    )
                if mission_state.active_work_items:
                    mission_hints.append(
                        f"mission_active_work_items={';'.join(mission_state.active_work_items[:3])}"
                    )
                if mission_state.active_artifact_refs:
                    mission_hints.append(
                        "mission_active_artifact_refs="
                        f"{';'.join(mission_state.active_artifact_refs[:3])}"
                    )
                if mission_state.open_checkpoint_refs:
                    mission_hints.append(
                        "mission_open_checkpoint_refs="
                        f"{';'.join(mission_state.open_checkpoint_refs[:3])}"
                    )
                if mission_state.objective_status:
                    mission_hints.append(
                        f"mission_objective_status={mission_state.objective_status}"
                    )
                if mission_state.project_ref:
                    mission_hints.append(f"mission_project_ref={mission_state.project_ref}")
                if mission_state.work_item_refs:
                    mission_hints.append(
                        f"mission_work_item_refs={','.join(mission_state.work_item_refs[:3])}"
                    )
                if mission_state.last_recommendation:
                    mission_hints.append(
                        f"mission_recommendation={mission_state.last_recommendation}"
                    )
                if mission_state.last_decision_frame:
                    mission_hints.append(f"last_decision_frame={mission_state.last_decision_frame}")
                if mission_state.active_surface_id:
                    mission_hints.append(
                        f"mission_active_surface_id={mission_state.active_surface_id}"
                    )
                if mission_state.surface_continuity_status:
                    mission_hints.append(
                        "mission_surface_continuity_status="
                        f"{mission_state.surface_continuity_status}"
                    )
                if mission_state.ecosystem_state_status:
                    mission_hints.append(
                        f"mission_ecosystem_state_status={mission_state.ecosystem_state_status}"
                    )
                if mission_state.active_work_items:
                    mission_hints.append(
                        f"mission_active_work_items={';'.join(mission_state.active_work_items[:3])}"
                    )
                if mission_state.active_artifact_refs:
                    mission_hints.append(
                        "mission_active_artifact_refs="
                        f"{';'.join(mission_state.active_artifact_refs[:3])}"
                    )
                if mission_state.open_checkpoint_refs:
                    mission_hints.append(
                        "mission_open_checkpoint_refs="
                        f"{';'.join(mission_state.open_checkpoint_refs[:3])}"
                    )
                if mission_state.ecosystem_state_summary:
                    mission_hints.append(
                        f"mission_ecosystem_state_summary={mission_state.ecosystem_state_summary}"
                    )
                if mission_state.project_ref:
                    mission_hints.append(f"mission_project_ref={mission_state.project_ref}")
                if mission_state.objective_ref:
                    mission_hints.append(f"mission_objective_ref={mission_state.objective_ref}")
                if mission_state.checkpoint_refs:
                    mission_hints.append(
                        f"mission_checkpoint_refs={','.join(mission_state.checkpoint_refs[:3])}"
                    )
                if mission_state.artifact_refs:
                    mission_hints.append(
                        f"mission_artifact_refs={','.join(mission_state.artifact_refs[:3])}"
                    )
                if mission_state.next_action_ref:
                    mission_hints.append(f"mission_next_action_ref={mission_state.next_action_ref}")
                if mission_state.linked_surface_ids:
                    mission_hints.append(
                        "mission_linked_surface_ids="
                        f"{';'.join(mission_state.linked_surface_ids[:3])}"
                    )
                if mission_state.active_surface_id:
                    mission_hints.append(
                        f"mission_active_surface_id={mission_state.active_surface_id}"
                    )
                if mission_state.last_surface_id:
                    mission_hints.append(f"mission_last_surface_id={mission_state.last_surface_id}")
                if mission_state.surface_continuity_status:
                    mission_hints.append(
                        "mission_surface_continuity_status="
                        f"{mission_state.surface_continuity_status}"
                    )
                if mission_state.surface_identity_conflict_flags:
                    mission_hints.append(
                        "mission_surface_identity_conflict_flags="
                        f"{';'.join(mission_state.surface_identity_conflict_flags[:3])}"
                    )
                if mission_state.semantic_focus:
                    mission_hints.append(
                        f"mission_focus={','.join(mission_state.semantic_focus[:3])}"
                    )
                mission_hints.append(
                    f"mission_state={mission_state.mission_status.value}:{','.join(mission_state.active_tasks[-3:])}"
                )
                if mission_state.recent_plan_steps:
                    mission_hints.append(
                        f"mission_steps={' ; '.join(mission_state.recent_plan_steps[:3])}"
                    )
                latest_artifact = self._latest_procedural_artifact(mission_state.related_artifacts)
                if latest_artifact is not None:
                    if latest_artifact.get("artifact_status") is not None:
                        plan_hints.append(
                            f"procedural_artifact_status={latest_artifact['artifact_status']}"
                        )
                    if (
                        latest_artifact.get("artifact_ref") is not None
                        and latest_artifact.get("artifact_status") != "archivable"
                    ):
                        plan_hints.append(
                            f"procedural_artifact_ref={latest_artifact['artifact_ref']}"
                        )
                    if (
                        latest_artifact.get("summary") is not None
                        and latest_artifact.get("artifact_status") != "archivable"
                    ):
                        plan_hints.append(
                            f"procedural_artifact_summary={latest_artifact['summary']}"
                        )
                    if (
                        latest_artifact.get("version") is not None
                        and latest_artifact.get("artifact_status") != "archivable"
                    ):
                        plan_hints.append(
                            f"procedural_artifact_version={latest_artifact['version']}"
                        )
                continuity_context = self._build_continuity_context(contract, mission_state)
                if continuity_context and continuity_context.related_candidates:
                    primary = continuity_context.related_candidates[0]
                    if continuity_context.recommended_action:
                        mission_hints.append(
                            f"continuity_recommendation={continuity_context.recommended_action}"
                        )
                    if continuity_context.recommended_reason:
                        mission_hints.append(
                            f"continuity_ranking={continuity_context.recommended_reason}"
                        )
                    mission_hints.append(f"related_mission_id={primary.mission_id}")
                    mission_hints.append(f"related_mission_goal={primary.mission_goal}")
                    mission_hints.append(f"related_continuity_reason={primary.continuity_reason}")
                    mission_hints.append(
                        f"related_continuity_priority={primary.priority_score:.2f}"
                    )
            else:
                continuity_context = self._build_continuity_context_for_new_mission(contract)
                if continuity_context and continuity_context.related_candidates:
                    primary = continuity_context.related_candidates[0]
                    if continuity_context.recommended_action:
                        mission_hints.append(
                            f"continuity_recommendation={continuity_context.recommended_action}"
                        )
                    if continuity_context.recommended_reason:
                        mission_hints.append(
                            f"continuity_ranking={continuity_context.recommended_reason}"
                        )
                    mission_hints.append(f"related_mission_id={primary.mission_id}")
                    mission_hints.append(f"related_mission_goal={primary.mission_goal}")
                    mission_hints.append(f"related_continuity_reason={primary.continuity_reason}")
                    mission_hints.append(
                        f"related_continuity_priority={primary.priority_score:.2f}"
                    )
        context_policy = context_window_policy(
            requested_limit=limit,
            user_scope_status=(
                user_scope_context.context_status if user_scope_context is not None else None
            ),
            interaction_count=(
                user_scope_context.interaction_count if user_scope_context is not None else 0
            ),
            has_session_continuity=session_continuity is not None,
            has_related_mission=bool(continuity_context and continuity_context.related_candidates),
            has_mission_context=mission_state is not None,
        )
        corpus_summary = self.repository.summarize_memory_corpus()
        corpus_telemetry = memory_corpus_telemetry(
            user_scope_records=corpus_summary.user_scope_records,
            mission_state_records=corpus_summary.mission_state_records,
            specialist_context_records=corpus_summary.specialist_context_records,
            semantic_records=corpus_summary.semantic_records,
            procedural_records=corpus_summary.procedural_records,
            retained_records=corpus_summary.retained_records,
            promoted_records=corpus_summary.promoted_records,
            aging_records=corpus_summary.aging_records,
            review_recommended_records=corpus_summary.review_recommended_records,
            fixed_records=corpus_summary.fixed_records,
            operational_records=corpus_summary.operational_records,
            archivable_records=corpus_summary.archivable_records,
            consolidating_records=corpus_summary.consolidating_records,
        )
        recovery_mode = (
            "review_before_reuse"
            if latest_artifact is not None
            and latest_artifact.get("artifact_status") == "archivable"
            else "consolidate_before_expand"
            if corpus_telemetry.retention_pressure == "high"
            else "active_guided"
        )
        maintenance_review_status = (
            "attention_required"
            if latest_artifact is not None
            and latest_artifact.get("artifact_status") == "archivable"
            else "review_recommended"
            if corpus_telemetry.corpus_status == "review_recommended"
            else "stable"
        )
        memory_maintenance = memory_maintenance_decision(
            memory_review_status=maintenance_review_status,
            retention_pressure=corpus_telemetry.retention_pressure,
            context_compaction_status=context_policy.compaction_status,
            cross_session_recall_status=context_policy.cross_session_recall_status,
        )
        if (
            latest_artifact is not None and latest_artifact.get("artifact_status") == "archivable"
        ) or corpus_telemetry.retention_pressure != "low":
            plan_hints.extend(
                [
                    f"memory_corpus_status={corpus_telemetry.corpus_status}",
                    f"memory_retention_pressure={corpus_telemetry.retention_pressure}",
                    f"memory_recovery_mode={recovery_mode}",
                ]
            )
        live_turn_context = list(session_context[-context_policy.live_turn_limit :])
        trimmed_continuity_hints = self._compact_prefixed_hints(
            continuity_hints,
            preferred_prefixes=(
                "session_continuity_brief=",
                "session_continuity_mode=",
                "continuity_checkpoint_id=",
                "continuity_checkpoint_status=",
                "continuity_replay_status=",
                "continuity_recovery_mode=",
                "continuity_resume_point=",
                "ecosystem_state_status=",
                "ecosystem_state_summary=",
                "ecosystem_active_work_items=",
                "ecosystem_active_artifact_refs=",
                "ecosystem_open_checkpoint_refs=",
                "ecosystem_surface_presence=",
                "objective_status=",
                "project_ref=",
                "objective_ref=",
                "work_item_refs=",
                "checkpoint_refs=",
                "artifact_refs=",
                "next_action_ref=",
                "linked_surface_ids=",
                "active_surface_id=",
                "last_surface_id=",
                "surface_continuity_status=",
                "surface_identity_conflict_flags=",
                "session_anchor_goal=",
                "continuity_pause_status=",
            ),
            limit=context_policy.continuity_hint_limit,
        )
        cross_session_sources = self._cross_session_recall_sources(
            user_scope_context=user_scope_context,
            session_continuity=session_continuity,
            mission_state=mission_state,
            continuity_context=continuity_context,
        )
        cross_session_summary = self._cross_session_recall_summary(
            user_scope_context=user_scope_context,
            session_continuity=session_continuity,
            mission_state=mission_state,
            continuity_context=continuity_context,
        )
        if context_policy.cross_session_recall_status != "not_applicable":
            plan_hints.extend(
                [
                    f"cross_session_recall_status={context_policy.cross_session_recall_status}",
                    "cross_session_recall_sources="
                    f"{';'.join(cross_session_sources) if cross_session_sources else 'none'}",
                ]
            )
            if cross_session_summary:
                plan_hints.append(f"cross_session_recall_summary={cross_session_summary}")
        should_surface_memory_maintenance = memory_maintenance.status != "stable" or bool(
            summary
            or session_context
            or continuity_hints
            or cross_session_sources
            or mission_hints
            or user_hints
        )
        if should_surface_memory_maintenance:
            plan_hints.extend(
                [
                    f"memory_maintenance_status={memory_maintenance.status}",
                    f"memory_maintenance_reason={memory_maintenance.reason}",
                    f"memory_maintenance_fallback_mode={memory_maintenance.fallback_mode}",
                ]
            )
        final_session_context: list[str] = []
        if (
            summary
            or live_turn_context
            or trimmed_continuity_hints
            or context_policy.cross_session_recall_status != "not_applicable"
        ):
            user_scope_label = user_scope_context.context_status if user_scope_context else "none"
            continuity_label = session_continuity.continuity_mode if session_continuity else "none"
            final_session_context.extend(
                [
                    f"context_compaction_status={context_policy.compaction_status}",
                    "context_compaction_summary="
                    f"live_turns={len(live_turn_context)};"
                    f"continuity_hints={len(trimmed_continuity_hints)};"
                    f"recalled_sources={len(cross_session_sources)}",
                    "context_live_summary="
                    f"turns={len(live_turn_context)};"
                    f"user_scope={user_scope_label};"
                    f"continuity={continuity_label};"
                    f"cross_session={context_policy.cross_session_recall_status}",
                    f"memory_maintenance_status={memory_maintenance.status}",
                    f"memory_maintenance_fallback_mode={memory_maintenance.fallback_mode}",
                ]
            )
            if context_policy.cross_session_recall_status != "not_applicable":
                final_session_context.append(
                    f"cross_session_recall_status={context_policy.cross_session_recall_status}"
                )
            if summary:
                final_session_context.insert(0, f"context_summary={summary}")
            if cross_session_summary:
                final_session_context.append(
                    f"cross_session_recall_summary={cross_session_summary}"
                )
            for item in [*live_turn_context, *trimmed_continuity_hints]:
                if item not in final_session_context:
                    final_session_context.append(item)
        compacted_plan_hints = self._compact_prefixed_hints(
            plan_hints,
            preferred_prefixes=(
                "prior_plan=",
                "prior_steps=",
                "procedural_artifact_status=",
                "memory_recovery_mode=",
                "memory_corpus_status=",
                "memory_retention_pressure=",
                "memory_maintenance_status=",
                "memory_maintenance_reason=",
                "memory_maintenance_fallback_mode=",
                "cross_session_recall_status=",
                "cross_session_recall_sources=",
                "cross_session_recall_summary=",
            ),
            limit=context_policy.plan_hint_limit,
        )
        return (
            user_hints[: context_policy.user_hint_limit],
            final_session_context,
            mission_hints[: context_policy.mission_hint_limit],
            compacted_plan_hints,
            continuity_context,
            user_scope_context,
        )

    @staticmethod
    def _cross_session_recall_sources(
        *,
        user_scope_context: UserScopeContextContract | None,
        session_continuity: SessionContinuitySnapshot | None,
        mission_state: MissionStateContract | None,
        continuity_context: MissionContinuityContextContract | None,
    ) -> list[str]:
        sources: list[str] = []
        if user_scope_context is not None and user_scope_context.context_status not in {
            "tracked_only",
            "not_applicable",
        }:
            sources.append("user_scope")
        if session_continuity is not None:
            sources.append("session_continuity")
        if mission_state is not None:
            sources.append("active_mission")
            if mission_state.ecosystem_state_status not in {None, "not_applicable"}:
                sources.append("ecosystem_state")
        if continuity_context and continuity_context.related_candidates:
            sources.append("related_mission")
        return sources

    @classmethod
    def _cross_session_recall_summary(
        cls,
        *,
        user_scope_context: UserScopeContextContract | None,
        session_continuity: SessionContinuitySnapshot | None,
        mission_state: MissionStateContract | None,
        continuity_context: MissionContinuityContextContract | None,
    ) -> str | None:
        fragments: list[str] = []
        if (
            user_scope_context is not None
            and user_scope_context.context_status not in {"tracked_only", "not_applicable"}
            and user_scope_context.user_context_brief
        ):
            fragments.append(
                f"user_scope={cls._shorten_memory_hint(user_scope_context.user_context_brief)}"
            )
        if session_continuity is not None:
            anchor = session_continuity.anchor_goal or session_continuity.continuity_brief
            if anchor:
                fragments.append(f"anchor={cls._shorten_memory_hint(anchor)}")
        if continuity_context and continuity_context.related_candidates:
            fragments.append(
                "related="
                f"{cls._shorten_memory_hint(continuity_context.related_candidates[0].mission_goal)}"
            )
        elif mission_state is not None and mission_state.semantic_brief:
            fragments.append(f"mission={cls._shorten_memory_hint(mission_state.semantic_brief)}")
        if (
            mission_state is not None
            and mission_state.ecosystem_state_status not in {None, "not_applicable"}
            and mission_state.ecosystem_state_summary
        ):
            fragments.append(
                f"ecosystem={cls._shorten_memory_hint(mission_state.ecosystem_state_summary)}"
            )
        if not fragments:
            return None
        return " | ".join(fragments[:3])

    @staticmethod
    def _shorten_memory_hint(value: str, *, limit: int = 96) -> str:
        compact = " ".join(value.split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3].rstrip()}..."

    @staticmethod
    def _compact_prefixed_hints(
        hints: list[str],
        *,
        preferred_prefixes: tuple[str, ...],
        limit: int,
    ) -> list[str]:
        if limit <= 0 or not hints:
            return []
        selected: list[str] = []
        for prefix in preferred_prefixes:
            match = next((item for item in hints if item.startswith(prefix)), None)
            if match and match not in selected:
                selected.append(match)
        for item in hints:
            if item not in selected:
                selected.append(item)
        return selected[:limit]

    def _resolve_related_states(
        self,
        *,
        session_id: str,
        mission_id: str | None,
        continuity_context: MissionContinuityContextContract | None,
    ) -> list[MissionStateContract]:
        states: list[MissionStateContract] = []
        seen: set[str] = set()
        if continuity_context:
            for candidate in continuity_context.related_candidates[:2]:
                state = self.repository.fetch_mission_state(str(candidate.mission_id))
                if state is not None and str(state.mission_id) not in seen:
                    states.append(state)
                    seen.add(str(state.mission_id))
        if mission_id:
            for state in self.repository.list_related_mission_states(
                session_id=session_id,
                exclude_mission_id=mission_id,
                limit=2,
            ):
                if str(state.mission_id) not in seen:
                    states.append(state)
                    seen.add(str(state.mission_id))
        return states[:2]

    def _build_specialist_shared_memory_context(
        self,
        *,
        specialist_type: str,
        continuity_mode: str,
        mission_state: MissionStateContract | None,
        related_states: list[MissionStateContract],
        active_domains: list[str],
        user_id: str | None,
        previous_context: SpecialistSharedMemoryContextContract | None,
    ) -> SpecialistSharedMemoryContextContract:
        related_mission_ids = [state.mission_id for state in related_states[:2]]
        memory_refs: list[str] = []
        semantic_focus: list[str] = []
        open_loops: list[str] = []
        user_scope_snapshot = (
            self.repository.fetch_user_scope_snapshot(user_id) if user_id else None
        )
        shared_memory_classes = [
            memory_class
            for memory_class in SHARED_MEMORY_CLASSES
            if memory_class not in {MemoryClass.SEMANTIC, MemoryClass.PROCEDURAL}
        ]
        dynamic_memory_refs: list[str] = []

        def append_unique(items: list[str], target: list[str], limit: int) -> None:
            for item in items:
                if item and item not in target:
                    target.append(item)
                if len(target) >= limit:
                    break

        if mission_state is not None:
            append_unique(mission_state.related_memories[-3:], dynamic_memory_refs, 2)
            append_unique(mission_state.semantic_focus, semantic_focus, 5)
            append_unique(mission_state.open_loops, open_loops, 4)
        for state in related_states:
            append_unique(state.related_memories[-2:], dynamic_memory_refs, 2)
            append_unique(state.semantic_focus, semantic_focus, 5)
            append_unique(state.open_loops, open_loops, 4)
        for domain_name in active_domains:
            domain_ref = f"memory://{MemoryClass.DOMAIN.value}/{domain_name}"
            if domain_ref not in dynamic_memory_refs and len(dynamic_memory_refs) < 2:
                dynamic_memory_refs.append(domain_ref)
            if domain_name not in semantic_focus and len(semantic_focus) < 5:
                semantic_focus.append(domain_name)
            route_payload = specialist_route_payload(domain_name)
            append_unique(list(route_payload.get("canonical_domain_refs", [])), semantic_focus, 5)
        source_goal = mission_state.mission_goal if mission_state else None
        source_mission_id = mission_state.mission_id if mission_state else None
        promoted_route_match = specialist_eligible_route(active_domains, specialist_type)
        promoted_route = promoted_route_match[1] if promoted_route_match is not None else None
        promoted_route_payload = (
            specialist_route_payload(promoted_route_match[0], specialist_type)
            if promoted_route_match is not None
            else {}
        )
        workflow_profile = (
            str(promoted_route_payload.get("workflow_profile"))
            if promoted_route_payload.get("workflow_profile") is not None
            else None
        )
        memory_decision = self._derive_guided_memory_decision(
            promoted_route=promoted_route,
            mission_state=mission_state,
            related_states=related_states,
            user_scope_snapshot=user_scope_snapshot,
            previous_context=previous_context,
            continuity_mode=continuity_mode,
        )
        if memory_decision.specialist_classes:
            shared_memory_classes = list(memory_decision.specialist_classes)
        corpus_summary = self.repository.summarize_memory_corpus()
        corpus_telemetry = memory_corpus_telemetry(
            user_scope_records=corpus_summary.user_scope_records,
            mission_state_records=corpus_summary.mission_state_records,
            specialist_context_records=corpus_summary.specialist_context_records,
            semantic_records=corpus_summary.semantic_records,
            procedural_records=corpus_summary.procedural_records,
            retained_records=corpus_summary.retained_records,
            promoted_records=corpus_summary.promoted_records,
            aging_records=corpus_summary.aging_records,
            review_recommended_records=corpus_summary.review_recommended_records,
            fixed_records=corpus_summary.fixed_records,
            operational_records=corpus_summary.operational_records,
            archivable_records=corpus_summary.archivable_records,
            consolidating_records=corpus_summary.consolidating_records,
        )
        runtime_semantic_state = memory_decision.semantic_memory_state
        runtime_procedural_state = memory_decision.procedural_memory_state
        runtime_review_status = memory_decision.review_status
        runtime_archive_status = memory_decision.archive_status
        if previous_context is not None:
            if mission_state is None and not related_states and user_scope_snapshot is None:
                runtime_semantic_state = (
                    previous_context.semantic_memory_state or runtime_semantic_state
                )
                runtime_procedural_state = (
                    previous_context.procedural_memory_state or runtime_procedural_state
                )
                runtime_review_status = (
                    previous_context.memory_review_status or runtime_review_status
                )
                runtime_archive_status = (
                    previous_context.memory_archive_status or runtime_archive_status
                )
            if (
                previous_context.memory_review_status == "review_recommended"
                and runtime_review_status != "review_recommended"
            ):
                runtime_review_status = previous_context.memory_review_status
            if (
                previous_context.memory_archive_status == "archive_candidate"
                and runtime_archive_status != "archive_candidate"
            ):
                runtime_archive_status = previous_context.memory_archive_status
                runtime_semantic_state = (
                    previous_context.semantic_memory_state or runtime_semantic_state
                )
                runtime_procedural_state = (
                    previous_context.procedural_memory_state or runtime_procedural_state
                )
        runtime_policy = memory_lifecycle_runtime_policy(
            semantic_memory_state=runtime_semantic_state,
            procedural_memory_state=runtime_procedural_state,
            review_status=runtime_review_status,
            archive_status=runtime_archive_status,
            retention_pressure=corpus_telemetry.retention_pressure,
        )
        if not runtime_policy.allow_semantic_specialist:
            shared_memory_classes = [
                memory_class
                for memory_class in shared_memory_classes
                if memory_class is not MemoryClass.SEMANTIC
            ]
        if not runtime_policy.allow_procedural_specialist:
            shared_memory_classes = [
                memory_class
                for memory_class in shared_memory_classes
                if memory_class is not MemoryClass.PROCEDURAL
            ]
        canonical_memory_refs = [
            f"memory://{memory_class.value}" for memory_class in shared_memory_classes
        ]
        if MemoryClass.SEMANTIC in shared_memory_classes:
            semantic_ref = (
                f"memory://semantic/mission/{source_mission_id}"
                if source_mission_id
                else f"memory://semantic/user/{user_id}"
                if user_id
                else f"memory://semantic/{specialist_type}"
            )
            if semantic_ref not in dynamic_memory_refs:
                dynamic_memory_refs.append(semantic_ref)
        if MemoryClass.PROCEDURAL in shared_memory_classes:
            procedural_ref = (
                f"memory://procedural/mission/{source_mission_id}"
                if source_mission_id
                else f"memory://procedural/user/{user_id}"
                if user_id
                else f"memory://procedural/{specialist_type}"
            )
            if procedural_ref not in dynamic_memory_refs:
                dynamic_memory_refs.append(procedural_ref)
        memory_refs = [*canonical_memory_refs, *dynamic_memory_refs]
        memory_class_policies = specialist_memory_policy_payload(shared_memory_classes)
        consumed_memory_classes = [memory_class.value for memory_class in shared_memory_classes]
        memory_write_policies = {
            memory_class_name: str(policy.get("write_policy", "through_core_only"))
            for memory_class_name, policy in memory_class_policies.items()
        }
        latest_artifact = (
            self._latest_procedural_artifact(mission_state.related_artifacts)
            if mission_state is not None
            else None
        )
        procedural_artifact_refs = (
            [str(latest_artifact.get("artifact_ref"))]
            if latest_artifact is not None and latest_artifact.get("artifact_ref") is not None
            else []
        )
        procedural_artifact_status = (
            str(latest_artifact.get("artifact_status"))
            if latest_artifact is not None and latest_artifact.get("artifact_status") is not None
            else None
        )
        procedural_artifact_version = (
            int(latest_artifact.get("version"))
            if latest_artifact is not None and latest_artifact.get("version") is not None
            else None
        )
        procedural_artifact_summary = (
            str(latest_artifact.get("summary"))
            if latest_artifact is not None and latest_artifact.get("summary") is not None
            else None
        )
        if not runtime_policy.allow_procedural_artifact_reuse:
            procedural_artifact_refs = []
            procedural_artifact_version = None
            procedural_artifact_summary = None

        related_summary = (
            ", ".join(str(item.mission_id) for item in related_states[:2]) or "nenhuma"
        )
        source_focus = ", ".join(semantic_focus[:3]) or "sem foco consolidado"
        open_loop_summary = "; ".join(open_loops[:2]) or "sem loop aberto dominante"
        dominant_recommendation = (
            mission_state.last_recommendation
            if mission_state and mission_state.last_recommendation
            else "sem recomendacao dominante"
        )
        mission_context_brief = (
            f"goal={source_goal or 'sessao sem missao ancorada'} | "
            f"related={related_summary} | "
            f"recommendation={dominant_recommendation}"
        )
        domain_context_brief = (
            f"active_domains={','.join(active_domains[:3]) or 'nenhum'} | "
            f"semantic_focus={source_focus} | "
            f"workflow_profile={workflow_profile or 'baseline'} | "
            f"semantic_source={memory_decision.semantic_source or 'none'} | "
            f"procedural_source={memory_decision.procedural_source or 'none'} | "
            f"semantic_state={memory_decision.semantic_memory_state or 'none'} | "
            f"procedural_state={memory_decision.procedural_memory_state or 'none'} | "
            f"memory_lifecycle={memory_decision.lifecycle_status} | "
            f"memory_review={memory_decision.review_status} | "
            f"memory_consolidation={memory_decision.consolidation_status} | "
            f"memory_fixation={memory_decision.fixation_status} | "
            f"memory_archive={memory_decision.archive_status} | "
            f"memory_runtime_mode={runtime_policy.specialist_mode} | "
            f"memory_recovery_mode={runtime_policy.recovery_mode} | "
            f"procedural_artifact_status={procedural_artifact_status or 'none'} | "
            f"memory_corpus_status={corpus_telemetry.corpus_status} | "
            f"memory_retention_pressure={corpus_telemetry.retention_pressure} | "
            f"memory_refs={','.join(memory_refs[:4])}"
        )
        continuity_context_brief = (
            f"continuity_mode={continuity_mode} | open_loops={open_loop_summary} | "
            f"source_mission_id={source_mission_id or 'none'} | "
            f"recurrent_memory_status={runtime_policy.recurrent_reuse_status}"
        )
        shared_memory_brief = (
            f"specialist={specialist_type} continuidade={continuity_mode} "
            f"fonte={source_goal or 'sessao sem missao ancorada'} "
            f"relacoes={related_summary} foco={source_focus} "
            f"open_loops={open_loop_summary} runtime={runtime_policy.specialist_mode}"
        )
        consumer_mode = (
            "domain_guided_memory_packet"
            if promoted_route is not None
            else "baseline_shared_context"
        )
        consumer_profile = (
            promoted_route_payload.get("consumer_profile") if promoted_route else None
        )
        consumer_objective = (
            promoted_route_payload.get("consumer_objective") if promoted_route else None
        )
        expected_deliverables = (
            list(promoted_route_payload.get("expected_deliverables", [])) if promoted_route else []
        )
        telemetry_focus = (
            list(promoted_route_payload.get("telemetry_focus", [])) if promoted_route else []
        )
        domain_mission_link_reason = (
            f"route={promoted_route.domain_name if promoted_route else 'baseline'} "
            "canonicos="
            f"{','.join(promoted_route_payload.get('canonical_domain_refs', [])) or 'none'} "
            f"missao={source_goal or 'sessao_sem_missao_ancorada'}"
        )
        recurrent_context = self._build_recurrent_specialist_context(
            user_id=user_id,
            specialist_type=specialist_type,
            promoted_route=promoted_route,
            previous_context=previous_context,
            active_domains=active_domains,
            continuity_mode=continuity_mode,
            source_goal=source_goal,
            consumer_objective=consumer_objective,
            memory_refs=memory_refs,
            recurrent_reuse_status=runtime_policy.recurrent_reuse_status,
            allow_reuse=runtime_policy.allow_recurrent_reuse,
        )
        return SpecialistSharedMemoryContextContract(
            specialist_type=specialist_type,
            sharing_mode="core_mediated_read_only",
            continuity_mode=continuity_mode,
            shared_memory_brief=shared_memory_brief,
            write_policy="through_core_only",
            consumer_mode=consumer_mode,
            source_mission_id=source_mission_id,
            source_mission_goal=source_goal,
            mission_context_brief=mission_context_brief,
            domain_context_brief=domain_context_brief,
            continuity_context_brief=continuity_context_brief,
            consumer_profile=consumer_profile,
            consumer_objective=consumer_objective,
            expected_deliverables=expected_deliverables,
            telemetry_focus=telemetry_focus,
            related_mission_ids=related_mission_ids,
            memory_refs=memory_refs,
            memory_class_policies=memory_class_policies,
            consumed_memory_classes=consumed_memory_classes,
            memory_write_policies=memory_write_policies,
            semantic_focus=semantic_focus,
            open_loops=open_loops,
            last_recommendation=mission_state.last_recommendation if mission_state else None,
            semantic_memory_source=memory_decision.semantic_source,
            procedural_memory_source=memory_decision.procedural_source,
            semantic_memory_effects=list(memory_decision.semantic_effects),
            procedural_memory_effects=list(memory_decision.procedural_effects),
            semantic_memory_lifecycle=memory_decision.semantic_lifecycle,
            procedural_memory_lifecycle=memory_decision.procedural_lifecycle,
            semantic_memory_state=memory_decision.semantic_memory_state,
            procedural_memory_state=memory_decision.procedural_memory_state,
            memory_lifecycle_status=memory_decision.lifecycle_status,
            memory_review_status=memory_decision.review_status,
            memory_consolidation_status=memory_decision.consolidation_status,
            memory_fixation_status=memory_decision.fixation_status,
            memory_archive_status=memory_decision.archive_status,
            procedural_artifact_status=procedural_artifact_status,
            procedural_artifact_refs=procedural_artifact_refs,
            procedural_artifact_version=procedural_artifact_version,
            procedural_artifact_summary=procedural_artifact_summary,
            memory_corpus_status=corpus_telemetry.corpus_status,
            memory_retention_pressure=corpus_telemetry.retention_pressure,
            memory_corpus_summary=dict(corpus_telemetry.summary),
            domain_mission_link_reason=domain_mission_link_reason,
            recurrent_context_status=recurrent_context["status"],
            recurrent_interaction_count=recurrent_context["interaction_count"],
            recurrent_context_brief=recurrent_context["brief"],
            recurrent_domain_focus=recurrent_context["domain_focus"],
            recurrent_memory_refs=recurrent_context["memory_refs"],
            recurrent_continuity_modes=recurrent_context["continuity_modes"],
        )

    def _derive_guided_memory_decision(
        self,
        *,
        promoted_route: object | None,
        mission_state: MissionStateContract | None,
        related_states: list[MissionStateContract],
        user_scope_snapshot: StoredUserScopeSnapshot | None,
        previous_context: SpecialistSharedMemoryContextContract | None,
        continuity_mode: str,
    ):
        if promoted_route is None:
            return guided_memory_decision(
                semantic_sources=[],
                procedural_sources=[],
                domain_compatible=False,
                workflow_profile=None,
                continuity_source=None,
            )

        semantic_labels: list[str] = []
        procedural_labels: list[str] = []
        semantic_evidence: list[str] = []
        procedural_evidence: list[str] = []
        if mission_state is not None:
            semantic_evidence.extend(mission_state.semantic_focus)
            if mission_state.semantic_brief:
                semantic_evidence.append(mission_state.semantic_brief)
            if semantic_evidence:
                semantic_labels.append("active_mission")
            if mission_state.recent_plan_steps:
                procedural_evidence.extend(mission_state.recent_plan_steps)
            if mission_state.last_recommendation:
                procedural_evidence.append(mission_state.last_recommendation)
            if procedural_evidence:
                procedural_labels.append("active_mission")
        for related_state in related_states:
            semantic_evidence.extend(related_state.semantic_focus)
            if related_state.semantic_brief:
                semantic_evidence.append(related_state.semantic_brief)
            semantic_labels.append("related_mission")
            if related_state.recent_plan_steps:
                procedural_evidence.extend(related_state.recent_plan_steps)
            if related_state.last_recommendation:
                procedural_evidence.append(related_state.last_recommendation)
            procedural_labels.append("related_mission")
        previous_context_allowed = (
            previous_context is not None
            and previous_context.memory_archive_status != "archive_candidate"
            and previous_context.memory_review_status != "review_recommended"
        )
        if previous_context_allowed and previous_context is not None:
            semantic_evidence.extend(previous_context.semantic_focus)
            if previous_context.shared_memory_brief:
                semantic_evidence.append(previous_context.shared_memory_brief)
            semantic_labels.append("recurrent_specialist")
            if previous_context.last_recommendation:
                procedural_evidence.append(previous_context.last_recommendation)
            procedural_evidence.extend(previous_context.recurrent_continuity_modes)
            procedural_labels.append("recurrent_specialist")
        if user_scope_snapshot is not None:
            if user_scope_snapshot.last_recommended_task_type:
                procedural_evidence.append(user_scope_snapshot.last_recommended_task_type)
            if user_scope_snapshot.continuity_preference:
                procedural_evidence.append(user_scope_snapshot.continuity_preference)
            if user_scope_snapshot.recent_domain_focus:
                semantic_labels.append("user_scope")
            if (
                user_scope_snapshot.last_recommended_task_type
                or user_scope_snapshot.continuity_preference
            ):
                procedural_labels.append("user_scope")

        route_refs = set(getattr(promoted_route, "canonical_refs", ()) or ())
        route_name = getattr(promoted_route, "domain_name", None)
        semantic_signal = bool(semantic_evidence)
        domain_compatible = (
            not route_refs
            or any(ref in semantic_evidence for ref in route_refs)
            or (route_name in semantic_evidence if route_name else False)
        )
        procedural_signal = bool(procedural_evidence)
        continuity_source = (
            "related_mission"
            if "related_mission" in semantic_labels or "related_mission" in procedural_labels
            else "active_mission"
            if "active_mission" in semantic_labels or "active_mission" in procedural_labels
            else "user_scope"
            if "user_scope" in semantic_labels or "user_scope" in procedural_labels
            else "fresh_request"
        )
        if continuity_mode == "retomar_missao_relacionada":
            continuity_source = "related_mission"
        return guided_memory_decision(
            semantic_sources=semantic_labels if semantic_signal else [],
            procedural_sources=procedural_labels if procedural_signal else [],
            domain_compatible=domain_compatible,
            workflow_profile=getattr(promoted_route, "workflow_profile", None),
            continuity_source=continuity_source,
        )

    def _build_recurrent_specialist_context(
        self,
        *,
        user_id: str | None,
        specialist_type: str,
        promoted_route: object | None,
        previous_context: SpecialistSharedMemoryContextContract | None,
        active_domains: list[str],
        continuity_mode: str,
        source_goal: str | None,
        consumer_objective: str | None,
        memory_refs: list[str],
        recurrent_reuse_status: str,
        allow_reuse: bool,
    ) -> dict[str, object]:
        if user_id is None or promoted_route is None:
            return {
                "status": "not_applicable",
                "interaction_count": 0,
                "brief": None,
                "domain_focus": [],
                "memory_refs": [],
                "continuity_modes": [],
            }
        stale_previous_context = previous_context is not None and (
            previous_context.memory_review_status == "review_recommended"
            or previous_context.memory_archive_status == "archive_candidate"
        )
        interaction_count = (
            previous_context.recurrent_interaction_count if previous_context else 0
        ) + 1
        domain_focus = self._merge_recent_values(
            previous_context.recurrent_domain_focus if previous_context and allow_reuse else [],
            active_domains[:3],
            limit=4,
        )
        recurrent_memory_refs = self._merge_recent_values(
            previous_context.recurrent_memory_refs if previous_context and allow_reuse else [],
            memory_refs[:4],
            limit=6,
        )
        continuity_modes = self._merge_recent_values(
            previous_context.recurrent_continuity_modes if previous_context and allow_reuse else [],
            [continuity_mode],
            limit=3,
        )
        status = (
            recurrent_reuse_status
            if stale_previous_context and recurrent_reuse_status != "enabled"
            else "recoverable"
            if interaction_count >= 2
            else "seeded"
        )
        brief_parts = [
            f"specialist={specialist_type}",
            f"interactions={interaction_count}",
            f"reuse={recurrent_reuse_status if stale_previous_context else 'enabled'}",
        ]
        if domain_focus:
            brief_parts.append(f"domains={','.join(domain_focus[:3])}")
        if continuity_modes:
            brief_parts.append(f"continuity={','.join(continuity_modes[:2])}")
        if source_goal:
            brief_parts.append(f"last_goal={source_goal}")
        if consumer_objective:
            brief_parts.append(f"objective={consumer_objective}")
        return {
            "status": status,
            "interaction_count": interaction_count,
            "brief": " | ".join(brief_parts),
            "domain_focus": domain_focus,
            "memory_refs": recurrent_memory_refs,
            "continuity_modes": continuity_modes,
        }

    def _build_session_continuity_snapshot(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract | None,
        governance_decision: PermissionDecision | None,
        ecosystem_state: EcosystemOperationalStateContract | None,
        surface_state: SurfaceContinuityState,
        objective_state: ProjectObjectiveContinuityState,
    ) -> SessionContinuitySnapshot | None:
        if deliberative_plan is None:
            return None
        previous = self.repository.fetch_session_continuity(str(contract.session_id))
        continuity_action = deliberative_plan.continuity_action or "continuar"
        if governance_decision == PermissionDecision.BLOCK and continuity_action not in {
            "reformular",
            "retomar",
            "encerrar",
        }:
            return previous

        anchor_mission_id: str | None
        anchor_goal: str | None
        if continuity_action == "retomar" and deliberative_plan.continuity_target_mission_id:
            anchor_mission_id = str(deliberative_plan.continuity_target_mission_id)
            anchor_goal = deliberative_plan.continuity_target_goal
        else:
            anchor_mission_id = str(contract.mission_id) if contract.mission_id else None
            anchor_goal = deliberative_plan.goal or contract.content

        brief = self._build_session_continuity_brief(
            continuity_action=continuity_action,
            plan=deliberative_plan,
            governance_decision=governance_decision,
            anchor_goal=anchor_goal or contract.content,
            previous=previous,
        )
        related_mission_id = (
            str(deliberative_plan.continuity_target_mission_id)
            if deliberative_plan.continuity_target_mission_id
            else None
        )
        related_goal = deliberative_plan.continuity_target_goal
        return SessionContinuitySnapshot(
            session_id=str(contract.session_id),
            continuity_brief=brief,
            continuity_mode=continuity_action,
            anchor_mission_id=anchor_mission_id,
            anchor_goal=anchor_goal,
            related_mission_id=related_mission_id,
            related_goal=related_goal,
            ecosystem_state_status=(
                ecosystem_state.ecosystem_state_status if ecosystem_state else None
            ),
            active_work_items=(list(ecosystem_state.active_work_items) if ecosystem_state else []),
            active_artifact_refs=(
                list(ecosystem_state.active_artifact_refs) if ecosystem_state else []
            ),
            open_checkpoint_refs=(
                list(ecosystem_state.open_checkpoint_refs) if ecosystem_state else []
            ),
            surface_presence=(list(ecosystem_state.surface_presence) if ecosystem_state else []),
            ecosystem_state_summary=(ecosystem_state.state_summary if ecosystem_state else None),
            linked_surface_ids=list(surface_state.linked_surface_ids),
            active_surface_id=surface_state.active_surface_id,
            last_surface_id=surface_state.last_surface_id,
            surface_continuity_status=surface_state.surface_continuity_status,
            surface_identity_conflict_flags=list(surface_state.surface_identity_conflict_flags),
            project_ref=objective_state.project_ref,
            objective_ref=objective_state.objective_ref,
            work_item_refs=list(objective_state.work_item_refs),
            checkpoint_refs=list(objective_state.checkpoint_refs),
            artifact_refs=list(objective_state.artifact_refs),
            objective_status=objective_state.objective_status,
            next_action_ref=objective_state.next_action_ref,
            updated_at=self.now(),
        )

    def _build_mission_state(
        self,
        contract: InputContract,
        memory_record_id: MemoryRecordId,
        intent: str,
        deliberative_plan: DeliberativePlanContract | None,
        *,
        open_loops: list[str],
        decision_frame: str,
        governance_decision: PermissionDecision | None,
        ecosystem_state: EcosystemOperationalStateContract | None,
        surface_state: SurfaceContinuityState,
        objective_state: ProjectObjectiveContinuityState,
    ) -> tuple[MissionStateContract | None, dict[str, object] | None]:
        mission_id = str(contract.mission_id)
        previous = self.repository.fetch_mission_state(mission_id)
        accepted = governance_decision not in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }
        if previous is None and not accepted:
            return None, None

        checkpoints = list(previous.checkpoints) if previous else []
        active_tasks = list(previous.active_tasks) if previous else []
        related_memories = list(previous.related_memories) if previous else []
        related_artifacts = list(previous.related_artifacts) if previous else []
        recent_plan_steps = list(previous.recent_plan_steps) if previous else []
        semantic_focus = list(previous.semantic_focus) if previous else []
        checkpoints.append(f"request:{contract.request_id}")
        related_memories.append(str(memory_record_id))
        if accepted:
            active_tasks.append(intent)
            if ecosystem_state:
                for item in ecosystem_state.active_work_items:
                    if item not in active_tasks:
                        active_tasks.append(item)
            if deliberative_plan:
                recent_plan_steps = list(deliberative_plan.steps[-3:])
                for domain in deliberative_plan.active_domains:
                    if domain not in semantic_focus:
                        semantic_focus.append(domain)
            if intent not in semantic_focus:
                semantic_focus.append(intent)

        mission_goal = previous.mission_goal if previous else contract.content
        last_recommendation = (
            deliberative_plan.plan_summary
            if accepted and deliberative_plan
            else (previous.last_recommendation if previous else None)
        )
        semantic_brief = self._build_semantic_brief(
            mission_goal=mission_goal,
            intent=intent,
            semantic_focus=semantic_focus,
            deliberative_plan=deliberative_plan if accepted else None,
            previous=previous,
        )
        persisted_open_loops = (
            list(previous.open_loops) if previous and not accepted else open_loops[:3]
        )
        persisted_frame = (
            previous.last_decision_frame if previous and not accepted else decision_frame
        )
        identity_continuity_brief = self._build_identity_continuity_brief(
            mission_goal=mission_goal,
            open_loops=persisted_open_loops,
            decision_frame=persisted_frame or decision_frame,
            recommendation=last_recommendation,
            previous=previous,
        )
        procedural_artifact = self._build_procedural_artifact(
            contract,
            deliberative_plan=deliberative_plan if accepted else None,
            previous_artifacts=related_artifacts,
        )
        if procedural_artifact is not None:
            related_artifacts = self._merge_procedural_artifact(
                existing_artifacts=related_artifacts,
                artifact=procedural_artifact,
            )
        mission_state = MissionStateContract(
            mission_id=contract.mission_id,
            mission_goal=mission_goal,
            mission_status=MissionStatus.ACTIVE,
            checkpoints=checkpoints[-5:],
            created_at=previous.created_at if previous else self.now(),
            session_origin=str(contract.session_id),
            active_tasks=active_tasks[-5:],
            related_memories=related_memories[-5:],
            related_artifacts=related_artifacts[-5:],
            recent_plan_steps=recent_plan_steps,
            last_recommendation=last_recommendation,
            semantic_brief=semantic_brief,
            semantic_focus=semantic_focus[-4:],
            identity_continuity_brief=identity_continuity_brief,
            open_loops=persisted_open_loops,
            last_decision_frame=persisted_frame,
            ecosystem_state_status=(
                ecosystem_state.ecosystem_state_status
                if ecosystem_state
                else (previous.ecosystem_state_status if previous else None)
            ),
            active_work_items=(
                list(ecosystem_state.active_work_items)
                if ecosystem_state
                else (list(previous.active_work_items) if previous else [])
            ),
            active_artifact_refs=(
                list(ecosystem_state.active_artifact_refs)
                if ecosystem_state
                else (list(previous.active_artifact_refs) if previous else [])
            ),
            open_checkpoint_refs=(
                list(ecosystem_state.open_checkpoint_refs)
                if ecosystem_state
                else (list(previous.open_checkpoint_refs) if previous else [])
            ),
            surface_presence=(
                list(ecosystem_state.surface_presence)
                if ecosystem_state
                else (list(previous.surface_presence) if previous else [])
            ),
            ecosystem_state_summary=(
                ecosystem_state.state_summary
                if ecosystem_state
                else (previous.ecosystem_state_summary if previous else None)
            ),
            project_ref=objective_state.project_ref or (previous.project_ref if previous else None),
            objective_ref=objective_state.objective_ref
            or (previous.objective_ref if previous else None),
            work_item_refs=(
                list(objective_state.work_item_refs)
                if objective_state.work_item_refs
                else (list(previous.work_item_refs) if previous else [])
            ),
            checkpoint_refs=(
                list(objective_state.checkpoint_refs)
                if objective_state.checkpoint_refs
                else (list(previous.checkpoint_refs) if previous else [])
            ),
            artifact_refs=(
                list(objective_state.artifact_refs)
                if objective_state.artifact_refs
                else (list(previous.artifact_refs) if previous else [])
            ),
            objective_status=objective_state.objective_status
            or (previous.objective_status if previous else None),
            next_action_ref=objective_state.next_action_ref
            or (previous.next_action_ref if previous else None),
            linked_surface_ids=(
                list(surface_state.linked_surface_ids)
                if surface_state.linked_surface_ids
                else (list(previous.linked_surface_ids) if previous else [])
            ),
            active_surface_id=(
                surface_state.active_surface_id
                if surface_state.active_surface_id
                else (previous.active_surface_id if previous else None)
            ),
            last_surface_id=(
                surface_state.last_surface_id
                if surface_state.last_surface_id
                else (previous.last_surface_id if previous else None)
            ),
            surface_continuity_status=(
                surface_state.surface_continuity_status
                if surface_state.surface_continuity_status
                else (previous.surface_continuity_status if previous else None)
            ),
            surface_identity_conflict_flags=(
                list(surface_state.surface_identity_conflict_flags)
                if surface_state.surface_identity_conflict_flags
                else (list(previous.surface_identity_conflict_flags) if previous else [])
            ),
            owner_context=contract.user_id or str(contract.session_id),
            updated_at=self.now(),
        )
        return mission_state, procedural_artifact

    def _build_procedural_artifact(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract | None,
        previous_artifacts: list[dict[str, object]],
    ) -> dict[str, object] | None:
        if deliberative_plan is None:
            return None
        artifact_route, workflow_profile = self._procedural_artifact_route_context(
            deliberative_plan
        )
        (
            procedural_lifecycle,
            procedural_memory_state,
            memory_review_status,
        ) = self._procedural_artifact_memory_signals(
            deliberative_plan,
            workflow_profile=workflow_profile,
        )
        artifact_decision = procedural_artifact_decision(
            workflow_profile=workflow_profile,
            procedural_lifecycle=procedural_lifecycle,
            procedural_memory_state=procedural_memory_state,
            memory_review_status=memory_review_status,
        )
        if not artifact_decision.eligible:
            return None
        artifact_key = f"{artifact_route}::{workflow_profile}"
        content_signature = "::".join(
            [
                deliberative_plan.plan_summary or "",
                deliberative_plan.smallest_safe_next_action or "",
                *deliberative_plan.steps[:3],
            ]
        )
        matching = [
            item
            for item in previous_artifacts
            if isinstance(item, dict) and item.get("artifact_key") == artifact_key
        ]
        latest = (
            max(
                matching,
                key=lambda item: int(item.get("version", 0) or 0),
            )
            if matching
            else None
        )
        if latest is not None and latest.get("content_signature") == content_signature:
            version = int(latest.get("version", 1) or 1)
        else:
            version = (
                max(
                    [int(item.get("version", 0) or 0) for item in matching],
                    default=0,
                )
                + 1
            )
        artifact_ref = f"artifact://procedural/{artifact_route}/{workflow_profile}/v{version}"
        return {
            "artifact_ref": artifact_ref,
            "artifact_key": artifact_key,
            "artifact_kind": artifact_decision.artifact_kind,
            "artifact_status": artifact_decision.artifact_status,
            "reuse_scope": artifact_decision.reuse_scope,
            "through_core_only": artifact_decision.through_core_only,
            "versioning_mode": artifact_decision.versioning_mode,
            "version": version,
            "workflow_profile": workflow_profile,
            "primary_route": artifact_route,
            "summary": (
                deliberative_plan.smallest_safe_next_action
                or deliberative_plan.plan_summary
                or deliberative_plan.goal
            ),
            "steps_snapshot": list(deliberative_plan.steps[:3]),
            "source_mission_id": str(contract.mission_id) if contract.mission_id else None,
            "source_request_id": str(contract.request_id),
            "content_signature": content_signature,
            "updated_at": self.now(),
        }

    @staticmethod
    def _procedural_artifact_memory_signals(
        deliberative_plan: DeliberativePlanContract,
        *,
        workflow_profile: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        procedural_lifecycle = deliberative_plan.procedural_memory_lifecycle
        procedural_memory_state = deliberative_plan.procedural_memory_state
        memory_review_status = deliberative_plan.memory_review_status
        if workflow_profile is None:
            return procedural_lifecycle, procedural_memory_state, memory_review_status
        if procedural_lifecycle is None:
            procedural_lifecycle = "consolidating"
        if procedural_memory_state is None:
            support_signals = memory_lifecycle_support_signals(
                semantic_lifecycle=None,
                procedural_lifecycle=procedural_lifecycle,
            )
            procedural_memory_state = support_signals["procedural_memory_state"]
        if memory_review_status is None:
            if procedural_lifecycle == "aging":
                memory_review_status = "review_recommended"
            elif procedural_lifecycle == "consolidating":
                memory_review_status = "monitor"
            else:
                memory_review_status = "stable"
        return procedural_lifecycle, procedural_memory_state, memory_review_status

    @staticmethod
    def _procedural_artifact_route_context(
        deliberative_plan: DeliberativePlanContract,
    ) -> tuple[str, str | None]:
        if deliberative_plan.primary_route is not None:
            return (
                deliberative_plan.primary_route,
                deliberative_plan.route_workflow_profile
                or deliberative_plan.recommended_task_type
                or "assisted_execution_workflow",
            )
        route_payload = primary_route_payload(deliberative_plan.active_domains)
        if route_payload is not None:
            route_name, payload = route_payload
            return (
                route_name,
                str(payload.get("workflow_profile") or deliberative_plan.recommended_task_type)
                if payload.get("workflow_profile") or deliberative_plan.recommended_task_type
                else "assisted_execution_workflow",
            )
        return (
            "baseline_runtime",
            deliberative_plan.route_workflow_profile
            or deliberative_plan.recommended_task_type
            or "assisted_execution_workflow",
        )

    @staticmethod
    def _merge_procedural_artifact(
        *,
        existing_artifacts: list[dict[str, object]],
        artifact: dict[str, object],
    ) -> list[dict[str, object]]:
        filtered = [
            item
            for item in existing_artifacts
            if not (
                isinstance(item, dict)
                and item.get("artifact_key") == artifact.get("artifact_key")
                and item.get("version") == artifact.get("version")
            )
        ]
        filtered.append(artifact)
        return filtered[-5:]

    @staticmethod
    def _latest_procedural_artifact(
        artifacts: list[dict[str, object]],
    ) -> dict[str, object] | None:
        normalized = [item for item in artifacts if isinstance(item, dict)]
        if not normalized:
            return None
        return max(
            normalized,
            key=lambda item: int(item.get("version", 0) or 0),
        )

    def _build_continuity_checkpoint(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract,
        governance_decision: PermissionDecision | None,
        continuity_snapshot: SessionContinuitySnapshot,
        ecosystem_state: EcosystemOperationalStateContract | None,
        surface_state: SurfaceContinuityState,
        objective_state: ProjectObjectiveContinuityState,
    ) -> StoredContinuityCheckpoint:
        continuity_action = deliberative_plan.continuity_action or "continuar"
        checkpoint_status = self._continuity_checkpoint_status(
            continuity_action=continuity_action,
            governance_decision=governance_decision,
        )
        return StoredContinuityCheckpoint(
            checkpoint_id=f"cck-{uuid4().hex[:8]}",
            session_id=str(contract.session_id),
            mission_id=str(contract.mission_id) if contract.mission_id else None,
            continuity_action=continuity_action,
            continuity_source=deliberative_plan.continuity_source,
            target_mission_id=(
                str(deliberative_plan.continuity_target_mission_id)
                if deliberative_plan.continuity_target_mission_id
                else None
            ),
            target_goal=deliberative_plan.continuity_target_goal,
            checkpoint_status=checkpoint_status,
            checkpoint_summary=continuity_snapshot.continuity_brief,
            origin_request_id=str(contract.request_id),
            replay_summary=self._continuity_replay_summary(
                contract=contract,
                plan=deliberative_plan,
                continuity_snapshot=continuity_snapshot,
                checkpoint_status=checkpoint_status,
            ),
            ecosystem_state_status=(
                ecosystem_state.ecosystem_state_status if ecosystem_state else None
            ),
            active_work_items=(list(ecosystem_state.active_work_items) if ecosystem_state else []),
            active_artifact_refs=(
                list(ecosystem_state.active_artifact_refs) if ecosystem_state else []
            ),
            open_checkpoint_refs=(
                list(ecosystem_state.open_checkpoint_refs) if ecosystem_state else []
            ),
            surface_presence=(list(ecosystem_state.surface_presence) if ecosystem_state else []),
            ecosystem_state_summary=(ecosystem_state.state_summary if ecosystem_state else None),
            linked_surface_ids=list(surface_state.linked_surface_ids),
            active_surface_id=surface_state.active_surface_id,
            last_surface_id=surface_state.last_surface_id,
            surface_continuity_status=surface_state.surface_continuity_status,
            surface_identity_conflict_flags=list(surface_state.surface_identity_conflict_flags),
            project_ref=objective_state.project_ref,
            objective_ref=objective_state.objective_ref,
            work_item_refs=list(objective_state.work_item_refs),
            checkpoint_refs=list(objective_state.checkpoint_refs),
            artifact_refs=list(objective_state.artifact_refs),
            objective_status=objective_state.objective_status,
            next_action_ref=objective_state.next_action_ref,
            updated_at=self.now(),
        )

    def _build_continuity_replay(
        self,
        *,
        checkpoint: StoredContinuityCheckpoint,
        continuity_snapshot: SessionContinuitySnapshot | None,
        mission_state: MissionStateContract | None,
    ) -> ContinuityReplayContract:
        ecosystem_policy = ecosystem_continuity_policy(
            ecosystem_state_status=checkpoint.ecosystem_state_status,
            active_work_items=checkpoint.active_work_items,
            active_artifact_refs=checkpoint.active_artifact_refs,
            open_checkpoint_refs=checkpoint.open_checkpoint_refs,
            surface_presence=checkpoint.surface_presence,
        )
        replay_status = self._continuity_replay_status(checkpoint.checkpoint_status)
        base_recovery_mode = self._continuity_recovery_mode(
            continuity_action=checkpoint.continuity_action,
            target_mission_id=checkpoint.target_mission_id,
            checkpoint_status=checkpoint.checkpoint_status,
        )
        recovery_mode = (
            ecosystem_policy.recovery_mode
            if ecosystem_policy.should_persist
            and checkpoint.checkpoint_status == "ready"
            and ecosystem_policy.recovery_mode != "not_applicable"
            else base_recovery_mode
        )
        resume_point = self._continuity_resume_point(
            checkpoint=checkpoint,
            continuity_snapshot=continuity_snapshot,
            mission_state=mission_state,
        )
        ecosystem_resume_point = self._ecosystem_resume_point(
            active_work_items=checkpoint.active_work_items,
            active_artifact_refs=checkpoint.active_artifact_refs,
            open_checkpoint_refs=checkpoint.open_checkpoint_refs,
        )
        if (
            ecosystem_policy.should_persist
            and checkpoint.checkpoint_status == "ready"
            and ecosystem_resume_point is not None
        ):
            resume_point = ecosystem_resume_point
        return ContinuityReplayContract(
            checkpoint_id=checkpoint.checkpoint_id,
            session_id=SessionId(checkpoint.session_id),
            replay_status=replay_status,
            recovery_mode=recovery_mode,
            resume_point=resume_point,
            checkpoint_status=checkpoint.checkpoint_status,
            continuity_action=checkpoint.continuity_action,
            updated_at=checkpoint.updated_at,
            mission_id=MissionId(checkpoint.mission_id) if checkpoint.mission_id else None,
            target_mission_id=(
                MissionId(checkpoint.target_mission_id) if checkpoint.target_mission_id else None
            ),
            target_goal=checkpoint.target_goal,
            origin_request_id=self._request_id_or_none(checkpoint.origin_request_id),
            replay_summary=checkpoint.replay_summary,
            ecosystem_state_status=checkpoint.ecosystem_state_status,
            active_work_items=list(checkpoint.active_work_items),
            active_artifact_refs=list(checkpoint.active_artifact_refs),
            open_checkpoint_refs=list(checkpoint.open_checkpoint_refs),
            surface_presence=list(checkpoint.surface_presence),
            ecosystem_state_summary=checkpoint.ecosystem_state_summary,
            linked_surface_ids=list(checkpoint.linked_surface_ids),
            active_surface_id=checkpoint.active_surface_id,
            last_surface_id=checkpoint.last_surface_id,
            surface_continuity_status=checkpoint.surface_continuity_status,
            surface_identity_conflict_flags=list(checkpoint.surface_identity_conflict_flags),
            requires_manual_resume=replay_status != "resumable",
        )

    def _build_continuity_pause(
        self,
        *,
        replay: ContinuityReplayContract,
        resolution: StoredContinuityPauseResolution | None,
    ) -> ContinuityPauseContract:
        pause_status = "pending"
        if resolution is not None:
            pause_status = "approved" if resolution.resolution_status == "approved" else "rejected"
        elif replay.replay_status == "contained":
            pause_status = "contained"
        elif replay.replay_status == "awaiting_validation":
            pause_status = "awaiting_validation"
        return ContinuityPauseContract(
            pause_id=f"cpause-{replay.checkpoint_id}",
            session_id=replay.session_id,
            checkpoint_id=replay.checkpoint_id,
            pause_status=pause_status,
            recovery_mode=replay.recovery_mode,
            resume_point=replay.resume_point,
            pause_reason=replay.replay_summary or replay.resume_point,
            issued_at=replay.updated_at,
            resolved_at=resolution.resolved_at if resolution else None,
            resolution_status=resolution.resolution_status if resolution else None,
            resolved_by=resolution.resolved_by if resolution else None,
            resolution_note=resolution.resolution_note if resolution else None,
            requires_human_input=replay.requires_manual_resume and resolution is None,
        )

    def _build_continuity_context(
        self,
        contract: InputContract,
        current_mission_state: MissionStateContract,
    ) -> MissionContinuityContextContract | None:
        related_states = self.repository.list_related_mission_states(
            session_id=str(contract.session_id),
            exclude_mission_id=str(contract.mission_id),
            limit=3,
        )
        candidates: list[MissionContinuityCandidateContract] = []
        for related_state in related_states:
            candidate = self._build_related_candidate(current_mission_state, related_state)
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=self._candidate_sort_key, reverse=True)
        active_priority = self._active_priority_score(current_mission_state)
        top_related = candidates[0].priority_score if candidates else None
        recommended_action, recommended_reason = self._resolve_continuity_recommendation(
            active_priority=active_priority,
            top_candidate=candidates[0] if candidates else None,
            has_open_loops=bool(current_mission_state.open_loops),
        )
        return MissionContinuityContextContract(
            active_mission_id=contract.mission_id,
            active_mission_goal=current_mission_state.mission_goal,
            active_continuity_brief=current_mission_state.identity_continuity_brief,
            related_candidates=candidates[:2],
            recommended_action=recommended_action,
            recommended_reason=recommended_reason,
            active_priority_score=active_priority,
            related_priority_score=top_related,
        )

    def _build_continuity_context_for_new_mission(
        self,
        contract: InputContract,
    ) -> MissionContinuityContextContract | None:
        related_states = self.repository.list_related_mission_states(
            session_id=str(contract.session_id),
            exclude_mission_id=str(contract.mission_id),
            limit=3,
        )
        current_tokens = self._meaningful_tokens(contract.content)
        candidates: list[MissionContinuityCandidateContract] = []
        for related_state in related_states:
            token_overlap = sorted(
                current_tokens.intersection(self._meaningful_tokens(related_state.mission_goal))
            )
            if not token_overlap:
                continue
            priority = 0.55 + (0.15 if related_state.open_loops else 0.0)
            confidence = 0.55 + (0.15 if len(token_overlap) > 1 else 0.0)
            reasons = [f"objetivo_relacionado={','.join(token_overlap[:2])}"]
            if related_state.open_loops:
                reasons.append(f"loop_relacionado={related_state.open_loops[0]}")
            candidates.append(
                MissionContinuityCandidateContract(
                    mission_id=related_state.mission_id,
                    relation_type="same_session_related_mission",
                    mission_goal=related_state.mission_goal,
                    continuity_reason="; ".join(reasons),
                    priority_score=min(priority, 1.0),
                    confidence_score=min(confidence, 1.0),
                    open_loops=list(related_state.open_loops[:2]),
                    semantic_focus=list(related_state.semantic_focus[:3]),
                    last_recommendation=related_state.last_recommendation,
                )
            )
        candidates.sort(key=self._candidate_sort_key, reverse=True)
        if not candidates:
            return None
        top_related = candidates[0].priority_score
        recommended_action = (
            "retomar_missao_relacionada" if top_related >= 0.7 else "seguir_novo_pedido"
        )
        recommended_reason = (
            f"melhor_missao_relacionada={candidates[0].mission_id}; prioridade={top_related:.2f}"
            if recommended_action == "retomar_missao_relacionada"
            else "sem evidencia suficiente para herdar continuidade de missao relacionada"
        )
        return MissionContinuityContextContract(
            active_mission_id=contract.mission_id,
            active_mission_goal=contract.content,
            active_continuity_brief=None,
            related_candidates=candidates[:2],
            recommended_action=recommended_action,
            recommended_reason=recommended_reason,
            active_priority_score=0.0,
            related_priority_score=top_related,
        )

    def _build_related_candidate(
        self,
        current_mission_state: MissionStateContract,
        related_state: MissionStateContract,
    ) -> MissionContinuityCandidateContract | None:
        current_focus = set(current_mission_state.semantic_focus)
        related_focus = set(related_state.semantic_focus)
        shared_focus = sorted(current_focus.intersection(related_focus))
        token_overlap = sorted(
            self._meaningful_tokens(current_mission_state.mission_goal).intersection(
                self._meaningful_tokens(related_state.mission_goal)
            )
        )
        if not shared_focus and not token_overlap and not related_state.open_loops:
            return None

        priority = 0.35
        confidence = 0.4
        reasons: list[str] = []
        if shared_focus:
            priority += 0.25
            confidence += 0.2
            reasons.append(f"foco_compartilhado={','.join(shared_focus[:2])}")
        if token_overlap:
            priority += 0.2
            confidence += 0.2
            reasons.append(f"objetivo_relacionado={','.join(token_overlap[:2])}")
        if related_state.open_loops:
            priority += 0.15
            confidence += 0.1
            reasons.append(f"loop_relacionado={related_state.open_loops[0]}")
        if (
            current_mission_state.last_decision_frame
            and current_mission_state.last_decision_frame == related_state.last_decision_frame
        ):
            priority += 0.05
            reasons.append(f"frame_compartilhado={current_mission_state.last_decision_frame}")

        return MissionContinuityCandidateContract(
            mission_id=related_state.mission_id,
            relation_type="same_session_related_mission",
            mission_goal=related_state.mission_goal,
            continuity_reason="; ".join(reasons[:3]) or "continuidade_relacionada_detectada",
            priority_score=min(priority, 1.0),
            confidence_score=min(confidence, 1.0),
            open_loops=list(related_state.open_loops[:2]),
            semantic_focus=list(related_state.semantic_focus[:3]),
            last_recommendation=related_state.last_recommendation,
        )

    @staticmethod
    def _candidate_sort_key(
        candidate: MissionContinuityCandidateContract,
    ) -> tuple[float, float, int, str]:
        return (
            candidate.priority_score,
            candidate.confidence_score,
            len(candidate.open_loops),
            str(candidate.mission_id),
        )

    @staticmethod
    def _active_priority_score(current_mission_state: MissionStateContract) -> float:
        if current_mission_state.open_loops:
            return 0.95
        if (
            current_mission_state.identity_continuity_brief
            or current_mission_state.last_recommendation
            or current_mission_state.semantic_brief
        ):
            return 0.72
        return 0.0

    @staticmethod
    def _resolve_continuity_recommendation(
        *,
        active_priority: float,
        top_candidate: MissionContinuityCandidateContract | None,
        has_open_loops: bool,
    ) -> tuple[str, str]:
        if has_open_loops:
            return (
                "priorizar_loop_ativo",
                "existem loops abertos na missao ativa com prioridade superior "
                "a qualquer continuidade relacionada",
            )
        if top_candidate is None:
            if active_priority > 0:
                return (
                    "priorizar_missao_ativa",
                    "nao ha missao relacionada suficientemente forte; manter a "
                    "missao ativa como ancora principal",
                )
            return (
                "seguir_novo_pedido",
                "nao ha missao relacionada suficientemente forte e a ancora ativa esta fraca",
            )

        if active_priority >= top_candidate.priority_score + 0.05:
            return (
                "priorizar_missao_ativa",
                "missao ativa supera a relacionada "
                f"{top_candidate.mission_id} no desempate de continuidade",
            )
        if top_candidate.priority_score >= max(active_priority, 0.7):
            return (
                "retomar_missao_relacionada",
                "missao relacionada "
                f"{top_candidate.mission_id} venceu o ranking de continuidade "
                f"com prioridade {top_candidate.priority_score:.2f}",
            )
        if active_priority > 0:
            return (
                "priorizar_missao_ativa",
                "manter a missao ativa como ancora principal por falta de "
                "evidencia suficiente para migrar continuidade",
            )
        return (
            "seguir_novo_pedido",
            "seguir o novo pedido porque a continuidade relacionada ainda nao "
            "venceu o limiar de retomada",
        )

    def _build_semantic_brief(
        self,
        *,
        mission_goal: str,
        intent: str,
        semantic_focus: list[str],
        deliberative_plan: DeliberativePlanContract | None,
        previous: MissionStateContract | None,
    ) -> str:
        focus_hint = ", ".join(semantic_focus[:3]) if semantic_focus else intent
        if deliberative_plan:
            recommendation = deliberative_plan.plan_summary
            return f"objetivo={mission_goal}; foco={focus_hint}; recomendacao={recommendation}"
        if previous and previous.semantic_brief:
            return previous.semantic_brief
        return (
            f"objetivo={mission_goal}; foco={focus_hint}; "
            "recomendacao=persistir continuidade segura"
        )

    @staticmethod
    def _build_identity_continuity_brief(
        *,
        mission_goal: str,
        open_loops: list[str],
        decision_frame: str,
        recommendation: str | None,
        previous: MissionStateContract | None,
    ) -> str:
        focus = open_loops[0] if open_loops else "consolidar a proxima decisao segura"
        if recommendation:
            return (
                f"objetivo={mission_goal}; prioridade={focus}; "
                f"frame={decision_frame}; ultimo_ajuste={recommendation}"
            )
        if previous and previous.identity_continuity_brief:
            return previous.identity_continuity_brief
        return f"objetivo={mission_goal}; prioridade={focus}; frame={decision_frame}"

    @staticmethod
    def _build_session_continuity_brief(
        *,
        continuity_action: str,
        plan: DeliberativePlanContract,
        governance_decision: PermissionDecision | None,
        anchor_goal: str,
        previous: SessionContinuitySnapshot | None,
    ) -> str:
        loop_focus = plan.open_loops[0] if plan.open_loops else None
        if continuity_action == "retomar" and plan.continuity_target_goal:
            return (
                "sessao retoma continuidade relacionada em "
                f"'{plan.continuity_target_goal}', preservando rastreabilidade do escopo atual"
            )
        if continuity_action == "encerrar":
            if loop_focus:
                return (
                    f"sessao entra em fechamento controlado de '{anchor_goal}', "
                    f"encerrando '{loop_focus}'"
                )
            return f"sessao entra em fechamento controlado de '{anchor_goal}'"
        if continuity_action == "reformular":
            if governance_decision == PermissionDecision.DEFER_FOR_VALIDATION:
                return (
                    f"sessao entrou em reformulacao governada de '{anchor_goal}' "
                    "e aguarda validacao explicita"
                )
            return f"sessao reformula o objetivo ativo '{anchor_goal}' de forma explicita"
        if continuity_action == "continuar":
            if loop_focus:
                return (
                    f"sessao segue ancorada em '{anchor_goal}', com continuidade ativa em "
                    f"'{loop_focus}'"
                )
            return f"sessao segue ancorada em '{anchor_goal}'"
        if previous is not None:
            return previous.continuity_brief
        return f"sessao preserva continuidade segura em '{anchor_goal}'"

    @staticmethod
    def _continuity_checkpoint_status(
        *,
        continuity_action: str,
        governance_decision: PermissionDecision | None,
    ) -> str:
        if continuity_action == "encerrar":
            return "closed"
        if governance_decision == PermissionDecision.DEFER_FOR_VALIDATION:
            return "awaiting_validation"
        if governance_decision == PermissionDecision.BLOCK:
            return "contained"
        return "ready"

    @staticmethod
    def _continuity_replay_summary(
        *,
        contract: InputContract,
        plan: DeliberativePlanContract,
        continuity_snapshot: SessionContinuitySnapshot,
        checkpoint_status: str,
    ) -> str:
        target_goal = plan.continuity_target_goal or continuity_snapshot.anchor_goal or plan.goal
        source = plan.continuity_source or "active_mission"
        summary = (
            f"request={contract.request_id}; status={checkpoint_status}; "
            f"acao={plan.continuity_action or 'continuar'}; "
            f"fonte={source}; alvo={target_goal}"
        )
        if continuity_snapshot.ecosystem_state_summary:
            summary = f"{summary}; ecosystem={continuity_snapshot.ecosystem_state_summary}"
        return summary

    @staticmethod
    def _continuity_replay_status(checkpoint_status: str) -> str:
        if checkpoint_status == "ready":
            return "resumable"
        if checkpoint_status == "awaiting_validation":
            return "awaiting_validation"
        if checkpoint_status == "contained":
            return "contained"
        return "closed"

    @staticmethod
    def _continuity_recovery_mode(
        *,
        continuity_action: str,
        target_mission_id: str | None,
        checkpoint_status: str,
    ) -> str:
        if checkpoint_status == "awaiting_validation":
            return "governed_review"
        if checkpoint_status == "contained":
            return "contained_recovery"
        if continuity_action == "retomar" and target_mission_id:
            return "resume_related_mission"
        if continuity_action == "reformular":
            return "resume_reformulation"
        if continuity_action == "encerrar":
            return "resume_closeout"
        return "resume_active_mission"

    @staticmethod
    def _continuity_resume_point(
        *,
        checkpoint: StoredContinuityCheckpoint,
        continuity_snapshot: SessionContinuitySnapshot | None,
        mission_state: MissionStateContract | None,
    ) -> str:
        if checkpoint.continuity_action == "retomar" and checkpoint.target_goal:
            return f"retomar:{checkpoint.target_goal}"
        if checkpoint.continuity_action == "reformular":
            goal = checkpoint.target_goal or (
                continuity_snapshot.anchor_goal if continuity_snapshot else None
            )
            return f"reformular:{goal or 'revisar_direcao_ativa'}"
        if checkpoint.continuity_action == "encerrar":
            goal = checkpoint.target_goal or (
                continuity_snapshot.anchor_goal if continuity_snapshot else None
            )
            return f"encerrar:{goal or 'fechar_continuidade_ativa'}"
        if mission_state and mission_state.open_loops:
            return f"continuar:{mission_state.open_loops[0]}"
        anchor_goal = (
            continuity_snapshot.anchor_goal if continuity_snapshot else checkpoint.target_goal
        )
        return f"continuar:{anchor_goal or checkpoint.checkpoint_summary}"

    @staticmethod
    def _append_pause_resolution_summary(
        replay_summary: str | None,
        resolution: StoredContinuityPauseResolution,
    ) -> str:
        summary = replay_summary or "checkpoint_sem_resumo"
        return (
            f"{summary}; resolucao={resolution.resolution_status}; "
            f"ator={resolution.resolved_by or 'unknown'}; nota={resolution.resolution_note}"
        )

    @staticmethod
    def _ecosystem_resume_point(
        *,
        active_work_items: list[str],
        active_artifact_refs: list[str],
        open_checkpoint_refs: list[str],
    ) -> str | None:
        if open_checkpoint_refs:
            return f"ecosystem_checkpoint:{open_checkpoint_refs[0]}"
        if active_work_items:
            return f"ecosystem_work_item:{active_work_items[0]}"
        if active_artifact_refs:
            return f"ecosystem_artifact:{active_artifact_refs[0]}"
        return None

    @staticmethod
    def _request_id_or_none(value: str | None) -> RequestId | None:
        return RequestId(value) if value else None

    @staticmethod
    def _bounded_memory_review_ref(value: str) -> bool:
        return (
            bool(value)
            and len(value) <= 160
            and fullmatch(
                r"[A-Za-z0-9:/._-]+",
                value,
            )
            is not None
        )

    @staticmethod
    def _memory_lifecycle_candidate(
        *,
        maintenance_action: str,
        target_scope: str,
        target_refs: list[str],
        reason: str,
        evidence_refs: list[str],
        rollback_plan_ref: str,
        generated_at: str,
    ) -> MemoryLifecycleCandidateContract:
        identity = "|".join([maintenance_action, target_scope, *target_refs, *evidence_refs])
        candidate_id = (
            "memory-lifecycle-candidate://"
            f"{maintenance_action}/{sha256(identity.encode()).hexdigest()[:16]}"
        )
        return MemoryLifecycleCandidateContract(
            candidate_id=candidate_id,
            maintenance_action=maintenance_action,
            target_scope=target_scope,
            target_refs=target_refs,
            reason=reason,
            evidence_refs=evidence_refs,
            rollback_plan_ref=rollback_plan_ref,
            review_status="needs_review",
            execution_status="not_executed",
            generated_at=generated_at,
            human_review_required=True,
            automatic_execution_allowed=False,
            core_mutation_allowed=False,
        )

    @staticmethod
    def _candidate_with_review(
        candidate: MemoryLifecycleCandidateContract,
        decision: MemoryLifecycleReviewDecisionContract | None,
    ) -> MemoryLifecycleCandidateContract:
        if decision is None:
            return candidate
        return replace(
            candidate,
            review_status=decision.review_status,
            last_review_decision_id=decision.review_decision_id,
            last_reviewed_by=decision.operator_ref,
            last_reviewed_at=decision.timestamp,
            execution_status="not_executed",
            automatic_execution_allowed=False,
            core_mutation_allowed=False,
        )

    @staticmethod
    def _timestamp_reached(expires_at: str, generated_at: str) -> bool:
        try:
            expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        return expires <= generated

    @staticmethod
    def _merge_unique_strings(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                if item and item not in merged:
                    merged.append(item)
        return merged

    @staticmethod
    def _bounded_operator_feedback_text(
        value: str | None,
        limit: int,
    ) -> str | None:
        if value is None:
            return None
        sanitized = "".join(
            character if ord(character) >= 32 and ord(character) != 127 else " "
            for character in str(value)
        )
        normalized = " ".join(sanitized.split()).strip()
        return normalized[:limit] or None

    @classmethod
    def _bounded_skill_values(
        cls,
        values: list[str],
        field_name: str,
        blockers: list[str],
        *,
        max_items: int = 20,
        item_limit: int = 200,
    ) -> list[str]:
        normalized = cls._merge_unique_strings(values, [])
        if len(normalized) > max_items:
            blockers.append(f"{field_name}_item_limit_exceeded")
        if any(len(item) > item_limit for item in normalized):
            blockers.append(f"{field_name}_value_limit_exceeded")
        return [item[:item_limit] for item in normalized[:max_items]]

    @staticmethod
    def _operator_feedback_summary(feedback: OperatorFeedbackContract) -> str:
        values = [
            f"feedback_id={feedback.feedback_id}",
            f"assessment={feedback.assessment}",
        ]
        if feedback.rating is not None:
            values.append(f"rating={feedback.rating}")
        if feedback.comment:
            values.append(f"comment={feedback.comment}")
        if feedback.correction:
            values.append(f"correction={feedback.correction}")
        if feedback.next_expectation:
            values.append(f"next_expectation={feedback.next_expectation}")
        return "; ".join(values)

    @staticmethod
    def _long_horizon_strategy_status(
        *,
        mission_state: MissionStateContract,
        milestone_refs: list[str],
        memory_anchor_refs: list[str],
        evidence_refs: list[str],
    ) -> str:
        if (
            mission_state.next_action_ref
            and milestone_refs
            and memory_anchor_refs
            and evidence_refs
        ):
            return "ready"
        if any(
            [
                mission_state.next_action_ref,
                milestone_refs,
                memory_anchor_refs,
                evidence_refs,
                mission_state.open_loops,
                mission_state.last_recommendation,
            ]
        ):
            return "partial"
        return "insufficient_state"

    @classmethod
    def _long_horizon_strategy_summary(
        cls,
        *,
        mission_state: MissionStateContract,
        strategy_status: str,
        milestone_refs: list[str],
        risk_refs: list[str],
    ) -> str:
        goal = cls._shorten_memory_hint(mission_state.mission_goal, limit=120)
        next_action = mission_state.next_action_ref or "missing_next_action"
        return (
            f"status={strategy_status}; goal={goal}; "
            f"milestones={len(milestone_refs)}; risks={len(risk_refs)}; "
            f"next_action={next_action}; mode=read_only_no_scheduler"
        )

    @staticmethod
    def _ecosystem_state_summary(
        *,
        active_work_items: list[str],
        active_artifact_refs: list[str],
        open_checkpoint_refs: list[str],
        surface_presence: list[str],
    ) -> str:
        return (
            f"work_items={len(active_work_items)}; "
            f"artifacts={len(active_artifact_refs)}; "
            f"open_checkpoints={len(open_checkpoint_refs)}; "
            f"surfaces={len(surface_presence)}"
        )

    @staticmethod
    def _extract_open_loops(
        deliberative_plan: DeliberativePlanContract | None,
        specialist_contributions: list[SpecialistContributionContract],
    ) -> list[str]:
        if deliberative_plan and deliberative_plan.open_loops:
            return list(deliberative_plan.open_loops[:3])
        loops: list[str] = []
        for contribution in specialist_contributions:
            for finding in contribution.findings:
                if finding.startswith("open_loop:"):
                    loop = finding.removeprefix("open_loop:").strip()
                    if loop and loop not in loops:
                        loops.append(loop)
        if not loops and deliberative_plan and deliberative_plan.continuity_action == "continuar":
            loops.append(deliberative_plan.goal)
        return loops[:3]

    @staticmethod
    def _meaningful_tokens(text: str) -> set[str]:
        return {
            token
            for token in "".join(char if char.isalnum() else " " for char in text.lower()).split()
            if len(token) > 3
        }

    @staticmethod
    def _decision_frame(deliberative_plan: DeliberativePlanContract | None) -> str:
        if not deliberative_plan:
            return "clarification"
        if deliberative_plan.recommended_task_type == "produce_analysis_brief":
            return "analysis"
        if deliberative_plan.recommended_task_type == "draft_plan":
            return "planning"
        if deliberative_plan.requires_human_validation:
            return "clarification"
        return "execution"

    def _build_user_scope_snapshot(
        self,
        contract: InputContract,
        *,
        intent: str,
        deliberative_plan: DeliberativePlanContract | None,
        governance_decision: PermissionDecision | None,
    ) -> StoredUserScopeSnapshot | None:
        if not contract.user_id:
            return None
        previous = self.repository.fetch_user_scope_snapshot(contract.user_id)
        accepted = governance_decision not in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }
        recent_intents = self._merge_recent_values(
            previous.recent_intents if previous else [],
            [intent],
            limit=4,
        )
        recent_domain_focus = self._merge_recent_values(
            previous.recent_domain_focus if previous else [],
            deliberative_plan.active_domains if accepted and deliberative_plan else [],
            limit=4,
        )
        active_mission_ids = self._merge_recent_values(
            previous.active_mission_ids if previous else [],
            [str(contract.mission_id)] if accepted and contract.mission_id else [],
            limit=3,
        )
        recent_session_ids = self._merge_recent_values(
            previous.recent_session_ids if previous else [],
            [str(contract.session_id)],
            limit=3,
        )
        interaction_count = (previous.interaction_count if previous else 0) + 1
        last_recommended_task_type = (
            deliberative_plan.recommended_task_type
            if accepted and deliberative_plan
            else (previous.last_recommended_task_type if previous else None)
        )
        continuity_preference = (
            deliberative_plan.continuity_action
            if accepted and deliberative_plan and deliberative_plan.continuity_action
            else (previous.continuity_preference if previous else None)
        )
        evidence_signals = sum(
            1
            for item in (
                len(recent_intents) >= 2,
                bool(recent_domain_focus),
                bool(active_mission_ids),
                continuity_preference is not None,
            )
            if item
        )
        context_status = (
            "recoverable" if interaction_count >= 2 and evidence_signals >= 2 else "seeded"
        )
        brief_parts = [f"intents={','.join(recent_intents[:3])}"]
        if recent_domain_focus:
            brief_parts.append(f"domains={','.join(recent_domain_focus[:3])}")
        if active_mission_ids:
            brief_parts.append(f"missions={','.join(active_mission_ids[:2])}")
        if continuity_preference:
            brief_parts.append(f"continuity={continuity_preference}")
        if last_recommended_task_type:
            brief_parts.append(f"task_type={last_recommended_task_type}")
        memory_refs = [f"memory://user/{contract.user_id}"]
        if active_mission_ids:
            memory_refs.extend(f"memory://mission/{item}" for item in active_mission_ids[:2])
        return StoredUserScopeSnapshot(
            user_id=contract.user_id,
            context_status=context_status,
            interaction_count=interaction_count,
            user_context_brief="; ".join(brief_parts),
            recent_intents=recent_intents,
            recent_domain_focus=recent_domain_focus,
            active_mission_ids=active_mission_ids,
            recent_session_ids=recent_session_ids,
            last_recommended_task_type=last_recommended_task_type,
            continuity_preference=continuity_preference,
            memory_refs=memory_refs,
            updated_at=self.now(),
        )

    @staticmethod
    def _user_scope_contract_from_snapshot(
        snapshot: StoredUserScopeSnapshot,
    ) -> UserScopeContextContract:
        return UserScopeContextContract(
            user_id=snapshot.user_id,
            context_status=snapshot.context_status,
            interaction_count=snapshot.interaction_count,
            user_context_brief=snapshot.user_context_brief,
            recent_intents=list(snapshot.recent_intents),
            recent_domain_focus=list(snapshot.recent_domain_focus),
            active_mission_ids=list(snapshot.active_mission_ids),
            recent_session_ids=list(snapshot.recent_session_ids),
            last_recommended_task_type=snapshot.last_recommended_task_type,
            continuity_preference=snapshot.continuity_preference,
            memory_refs=list(snapshot.memory_refs),
        )

    @staticmethod
    def _tracked_only_user_scope_context(user_id: str) -> UserScopeContextContract:
        return UserScopeContextContract(
            user_id=user_id,
            context_status="tracked_only",
            interaction_count=0,
            memory_refs=[f"memory://user/{user_id}"],
        )

    @staticmethod
    def _merge_recent_values(
        existing: list[str],
        incoming: list[str],
        *,
        limit: int,
    ) -> list[str]:
        merged: list[str] = []
        for item in [*incoming, *existing]:
            if item and item not in merged:
                merged.append(item)
        return merged[:limit]

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
