"""Persistent memory service backed by canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from os import getenv
from uuid import uuid4

from memory_service.repository import (
    SessionContinuitySnapshot,
    StoredContinuityCheckpoint,
    StoredContinuityPauseResolution,
    StoredSpecialistSharedMemory,
    StoredTurn,
    StoredUserScopeSnapshot,
    build_memory_repository,
    continuity_checkpoint_to_contract,
)
from shared.contracts import (
    ContinuityCheckpointContract,
    ContinuityPauseContract,
    ContinuityReplayContract,
    DeliberativePlanContract,
    EcosystemOperationalStateContract,
    InputContract,
    MemoryRecordContract,
    MemoryRecoveryContract,
    MissionContinuityCandidateContract,
    MissionContinuityContextContract,
    MissionStateContract,
    OperationDispatchContract,
    OperationResultContract,
    SpecialistContributionContract,
    SpecialistSharedMemoryContextContract,
    UserScopeContextContract,
)
from shared.domain_registry import (
    primary_route_payload,
    specialist_eligible_route,
    specialist_route_payload,
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
    PermissionDecision,
    RecoveryType,
    RequestId,
    RiskLevel,
    SessionId,
    TimeWindow,
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


class MemoryService:
    """Handles contextual continuity with persistent episodic and mission memory."""

    name = "memory-service"

    def __init__(self, database_url: str | None = None) -> None:
        configured_url = database_url or getenv("DATABASE_URL")
        self.repository = build_memory_repository(configured_url)

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
                else operation_dispatch.ecosystem_state_status if operation_dispatch else None
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
                user_hints.append(
                    f"user_context_brief={user_scope_context.user_context_brief}"
                )
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
                    "user_continuity_preference="
                    f"{user_scope_context.continuity_preference}"
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
                    "ecosystem_state_status="
                    f"{session_continuity.ecosystem_state_status}"
                )
            if session_continuity.ecosystem_state_summary:
                continuity_hints.append(
                    "ecosystem_state_summary="
                    f"{session_continuity.ecosystem_state_summary}"
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
        continuity_replay = self.get_session_continuity_replay(str(contract.session_id))
        if continuity_replay:
            continuity_hints.append(f"continuity_replay_status={continuity_replay.replay_status}")
            continuity_hints.append(f"continuity_recovery_mode={continuity_replay.recovery_mode}")
            continuity_hints.append(f"continuity_resume_point={continuity_replay.resume_point}")
            if continuity_replay.ecosystem_state_status:
                continuity_hints.append(
                    "continuity_ecosystem_state_status="
                    f"{continuity_replay.ecosystem_state_status}"
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
                if mission_state.last_recommendation:
                    mission_hints.append(
                        f"mission_recommendation={mission_state.last_recommendation}"
                    )
                if mission_state.last_decision_frame:
                    mission_hints.append(f"last_decision_frame={mission_state.last_decision_frame}")
                if mission_state.ecosystem_state_status:
                    mission_hints.append(
                        f"mission_ecosystem_state_status={mission_state.ecosystem_state_status}"
                    )
                if mission_state.active_work_items:
                    mission_hints.append(
                        "mission_active_work_items="
                        f"{';'.join(mission_state.active_work_items[:3])}"
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
                latest_artifact = self._latest_procedural_artifact(
                    mission_state.related_artifacts
                )
                if latest_artifact is not None:
                    if latest_artifact.get("artifact_status") is not None:
                        plan_hints.append(
                            "procedural_artifact_status="
                            f"{latest_artifact['artifact_status']}"
                        )
                    if (
                        latest_artifact.get("artifact_ref") is not None
                        and latest_artifact.get("artifact_status") != "archivable"
                    ):
                        plan_hints.append(
                            "procedural_artifact_ref="
                            f"{latest_artifact['artifact_ref']}"
                        )
                    if (
                        latest_artifact.get("summary") is not None
                        and latest_artifact.get("artifact_status") != "archivable"
                    ):
                        plan_hints.append(
                            "procedural_artifact_summary="
                            f"{latest_artifact['summary']}"
                        )
                    if (
                        latest_artifact.get("version") is not None
                        and latest_artifact.get("artifact_status") != "archivable"
                    ):
                        plan_hints.append(
                            "procedural_artifact_version="
                            f"{latest_artifact['version']}"
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
            has_related_mission=bool(
                continuity_context and continuity_context.related_candidates
            ),
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
            latest_artifact is not None
            and latest_artifact.get("artifact_status") == "archivable"
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
                    "memory_maintenance_fallback_mode="
                    f"{memory_maintenance.fallback_mode}",
                ]
            )
        final_session_context: list[str] = []
        if (
            summary
            or live_turn_context
            or trimmed_continuity_hints
            or context_policy.cross_session_recall_status != "not_applicable"
        ):
            user_scope_label = (
                user_scope_context.context_status if user_scope_context else "none"
            )
            continuity_label = (
                session_continuity.continuity_mode if session_continuity else "none"
            )
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
                    "memory_maintenance_fallback_mode="
                    f"{memory_maintenance.fallback_mode}",
                ]
            )
            if context_policy.cross_session_recall_status != "not_applicable":
                final_session_context.append(
                    "cross_session_recall_status="
                    f"{context_policy.cross_session_recall_status}"
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
        if (
            user_scope_context is not None
            and user_scope_context.context_status not in {"tracked_only", "not_applicable"}
        ):
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
            fragments.append(
                f"mission={cls._shorten_memory_hint(mission_state.semantic_brief)}"
            )
        if (
            mission_state is not None
            and mission_state.ecosystem_state_status not in {None, "not_applicable"}
            and mission_state.ecosystem_state_summary
        ):
            fragments.append(
                "ecosystem="
                f"{cls._shorten_memory_hint(mission_state.ecosystem_state_summary)}"
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
            if (
                mission_state is None
                and not related_states
                and user_scope_snapshot is None
            ):
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
            list(promoted_route_payload.get("expected_deliverables", []))
            if promoted_route
            else []
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
        domain_compatible = not route_refs or any(
            ref in semantic_evidence for ref in route_refs
        ) or (route_name in semantic_evidence if route_name else False)
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
            previous_context.recurrent_continuity_modes
            if previous_context and allow_reuse
            else [],
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
            "reuse="
            f"{recurrent_reuse_status if stale_previous_context else 'enabled'}",
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
            active_work_items=(
                list(ecosystem_state.active_work_items) if ecosystem_state else []
            ),
            active_artifact_refs=(
                list(ecosystem_state.active_artifact_refs) if ecosystem_state else []
            ),
            open_checkpoint_refs=(
                list(ecosystem_state.open_checkpoint_refs) if ecosystem_state else []
            ),
            surface_presence=(
                list(ecosystem_state.surface_presence) if ecosystem_state else []
            ),
            ecosystem_state_summary=(ecosystem_state.state_summary if ecosystem_state else None),
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
            version = max(
                [int(item.get("version", 0) or 0) for item in matching],
                default=0,
            ) + 1
        artifact_ref = (
            f"artifact://procedural/{artifact_route}/{workflow_profile}/v{version}"
        )
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
            active_work_items=(
                list(ecosystem_state.active_work_items) if ecosystem_state else []
            ),
            active_artifact_refs=(
                list(ecosystem_state.active_artifact_refs) if ecosystem_state else []
            ),
            open_checkpoint_refs=(
                list(ecosystem_state.open_checkpoint_refs) if ecosystem_state else []
            ),
            surface_presence=(
                list(ecosystem_state.surface_presence) if ecosystem_state else []
            ),
            ecosystem_state_summary=(ecosystem_state.state_summary if ecosystem_state else None),
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
            summary = (
                f"{summary}; ecosystem={continuity_snapshot.ecosystem_state_summary}"
            )
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
    def _merge_unique_strings(*groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                if item and item not in merged:
                    merged.append(item)
        return merged

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
            "recoverable"
            if interaction_count >= 2 and evidence_signals >= 2
            else "seeded"
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
