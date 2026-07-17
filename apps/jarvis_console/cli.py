# ruff: noqa: E402
"""Minimal console surface for the JARVIS v1 baseline."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.registry import COMMAND_REGISTRY

ensure_src_paths()

from evolution_lab.service import EvolutionLabService, PostTaskReflectionInput
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import (
    ArtifactLifecycleTransitionResult,
    LongHorizonGoalStrategyResult,
    MissionProgressReportResult,
    ObjectiveTransitionResult,
    OperatorFeedbackResult,
    OrchestratorResponse,
    OrchestratorService,
    WorkItemTransitionResult,
)

from shared.contracts import (
    InputContract,
    LongHorizonGoalStrategyContract,
    LongitudinalLearningReportContract,
    MissionStateContract,
    RegressionReadinessReportContract,
    SkillEvolutionOperatorViewContract,
)
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId
from tools.longitudinal_learning_report import build_longitudinal_report
from tools.readiness_dashboard import build_repository_readiness_report

CONSOLE_SURFACE_ID = "surface://jarvis_console"
CONSOLE_SURFACE_KIND = "console"
CONSOLE_SURFACE_CAPABILITIES = ["text_input", "core_orchestrated_response"]
DEFAULT_OPERATOR_IDENTITY_REF = "operator://local_console"
DEFAULT_CANONICAL_USER_REF = "user://local_operator"
MAX_CONSOLE_FIELD_LENGTH = 500


@dataclass
class JarvisConsole:
    orchestrator: OrchestratorService

    @classmethod
    def build(
        cls,
        *,
        runtime_dir: Path | None = None,
        database_url: str | None = None,
    ) -> "JarvisConsole":
        if runtime_dir is None:
            return cls(orchestrator=OrchestratorService())
        runtime_dir.mkdir(parents=True, exist_ok=True)
        default_database_url = f"sqlite:///{(runtime_dir / 'memory.db').as_posix()}"
        resolved_database_url = database_url or default_database_url
        return cls(
            orchestrator=OrchestratorService(
                memory_service=MemoryService(database_url=resolved_database_url),
                operational_service=OperationalService(
                    artifact_dir=str(runtime_dir / "artifacts")
                ),
                observability_service=ObservabilityService(
                    database_path=str(runtime_dir / "observability.db")
                ),
            )
        )

    def ask(
        self,
        prompt: str,
        *,
        session_id: str,
        mission_id: str | None,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> OrchestratorResponse:
        contract = InputContract(
            request_id=RequestId(f"req-console-{uuid4().hex[:8]}"),
            session_id=SessionId(session_id),
            mission_id=MissionId(mission_id) if mission_id else None,
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=prompt,
            timestamp=datetime.now(UTC).isoformat(),
            surface_id=CONSOLE_SURFACE_ID,
            surface_kind=CONSOLE_SURFACE_KIND,
            surface_session_id=session_id,
            surface_capability_scope=list(CONSOLE_SURFACE_CAPABILITIES),
            operator_identity_ref=(
                operator_identity_ref or DEFAULT_OPERATOR_IDENTITY_REF
            ),
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
            surface_continuity_status="single_surface",
        )
        return self.orchestrator.handle_input(contract)

    def get_objective_state(self, *, mission_id: str) -> MissionStateContract | None:
        return self.orchestrator.inspect_objective_state(
            mission_id=mission_id,
            session_id="console-objectives",
            operator_identity_ref=DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=DEFAULT_CANONICAL_USER_REF,
        )

    def transition_objective(
        self,
        *,
        mission_id: str,
        transition: str,
        session_id: str,
        next_action_ref: str | None = None,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> ObjectiveTransitionResult:
        return self.orchestrator.transition_objective(
            mission_id=mission_id,
            transition=transition,
            session_id=session_id,
            next_action_ref=next_action_ref,
            operator_identity_ref=operator_identity_ref or DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
        )

    def transition_work_item(
        self,
        *,
        mission_id: str,
        work_item_ref: str | None,
        transition: str,
        session_id: str,
        next_action_ref: str | None = None,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> WorkItemTransitionResult:
        return self.orchestrator.transition_work_item(
            mission_id=mission_id,
            work_item_ref=work_item_ref,
            transition=transition,
            session_id=session_id,
            next_action_ref=next_action_ref,
            operator_identity_ref=operator_identity_ref or DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
        )

    def transition_artifact_lifecycle(
        self,
        *,
        mission_id: str,
        artifact_ref: str | None,
        transition: str,
        session_id: str,
        artifact_version: int | None = None,
        work_item_ref: str | None = None,
        replacement_artifact_ref: str | None = None,
        rollback_plan_ref: str | None = None,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> ArtifactLifecycleTransitionResult:
        return self.orchestrator.transition_artifact_lifecycle(
            mission_id=mission_id,
            artifact_ref=artifact_ref,
            transition=transition,
            session_id=session_id,
            artifact_version=artifact_version,
            work_item_ref=work_item_ref,
            replacement_artifact_ref=replacement_artifact_ref,
            rollback_plan_ref=rollback_plan_ref,
            operator_identity_ref=operator_identity_ref or DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
        )

    def inspect_goal_strategy(
        self,
        *,
        mission_id: str,
        session_id: str,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> LongHorizonGoalStrategyResult:
        return self.orchestrator.inspect_long_horizon_goal_strategy(
            mission_id=mission_id,
            session_id=session_id,
            operator_identity_ref=operator_identity_ref or DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
        )

    def inspect_progress_report(
        self,
        *,
        mission_id: str,
        session_id: str,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> MissionProgressReportResult:
        return self.orchestrator.inspect_mission_progress_report(
            mission_id=mission_id,
            session_id=session_id,
            operator_identity_ref=operator_identity_ref
            or DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
        )

    def record_mission_feedback(
        self,
        *,
        mission_id: str,
        session_id: str,
        assessment: str,
        rating: int | None = None,
        comment: str | None = None,
        correction: str | None = None,
        next_expectation: str | None = None,
        evidence_refs: list[str] | None = None,
        experience_id: str | None = None,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> OperatorFeedbackResult:
        return self.orchestrator.record_operator_feedback(
            mission_id=mission_id,
            session_id=session_id,
            assessment=assessment,
            rating=rating,
            comment=comment,
            correction=correction,
            next_expectation=next_expectation,
            evidence_refs=list(evidence_refs or []),
            experience_id=experience_id,
            operator_identity_ref=operator_identity_ref
            or DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
        )

    def list_procedural_playbook_candidates(
        self,
        *,
        memory_db: str | None = None,
        workflow_profile: str | None = None,
        review_status: str | None = None,
        limit: int = 5,
    ) -> list[object]:
        service = self.memory_service
        if memory_db:
            service = MemoryService(database_url=f"sqlite:///{Path(memory_db).as_posix()}")
        return service.list_procedural_playbook_candidates(
            workflow_profile=workflow_profile,
            review_status=review_status,
            limit=limit,
        )


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the minimal JARVIS console.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Execute a single prompt.")
    ask_parser.add_argument("prompt", help="Single prompt to send to JARVIS.")
    ask_parser.add_argument("--session-id", default="console-ask")
    ask_parser.add_argument("--mission-id")
    ask_parser.add_argument("--operator-identity-ref")
    ask_parser.add_argument("--canonical-user-ref")
    ask_parser.add_argument("--debug", action="store_true")

    chat_parser = subparsers.add_parser("chat", help="Run a simple multi-turn chat session.")
    chat_parser.add_argument("--session-id", default=f"console-chat-{uuid4().hex[:6]}")
    chat_parser.add_argument("--mission-id")
    chat_parser.add_argument("--message", action="append", default=[])
    chat_parser.add_argument("--operator-identity-ref")
    chat_parser.add_argument("--canonical-user-ref")
    chat_parser.add_argument("--debug", action="store_true")

    objectives_parser = subparsers.add_parser(
        "objectives",
        help="Show the persisted objective state for a mission.",
    )
    objectives_parser.add_argument("--mission-id", required=True)

    goal_strategy_parser = subparsers.add_parser(
        "goal-strategy",
        help="Show read-only long-horizon strategy for a mission.",
    )
    goal_strategy_parser.add_argument("--mission-id", required=True)
    goal_strategy_parser.add_argument("--session-id", default="console-goal-strategy")
    goal_strategy_parser.add_argument("--operator-identity-ref")
    goal_strategy_parser.add_argument("--canonical-user-ref")

    objective_parser = subparsers.add_parser(
        "objective",
        help="Apply a bounded operator transition to a mission objective.",
    )
    objective_parser.add_argument("--mission-id", required=True)
    objective_parser.add_argument("--session-id", default="console-objective")
    objective_parser.add_argument(
        "--action",
        required=True,
        choices=["resume", "pause", "block", "complete", "redefine-next-action"],
    )
    objective_parser.add_argument("--next-action-ref")
    objective_parser.add_argument("--operator-identity-ref")
    objective_parser.add_argument("--canonical-user-ref")

    work_items_parser = subparsers.add_parser(
        "work-items",
        help="Show governed work items for a mission.",
    )
    work_items_parser.add_argument("--mission-id", required=True)

    work_item_parser = subparsers.add_parser(
        "work-item",
        help="Apply a bounded operator transition to a mission work item.",
    )
    work_item_parser.add_argument("--mission-id", required=True)
    work_item_parser.add_argument("--session-id", default="console-work-item")
    work_item_parser.add_argument(
        "--action",
        required=True,
        choices=[
            "create",
            "resume",
            "pause",
            "block",
            "complete",
            "redefine-next-action",
        ],
    )
    work_item_parser.add_argument("--work-item-ref", required=True)
    work_item_parser.add_argument("--next-action-ref")
    work_item_parser.add_argument("--operator-identity-ref")
    work_item_parser.add_argument("--canonical-user-ref")

    artifacts_parser = subparsers.add_parser(
        "artifacts",
        help="Show governed living artifacts for a mission.",
    )
    artifacts_parser.add_argument("--mission-id", required=True)

    artifact_parser = subparsers.add_parser(
        "artifact",
        help="Apply a bounded lifecycle transition to a mission artifact.",
    )
    artifact_parser.add_argument("--mission-id", required=True)
    artifact_parser.add_argument("--session-id", default="console-artifact")
    artifact_parser.add_argument(
        "--action",
        required=True,
        choices=["register", "activate", "archive", "replace", "rollback"],
    )
    artifact_parser.add_argument("--artifact-ref", required=True)
    artifact_parser.add_argument("--artifact-version", type=int)
    artifact_parser.add_argument("--work-item-ref")
    artifact_parser.add_argument("--replacement-artifact-ref")
    artifact_parser.add_argument("--rollback-plan-ref")
    artifact_parser.add_argument("--operator-identity-ref")
    artifact_parser.add_argument("--canonical-user-ref")

    technology_parser = subparsers.add_parser(
        "technology-candidates",
        help="Show recent governed technology absorption candidates.",
    )
    technology_parser.add_argument("--evolution-db")
    technology_parser.add_argument("--limit", type=int, default=5)

    reflections_parser = subparsers.add_parser(
        "experience-reflections",
        help="Show recent bounded post-task experience reflections.",
    )
    reflections_parser.add_argument("--memory-db")
    reflections_parser.add_argument("--mission-id")
    reflections_parser.add_argument("--workflow-profile")
    reflections_parser.add_argument("--limit", type=int, default=5)

    playbooks_parser = subparsers.add_parser(
        "procedural-playbooks",
        help="Show bounded procedural playbook candidates without activating them.",
    )
    playbooks_parser.add_argument("--memory-db")
    playbooks_parser.add_argument("--workflow-profile")
    playbooks_parser.add_argument("--review-status")
    playbooks_parser.add_argument("--limit", type=int, default=5)

    skill_evolution_parser = subparsers.add_parser(
        "skill-evolution",
        help="Show the read-only skill evidence, review and sandbox chain.",
    )
    skill_evolution_parser.add_argument("--memory-db")
    skill_evolution_parser.add_argument("--evolution-db")
    skill_evolution_parser.add_argument("--skill-id")
    skill_evolution_parser.add_argument("--version")
    skill_evolution_parser.add_argument("--workflow-profile")
    skill_evolution_parser.add_argument("--route")
    skill_evolution_parser.add_argument("--domain")
    skill_evolution_parser.add_argument("--limit", type=int, default=10)

    review_parser = subparsers.add_parser(
        "evolution-review-queue",
        help="Show human-review evolution proposals without promoting them.",
    )
    review_parser.add_argument("--evolution-db")
    review_parser.add_argument("--limit", type=int, default=5)

    review_decision_parser = subparsers.add_parser(
        "evolution-review",
        help="Apply a human review decision to an evolution proposal.",
    )
    review_decision_parser.add_argument("--evolution-db")
    review_decision_parser.add_argument("--proposal-id", required=True)
    review_decision_parser.add_argument(
        "--action",
        required=True,
        choices=["approve", "reject", "sandbox", "needs-review", "rollback"],
    )
    review_decision_parser.add_argument(
        "--operator-ref",
        default=DEFAULT_OPERATOR_IDENTITY_REF,
    )
    review_decision_parser.add_argument("--evidence-ref", action="append", default=[])
    review_decision_parser.add_argument("--proposed-test", action="append", default=[])
    review_decision_parser.add_argument("--rollback-plan-ref")
    review_decision_parser.add_argument("--risk-acceptance")
    review_decision_parser.add_argument("--note", action="append", default=[])

    memory_review_queue_parser = subparsers.add_parser(
        "memory-review-queue",
        help="Show human-only consolidation, archive and expiration candidates.",
    )
    memory_review_queue_parser.add_argument("--memory-db")
    memory_review_queue_parser.add_argument(
        "--maintenance-action",
        choices=["consolidate", "archive", "expire"],
    )
    memory_review_queue_parser.add_argument("--review-status")
    memory_review_queue_parser.add_argument("--limit", type=int, default=10)

    memory_review_parser = subparsers.add_parser(
        "memory-review",
        help="Record a governed human decision without executing memory maintenance.",
    )
    memory_review_parser.add_argument("--memory-db")
    memory_review_parser.add_argument("--candidate-id", required=True)
    memory_review_parser.add_argument(
        "--action",
        required=True,
        choices=["approve", "reject", "needs-review", "rollback"],
    )
    memory_review_parser.add_argument(
        "--operator-ref",
        default=DEFAULT_OPERATOR_IDENTITY_REF,
    )
    memory_review_parser.add_argument("--evidence-ref", action="append", default=[])
    memory_review_parser.add_argument("--rollback-plan-ref")
    memory_review_parser.add_argument("--note", action="append", default=[])

    mission_cycle_parser = subparsers.add_parser(
        "mission-cycle",
        help="Show a read-only operator learning loop for one mission.",
    )
    mission_cycle_parser.add_argument("--mission-id", required=True)
    mission_cycle_parser.add_argument("--memory-db")
    mission_cycle_parser.add_argument("--evolution-db")
    mission_cycle_parser.add_argument("--workflow-profile")
    mission_cycle_parser.add_argument("--limit", type=int, default=5)

    dashboard_parser = subparsers.add_parser(
        "operator-dashboard",
        help="Show a read-only daily operator dashboard.",
    )
    dashboard_parser.add_argument("--mission-id")
    dashboard_parser.add_argument("--memory-db")
    dashboard_parser.add_argument("--evolution-db")
    dashboard_parser.add_argument("--workflow-profile")
    dashboard_parser.add_argument("--limit", type=int, default=5)

    readiness_parser = subparsers.add_parser(
        "readiness-dashboard",
        help="Show repository regression and readiness signals.",
    )
    readiness_parser.add_argument(
        "--run-gate",
        choices=["quick", "standard"],
        help="Explicitly refresh engineering gate evidence before reporting.",
    )
    readiness_parser.add_argument(
        "--longitudinal-report",
        help="Use an explicit MB-188 longitudinal report JSON artifact.",
    )

    learning_report_parser = subparsers.add_parser(
        "learning-report",
        help="Show read-only longitudinal outcomes by reviewed version.",
    )
    learning_report_parser.add_argument("--observability-db")
    learning_report_parser.add_argument("--memory-db")
    learning_report_parser.add_argument("--evolution-db")
    learning_report_parser.add_argument("--limit", type=int, default=100)
    learning_report_parser.add_argument("--minimum-observations", type=int, default=2)

    progress_report_parser = subparsers.add_parser(
        "progress-report",
        help="Show a synthesized read-only mission progress report.",
    )
    progress_report_parser.add_argument("--mission-id", required=True)
    progress_report_parser.add_argument(
        "--session-id",
        default="console-progress-report",
    )
    progress_report_parser.add_argument("--operator-identity-ref")
    progress_report_parser.add_argument("--canonical-user-ref")

    mission_workflow_parser = subparsers.add_parser(
        "mission-workflow",
        help="Run a governed mission and show the operator learning loop.",
    )
    mission_workflow_parser.add_argument("prompt")
    mission_workflow_parser.add_argument("--session-id", default="console-mission-workflow")
    mission_workflow_parser.add_argument("--mission-id", required=True)
    mission_workflow_parser.add_argument("--evolution-db")
    mission_workflow_parser.add_argument("--operator-identity-ref")
    mission_workflow_parser.add_argument("--canonical-user-ref")

    mission_feedback_parser = subparsers.add_parser(
        "mission-feedback",
        help="Record explicit bounded operator feedback after a mission.",
    )
    mission_feedback_parser.add_argument("--mission-id", required=True)
    mission_feedback_parser.add_argument(
        "--session-id",
        default="console-mission-feedback",
    )
    mission_feedback_parser.add_argument("--experience-id")
    mission_feedback_parser.add_argument(
        "--assessment",
        required=True,
        choices=["helpful", "partially-helpful", "not-helpful", "correction"],
    )
    mission_feedback_parser.add_argument("--rating", type=int)
    mission_feedback_parser.add_argument("--comment")
    mission_feedback_parser.add_argument("--correction")
    mission_feedback_parser.add_argument("--next-expectation")
    mission_feedback_parser.add_argument("--evidence-ref", action="append", default=[])
    mission_feedback_parser.add_argument("--evolution-db")
    mission_feedback_parser.add_argument("--operator-identity-ref")
    mission_feedback_parser.add_argument("--canonical-user-ref")

    COMMAND_REGISTRY.validate_parser_commands(
        {
            action.dest: action.help
            for action in subparsers._choices_actions
        }
    )
    return parser


def render_response(response: OrchestratorResponse, *, debug: bool) -> str:
    lines = [response.response_text]
    if debug:
        plan = response.deliberative_plan
        lines.extend(
            [
                f"request_id={response.request_id}",
                f"decision={response.governance_decision.decision.value}",
                f"continuity={plan.continuity_action or 'none'}",
                "semantic_memory_anchor_refs="
                + safe_console_list(plan.semantic_memory_anchor_refs),
                "semantic_memory_evidence_refs="
                + safe_console_list(plan.semantic_memory_evidence_refs),
                "semantic_memory_use_reason="
                + safe_console_value(plan.semantic_memory_use_reason),
                "semantic_memory_non_use_reason="
                + safe_console_value(plan.semantic_memory_non_use_reason),
            ]
        )
    return "\n".join(lines)


def safe_console_value(value: object | None) -> str:
    if value is None:
        return "none"
    normalized = str(value)
    sanitized_characters: list[str] = []
    for character in normalized:
        codepoint = ord(character)
        sanitized_characters.append(
            character if codepoint >= 32 and codepoint != 127 else " "
        )
    sanitized = "".join(sanitized_characters)
    return sanitized[:MAX_CONSOLE_FIELD_LENGTH].strip() or "none"


def safe_console_list(values: list[object]) -> str:
    rendered = [safe_console_value(value) for value in values]
    return ",".join(item for item in rendered if item != "none") or "none"


def render_objective_state(
    mission_state: MissionStateContract | None,
    *,
    mission_id: str,
) -> str:
    if mission_state is None:
        return f"No objective state found for mission_id={mission_id}"
    return "\n".join(
        [
            f"mission_id={safe_console_value(mission_state.mission_id)}",
            f"mission_goal={safe_console_value(mission_state.mission_goal)}",
            f"project_ref={safe_console_value(mission_state.project_ref)}",
            f"objective_ref={safe_console_value(mission_state.objective_ref)}",
            f"objective_status={safe_console_value(mission_state.objective_status)}",
            f"next_action_ref={safe_console_value(mission_state.next_action_ref)}",
            f"work_item_refs={safe_console_list(mission_state.work_item_refs)}",
            f"checkpoint_refs={safe_console_list(mission_state.checkpoint_refs)}",
            f"artifact_refs={safe_console_list(mission_state.artifact_refs)}",
            f"active_work_items={safe_console_list(mission_state.active_work_items)}",
            f"open_checkpoint_refs={safe_console_list(mission_state.open_checkpoint_refs)}",
        ]
    )


def render_objective_transition(result: ObjectiveTransitionResult) -> str:
    return "\n".join(
        [
            f"mission_id={safe_console_value(result.mission_id)}",
            f"transition={safe_console_value(result.transition)}",
            f"transition_status={safe_console_value(result.status)}",
            f"governance_decision={safe_console_value(result.governance_decision.decision)}",
            f"previous_mission_status={safe_console_value(result.previous_mission_status)}",
            f"previous_objective_status={safe_console_value(result.previous_objective_status)}",
            f"objective_status={safe_console_value(result.objective_status)}",
            f"next_action_ref={safe_console_value(result.next_action_ref)}",
            "memory_write_mode=through_core_only",
            f"event_names={safe_console_list([event.event_name for event in result.events])}",
        ]
    )


def render_goal_strategy(result: LongHorizonGoalStrategyResult) -> str:
    strategy = result.strategy
    if strategy is None:
        return f"No goal strategy found for mission_id={result.mission_id}"
    return render_goal_strategy_contract(strategy, status=result.status)


def render_goal_strategy_contract(
    strategy: LongHorizonGoalStrategyContract,
    *,
    status: str,
) -> str:
    return "\n".join(
        [
            f"mission_id={safe_console_value(strategy.mission_id)}",
            f"inspection_status={safe_console_value(status)}",
            f"strategy_status={safe_console_value(strategy.strategy_status)}",
            f"strategy_summary={safe_console_value(strategy.strategy_summary)}",
            f"milestone_refs={safe_console_list(strategy.milestone_refs)}",
            f"risk_refs={safe_console_list(strategy.risk_refs)}",
            f"memory_anchor_refs={safe_console_list(strategy.memory_anchor_refs)}",
            f"next_action_ref={safe_console_value(strategy.next_action_ref)}",
            f"evidence_refs={safe_console_list(strategy.evidence_refs)}",
            f"generated_from_state_refs={safe_console_list(strategy.generated_from_state_refs)}",
            f"memory_write_mode={safe_console_value(strategy.memory_write_mode)}",
            "autonomous_scheduling_allowed=False",
        ]
    )


def work_item_status_from_state(
    mission_state: MissionStateContract | None,
    work_item_ref: str,
) -> str:
    if mission_state is None:
        return "missing"
    if work_item_ref in mission_state.active_work_items:
        return "active"
    for checkpoint_ref in reversed(mission_state.checkpoint_refs):
        for transition, status in {
            "complete": "completed",
            "block": "blocked",
            "pause": "paused",
            "create": "active",
            "resume": "active",
            "redefine-next-action": "active",
        }.items():
            marker = f"work_item_transition:{transition}:{work_item_ref}:"
            if marker in checkpoint_ref:
                return status
    return "inactive" if work_item_ref in mission_state.work_item_refs else "missing"


def render_work_items_state(
    mission_state: MissionStateContract | None,
    *,
    mission_id: str,
) -> str:
    if mission_state is None:
        return f"No work items found for mission_id={safe_console_value(mission_id)}"
    work_item_refs = list(mission_state.work_item_refs)
    if not work_item_refs:
        return f"No work items found for mission_id={safe_console_value(mission_id)}"
    lines = [
        f"mission_id={safe_console_value(mission_state.mission_id)}",
        f"objective_status={safe_console_value(mission_state.objective_status)}",
        f"next_action_ref={safe_console_value(mission_state.next_action_ref)}",
    ]
    for work_item_ref in work_item_refs:
        lines.extend(
            [
                "---",
                f"work_item_ref={safe_console_value(work_item_ref)}",
                "work_item_status="
                + safe_console_value(
                    work_item_status_from_state(mission_state, work_item_ref)
                ),
                f"is_active={safe_console_value(work_item_ref in mission_state.active_work_items)}",
            ]
        )
    return "\n".join(lines)


def render_work_item_transition(result: WorkItemTransitionResult) -> str:
    work_item_state = result.work_item_state
    mission_state = result.mission_state
    return "\n".join(
        [
            f"mission_id={safe_console_value(result.mission_id)}",
            f"work_item_ref={safe_console_value(result.work_item_ref)}",
            f"transition={safe_console_value(result.transition)}",
            f"transition_status={safe_console_value(result.status)}",
            f"governance_decision={safe_console_value(result.governance_decision.decision)}",
            "previous_work_item_status="
            + safe_console_value(result.previous_work_item_status),
            "work_item_status="
            + safe_console_value(
                getattr(work_item_state, "work_item_status", None)
            ),
            f"next_action_ref={safe_console_value(result.next_action_ref)}",
            "active_work_items="
            + safe_console_list(list(getattr(mission_state, "active_work_items", []))),
            "work_item_refs="
            + safe_console_list(list(getattr(mission_state, "work_item_refs", []))),
            "memory_write_mode=through_core_only",
            f"event_names={safe_console_list([event.event_name for event in result.events])}",
        ]
    )


def artifact_status_from_state(
    mission_state: MissionStateContract | None,
    artifact_ref: str,
) -> str:
    if mission_state is None:
        return "missing"
    if artifact_ref in mission_state.active_artifact_refs:
        return "active"
    for checkpoint_ref in reversed(mission_state.checkpoint_refs):
        for transition, status in {
            "archive": "archived",
            "register": "active",
            "activate": "active",
            "replace": "active",
            "rollback": "active",
        }.items():
            marker = f"artifact_lifecycle_transition:{transition}:{artifact_ref}:"
            if marker in checkpoint_ref:
                return status
    return "inactive" if artifact_ref in mission_state.artifact_refs else "missing"


def render_artifacts_state(
    mission_state: MissionStateContract | None,
    *,
    mission_id: str,
) -> str:
    if mission_state is None:
        return f"No artifacts found for mission_id={safe_console_value(mission_id)}"
    artifact_refs = list(mission_state.artifact_refs)
    if not artifact_refs:
        return f"No artifacts found for mission_id={safe_console_value(mission_id)}"
    lines = [
        f"mission_id={safe_console_value(mission_state.mission_id)}",
        f"objective_ref={safe_console_value(mission_state.objective_ref)}",
        f"objective_status={safe_console_value(mission_state.objective_status)}",
    ]
    for artifact_ref in artifact_refs:
        lines.extend(
            [
                "---",
                f"artifact_ref={safe_console_value(artifact_ref)}",
                "artifact_status="
                + safe_console_value(artifact_status_from_state(mission_state, artifact_ref)),
                "is_active="
                + safe_console_value(artifact_ref in mission_state.active_artifact_refs),
            ]
        )
    return "\n".join(lines)


def render_artifact_transition(result: ArtifactLifecycleTransitionResult) -> str:
    artifact_state = result.artifact_state
    mission_state = result.mission_state
    return "\n".join(
        [
            f"mission_id={safe_console_value(result.mission_id)}",
            f"artifact_ref={safe_console_value(result.artifact_ref)}",
            f"transition={safe_console_value(result.transition)}",
            f"transition_status={safe_console_value(result.status)}",
            f"governance_decision={safe_console_value(result.governance_decision.decision)}",
            "previous_artifact_status="
            + safe_console_value(result.previous_artifact_status),
            "artifact_status="
            + safe_console_value(
                getattr(artifact_state, "artifact_status", None)
            ),
            "artifact_version="
            + safe_console_value(getattr(artifact_state, "artifact_version", None)),
            "work_item_ref="
            + safe_console_value(getattr(artifact_state, "work_item_ref", None)),
            "replacement_artifact_ref="
            + safe_console_value(
                getattr(artifact_state, "replacement_artifact_ref", None)
            ),
            "rollback_plan_ref="
            + safe_console_value(getattr(artifact_state, "rollback_plan_ref", None)),
            "active_artifact_refs="
            + safe_console_list(
                list(getattr(mission_state, "active_artifact_refs", []))
            ),
            "artifact_refs="
            + safe_console_list(list(getattr(mission_state, "artifact_refs", []))),
            "memory_write_mode=through_core_only",
            f"event_names={safe_console_list([event.event_name for event in result.events])}",
        ]
    )


def render_technology_absorption_candidates(proposals: list[object]) -> str:
    candidates = [
        proposal
        for proposal in proposals
        if getattr(proposal, "proposal_type", None) == "technology_absorption_candidate"
    ]
    if not candidates:
        return "No technology absorption candidates found."
    lines: list[str] = []
    for proposal in candidates:
        matrix = getattr(proposal, "evaluation_matrix", {}).get(
            "technology_absorption",
            {},
        )
        state = getattr(proposal, "strategy_context", {}).get(
            "technology_absorption_state",
            {},
        )
        policy = getattr(proposal, "strategy_context", {}).get("promotion_policy", {})
        lines.extend(
            [
                f"candidate_ref={safe_console_list(getattr(proposal, 'candidate_refs', []))}",
                f"technology_name={safe_console_value(matrix.get('technology_name'))}",
                f"absorption_class={safe_console_value(matrix.get('absorption_class'))}",
                f"candidate_status={safe_console_value(matrix.get('candidate_status'))}",
                f"absorption_readiness={safe_console_value(state.get('absorption_readiness'))}",
                f"absorption_decision={safe_console_value(state.get('absorption_decision'))}",
                f"promotion_readiness={safe_console_value(state.get('promotion_readiness'))}",
                f"blockers={safe_console_list(list(state.get('blockers', [])))}",
                f"automatic_promotion={safe_console_value(policy.get('automatic_promotion'))}",
                f"core_replacement_allowed={safe_console_value(policy.get('core_replacement_allowed'))}",
                "---",
            ]
        )
    if lines and lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)


def render_experience_reflections(records: list[object]) -> str:
    if not records:
        return "No experience reflections found."
    lines: list[str] = []
    for record in records:
        experience = getattr(record, "experience")
        reflection = getattr(record, "reflection")
        primary_domain_driver = getattr(experience, "primary_domain_driver", None)
        specialist_used = list(getattr(experience, "specialist_used", []))
        reflection_status = reflection.reflection_status if reflection else "pending"
        proposed_change_type = (
            reflection.proposed_change_type if reflection else None
        )
        learning_candidate = reflection.learning_candidate if reflection else None
        recommendation = reflection.recommendation if reflection else None
        blockers = list(reflection.blockers) if reflection else []
        automatic_promotion = (
            reflection.automatic_promotion_allowed if reflection else False
        )
        core_mutation_allowed = (
            reflection.core_mutation_allowed if reflection else False
        )
        lines.extend(
            [
                f"experience_id={safe_console_value(experience.experience_id)}",
                f"mission_id={safe_console_value(experience.mission_id)}",
                f"workflow_profile={safe_console_value(experience.workflow_profile)}",
                f"outcome_status={safe_console_value(experience.outcome_status)}",
                f"user_intent={safe_console_value(getattr(experience, 'user_intent', None))}",
                f"route={safe_console_value(getattr(experience, 'route', None))}",
                f"primary_mind={safe_console_value(getattr(experience, 'primary_mind', None))}",
                f"primary_domain_driver={safe_console_value(primary_domain_driver)}",
                f"specialist_used={safe_console_list(specialist_used)}",
                f"reflection_status={safe_console_value(reflection_status)}",
                f"proposed_change_type={safe_console_value(proposed_change_type)}",
                f"learning_candidate={safe_console_value(learning_candidate)}",
                f"recommendation={safe_console_value(recommendation)}",
                f"blockers={safe_console_list(blockers)}",
                f"automatic_promotion={safe_console_value(automatic_promotion)}",
                f"core_mutation_allowed={safe_console_value(core_mutation_allowed)}",
                "---",
            ]
        )
    if lines and lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)


def render_procedural_playbook_candidates(records: list[object]) -> str:
    if not records:
        return "No procedural playbook candidates found."
    lines: list[str] = []
    for record in records:
        candidate = getattr(record, "candidate", record)
        lines.extend(
            [
                f"playbook_candidate_id={safe_console_value(candidate.playbook_candidate_id)}",
                f"procedure_name={safe_console_value(candidate.procedure_name)}",
                f"workflow_profile={safe_console_value(candidate.workflow_profile)}",
                f"route={safe_console_value(candidate.route)}",
                f"domain={safe_console_value(candidate.domain)}",
                f"review_status={safe_console_value(candidate.review_status)}",
                f"bounded_steps={safe_console_list(list(candidate.bounded_steps))}",
                f"evidence_refs={safe_console_list(list(candidate.evidence_refs))}",
                f"source_artifact_refs={safe_console_list(list(candidate.source_artifact_refs))}",
                f"source_reflection_refs={safe_console_list(list(candidate.source_reflection_refs))}",
                f"proposed_tests={safe_console_list(list(candidate.proposed_tests))}",
                f"rollback_plan_ref={safe_console_value(candidate.rollback_plan_ref)}",
                f"blockers={safe_console_list(list(candidate.blockers))}",
                f"human_review_required={safe_console_value(candidate.human_review_required)}",
                f"automatic_promotion={safe_console_value(candidate.automatic_promotion_allowed)}",
                f"core_mutation_allowed={safe_console_value(candidate.core_mutation_allowed)}",
                f"memory_write_mode={safe_console_value(candidate.memory_write_mode)}",
                "---",
            ]
        )
    if lines and lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)


def render_skill_evolution_operator_view(
    view: SkillEvolutionOperatorViewContract,
) -> str:
    lines = [
        "skill_evolution_view=read_only",
        f"view_id={safe_console_value(view.view_id)}",
        f"view_status={safe_console_value(view.view_status)}",
        f"pattern_report_id={safe_console_value(view.pattern_report_id)}",
        f"pattern_report_status={safe_console_value(view.pattern_report_status)}",
        f"pattern_count={safe_console_value(view.pattern_count)}",
        f"candidate_count={safe_console_value(view.candidate_count)}",
        "unregistered_pattern_refs="
        + safe_console_list(list(view.unregistered_pattern_refs)),
        f"view_blockers={safe_console_list(list(view.blockers))}",
        f"human_review_required={safe_console_value(view.human_review_required)}",
        f"runtime_activation_allowed={safe_console_value(view.runtime_activation_allowed)}",
        f"promotion_authorized={safe_console_value(view.promotion_authorized)}",
        "automatic_promotion_allowed="
        + safe_console_value(view.automatic_promotion_allowed),
        f"core_mutation_allowed={safe_console_value(view.core_mutation_allowed)}",
    ]
    for item in view.items:
        lines.extend(
            [
                "---",
                f"skill_candidate_id={safe_console_value(item.skill_candidate_id)}",
                f"skill_id={safe_console_value(item.skill_id)}",
                f"skill_name={safe_console_value(item.skill_name)}",
                f"version={safe_console_value(item.version)}",
                f"workflow_profile={safe_console_value(item.workflow_profile)}",
                f"route={safe_console_value(item.route)}",
                f"domain={safe_console_value(item.domain)}",
                f"specialist_type={safe_console_value(item.specialist_type)}",
                f"risk_level={safe_console_value(item.risk_level)}",
                f"registry_status={safe_console_value(item.registry_status)}",
                f"review_status={safe_console_value(item.review_status)}",
                f"activation_status={safe_console_value(item.activation_status)}",
                f"evolution_status={safe_console_value(item.evolution_status)}",
                "origin_pattern_refs="
                + safe_console_list(list(item.source_pattern_refs)),
                f"pattern_status={safe_console_value(item.pattern_status)}",
                f"pattern_summary={safe_console_value(item.pattern_summary)}",
                f"occurrence_count={safe_console_value(item.occurrence_count)}",
                "minimum_occurrences="
                + safe_console_value(item.minimum_occurrences),
                f"confidence_status={safe_console_value(item.confidence_status)}",
                f"proposal_id={safe_console_value(item.proposal_id)}",
                f"proposal_status={safe_console_value(item.proposal_status)}",
                f"sandbox_eval_ref={safe_console_value(item.sandbox_eval_ref)}",
                f"sandbox_eval_status={safe_console_value(item.sandbox_eval_status)}",
                f"sandbox_pass_rate={safe_console_value(item.sandbox_pass_rate)}",
                f"allowed_tools={safe_console_list(list(item.allowed_tools))}",
                f"evidence_refs={safe_console_list(list(item.evidence_refs))}",
                f"proposed_tests={safe_console_list(list(item.proposed_tests))}",
                f"rollback_plan_ref={safe_console_value(item.rollback_plan_ref)}",
                f"blockers={safe_console_list(list(item.blockers))}",
                "next_operator_action="
                + safe_console_value(item.next_operator_action),
                "runtime_activation_allowed="
                + safe_console_value(item.runtime_activation_allowed),
                f"promotion_authorized={safe_console_value(item.promotion_authorized)}",
            ]
        )
    return "\n".join(lines)


def render_evolution_review_queue(items: list[object]) -> str:
    if not items:
        return "No evolution review items found."
    lines: list[str] = []
    for item in items:
        requires_human_review = safe_console_value(
            getattr(item, "requires_human_review", None)
        )
        requires_sandbox = safe_console_value(getattr(item, "requires_sandbox", None))
        lines.extend(
            [
                f"review_item_id={safe_console_value(getattr(item, 'review_item_id', None))}",
                f"proposal_id={safe_console_value(getattr(item, 'evolution_proposal_id', None))}",
                f"proposal_type={safe_console_value(getattr(item, 'proposal_type', None))}",
                f"review_status={safe_console_value(getattr(item, 'review_status', None))}",
                f"review_reason={safe_console_value(getattr(item, 'review_reason', None))}",
                f"requires_human_review={requires_human_review}",
                f"requires_sandbox={requires_sandbox}",
                f"target_scope={safe_console_value(getattr(item, 'target_scope', None))}",
                f"candidate_refs={safe_console_list(list(getattr(item, 'candidate_refs', [])))}",
                f"blockers={safe_console_list(list(getattr(item, 'blockers', [])))}",
                f"proposed_tests={safe_console_list(list(getattr(item, 'proposed_tests', [])))}",
                f"rollback_plan_ref={safe_console_value(getattr(item, 'rollback_plan_ref', None))}",
                "automatic_promotion=False",
                "---",
            ]
        )
    if lines and lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)


def render_evolution_review_decision(decision: object) -> str:
    review_decision_id = safe_console_value(
        getattr(decision, "review_decision_id", None)
    )
    proposal_id = safe_console_value(getattr(decision, "evolution_proposal_id", None))
    evidence_refs = safe_console_list(list(getattr(decision, "evidence_refs", [])))
    proposed_tests = safe_console_list(list(getattr(decision, "proposed_tests", [])))
    rollback_plan_ref = safe_console_value(
        getattr(decision, "rollback_plan_ref", None)
    )
    return "\n".join(
        [
            f"review_decision_id={review_decision_id}",
            f"proposal_id={proposal_id}",
            f"decision={safe_console_value(getattr(decision, 'decision', None))}",
            f"review_status={safe_console_value(getattr(decision, 'review_status', None))}",
            f"operator_ref={safe_console_value(getattr(decision, 'operator_ref', None))}",
            f"evidence_refs={evidence_refs}",
            f"proposed_tests={proposed_tests}",
            f"rollback_plan_ref={rollback_plan_ref}",
            f"risk_acceptance={safe_console_value(getattr(decision, 'risk_acceptance', None))}",
            f"review_notes={safe_console_list(list(getattr(decision, 'review_notes', [])))}",
            "automatic_promotion=False",
            "core_mutation_allowed=False",
        ]
    )


def render_memory_lifecycle_review_queue(items: list[object]) -> str:
    if not items:
        return "No memory lifecycle review items found."
    lines: list[str] = []
    for item in items:
        lines.extend(
            [
                f"candidate_id={safe_console_value(getattr(item, 'candidate_id', None))}",
                "maintenance_action="
                + safe_console_value(getattr(item, "maintenance_action", None)),
                f"target_scope={safe_console_value(getattr(item, 'target_scope', None))}",
                "target_refs="
                + safe_console_list(list(getattr(item, "target_refs", []))),
                f"reason={safe_console_value(getattr(item, 'reason', None))}",
                "evidence_refs="
                + safe_console_list(list(getattr(item, "evidence_refs", []))),
                "rollback_plan_ref="
                + safe_console_value(getattr(item, "rollback_plan_ref", None)),
                f"review_status={safe_console_value(getattr(item, 'review_status', None))}",
                "execution_status="
                + safe_console_value(getattr(item, "execution_status", None)),
                "last_review_decision_id="
                + safe_console_value(getattr(item, "last_review_decision_id", None)),
                "human_review_required="
                + safe_console_value(getattr(item, "human_review_required", None)),
                "automatic_execution_allowed="
                + safe_console_value(
                    getattr(item, "automatic_execution_allowed", None)
                ),
                "core_mutation_allowed="
                + safe_console_value(getattr(item, "core_mutation_allowed", None)),
                "---",
            ]
        )
    lines.pop()
    return "\n".join(lines)


def render_memory_lifecycle_review_result(
    *,
    assessment: object,
    decision: object | None,
) -> str:
    lines = [
        "governance_assessment_id="
        + safe_console_value(getattr(assessment, "assessment_id", None)),
        f"governance_status={safe_console_value(getattr(assessment, 'status', None))}",
        "governance_blockers="
        + safe_console_list(list(getattr(assessment, "blockers", []))),
        "execution_authorized=False",
        "automatic_execution_allowed=False",
        "core_mutation_allowed=False",
    ]
    if decision is not None:
        lines.extend(
            [
                "review_decision_id="
                + safe_console_value(getattr(decision, "review_decision_id", None)),
                f"candidate_id={safe_console_value(getattr(decision, 'candidate_id', None))}",
                "maintenance_action="
                + safe_console_value(getattr(decision, "maintenance_action", None)),
                "decision_action="
                + safe_console_value(getattr(decision, "decision_action", None)),
                f"review_status={safe_console_value(getattr(decision, 'review_status', None))}",
                f"operator_ref={safe_console_value(getattr(decision, 'operator_ref', None))}",
                "evidence_refs="
                + safe_console_list(list(getattr(decision, "evidence_refs", []))),
                "rollback_plan_ref="
                + safe_console_value(getattr(decision, "rollback_plan_ref", None)),
            ]
        )
    return "\n".join(lines)


def render_mission_cycle(
    *,
    mission_id: str,
    mission_state: MissionStateContract | None,
    records: list[object],
    review_items: list[object],
    flow_audit: object | None = None,
) -> str:
    if mission_state is None and not records and not review_items:
        return f"No mission cycle found for mission_id={safe_console_value(mission_id)}"

    latest_record = records[0] if records else None
    experience = getattr(latest_record, "experience", None)
    reflection = getattr(latest_record, "reflection", None)
    matching_review_items = _matching_review_items(
        review_items=review_items,
        experience=experience,
        reflection=reflection,
    )
    primary_review = matching_review_items[0] if matching_review_items else None
    reflection_status = safe_console_value(
        getattr(reflection, "reflection_status", "pending")
    )
    next_step = _mission_cycle_next_step(
        mission_state=mission_state,
        reflection=reflection,
        review_item=primary_review,
    )
    reviewed_learning_status = safe_console_value(
        getattr(flow_audit, "reviewed_learning_influence_status", "not_applicable")
    )
    reviewed_learning_refs = safe_console_list(
        list(getattr(flow_audit, "reviewed_learning_influence_refs", []))
    )
    reviewed_learning_reason = safe_console_value(
        getattr(flow_audit, "reviewed_learning_influence_reason", None)
    )
    reviewed_learning_eval_status = safe_console_value(
        getattr(
            flow_audit,
            "reviewed_learning_assisted_eval_status",
            "baseline_no_reviewed_learning",
        )
    )
    reviewed_learning_release = safe_console_value(
        getattr(
            flow_audit,
            "reviewed_learning_release_conclusion",
            "no_promotion_without_release_gate",
        )
    )
    lines = [
        "operator_learning_loop=read_only",
        f"mission_id={safe_console_value(mission_id)}",
        f"mission_goal={safe_console_value(getattr(mission_state, 'mission_goal', None))}",
        f"objective_status={safe_console_value(getattr(mission_state, 'objective_status', None))}",
        f"next_action_ref={safe_console_value(getattr(mission_state, 'next_action_ref', None))}",
        f"route={safe_console_value(getattr(experience, 'route', None))}",
        f"workflow_profile={safe_console_value(getattr(experience, 'workflow_profile', None))}",
        f"plan_summary={safe_console_value(getattr(experience, 'plan_summary', None))}",
        f"execution_summary={safe_console_value(getattr(experience, 'execution_summary', None))}",
        f"checkpoints={safe_console_list(list(getattr(experience, 'checkpoints', [])))}",
        f"memory_used={safe_console_list(list(getattr(experience, 'evidence_refs', [])))}",
        f"specialist_used={safe_console_list(list(getattr(experience, 'specialist_used', [])))}",
        f"experience_id={safe_console_value(getattr(experience, 'experience_id', None))}",
        f"experience_outcome={safe_console_value(getattr(experience, 'outcome_status', None))}",
        f"reflection_id={safe_console_value(getattr(reflection, 'reflection_id', None))}",
        f"reflection_status={reflection_status}",
        f"learning_candidate={safe_console_value(getattr(reflection, 'learning_candidate', None))}",
        f"recommendation={safe_console_value(getattr(reflection, 'recommendation', None))}",
        f"reviewed_learning_influence_status={reviewed_learning_status}",
        f"reviewed_learning_influence_refs={reviewed_learning_refs}",
        f"reviewed_learning_influence_reason={reviewed_learning_reason}",
        f"reviewed_learning_assisted_eval_status={reviewed_learning_eval_status}",
        f"reviewed_learning_release_conclusion={reviewed_learning_release}",
        f"proposal_id={safe_console_value(getattr(primary_review, 'evolution_proposal_id', None))}",
        f"review_status={safe_console_value(getattr(primary_review, 'review_status', None))}",
        f"review_blockers={safe_console_list(list(getattr(primary_review, 'blockers', [])))}",
        "automatic_promotion=False",
        f"next_operator_step={safe_console_value(next_step)}",
    ]
    return "\n".join(lines)


def _matching_review_items(
    *,
    review_items: list[object],
    experience: object | None,
    reflection: object | None,
) -> list[object]:
    refs = {
        str(value)
        for value in [
            getattr(experience, "experience_id", None),
            getattr(reflection, "reflection_id", None),
        ]
        if value is not None
    }
    if not refs:
        return []
    return [
        item
        for item in review_items
        if refs.intersection(str(ref) for ref in getattr(item, "candidate_refs", []))
    ]


def _mission_cycle_next_step(
    *,
    mission_state: MissionStateContract | None,
    reflection: object | None,
    review_item: object | None,
) -> str:
    if review_item is not None:
        return "review_evolution_proposal"
    if reflection is not None:
        return "create_or_link_evolution_review"
    if mission_state is not None:
        return safe_console_value(mission_state.next_action_ref)
    return "start_governed_mission"


def _operator_pending_decisions(
    *,
    mission_state: MissionStateContract | None,
    review_item: object | None,
    flow_audit: object | None,
) -> list[str]:
    decisions: list[str] = []
    review_status = getattr(review_item, "review_status", None)
    if review_status in {"observed", "candidate", "needs_review", "sandboxed"}:
        proposal_id = safe_console_value(
            getattr(review_item, "evolution_proposal_id", None)
        )
        decisions.append(f"review_evolution_proposal:{proposal_id}")

    promotion_gate_status = getattr(flow_audit, "promotion_gate_status", None)
    promotion_gate_id = safe_console_value(
        getattr(flow_audit, "promotion_gate_id", None)
    )
    if promotion_gate_status == "blocked":
        decisions.append(f"resolve_promotion_gate_blockers:{promotion_gate_id}")
    elif promotion_gate_status == "passed" and not bool(
        getattr(flow_audit, "promotion_gate_promotion_authorized", False)
    ):
        decisions.append(f"human_promotion_decision:{promotion_gate_id}")

    effective_autonomy_level = getattr(
        flow_audit,
        "effective_autonomy_level",
        None,
    )
    if effective_autonomy_level not in {None, "", "not_applicable"} and bool(
        getattr(flow_audit, "autonomy_human_confirmation_required", False)
    ):
        confirmation_mode = safe_console_value(
            getattr(flow_audit, "autonomy_confirmation_mode", None)
        )
        decisions.append(f"confirm_autonomy_action:{confirmation_mode}")

    checkpoint_refs = list(getattr(mission_state, "open_checkpoint_refs", []))
    if checkpoint_refs:
        decisions.append(
            "resolve_workflow_checkpoint:"
            f"{safe_console_value(checkpoint_refs[0])}"
        )
    if mission_state is not None and getattr(
        mission_state,
        "objective_status",
        None,
    ) == "requires_operator_decision":
        decisions.append("resolve_objective_decision")
    return list(dict.fromkeys(decisions))


def render_operator_dashboard(
    *,
    mission_id: str | None,
    mission_state: MissionStateContract | None,
    records: list[object],
    review_items: list[object],
    flow_audit: object | None = None,
) -> str:
    latest_record = records[0] if records else None
    experience = getattr(latest_record, "experience", None)
    reflection = getattr(latest_record, "reflection", None)
    matching_review_items = _matching_review_items(
        review_items=review_items,
        experience=experience,
        reflection=reflection,
    )
    pending_review_items = [
        item
        for item in review_items
        if getattr(item, "review_status", None)
        in {"observed", "candidate", "needs_review", "sandboxed"}
    ]
    primary_review = (
        matching_review_items[0]
        if matching_review_items
        else pending_review_items[0]
        if pending_review_items
        else None
    )
    next_step = _mission_cycle_next_step(
        mission_state=mission_state,
        reflection=reflection,
        review_item=primary_review,
    )
    if mission_state is None and reflection is None and primary_review is None:
        next_step = "start_governed_mission"

    dashboard_scope = "mission" if mission_id else "global"
    reviewed_learning_status = safe_console_value(
        getattr(flow_audit, "reviewed_learning_influence_status", "not_applicable")
    )
    reviewed_learning_eval_status = safe_console_value(
        getattr(
            flow_audit,
            "reviewed_learning_assisted_eval_status",
            "baseline_no_reviewed_learning",
        )
    )
    reviewed_learning_release = safe_console_value(
        getattr(
            flow_audit,
            "reviewed_learning_release_conclusion",
            "no_promotion_without_release_gate",
        )
    )
    mission_goal = safe_console_value(getattr(mission_state, "mission_goal", None))
    objective_status = safe_console_value(
        getattr(mission_state, "objective_status", None)
    )
    next_action_ref = safe_console_value(
        getattr(mission_state, "next_action_ref", None)
    )
    active_work_items = safe_console_list(
        list(getattr(mission_state, "active_work_items", []))
    )
    work_item_refs = list(getattr(mission_state, "work_item_refs", []))
    work_item_count = len(work_item_refs)
    open_checkpoint_refs = safe_console_list(
        list(getattr(mission_state, "open_checkpoint_refs", []))
    )
    artifact_ref_values = list(getattr(mission_state, "artifact_refs", []))
    artifact_refs = safe_console_list(artifact_ref_values)
    artifact_count = len(artifact_ref_values)
    latest_experience_id = safe_console_value(
        getattr(experience, "experience_id", None)
    )
    latest_experience_outcome = safe_console_value(
        getattr(experience, "outcome_status", None)
    )
    latest_reflection_id = safe_console_value(
        getattr(reflection, "reflection_id", None)
    )
    latest_reflection_status = safe_console_value(
        getattr(reflection, "reflection_status", None)
    )
    operator_usefulness_status = safe_console_value(
        getattr(flow_audit, "operator_usefulness_status", "insufficient_signal")
    )
    operator_usefulness_score = safe_console_value(
        getattr(flow_audit, "operator_usefulness_score", 0)
    )
    operator_usefulness_signals = safe_console_list(
        list(getattr(flow_audit, "operator_usefulness_signals", []))
    )
    semantic_memory_anchor_refs = safe_console_list(
        list(getattr(flow_audit, "semantic_memory_anchor_refs", []))
    )
    semantic_memory_evidence_refs = safe_console_list(
        list(getattr(flow_audit, "semantic_memory_evidence_refs", []))
    )
    semantic_memory_use_reason = safe_console_value(
        getattr(flow_audit, "semantic_memory_use_reason", None)
    )
    semantic_memory_non_use_reason = safe_console_value(
        getattr(flow_audit, "semantic_memory_non_use_reason", None)
    )
    memory_influence_used_refs = safe_console_list(
        list(getattr(flow_audit, "memory_influence_used_refs", []))
    )
    memory_influence_ignored_refs = safe_console_list(
        list(getattr(flow_audit, "memory_influence_ignored_refs", []))
    )
    memory_influence_reasons = safe_console_list(
        list(getattr(flow_audit, "memory_influence_reasons", []))
    )
    memory_influence_evidence_refs = safe_console_list(
        list(getattr(flow_audit, "memory_influence_evidence_refs", []))
    )
    effective_autonomy_level = safe_console_value(
        getattr(flow_audit, "effective_autonomy_level", None)
    )
    autonomy_ladder_status = safe_console_value(
        getattr(flow_audit, "autonomy_ladder_status", None)
    )
    max_autonomy_capability_mode = safe_console_value(
        getattr(flow_audit, "max_autonomy_capability_mode", None)
    )
    autonomy_human_confirmation_required = safe_console_value(
        getattr(flow_audit, "autonomy_human_confirmation_required", True)
    )
    autonomy_confirmation_mode = safe_console_value(
        getattr(flow_audit, "autonomy_confirmation_mode", None)
    )
    autonomy_blocked_runtime_actions = safe_console_list(
        list(getattr(flow_audit, "autonomy_blocked_runtime_actions", []))
    )
    objective_continuity_status = safe_console_value(
        getattr(flow_audit, "objective_continuity_status", "not_applicable")
    )
    artifact_continuity_status = safe_console_value(
        getattr(flow_audit, "artifact_continuity_status", "not_applicable")
    )
    next_action_status = safe_console_value(
        getattr(flow_audit, "next_action_status", "not_applicable")
    )
    primary_review_status = safe_console_value(
        getattr(primary_review, "review_status", None)
    )
    primary_review_blockers = safe_console_list(
        list(getattr(primary_review, "blockers", []))
    )
    primary_review_tests = safe_console_list(
        list(getattr(primary_review, "proposed_tests", []))
    )
    primary_review_rollback = safe_console_value(
        getattr(primary_review, "rollback_plan_ref", None)
    )
    promotion_gate_status = safe_console_value(
        getattr(flow_audit, "promotion_gate_status", "not_applicable")
    )
    promotion_gate_decision = safe_console_value(
        getattr(flow_audit, "promotion_gate_decision", "not_applicable")
    )
    promotion_gate_release_conclusion = safe_console_value(
        getattr(
            flow_audit,
            "promotion_gate_release_conclusion",
            "no_promotion_gate_evidence",
        )
    )
    promotion_gate_missing_gates = safe_console_list(
        list(getattr(flow_audit, "promotion_gate_missing_gates", []))
    )
    promotion_gate_blockers = safe_console_list(
        list(getattr(flow_audit, "promotion_gate_blockers", []))
    )
    promotion_gate_evidence_refs = safe_console_list(
        list(getattr(flow_audit, "promotion_gate_evidence_refs", []))
    )
    promotion_gate_human_decision_required = safe_console_value(
        getattr(flow_audit, "promotion_gate_human_decision_required", True)
    )
    promotion_gate_promotion_authorized = safe_console_value(
        getattr(flow_audit, "promotion_gate_promotion_authorized", False)
    )
    pending_decision_values = _operator_pending_decisions(
        mission_state=mission_state,
        review_item=primary_review,
        flow_audit=flow_audit,
    )
    pending_decisions = safe_console_list(pending_decision_values)
    cockpit_status = (
        "operator_decision_required"
        if pending_decision_values
        else "ready_for_next_action"
        if next_action_ref not in {"none", "not_applicable", ""}
        else "idle"
    )
    next_operator_decision = (
        pending_decision_values[0] if pending_decision_values else next_step
    )

    return "\n".join(
        [
            "operator_dashboard=read_only",
            f"dashboard_scope={dashboard_scope}",
            f"mission_id={safe_console_value(mission_id)}",
            f"mission_goal={mission_goal}",
            f"objective_status={objective_status}",
            f"objective_continuity_status={objective_continuity_status}",
            f"next_action_ref={next_action_ref}",
            f"next_action_status={next_action_status}",
            f"active_work_items={active_work_items}",
            f"work_item_refs={safe_console_list(work_item_refs)}",
            f"work_item_count={work_item_count}",
            f"open_checkpoint_refs={open_checkpoint_refs}",
            f"artifact_refs={artifact_refs}",
            f"artifact_count={artifact_count}",
            f"artifact_continuity_status={artifact_continuity_status}",
            f"latest_experience_id={latest_experience_id}",
            f"latest_experience_outcome={latest_experience_outcome}",
            f"latest_reflection_id={latest_reflection_id}",
            f"latest_reflection_status={latest_reflection_status}",
            f"pending_review_count={len(pending_review_items)}",
            "pending_review_proposal_ids="
            + safe_console_list(
                [
                    getattr(item, "evolution_proposal_id", None)
                    for item in pending_review_items
                ]
            ),
            f"primary_review_status={primary_review_status}",
            f"primary_review_blockers={primary_review_blockers}",
            f"primary_review_tests={primary_review_tests}",
            f"primary_review_rollback_plan_ref={primary_review_rollback}",
            f"reviewed_learning_influence_status={reviewed_learning_status}",
            f"reviewed_learning_assisted_eval_status={reviewed_learning_eval_status}",
            f"reviewed_learning_release_conclusion={reviewed_learning_release}",
            f"semantic_memory_anchor_refs={semantic_memory_anchor_refs}",
            f"semantic_memory_evidence_refs={semantic_memory_evidence_refs}",
            f"semantic_memory_use_reason={semantic_memory_use_reason}",
            f"semantic_memory_non_use_reason={semantic_memory_non_use_reason}",
            f"memory_influence_used_refs={memory_influence_used_refs}",
            f"memory_influence_ignored_refs={memory_influence_ignored_refs}",
            f"memory_influence_reasons={memory_influence_reasons}",
            f"memory_influence_evidence_refs={memory_influence_evidence_refs}",
            f"effective_autonomy_level={effective_autonomy_level}",
            f"autonomy_ladder_status={autonomy_ladder_status}",
            f"max_autonomy_capability_mode={max_autonomy_capability_mode}",
            "autonomy_human_confirmation_required="
            f"{autonomy_human_confirmation_required}",
            f"autonomy_confirmation_mode={autonomy_confirmation_mode}",
            f"autonomy_blocked_runtime_actions={autonomy_blocked_runtime_actions}",
            f"operator_usefulness_status={operator_usefulness_status}",
            f"operator_usefulness_score={operator_usefulness_score}",
            f"operator_usefulness_signals={operator_usefulness_signals}",
            f"promotion_gate_status={promotion_gate_status}",
            f"promotion_gate_decision={promotion_gate_decision}",
            "promotion_gate_release_conclusion="
            f"{promotion_gate_release_conclusion}",
            f"promotion_gate_missing_gates={promotion_gate_missing_gates}",
            f"promotion_gate_blockers={promotion_gate_blockers}",
            f"promotion_gate_evidence_refs={promotion_gate_evidence_refs}",
            "promotion_gate_human_decision_required="
            f"{promotion_gate_human_decision_required}",
            "promotion_gate_promotion_authorized="
            f"{promotion_gate_promotion_authorized}",
            f"cockpit_status={cockpit_status}",
            f"pending_decision_count={len(pending_decision_values)}",
            f"pending_decisions={pending_decisions}",
            "automatic_promotion=False",
            f"next_operator_decision={safe_console_value(next_operator_decision)}",
            f"next_operator_step={safe_console_value(next_step)}",
        ]
    )


def render_mission_progress_report(result: MissionProgressReportResult) -> str:
    report = result.report
    return "\n".join(
        [
            "mission_progress_report=read_only",
            f"report_id={safe_console_value(report.report_id)}",
            f"mission_id={safe_console_value(result.mission_id)}",
            f"report_status={safe_console_value(report.report_status)}",
            f"progress_summary={safe_console_value(report.progress_summary)}",
            f"work_item_refs={safe_console_list(report.work_item_refs)}",
            f"active_work_items={safe_console_list(report.active_work_items)}",
            f"artifact_refs={safe_console_list(report.artifact_refs)}",
            f"open_checkpoint_refs={safe_console_list(report.open_checkpoint_refs)}",
            f"milestone_refs={safe_console_list(report.milestone_refs)}",
            f"risk_refs={safe_console_list(report.risk_refs)}",
            f"memory_influence_refs={safe_console_list(report.memory_influence_refs)}",
            f"learning_refs={safe_console_list(report.learning_refs)}",
            f"evidence_refs={safe_console_list(report.evidence_refs)}",
            f"pending_decisions={safe_console_list(report.pending_decisions)}",
            f"operator_usefulness_status={safe_console_value(report.operator_usefulness_status)}",
            f"next_action_ref={safe_console_value(report.next_action_ref)}",
            f"memory_write_mode={safe_console_value(report.memory_write_mode)}",
            "autonomous_execution_allowed="
            f"{safe_console_value(report.autonomous_execution_allowed)}",
            "---",
            report.report_text,
        ]
    )


def render_readiness_dashboard(report: RegressionReadinessReportContract) -> str:
    counts = report.capability_counts
    return "\n".join(
        [
            "regression_readiness=read_only",
            f"status={safe_console_value(report.status)}",
            f"overall_score={safe_console_value(report.overall_score)}",
            f"gate_mode={safe_console_value(report.gate_mode)}",
            f"gate_status={safe_console_value(report.gate_status)}",
            f"test_status={safe_console_value(report.test_status)}",
            f"document_status={safe_console_value(report.document_status)}",
            f"backlog_status={safe_console_value(report.backlog_status)}",
            f"next_ready_item={safe_console_value(report.next_ready_item)}",
            "longitudinal_learning_status="
            f"{safe_console_value(report.longitudinal_learning_status)}",
            "longitudinal_regression_flags="
            f"{safe_console_list(report.longitudinal_regression_flags)}",
            "longitudinal_learning_evidence_ref="
            f"{safe_console_value(report.longitudinal_learning_evidence_ref)}",
            "longitudinal_learning_authority_safe="
            f"{safe_console_value(report.longitudinal_learning_authority_safe)}",
            f"capability_ready={safe_console_value(counts.get('ready', 0))}",
            f"capability_partial={safe_console_value(counts.get('partial', 0))}",
            "capability_attention="
            f"{safe_console_value(counts.get('attention_required', 0))}",
            f"capability_missing={safe_console_value(counts.get('missing', 0))}",
            f"capability_deferred={safe_console_value(counts.get('deferred', 0))}",
            f"status_drift={safe_console_list(report.status_drift)}",
            f"blockers={safe_console_list(report.blockers)}",
            f"warnings={safe_console_list(report.warnings)}",
            "read_only=True",
            "autonomous_release_allowed=False",
        ]
    )


def render_longitudinal_learning_report(
    report: LongitudinalLearningReportContract,
) -> str:
    lines = [
        "longitudinal_learning=read_only",
        f"report_id={safe_console_value(report.report_id)}",
        f"report_status={safe_console_value(report.report_status)}",
        f"minimum_observations={safe_console_value(report.minimum_observations)}",
        f"target_count={safe_console_value(report.target_count)}",
        f"observation_count={safe_console_value(report.observation_count)}",
        f"observed_version_count={safe_console_value(report.observed_version_count)}",
        f"period_start={safe_console_value(report.period_start)}",
        f"period_end={safe_console_value(report.period_end)}",
        f"missing_evidence_refs={safe_console_list(report.missing_evidence_refs)}",
        f"regression_flags={safe_console_list(report.regression_flags)}",
        f"rollback_refs={safe_console_list(report.rollback_refs)}",
        f"limitations={safe_console_list(report.limitations)}",
        "promotion_authorized=False",
        "automatic_promotion_allowed=False",
        "core_mutation_allowed=False",
    ]
    for metric in report.version_metrics:
        lines.extend(
            [
                "---",
                f"capability_kind={safe_console_value(metric.capability_kind)}",
                f"capability_id={safe_console_value(metric.capability_id)}",
                f"version_ref={safe_console_value(metric.version_ref)}",
                f"baseline_version_ref={safe_console_value(metric.baseline_version_ref)}",
                f"lifecycle_status={safe_console_value(metric.lifecycle_status)}",
                f"runtime_status={safe_console_value(metric.runtime_status)}",
                f"trend_status={safe_console_value(metric.trend_status)}",
                f"observations={safe_console_value(metric.observation_count)}",
                f"runtime_observations={safe_console_value(metric.runtime_observation_count)}",
                f"offline_observations={safe_console_value(metric.offline_observation_count)}",
                f"missions={safe_console_value(metric.mission_count)}",
                f"success_rate={safe_console_value(metric.success_rate)}",
                "average_success_score="
                + safe_console_value(metric.average_success_score),
                f"success_rate_delta={safe_console_value(metric.success_rate_delta)}",
                f"rework_rate={safe_console_value(metric.rework_rate)}",
                f"rework_rate_delta={safe_console_value(metric.rework_rate_delta)}",
                f"feedback_count={safe_console_value(metric.feedback_count)}",
                "helpful_feedback_rate="
                + safe_console_value(metric.helpful_feedback_rate),
                f"regression_count={safe_console_value(metric.regression_count)}",
                f"rollback_count={safe_console_value(metric.rollback_count)}",
                f"blockers={safe_console_list(metric.blockers)}",
            ]
        )
    return "\n".join(lines)


def render_mission_workflow_report(
    *,
    response: OrchestratorResponse,
    proposal: object | None,
    cycle_report: str,
) -> str:
    proposal_id = safe_console_value(
        getattr(proposal, "evolution_proposal_id", None)
    )
    mission_id = safe_console_value(
        getattr(getattr(response, "experience_record", None), "mission_id", None)
    )
    operation_status = getattr(getattr(response, "operation_result", None), "status", None)
    execution_status = safe_console_value(
        getattr(operation_status, "value", operation_status)
    )
    reflection_recorded = safe_console_value(response.post_task_reflection is not None)
    return "\n".join(
        [
            "mission_workflow_status=closed_with_human_review_pending",
            f"request_id={safe_console_value(response.request_id)}",
            f"governance_decision={safe_console_value(response.governance_decision.decision.value)}",
            f"mission_started={mission_id}",
            f"intent={safe_console_value(response.intent)}",
            "plan_status=created",
            f"execution_status={execution_status}",
            f"experience_recorded={safe_console_value(response.experience_record is not None)}",
            f"post_task_reflection_recorded={reflection_recorded}",
            f"evolution_proposal_id={proposal_id}",
            "review_status=needs_review" if proposal is not None else "review_status=pending",
            "automatic_promotion=False",
            "---",
            cycle_report,
        ]
    )


def render_operator_feedback_result(
    result: OperatorFeedbackResult,
    *,
    proposal: object | None,
) -> str:
    feedback = result.feedback
    experience = result.experience_record
    reflection = result.post_task_reflection
    return "\n".join(
        [
            f"operator_feedback_status={safe_console_value(result.status)}",
            f"mission_id={safe_console_value(result.mission_id)}",
            f"experience_id={safe_console_value(result.experience_id)}",
            "governance_decision="
            f"{safe_console_value(result.governance_decision.decision.value)}",
            "governance_justification="
            f"{safe_console_value(result.governance_decision.justification)}",
            f"feedback_id={safe_console_value(getattr(feedback, 'feedback_id', None))}",
            f"assessment={safe_console_value(getattr(feedback, 'assessment', None))}",
            f"rating={safe_console_value(getattr(feedback, 'rating', None))}",
            "feedback_memory_status="
            f"{safe_console_value(getattr(feedback, 'feedback_status', None))}",
            "experience_feedback="
            f"{safe_console_value(getattr(experience, 'user_feedback', None))}",
            "reflection_id="
            f"{safe_console_value(getattr(reflection, 'reflection_id', None))}",
            "reflection_status="
            f"{safe_console_value(getattr(reflection, 'reflection_status', None))}",
            "feedback_evidence_refs="
            f"{safe_console_list(list(getattr(feedback, 'evidence_refs', [])))}",
            "reflection_evidence_refs="
            f"{safe_console_list(list(getattr(reflection, 'evidence_refs', [])))}",
            "evolution_proposal_id="
            f"{safe_console_value(getattr(proposal, 'evolution_proposal_id', None))}",
            "evolution_review_status="
            + ("needs_review" if proposal is not None else "not_created"),
            "memory_write_mode=through_core_only",
            "automatic_promotion=False",
            "core_mutation_allowed=False",
        ]
    )
def run_ask_command(console: JarvisConsole, args: Namespace) -> list[str]:
    response = console.ask(
        args.prompt,
        session_id=args.session_id,
        mission_id=args.mission_id,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_response(response, debug=args.debug)]


def run_chat_command(console: JarvisConsole, args: Namespace) -> list[str]:
    outputs: list[str] = []
    if args.message:
        for message in args.message:
            response = console.ask(
                message,
                session_id=args.session_id,
                mission_id=args.mission_id,
                operator_identity_ref=args.operator_identity_ref,
                canonical_user_ref=args.canonical_user_ref,
            )
            outputs.append(render_response(response, debug=args.debug))
        return outputs

    print("JARVIS console ready. Type 'exit' to quit.")
    while True:
        prompt = input("jarvis> ").strip()
        if prompt.lower() in {"exit", "quit"}:
            break
        if not prompt:
            continue
        response = console.ask(
            prompt,
            session_id=args.session_id,
            mission_id=args.mission_id,
            operator_identity_ref=args.operator_identity_ref,
            canonical_user_ref=args.canonical_user_ref,
        )
        rendered = render_response(response, debug=args.debug)
        outputs.append(rendered)
        print(rendered)
    return outputs


def run_objectives_command(console: JarvisConsole, args: Namespace) -> list[str]:
    mission_state = console.get_objective_state(mission_id=args.mission_id)
    return [
        render_objective_state(
            mission_state,
            mission_id=args.mission_id,
        )
    ]


def run_objective_command(console: JarvisConsole, args: Namespace) -> list[str]:
    result = console.transition_objective(
        mission_id=args.mission_id,
        transition=args.action,
        session_id=args.session_id,
        next_action_ref=args.next_action_ref,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_objective_transition(result)]


def run_goal_strategy_command(console: JarvisConsole, args: Namespace) -> list[str]:
    result = console.inspect_goal_strategy(
        mission_id=args.mission_id,
        session_id=args.session_id,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_goal_strategy(result)]


def run_work_items_command(console: JarvisConsole, args: Namespace) -> list[str]:
    mission_state = console.get_objective_state(mission_id=args.mission_id)
    return [
        render_work_items_state(
            mission_state,
            mission_id=args.mission_id,
        )
    ]


def run_work_item_command(console: JarvisConsole, args: Namespace) -> list[str]:
    result = console.transition_work_item(
        mission_id=args.mission_id,
        work_item_ref=args.work_item_ref,
        transition=args.action,
        session_id=args.session_id,
        next_action_ref=args.next_action_ref,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_work_item_transition(result)]


def run_artifacts_command(console: JarvisConsole, args: Namespace) -> list[str]:
    mission_state = console.get_objective_state(mission_id=args.mission_id)
    return [
        render_artifacts_state(
            mission_state,
            mission_id=args.mission_id,
        )
    ]


def run_artifact_command(console: JarvisConsole, args: Namespace) -> list[str]:
    result = console.transition_artifact_lifecycle(
        mission_id=args.mission_id,
        artifact_ref=args.artifact_ref,
        transition=args.action,
        session_id=args.session_id,
        artifact_version=args.artifact_version,
        work_item_ref=args.work_item_ref,
        replacement_artifact_ref=args.replacement_artifact_ref,
        rollback_plan_ref=args.rollback_plan_ref,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_artifact_transition(result)]


def run_technology_candidates_command(args: Namespace) -> list[str]:
    evolution_db = (
        Path(args.evolution_db)
        if args.evolution_db
        else ROOT / ".jarvis_runtime" / "evolution.db"
    )
    service = EvolutionLabService(database_path=str(evolution_db))
    proposals = service.list_recent_proposals(limit=max(1, args.limit))
    return [render_technology_absorption_candidates(proposals)]


def _memory_service_from_args(args: Namespace) -> MemoryService:
    memory_db = (
        Path(args.memory_db)
        if args.memory_db
        else ROOT / ".jarvis_runtime" / "memory.db"
    )
    memory_db = memory_db.expanduser()
    if not memory_db.is_absolute():
        memory_db = (Path.cwd() / memory_db).resolve()
    return MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")


def _evolution_service_from_args(args: Namespace) -> EvolutionLabService:
    evolution_db = (
        Path(args.evolution_db)
        if args.evolution_db
        else ROOT / ".jarvis_runtime" / "evolution.db"
    )
    evolution_db = evolution_db.expanduser()
    if not evolution_db.is_absolute():
        evolution_db = (Path.cwd() / evolution_db).resolve()
    return EvolutionLabService(database_path=str(evolution_db))


def run_experience_reflections_command(args: Namespace) -> list[str]:
    service = _memory_service_from_args(args)
    records = service.list_experience_reflections(
        mission_id=args.mission_id,
        workflow_profile=args.workflow_profile,
        limit=max(1, args.limit),
    )
    return [render_experience_reflections(records)]


def run_procedural_playbooks_command(args: Namespace) -> list[str]:
    service = _memory_service_from_args(args)
    records = service.list_procedural_playbook_candidates(
        workflow_profile=args.workflow_profile,
        review_status=args.review_status,
        limit=max(1, args.limit),
    )
    return [render_procedural_playbook_candidates(records)]


def run_skill_evolution_command(args: Namespace) -> list[str]:
    memory_service = _memory_service_from_args(args)
    evolution_service = _evolution_service_from_args(args)
    limit = max(1, min(args.limit, 100))
    generated_at = datetime.now(UTC).isoformat()
    pattern_report = memory_service.build_recurring_pattern_report(
        workflow_profile=args.workflow_profile,
        route=args.route,
        domain=args.domain,
        minimum_occurrences=2,
        max_records=max(20, min(limit * 20, 100)),
        max_patterns=limit,
        generated_at=generated_at,
    )
    candidate_records = memory_service.list_skill_candidates(
        skill_id=args.skill_id,
        version=args.version,
        domain=args.domain,
        limit=100,
    )
    candidates = [record.candidate for record in candidate_records]
    if args.workflow_profile:
        candidates = [
            candidate
            for candidate in candidates
            if candidate.workflow_profile == args.workflow_profile
        ]
    if args.route:
        visible_pattern_refs = {
            pattern.pattern_id for pattern in pattern_report.patterns
        }
        candidates = [
            candidate
            for candidate in candidates
            if visible_pattern_refs.intersection(candidate.source_pattern_refs)
        ]
    candidates = candidates[:limit]
    proposals = evolution_service.list_recent_proposals(
        limit=max(20, min(limit * 5, 100))
    )
    view = ObservabilityService.build_skill_evolution_operator_view(
        view_id=f"skill-evolution-view://{uuid4().hex[:12]}",
        pattern_report=pattern_report,
        candidates=candidates,
        proposals=proposals,
        generated_at=generated_at,
    )
    return [render_skill_evolution_operator_view(view)]


def run_mission_cycle_command(console: JarvisConsole, args: Namespace) -> list[str]:
    mission_state = console.get_objective_state(mission_id=args.mission_id)
    memory_service = _memory_service_from_args(args)
    evolution_service = _evolution_service_from_args(args)
    records = memory_service.list_experience_reflections(
        mission_id=args.mission_id,
        workflow_profile=args.workflow_profile,
        limit=max(1, args.limit),
    )
    review_items = evolution_service.list_human_review_queue(limit=max(1, args.limit))
    flow_audit = console.orchestrator.observability_service.audit_flow(
        ObservabilityQuery(mission_id=args.mission_id, limit=100)
    )
    return [
        render_mission_cycle(
            mission_id=args.mission_id,
            mission_state=mission_state,
            records=records,
            review_items=review_items,
            flow_audit=flow_audit,
        )
    ]


def run_operator_dashboard_command(console: JarvisConsole, args: Namespace) -> list[str]:
    mission_state = (
        console.get_objective_state(mission_id=args.mission_id)
        if args.mission_id
        else None
    )
    memory_service = _memory_service_from_args(args)
    evolution_service = _evolution_service_from_args(args)
    records = memory_service.list_experience_reflections(
        mission_id=args.mission_id,
        workflow_profile=args.workflow_profile,
        limit=max(1, args.limit),
    )
    review_items = evolution_service.list_human_review_queue(limit=max(1, args.limit))
    flow_audit = (
        console.orchestrator.observability_service.audit_flow(
            ObservabilityQuery(mission_id=args.mission_id, limit=100)
        )
        if args.mission_id
        else None
    )
    return [
        render_operator_dashboard(
            mission_id=args.mission_id,
            mission_state=mission_state,
            records=records,
            review_items=review_items,
            flow_audit=flow_audit,
        )
    ]


def run_readiness_dashboard_command(args: Namespace) -> list[str]:
    report = build_repository_readiness_report(
        root=ROOT,
        gate_mode=args.run_gate,
        longitudinal_report_path=(
            Path(args.longitudinal_report).expanduser()
            if args.longitudinal_report
            else None
        ),
    )
    return [render_readiness_dashboard(report)]


def run_longitudinal_learning_report_command(args: Namespace) -> list[str]:
    observability_db = (
        Path(args.observability_db)
        if args.observability_db
        else ROOT / ".jarvis_runtime" / "observability.db"
    ).expanduser()
    if not observability_db.is_absolute():
        observability_db = (Path.cwd() / observability_db).resolve()
    report = build_longitudinal_report(
        observability_service=ObservabilityService(
            database_path=str(observability_db)
        ),
        memory_service=_memory_service_from_args(args),
        evolution_service=_evolution_service_from_args(args),
        limit=max(1, min(args.limit, 500)),
        minimum_observations=args.minimum_observations,
    )
    return [render_longitudinal_learning_report(report)]


def run_progress_report_command(console: JarvisConsole, args: Namespace) -> list[str]:
    result = console.inspect_progress_report(
        mission_id=args.mission_id,
        session_id=args.session_id,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_mission_progress_report(result)]


def run_mission_workflow_command(console: JarvisConsole, args: Namespace) -> list[str]:
    response = console.ask(
        args.prompt,
        session_id=args.session_id,
        mission_id=args.mission_id,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    evolution_service = _evolution_service_from_args(args)
    proposal = _create_review_proposal_from_response(evolution_service, response)
    records = console.orchestrator.memory_service.list_experience_reflections(
        mission_id=args.mission_id,
        workflow_profile=(
            response.experience_record.workflow_profile
            if response.experience_record is not None
            else None
        ),
        limit=5,
    )
    review_items = evolution_service.list_human_review_queue(limit=5)
    flow_audit = console.orchestrator.observability_service.audit_flow(
        ObservabilityQuery(request_id=str(response.request_id), limit=100)
    )
    cycle_report = render_mission_cycle(
        mission_id=args.mission_id,
        mission_state=console.get_objective_state(mission_id=args.mission_id),
        records=records,
        review_items=review_items,
        flow_audit=flow_audit,
    )
    return [
        render_mission_workflow_report(
            response=response,
            proposal=proposal,
            cycle_report=cycle_report,
        )
    ]


def run_mission_feedback_command(
    console: JarvisConsole,
    args: Namespace,
) -> list[str]:
    result = console.record_mission_feedback(
        mission_id=args.mission_id,
        session_id=args.session_id,
        assessment=args.assessment,
        rating=args.rating,
        comment=args.comment,
        correction=args.correction,
        next_expectation=args.next_expectation,
        evidence_refs=list(args.evidence_ref),
        experience_id=args.experience_id,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    proposal = None
    if (
        result.feedback is not None
        and result.experience_record is not None
        and result.post_task_reflection is not None
    ):
        proposal = _evolution_service_from_args(
            args
        ).create_proposal_from_operator_feedback(
            result.feedback,
            experience=result.experience_record,
            reflection=result.post_task_reflection,
        )
    return [render_operator_feedback_result(result, proposal=proposal)]


def _create_review_proposal_from_response(
    evolution_service: EvolutionLabService,
    response: OrchestratorResponse,
) -> object | None:
    experience = response.experience_record
    reflection = response.post_task_reflection
    if experience is None or reflection is None:
        return None
    return evolution_service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id=experience.experience_id,
            mission_id=str(experience.mission_id),
            workflow_profile=experience.workflow_profile,
            outcome_status=experience.outcome_status,
            learning_candidate=reflection.learning_candidate,
            recommendation=reflection.recommendation,
            evidence_refs=list(reflection.evidence_refs),
            proposed_tests=list(reflection.proposed_tests),
            rollback_plan_ref=reflection.rollback_plan_ref,
            proposed_change_type=reflection.proposed_change_type,
        )
    )


def run_evolution_review_queue_command(args: Namespace) -> list[str]:
    service = _evolution_service_from_args(args)
    items = service.list_human_review_queue(limit=max(1, args.limit))
    return [render_evolution_review_queue(items)]


def run_evolution_review_command(args: Namespace) -> list[str]:
    service = _evolution_service_from_args(args)
    decision = service.review_proposal(
        evolution_proposal_id=args.proposal_id,
        action=args.action,
        operator_ref=args.operator_ref,
        evidence_refs=list(args.evidence_ref),
        proposed_tests=list(args.proposed_test),
        rollback_plan_ref=args.rollback_plan_ref,
        risk_acceptance=args.risk_acceptance,
        review_notes=list(args.note),
    )
    return [render_evolution_review_decision(decision)]


def run_memory_lifecycle_review_queue_command(args: Namespace) -> list[str]:
    service = _memory_service_from_args(args)
    items = service.list_memory_lifecycle_review_queue(
        maintenance_action=args.maintenance_action,
        review_status=args.review_status,
        limit=max(1, args.limit),
    )
    return [render_memory_lifecycle_review_queue(items)]


def run_memory_lifecycle_review_command(args: Namespace) -> list[str]:
    service = _memory_service_from_args(args)
    candidate = service.get_memory_lifecycle_candidate(args.candidate_id)
    if candidate is None:
        raise ValueError(f"unknown memory lifecycle candidate: {args.candidate_id}")
    previous_decisions = service.list_memory_lifecycle_review_decisions(
        candidate_id=candidate.candidate_id,
        limit=1,
    )
    previous_review_status = (
        previous_decisions[0].decision.review_status if previous_decisions else None
    )
    assessment = GovernanceService().assess_memory_lifecycle_review(
        candidate,
        decision_action=args.action,
        operator_ref=args.operator_ref,
        evidence_refs=list(args.evidence_ref),
        rollback_plan_ref=args.rollback_plan_ref,
        previous_review_status=previous_review_status,
    )
    decision = None
    if assessment.status == "governed":
        decision = service.record_memory_lifecycle_review_decision(
            candidate_id=candidate.candidate_id,
            decision_action=args.action,
            operator_ref=args.operator_ref,
            evidence_refs=list(args.evidence_ref),
            rollback_plan_ref=args.rollback_plan_ref,
            review_notes=list(args.note),
            governance_assessment=assessment,
        )
    return [
        render_memory_lifecycle_review_result(
            assessment=assessment,
            decision=decision,
        )
    ]


BOUND_COMMAND_REGISTRY = COMMAND_REGISTRY.bind(globals())


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command, outputs = BOUND_COMMAND_REGISTRY.invoke(
        args.command,
        args=args,
        console_factory=lambda: JarvisConsole.build(
            runtime_dir=ROOT / ".jarvis_runtime" / "console"
        ),
    )
    for output in command.emitted_outputs(args=args, outputs=outputs):
        print(output)
    return 0
