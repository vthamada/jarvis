"""Persistent memory service backed by canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from uuid import uuid4

from memory_service.repository import (
    SessionContinuitySnapshot,
    StoredContinuityCheckpoint,
    StoredContinuityPauseResolution,
    StoredSpecialistSharedMemory,
    StoredTurn,
    build_memory_repository,
    continuity_checkpoint_to_contract,
)
from shared.contracts import (
    ContinuityCheckpointContract,
    ContinuityPauseContract,
    ContinuityReplayContract,
    DeliberativePlanContract,
    InputContract,
    MemoryRecordContract,
    MemoryRecoveryContract,
    MissionContinuityCandidateContract,
    MissionContinuityContextContract,
    MissionStateContract,
    SpecialistContributionContract,
    SpecialistSharedMemoryContextContract,
)
from shared.domain_registry import resolve_route
from shared.memory_registry import (
    DEFAULT_MEMORY_SCOPES,
    SHARED_MEMORY_CLASSES,
    default_priority_rules,
    specialist_memory_policy_payload,
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
    session_context: list[str]
    mission_hints: list[str]
    plan_hints: list[str]
    continuity_context: MissionContinuityContextContract | None = None

    @property
    def recovered_items(self) -> list[str]:
        return [*self.session_context, *self.mission_hints, *self.plan_hints]


@dataclass
class MemoryRecordResult:
    """Structured result for memory recording."""

    record_contract: MemoryRecordContract


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
            session_context,
            mission_hints,
            plan_hints,
            continuity_context,
        ) = self._compose_recovered_items(contract, recovery_contract.max_items or 4)
        return MemoryRecoveryResult(
            recovery_contract=recovery_contract,
            session_context=session_context,
            mission_hints=mission_hints,
            plan_hints=plan_hints,
            continuity_context=continuity_context,
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
    ) -> MemoryRecordResult:
        """Persist a minimal episodic entry and refresh contextual continuity."""

        specialist_contributions = specialist_contributions or []
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
        )
        if continuity_snapshot is not None:
            self.repository.upsert_session_continuity(continuity_snapshot)
            self.repository.upsert_continuity_checkpoint(
                self._build_continuity_checkpoint(
                    contract,
                    deliberative_plan=deliberative_plan,
                    governance_decision=governance_decision,
                    continuity_snapshot=continuity_snapshot,
                )
            )
        if contract.mission_id:
            mission_state = self._build_mission_state(
                contract,
                record_contract.memory_record_id,
                intent,
                deliberative_plan,
                open_loops=open_loops,
                decision_frame=decision_frame,
                governance_decision=governance_decision,
            )
            if mission_state is not None:
                self.repository.upsert_mission_state(mission_state)
        return MemoryRecordResult(record_contract=record_contract)

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
        contexts: dict[str, SpecialistSharedMemoryContextContract] = {}
        for specialist_hint in specialist_hints:
            context = self._build_specialist_shared_memory_context(
                specialist_type=specialist_hint,
                continuity_mode=continuity_mode,
                mission_state=mission_state,
                related_states=related_states,
                active_domains=active_domains or [],
            )
            contexts[specialist_hint] = context
            self.repository.upsert_specialist_shared_memory(
                StoredSpecialistSharedMemory(
                    session_id=session_id,
                    specialist_type=specialist_hint,
                    sharing_mode=context.sharing_mode,
                    continuity_mode=context.continuity_mode,
                    shared_memory_brief=context.shared_memory_brief,
                    write_policy=context.write_policy,
                    source_mission_id=str(context.source_mission_id)
                    if context.source_mission_id
                    else None,
                    source_mission_goal=context.source_mission_goal,
                    consumer_mode=context.consumer_mode,
                    mission_context_brief=context.mission_context_brief,
                    domain_context_brief=context.domain_context_brief,
                    continuity_context_brief=context.continuity_context_brief,
                    related_mission_ids=[str(item) for item in context.related_mission_ids],
                    memory_refs=list(context.memory_refs),
                    memory_class_policies=dict(context.memory_class_policies),
                    consumed_memory_classes=list(context.consumed_memory_classes),
                    memory_write_policies=dict(context.memory_write_policies),
                    semantic_focus=list(context.semantic_focus),
                    open_loops=list(context.open_loops),
                    last_recommendation=context.last_recommendation,
                    domain_mission_link_reason=context.domain_mission_link_reason,
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

        return self.repository.fetch_specialist_shared_memory(
            session_id=session_id,
            specialist_type=specialist_type,
        )

    def _compose_recovered_items(
        self,
        contract: InputContract,
        limit: int,
    ) -> tuple[list[str], list[str], list[str], MissionContinuityContextContract | None]:
        session_context: list[str] = []
        continuity_hints: list[str] = []
        mission_hints: list[str] = []
        plan_hints: list[str] = []
        continuity_context: MissionContinuityContextContract | None = None
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
        continuity_replay = self.get_session_continuity_replay(str(contract.session_id))
        if continuity_replay:
            continuity_hints.append(f"continuity_replay_status={continuity_replay.replay_status}")
            continuity_hints.append(f"continuity_recovery_mode={continuity_replay.recovery_mode}")
            continuity_hints.append(f"continuity_resume_point={continuity_replay.resume_point}")
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
        final_session_context = list(session_context[-limit:])
        if summary and not any(
            item.startswith("context_summary=") for item in final_session_context
        ):
            final_session_context.insert(0, f"context_summary={summary}")
        for hint in continuity_hints:
            if hint not in final_session_context:
                final_session_context.append(hint)
        return final_session_context, mission_hints[:12], plan_hints[-2:], continuity_context

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
    ) -> SpecialistSharedMemoryContextContract:
        related_mission_ids = [state.mission_id for state in related_states[:2]]
        memory_refs: list[str] = []
        semantic_focus: list[str] = []
        open_loops: list[str] = []
        shared_memory_classes = list(SHARED_MEMORY_CLASSES)
        canonical_memory_refs = [
            f"memory://{memory_class.value}" for memory_class in shared_memory_classes
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
            route = resolve_route(domain_name)
            if route is not None:
                append_unique(list(route.canonical_refs), semantic_focus, 5)
        memory_refs = [*canonical_memory_refs, *dynamic_memory_refs]
        memory_class_policies = specialist_memory_policy_payload(shared_memory_classes)
        consumed_memory_classes = [memory_class.value for memory_class in shared_memory_classes]
        memory_write_policies = {
            memory_class_name: str(policy.get("write_policy", "through_core_only"))
            for memory_class_name, policy in memory_class_policies.items()
        }

        source_goal = mission_state.mission_goal if mission_state else None
        source_mission_id = mission_state.mission_id if mission_state else None
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
            f"memory_refs={','.join(memory_refs[:4])}"
        )
        continuity_context_brief = (
            f"continuity_mode={continuity_mode} | open_loops={open_loop_summary} | "
            f"source_mission_id={source_mission_id or 'none'}"
        )
        shared_memory_brief = (
            f"specialist={specialist_type} continuidade={continuity_mode} "
            f"fonte={source_goal or 'sessao sem missao ancorada'} "
            f"relacoes={related_summary} foco={source_focus} "
            f"open_loops={open_loop_summary}"
        )
        promoted_route = next(
            (
                route
                for domain_name in active_domains
                if (route := resolve_route(domain_name)) is not None
                and route.linked_specialist_type == specialist_type
                and route.specialist_mode in {"guided", "active"}
            ),
            None,
        )
        consumer_mode = (
            "domain_guided_memory_packet"
            if promoted_route is not None
            else "baseline_shared_context"
        )
        domain_mission_link_reason = (
            f"route={promoted_route.domain_name if promoted_route else 'baseline'} "
            "canonicos="
            f"{','.join(promoted_route.canonical_refs if promoted_route else ()) or 'none'} "
            f"missao={source_goal or 'sessao_sem_missao_ancorada'}"
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
            related_mission_ids=related_mission_ids,
            memory_refs=memory_refs,
            memory_class_policies=memory_class_policies,
            consumed_memory_classes=consumed_memory_classes,
            memory_write_policies=memory_write_policies,
            semantic_focus=semantic_focus,
            open_loops=open_loops,
            last_recommendation=mission_state.last_recommendation if mission_state else None,
            domain_mission_link_reason=domain_mission_link_reason,
        )

    def _build_session_continuity_snapshot(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract | None,
        governance_decision: PermissionDecision | None,
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
    ) -> MissionStateContract | None:
        mission_id = str(contract.mission_id)
        previous = self.repository.fetch_mission_state(mission_id)
        accepted = governance_decision not in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }
        if previous is None and not accepted:
            return None

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
        return MissionStateContract(
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
            owner_context=contract.user_id or str(contract.session_id),
            updated_at=self.now(),
        )

    def _build_continuity_checkpoint(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract,
        governance_decision: PermissionDecision | None,
        continuity_snapshot: SessionContinuitySnapshot,
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
            updated_at=self.now(),
        )

    def _build_continuity_replay(
        self,
        *,
        checkpoint: StoredContinuityCheckpoint,
        continuity_snapshot: SessionContinuitySnapshot | None,
        mission_state: MissionStateContract | None,
    ) -> ContinuityReplayContract:
        replay_status = self._continuity_replay_status(checkpoint.checkpoint_status)
        recovery_mode = self._continuity_recovery_mode(
            continuity_action=checkpoint.continuity_action,
            target_mission_id=checkpoint.target_mission_id,
            checkpoint_status=checkpoint.checkpoint_status,
        )
        resume_point = self._continuity_resume_point(
            checkpoint=checkpoint,
            continuity_snapshot=continuity_snapshot,
            mission_state=mission_state,
        )
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
        return (
            f"request={contract.request_id}; status={checkpoint_status}; "
            f"acao={plan.continuity_action or 'continuar'}; "
            f"fonte={source}; alvo={target_goal}"
        )

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
    def _request_id_or_none(value: str | None) -> RequestId | None:
        return RequestId(value) if value else None

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

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
