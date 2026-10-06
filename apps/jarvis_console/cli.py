# ruff: noqa: E402
"""Minimal console surface for the JARVIS v1 baseline."""

from __future__ import annotations

import json
from argparse import SUPPRESS, ArgumentParser, Namespace
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sys import argv as process_argv
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.registry import COMMAND_REGISTRY, CommandExecutionResult
from apps.jarvis_console.runtime import (
    ConsoleCommandError,
    ConsoleExitCode,
    ConsoleRuntime,
)

ensure_src_paths()

from evolution_lab.service import EvolutionLabService, PostTaskReflectionInput
from governance_service.service import GovernanceService
from knowledge_service.service import KnowledgeService
from memory_service.service import MemoryService, WorkflowLifecycleIntegrityError
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import (
    ArtifactLifecycleTransitionResult,
    LongHorizonGoalStrategyResult,
    MissionProgressReportResult,
    ObjectiveTransitionResult,
    OpenLoopResumeResult,
    OperatorFeedbackResult,
    OrchestratorResponse,
    OrchestratorService,
    WorkItemTransitionResult,
)

from apps.jarvis_console.commands.doctor import (
    build_doctor_report,
    render_doctor_report,
)
from apps.jarvis_console.reference import (
    render_command_reference,
    render_shell_completion,
)
from shared.action_confirmation import human_confirmation_receipt_fingerprint
from shared.autonomy_ladder import AUTONOMY_LEVEL_ORDER
from shared.contracts import (
    DailyOperatorUtilityReportContract,
    DailyOperatorWorkspaceContract,
    DecisionOutcomeAttributionReportContract,
    HumanConfirmationReceiptContract,
    InputContract,
    LongHorizonGoalStrategyContract,
    LongitudinalLearningReportContract,
    MissionStateContract,
    OpenLoopRegistryContract,
    RegressionReadinessReportContract,
    SkillEvolutionOperatorViewContract,
    TechnologyExperimentEvalRunContract,
    TechnologyExperimentPackContract,
    TechnologyRadarIntakeContract,
)
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId
from tools.daily_operator_utility_report import build_daily_operator_utility_report
from tools.decision_attribution_report import (
    build_decision_attribution_report,
)
from tools.decision_attribution_report import (
    save_report as save_decision_attribution_report,
)
from tools.longitudinal_learning_report import build_longitudinal_report
from tools.readiness_dashboard import build_repository_readiness_report
from tools.technology_experiment import (
    TechnologyExperimentRegistrationResult,
    assess_technology_experiment_pack_manifest,
    prepare_technology_experiment_eval_manifest,
    record_technology_experiment_eval,
    register_technology_experiment_pack,
)
from tools.technology_radar_intake import (
    TechnologyRadarIntakeRegistrationResult,
    assess_technology_radar_intake_manifest,
    register_technology_radar_intake,
)

CONSOLE_SURFACE_ID = "surface://jarvis_console"
CONSOLE_SURFACE_KIND = "console"
CONSOLE_SURFACE_CAPABILITIES = ["text_input", "core_orchestrated_response"]
DEFAULT_OPERATOR_IDENTITY_REF = "operator://local_console"
DEFAULT_CANONICAL_USER_REF = "user://local_operator"
MAX_CONSOLE_FIELD_LENGTH = 500


class ConsoleArgumentParser(ArgumentParser):
    def error(self, message: str) -> None:
        raise ConsoleCommandError(
            message,
            error_code="invalid_cli_usage",
            exit_code=ConsoleExitCode.USAGE_ERROR,
        )


class _LocalConsoleObservability(ObservabilityService):
    @staticmethod
    def _build_agentic_adapter():
        return None


@dataclass
class JarvisConsole:
    orchestrator: OrchestratorService

    @classmethod
    def build(
        cls,
        *,
        runtime_dir: Path | None = None,
        database_url: str | None = None,
        local_observability_only: bool = False,
    ) -> "JarvisConsole":
        if type(local_observability_only) is not bool:
            raise ValueError("invalid_local_observability_option")
        observability_type = (
            _LocalConsoleObservability if local_observability_only else ObservabilityService
        )
        if runtime_dir is None:
            governance_service = GovernanceService()
            operational_service = OperationalService(
                action_confirmation_verifier=(
                    governance_service.verify_action_confirmation_claim
                )
            )
            return cls(
                orchestrator=OrchestratorService(
                    governance_service=governance_service,
                    operational_service=operational_service,
                    observability_service=observability_type(),
                )
            )
        runtime_dir.mkdir(parents=True, exist_ok=True)
        default_database_url = f"sqlite:///{(runtime_dir / 'memory.db').as_posix()}"
        resolved_database_url = database_url or default_database_url
        evolution_service = EvolutionLabService(
            database_path=str(runtime_dir / "evolution.db")
        )
        governance_service = GovernanceService(
            action_confirmation_database_path=runtime_dir / "governance.db"
        )
        operational_service = OperationalService(
            artifact_dir=str(runtime_dir / "artifacts"),
            action_confirmation_verifier=(
                governance_service.verify_action_confirmation_claim
            ),
        )
        return cls(
            orchestrator=OrchestratorService(
                governance_service=governance_service,
                memory_service=MemoryService(
                    database_url=resolved_database_url,
                    reviewed_procedural_playbook_verifier=(
                        evolution_service.verify_persisted_reviewed_procedural_playbook
                    ),
                    workflow_lifecycle_transition_verifier=(
                        evolution_service.verify_persisted_workflow_lifecycle_transition
                    ),
                ),
                operational_service=operational_service,
                observability_service=observability_type(
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
        requested_autonomy_level: str | None = None,
        max_autonomy_level: str | None = None,
        autonomy_confirmation_mode: str | None = None,
        action_confirmation_receipt_id: str | None = None,
        action_confirmation_origin_request_id: str | None = None,
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
            requested_autonomy_level=requested_autonomy_level,
            max_autonomy_level=max_autonomy_level,
            autonomy_confirmation_mode=autonomy_confirmation_mode,
            action_confirmation_receipt_id=action_confirmation_receipt_id,
            action_confirmation_origin_request_id=(
                action_confirmation_origin_request_id
            ),
        )
        return self.orchestrator.handle_input(contract)

    def confirm_action_challenge(
        self,
        *,
        challenge_id: str,
        action_fingerprint: str,
        operator_identity_ref: str,
    ) -> HumanConfirmationReceiptContract:
        """Persist exact operator evidence without granting execution authority."""

        return self.orchestrator.governance_service.confirm_action_challenge(
            challenge_id,
            operator_identity_ref=operator_identity_ref,
            expected_action_fingerprint=action_fingerprint,
        )

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
        dependency_refs: list[str] | None = None,
        priority_level: str | None = None,
        blocker_refs: list[str] | None = None,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> WorkItemTransitionResult:
        return self.orchestrator.transition_work_item(
            mission_id=mission_id,
            work_item_ref=work_item_ref,
            transition=transition,
            session_id=session_id,
            next_action_ref=next_action_ref,
            dependency_refs=dependency_refs,
            priority_level=priority_level,
            blocker_refs=blocker_refs,
            operator_identity_ref=operator_identity_ref or DEFAULT_OPERATOR_IDENTITY_REF,
            canonical_user_ref=canonical_user_ref or DEFAULT_CANONICAL_USER_REF,
        )

    def get_open_loop_registry(
        self,
        *,
        mission_id: str,
    ) -> OpenLoopRegistryContract | None:
        mission_state = self.get_objective_state(mission_id=mission_id)
        if mission_state is None:
            return None
        return self.orchestrator.operational_service.build_open_loop_registry(
            mission_state,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def resume_open_loop(
        self,
        *,
        mission_id: str,
        open_loop_ref: str,
        session_id: str,
        operator_identity_ref: str | None = None,
        canonical_user_ref: str | None = None,
    ) -> OpenLoopResumeResult:
        return self.orchestrator.resume_open_loop(
            mission_id=mission_id,
            open_loop_ref=open_loop_ref,
            session_id=session_id,
            operator_identity_ref=operator_identity_ref
            or DEFAULT_OPERATOR_IDENTITY_REF,
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
    parser = ConsoleArgumentParser(description="Run the minimal JARVIS console.")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        dest="output_format",
        default="text",
        help="Select human text or supported machine-readable JSON output.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    transcript_parser = subparsers.add_parser(
        "transcript-review",
        help="Revalidate supplied transcript text before explicit local Core handoff.",
    )
    transcript_parser.add_argument("--authorized", action="store_true",
                                   help="Opt into a new canonical Core turn after validation.")
    transcript_parser.add_argument("--session-id", default="transcript-review",
                                   help="Local session binding, not operator authentication.")
    transcript_parser.add_argument("--include-content", action="store_true",
                                   help="Display exact reviewed text and Core final if safe.")
    from apps.jarvis_console.transcript_tts_options import add_transcript_tts_arguments

    add_transcript_tts_arguments(transcript_parser)

    account_parser = subparsers.add_parser(
        "chatgpt-account",
        help="Manage an explicit private ChatGPT provider account; no Core authority.",
    )
    account_parser.add_argument("--authorized", action="store_true",
                                help="Explicit opt-in before storage, browser or network use.")
    account_parser.add_argument("--credential-dir", required=True, type=Path,
                                help="Absolute private directory outside Git/OneDrive; "
                                "parent exists.")
    account_parser.add_argument("--action", required=True,
                                choices=["connect", "profiles", "catalog", "refresh"])
    account_parser.add_argument("--profile-ref", help="Opaque reference from profiles/connect.")
    account_parser.add_argument("--timeout-seconds", type=int, default=300,
                                help="Loopback authorization budget (1..600 seconds).")

    jobs_parser = subparsers.add_parser(
        "job-inspect", help="Inspect exact jobs in an existing read-only ledger; never execute.",
    )
    jobs_parser.add_argument("--job-db", required=True, type=Path,
                             help="Explicit existing absolute quiescent SQLite database.")
    jobs_parser.add_argument("--actor-ref", required=True)
    jobs_parser.add_argument("--session-ref", required=True)
    jobs_parser.add_argument("--job-id", required=True, action="append")
    jobs_parser.add_argument("--include-refs", action="store_true",
                             help="Opt into bounded caller-scoped ledger references.")

    for command_id, help_text in (
        ("code-review", "Review a bounded in-memory patch supplied on stdin; never apply."),
        ("research-review", "Review lexical evidence from supplied texts; never fetch or trust."),
    ):
        review_parser = subparsers.add_parser(command_id, help=help_text)
        review_parser.add_argument(
            "--include-content", action="store_true",
            help="Opt into escaped untrusted diff or exact evidence excerpts.",
        )

    recall_parser = subparsers.add_parser(
        "memory-recall", help="Inspect bounded read-only canonical turn evidence.",
    )
    recall_parser.add_argument("--memory-db", required=True, type=Path,
                               help="Explicit existing absolute quiescent SQLite database.")
    recall_parser.add_argument("--subject-id", required=True)
    recall_parser.add_argument("--session-id", required=True, action="append",
                               help="Explicit canonical session; repeat to allow another.")
    recall_parser.add_argument("--query", required=True)
    recall_parser.add_argument("--limit", type=int, default=4)
    recall_parser.add_argument("--include-content", action="store_true",
                               help="Opt into bounded untrusted evidence excerpts.")

    physical_parser = subparsers.add_parser(
        "physical", help="Inspect and control exact opt-in physical artifact operations.",
    )
    physical_parser.add_argument("--runtime-dir", required=True, type=Path)
    physical_parser.add_argument("--root", action="append", required=True,
                                 help="Explicit alias=absolute-directory; repeat for each root.")
    physical_parser.add_argument("--enable-execution", action="store_true",
                                 help="Opt into Linux physical execution; Windows refuses.")
    physical_parser.add_argument("--action", required=True, choices=[
        "prepare", "inspect", "confirm", "execute", "status", "recover",
        "prepare-rollback", "confirm-rollback", "rollback",
    ])
    physical_parser.add_argument("--request-id")
    physical_parser.add_argument("--mission-id")
    physical_parser.add_argument("--work-item-ref")
    physical_parser.add_argument("--artifact-ref")
    physical_parser.add_argument("--resource-ref")
    physical_parser.add_argument("--desired-file", type=Path)
    physical_parser.add_argument("--operation", choices=["create_text", "replace_text"],
                                 default="create_text")
    physical_parser.add_argument("--expected-current-sha256")
    physical_parser.add_argument("--supersedes-artifact-ref")
    physical_parser.add_argument("--challenge-id")
    physical_parser.add_argument("--action-fingerprint")
    physical_parser.add_argument("--confirmation-receipt-id")
    physical_parser.add_argument("--session-id", default="console-physical")
    physical_parser.add_argument("--operator-identity-ref", default=DEFAULT_OPERATOR_IDENTITY_REF)
    physical_parser.add_argument("--canonical-user-ref", default=DEFAULT_CANONICAL_USER_REF)
    physical_parser.add_argument("--show-diff", action="store_true",
                                 help="Print sensitive ephemeral diff explicitly; never telemetry.")

    ask_parser = subparsers.add_parser("ask", help="Execute a single prompt.")
    ask_parser.add_argument("prompt", help="Single prompt to send to JARVIS.")
    ask_parser.add_argument("--session-id", default="console-ask")
    ask_parser.add_argument("--mission-id")
    ask_parser.add_argument("--operator-identity-ref")
    ask_parser.add_argument("--canonical-user-ref")
    ask_parser.add_argument(
        "--requested-autonomy-level",
        choices=AUTONOMY_LEVEL_ORDER,
        help="Request one canonical bounded autonomy level.",
    )
    ask_parser.add_argument(
        "--max-autonomy-level",
        choices=AUTONOMY_LEVEL_ORDER,
        help="Set the maximum canonical autonomy level for this request.",
    )
    ask_parser.add_argument(
        "--autonomy-confirmation-mode",
        choices=["explicit"],
        help="Require explicit confirmation when the selected action needs it.",
    )
    ask_parser.add_argument(
        "--action-confirmation-receipt-id",
        help="Present one exact, unclaimed confirmation receipt for this retry.",
    )
    ask_parser.add_argument(
        "--action-confirmation-origin-request-id",
        "--origin-request-id",
        dest="action_confirmation_origin_request_id",
        help="Bind the retry to the request that produced the challenge.",
    )
    ask_parser.add_argument("--debug", action="store_true")

    action_confirm_parser = subparsers.add_parser(
        "action-confirm",
        help="Record exact human confirmation evidence without granting authority.",
    )
    action_confirm_parser.add_argument("--challenge-id", required=True)
    action_confirm_parser.add_argument("--action-fingerprint", required=True)
    action_confirm_parser.add_argument("--operator-identity-ref", required=True)

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
            "update",
            "resume",
            "pause",
            "block",
            "complete",
            "redefine-next-action",
        ],
    )
    work_item_parser.add_argument("--work-item-ref", required=True)
    work_item_parser.add_argument("--next-action-ref")
    work_item_dependency_group = work_item_parser.add_mutually_exclusive_group()
    work_item_dependency_group.add_argument(
        "--depends-on",
        dest="dependency_refs",
        action="append",
        help="Add a governed dependency ref; repeat for multiple dependencies.",
    )
    work_item_dependency_group.add_argument(
        "--clear-dependencies",
        action="store_true",
        help="Replace the dependency set with an empty governed set.",
    )
    work_item_parser.add_argument(
        "--priority",
        dest="priority_level",
        choices=["p0", "p1", "p2", "p3"],
    )
    work_item_parser.add_argument(
        "--blocker-ref",
        dest="blocker_refs",
        action="append",
        help="Declare an explicit blocker; required by the block action.",
    )
    work_item_parser.add_argument("--operator-identity-ref")
    work_item_parser.add_argument("--canonical-user-ref")

    open_loops_parser = subparsers.add_parser(
        "open-loops",
        help="Show governed open loops eligible for explicit resume.",
    )
    open_loops_parser.add_argument("--mission-id", required=True)

    resume_loop_parser = subparsers.add_parser(
        "resume-loop",
        help="Explicitly resume one governed open loop without autonomous execution.",
    )
    resume_loop_parser.add_argument("--mission-id", required=True)
    resume_loop_parser.add_argument("--open-loop-ref", required=True)
    resume_loop_parser.add_argument("--session-id", default="console-resume-loop")
    resume_loop_parser.add_argument("--operator-identity-ref")
    resume_loop_parser.add_argument("--canonical-user-ref")

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

    technology_intake_parser = subparsers.add_parser(
        "technology-radar-intake",
        help="Register one reviewed local technology reference without fetching it.",
    )
    technology_intake_parser.add_argument("--evolution-db")
    technology_intake_parser.add_argument("--intake-root", required=True)
    technology_intake_parser.add_argument("--manifest", required=True)
    technology_intake_parser.add_argument(
        "--manifest-sha256",
        required=True,
        help="Bind registration to the detached SHA-256 reviewed by the operator.",
    )

    technology_radar_parser = subparsers.add_parser(
        "technology-radar",
        help="Show verified reviewed references from the technology radar.",
    )
    technology_radar_parser.add_argument("--evolution-db")
    technology_radar_parser.add_argument(
        "--intake-id",
        help="Resolve one exact intake instead of listing the registry.",
    )
    technology_radar_parser.add_argument("--candidate-ref")
    technology_radar_parser.add_argument("--intake-version")
    technology_radar_parser.add_argument("--source-kind")
    technology_radar_parser.add_argument("--absorption-class")
    technology_radar_parser.add_argument("--target-gap-ref")
    technology_radar_parser.add_argument("--limit", type=int, default=20)
    technology_radar_parser.add_argument("--offset", type=int, default=0)

    technology_experiment_pack_parser = subparsers.add_parser(
        "technology-experiment-pack",
        help="Register one inert sandbox experiment pack from a reviewed intake.",
    )
    technology_experiment_pack_parser.add_argument("--evolution-db")
    technology_experiment_pack_parser.add_argument("--manifest-root", required=True)
    technology_experiment_pack_parser.add_argument("--manifest", required=True)
    technology_experiment_pack_parser.add_argument(
        "--manifest-sha256",
        required=True,
        help="Bind registration to the detached SHA-256 reviewed by the operator.",
    )

    technology_experiment_eval_parser = subparsers.add_parser(
        "technology-experiment-eval",
        help="Derive and append one offline paired technology experiment evaluation.",
    )
    technology_experiment_eval_parser.add_argument("--evolution-db")
    technology_experiment_eval_parser.add_argument("--manifest-root", required=True)
    technology_experiment_eval_parser.add_argument("--manifest", required=True)
    technology_experiment_eval_parser.add_argument(
        "--manifest-sha256",
        required=True,
        help="Bind evaluation to the detached SHA-256 reviewed by the operator.",
    )

    technology_experiments_parser = subparsers.add_parser(
        "technology-experiments",
        help="Show verified inert technology experiment packs or evaluation runs.",
    )
    technology_experiments_parser.add_argument("--evolution-db")
    technology_experiments_parser.add_argument(
        "--view",
        choices=["packs", "runs"],
        default="packs",
    )
    technology_experiments_parser.add_argument("--experiment-pack-id")
    technology_experiments_parser.add_argument("--pack-version")
    technology_experiments_parser.add_argument("--run-id")
    technology_experiments_parser.add_argument("--intake-id")
    technology_experiments_parser.add_argument("--candidate-ref")
    technology_experiments_parser.add_argument("--status")
    technology_experiments_parser.add_argument("--limit", type=int, default=20)
    technology_experiments_parser.add_argument("--offset", type=int, default=0)

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

    workflow_lifecycle_parser = subparsers.add_parser(
        "workflow-lifecycle",
        help="Show the verified active workflow binding and transition history.",
    )
    workflow_lifecycle_parser.add_argument(
        "--memory-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "memory.db"),
        help="Use an explicit canonical memory store (defaults to the console store).",
    )
    workflow_lifecycle_parser.add_argument(
        "--evolution-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "evolution.db"),
        help="Use the release-bundle store paired with canonical console memory.",
    )
    workflow_lifecycle_parser.add_argument("--workflow-profile")
    workflow_lifecycle_parser.add_argument("--route")
    workflow_lifecycle_parser.add_argument("--limit", type=int, default=20)
    workflow_lifecycle_parser.add_argument("--offset", type=int, default=0)

    workflow_transition_parser = subparsers.add_parser(
        "workflow-transition",
        help="Record an explicit governed workflow activation or rollback.",
    )
    workflow_transition_parser.add_argument(
        "--memory-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "memory.db"),
        help="Use an explicit canonical memory store (defaults to the console store).",
    )
    workflow_transition_parser.add_argument(
        "--evolution-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "evolution.db"),
        help="Use the release-bundle store paired with canonical console memory.",
    )
    workflow_transition_parser.add_argument("--workflow-profile", required=True)
    workflow_transition_parser.add_argument("--route", required=True)
    workflow_transition_parser.add_argument(
        "--action",
        required=True,
        choices=["activate_candidate", "rollback_to_baseline"],
    )
    workflow_transition_parser.add_argument("--proposal-id", required=True)
    workflow_transition_parser.add_argument("--workflow-eval-run-id", required=True)
    workflow_transition_parser.add_argument(
        "--human-authorization-ref",
        required=True,
    )
    workflow_transition_parser.add_argument(
        "--operator-ref",
        default=DEFAULT_OPERATOR_IDENTITY_REF,
    )
    workflow_transition_parser.add_argument(
        "--evidence-ref",
        action="append",
        required=True,
        help="Bind explicit release evidence; repeat for multiple references.",
    )
    workflow_transition_parser.add_argument(
        "--completed-test-ref",
        action="append",
        required=True,
        help="Bind each completed candidate test exactly as reviewed.",
    )
    workflow_transition_parser.add_argument(
        "--completed-external-gate",
        action="append",
        required=True,
        choices=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
        help="Bind each completed external release gate.",
    )
    workflow_transition_parser.add_argument(
        "--failure-ref",
        action="append",
        default=[],
        help="Bind an observed failure; required for rollback.",
    )
    workflow_transition_parser.add_argument("--transition-id")

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

    daily_workspace_parser = subparsers.add_parser(
        "daily-workspace",
        help="Show a read-only cross-session operator workspace.",
    )
    daily_workspace_parser.add_argument(
        "--memory-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "memory.db"),
        help="Use an explicit canonical memory store (defaults to the console store).",
    )
    daily_workspace_parser.add_argument("--evolution-db")
    daily_workspace_parser.add_argument("--limit", type=int, default=20)

    operator_outcomes_parser = subparsers.add_parser(
        "operator-outcomes",
        help="Show evidence-backed daily operator utility outcomes.",
    )
    operator_outcomes_parser.add_argument(
        "--observability-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "observability.db"),
    )
    operator_outcomes_parser.add_argument(
        "--memory-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "memory.db"),
    )
    operator_outcomes_parser.add_argument("--period-start")
    operator_outcomes_parser.add_argument("--period-end")
    operator_outcomes_parser.add_argument("--event-limit", type=int, default=1000)
    operator_outcomes_parser.add_argument("--mission-limit", type=int, default=200)

    decision_attribution_parser = subparsers.add_parser(
        "decision-attribution",
        help="Show read-only decision/outcome attribution evidence.",
    )
    decision_attribution_parser.add_argument(
        "--observability-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "observability.db"),
    )
    decision_attribution_parser.add_argument(
        "--memory-db",
        default=str(ROOT / ".jarvis_runtime" / "console" / "memory.db"),
    )
    decision_attribution_parser.add_argument("--request-id")
    decision_attribution_parser.add_argument("--mission-id")
    decision_attribution_parser.add_argument("--workflow-profile")
    decision_attribution_parser.add_argument("--limit", type=int, default=20)
    decision_attribution_parser.add_argument(
        "--output-dir",
        help="Persist derived report JSON outside canonical stores.",
    )

    subparsers.add_parser(
        "command-reference",
        help="Show the deterministic registry-derived command reference.",
    )
    completion_parser = subparsers.add_parser(
        "completion",
        help="Generate deterministic shell completion from the command registry.",
    )
    completion_parser.add_argument(
        "--shell",
        required=True,
        choices=["powershell", "bash", "zsh"],
        help="Select the target shell.",
    )

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

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run read-only local runtime and governance diagnostics.",
    )
    doctor_parser.add_argument("--runtime-dir")
    doctor_parser.add_argument("--memory-db")
    doctor_parser.add_argument("--evolution-db")
    doctor_parser.add_argument("--observability-db")

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

    for command_parser in subparsers.choices.values():
        command_parser.add_argument(
            "--format",
            choices=["text", "json"],
            dest="output_format",
            default=SUPPRESS,
            help="Select human text or supported machine-readable JSON output.",
        )
    COMMAND_REGISTRY.validate_parser_commands(
        {
            action.dest: action.help
            for action in subparsers._choices_actions
        }
    )
    return parser


def render_response(response: OrchestratorResponse, *, debug: bool) -> str:
    lines = [response.response_text]
    challenge = getattr(response, "action_confirmation_challenge", None)
    if challenge is not None:
        lines.extend(
            [
                "action_confirmation_required=True",
                f"challenge_id={safe_console_value(challenge.challenge_id)}",
                "origin_request_id="
                + safe_console_value(challenge.origin_request_id),
                "action_fingerprint="
                + safe_console_value(challenge.action_fingerprint),
                f"expires_at={safe_console_value(challenge.expires_at)}",
                "confirmation_evidence_only=True",
                "confirmation_execution_allowed=False",
            ]
        )
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


def render_action_confirmation_receipt(
    receipt: HumanConfirmationReceiptContract,
) -> str:
    """Render non-authorizing receipt evidence without action payload or paths."""

    return "\n".join(
        [
            f"receipt_id={safe_console_value(receipt.receipt_id)}",
            f"challenge_id={safe_console_value(receipt.challenge_id)}",
            "origin_request_id=" + safe_console_value(receipt.origin_request_id),
            "action_fingerprint=" + safe_console_value(receipt.action_fingerprint),
            "receipt_fingerprint="
            + safe_console_value(human_confirmation_receipt_fingerprint(receipt)),
            f"confirmed_at={safe_console_value(receipt.confirmed_at)}",
            f"expires_at={safe_console_value(receipt.expires_at)}",
            "confirmation_evidence_only=True",
            f"single_use={safe_console_value(receipt.single_use)}",
            f"read_only={safe_console_value(receipt.read_only)}",
            f"immutable={safe_console_value(receipt.immutable)}",
            f"execution_allowed={safe_console_value(receipt.execution_allowed)}",
            "tool_dispatch_allowed="
            + safe_console_value(receipt.tool_dispatch_allowed),
            "runtime_activation_allowed="
            + safe_console_value(receipt.runtime_activation_allowed),
            "promotion_authorized="
            + safe_console_value(receipt.promotion_authorized),
            "automatic_promotion_allowed="
            + safe_console_value(receipt.automatic_promotion_allowed),
            "core_mutation_allowed="
            + safe_console_value(receipt.core_mutation_allowed),
        ]
    )


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


def safe_console_metric(value: object | None) -> str:
    return "unavailable" if value is None else safe_console_value(value)


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
    for item in mission_state.work_items:
        if item.work_item_ref == work_item_ref:
            return item.work_item_status
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
    queue = OperationalService.build_work_item_queue(mission_state)
    if not queue.ordered_work_items:
        return f"No work items found for mission_id={safe_console_value(mission_id)}"
    lines = [
        f"mission_id={safe_console_value(mission_state.mission_id)}",
        f"objective_status={safe_console_value(mission_state.objective_status)}",
        f"next_action_ref={safe_console_value(mission_state.next_action_ref)}",
        f"queue_status={safe_console_value(queue.queue_status)}",
        "ordered_work_item_refs="
        + safe_console_list([item.work_item_ref for item in queue.ordered_work_items]),
        "executable_work_item_refs="
        + safe_console_list(queue.executable_work_item_refs),
        "blocked_work_item_refs=" + safe_console_list(queue.blocked_work_item_refs),
        f"ordering_policy={safe_console_value(queue.ordering_policy)}",
        "autonomous_execution_allowed=False",
    ]
    for rank, item in enumerate(queue.ordered_work_items, start=1):
        lines.extend(
            [
                "---",
                f"operator_order={rank}",
                f"work_item_ref={safe_console_value(item.work_item_ref)}",
                f"work_item_status={safe_console_value(item.work_item_status)}",
                f"priority_level={safe_console_value(item.priority_level)}",
                f"dependency_refs={safe_console_list(item.dependency_refs)}",
                f"blocking_state={safe_console_value(item.blocking_state)}",
                f"blocker_refs={safe_console_list(item.blocker_refs)}",
                f"next_action_ref={safe_console_value(item.next_action_ref)}",
                "is_executable="
                + safe_console_value(
                    item.work_item_ref in queue.executable_work_item_refs
                ),
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
            "priority_level="
            + safe_console_value(getattr(work_item_state, "priority_level", None)),
            "dependency_refs="
            + safe_console_list(
                list(getattr(work_item_state, "dependency_refs", []))
            ),
            "blocking_state="
            + safe_console_value(getattr(work_item_state, "blocking_state", None)),
            "blocker_refs="
            + safe_console_list(list(getattr(work_item_state, "blocker_refs", []))),
            f"next_action_ref={safe_console_value(result.next_action_ref)}",
            "active_work_items="
            + safe_console_list(list(getattr(mission_state, "active_work_items", []))),
            "work_item_refs="
            + safe_console_list(list(getattr(mission_state, "work_item_refs", []))),
            "memory_write_mode=through_core_only",
            f"event_names={safe_console_list([event.event_name for event in result.events])}",
        ]
    )


def render_open_loop_registry(
    registry: OpenLoopRegistryContract | None,
    *,
    mission_id: str,
) -> str:
    if registry is None or not registry.open_loop_states:
        return f"No open loops found for mission_id={safe_console_value(mission_id)}"
    lines = [
        f"mission_id={safe_console_value(registry.mission_id)}",
        f"registry_status={safe_console_value(registry.registry_status)}",
        f"freshness_status={safe_console_value(registry.freshness_status)}",
        f"mission_age_hours={safe_console_value(registry.mission_age_hours)}",
        "eligible_open_loop_refs=" + safe_console_list(registry.eligible_open_loop_refs),
        "blocked_open_loop_refs=" + safe_console_list(registry.blocked_open_loop_refs),
        "selected_work_item_ref="
        + safe_console_value(registry.selected_work_item_ref),
        "evidence_refs=" + safe_console_list(registry.evidence_refs),
        "open_loop_registry=read_only",
        "autonomous_resume_allowed=False",
        "autonomous_scheduling_allowed=False",
    ]
    eligible_refs = set(registry.eligible_open_loop_refs)
    for state in registry.open_loop_states:
        lines.extend(
            [
                "---",
                f"open_loop_ref={safe_console_value(state.open_loop_ref)}",
                f"loop_summary={safe_console_value(state.loop_summary)}",
                f"loop_status={safe_console_value(state.loop_status)}",
                "source_work_item_ref="
                + safe_console_value(state.source_work_item_ref),
                "eligible="
                + safe_console_value(state.open_loop_ref in eligible_refs),
                "blocking_reasons="
                + safe_console_list(
                    registry.blocking_reasons.get(state.open_loop_ref, [])
                ),
                f"resumed_at={safe_console_value(state.resumed_at)}",
                f"next_action_ref={safe_console_value(state.next_action_ref)}",
            ]
        )
    return "\n".join(lines)


def render_open_loop_resume(result: OpenLoopResumeResult) -> str:
    plan = result.resume_plan
    state = result.open_loop_state
    return "\n".join(
        [
            f"mission_id={safe_console_value(result.mission_id)}",
            f"open_loop_ref={safe_console_value(result.open_loop_ref)}",
            f"resume_status={safe_console_value(result.status)}",
            "governance_decision="
            + safe_console_value(result.governance_decision.decision),
            "loop_status=" + safe_console_value(getattr(state, "loop_status", None)),
            "loop_summary=" + safe_console_value(getattr(state, "loop_summary", None)),
            "next_action_ref="
            + safe_console_value(getattr(plan, "next_action_ref", None)),
            "next_action_summary="
            + safe_console_value(getattr(plan, "next_action_summary", None)),
            "selected_work_item_ref="
            + safe_console_value(getattr(plan, "selected_work_item_ref", None)),
            "evidence_refs="
            + safe_console_list(list(getattr(plan, "evidence_refs", []))),
            "response_text=" + safe_console_value(result.response_text),
            "memory_write_mode=through_core_only",
            "autonomous_resume_allowed=False",
            "autonomous_scheduling_allowed=False",
            "autonomous_execution_allowed=False",
            "event_names="
            + safe_console_list([event.event_name for event in result.events]),
        ]
    )


def artifact_status_from_state(
    mission_state: MissionStateContract | None,
    artifact_ref: str,
) -> str:
    if mission_state is None:
        return "missing"
    for artifact_state in mission_state.artifact_states:
        if artifact_state.artifact_ref == artifact_ref:
            return artifact_state.artifact_status
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
    registry = OperationalService.build_artifact_registry(mission_state)
    if not registry.artifact_states:
        return f"No artifacts found for mission_id={safe_console_value(mission_id)}"
    lines = [
        f"mission_id={safe_console_value(mission_state.mission_id)}",
        f"objective_ref={safe_console_value(mission_state.objective_ref)}",
        f"objective_status={safe_console_value(mission_state.objective_status)}",
        f"registry_status={safe_console_value(registry.registry_status)}",
        "active_artifact_refs=" + safe_console_list(registry.active_artifact_refs),
        "superseded_artifact_refs="
        + safe_console_list(registry.superseded_artifact_refs),
        "rolled_back_artifact_refs="
        + safe_console_list(registry.rolled_back_artifact_refs),
        "external_file_mutation_allowed=False",
    ]
    for artifact_state in registry.artifact_states:
        lines.extend(
            [
                "---",
                f"artifact_ref={safe_console_value(artifact_state.artifact_ref)}",
                f"artifact_status={safe_console_value(artifact_state.artifact_status)}",
                f"artifact_version={safe_console_value(artifact_state.artifact_version)}",
                "owner_mission_id="
                + safe_console_value(artifact_state.owner_mission_id),
                f"objective_ref={safe_console_value(artifact_state.objective_ref)}",
                f"work_item_ref={safe_console_value(artifact_state.work_item_ref)}",
                "lineage_root_ref="
                + safe_console_value(artifact_state.lineage_root_ref),
                "supersedes_artifact_ref="
                + safe_console_value(artifact_state.supersedes_artifact_ref),
                "replacement_artifact_ref="
                + safe_console_value(artifact_state.replacement_artifact_ref),
                "rollback_plan_ref="
                + safe_console_value(artifact_state.rollback_plan_ref),
                f"created_at={safe_console_value(artifact_state.created_at)}",
                f"updated_at={safe_console_value(artifact_state.updated_at)}",
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
            "resulting_artifact_ref="
            + safe_console_value(result.resulting_artifact_ref),
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
            "owner_mission_id="
            + safe_console_value(getattr(artifact_state, "owner_mission_id", None)),
            "lineage_root_ref="
            + safe_console_value(getattr(artifact_state, "lineage_root_ref", None)),
            "supersedes_artifact_ref="
            + safe_console_value(
                getattr(artifact_state, "supersedes_artifact_ref", None)
            ),
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
            "external_file_mutation_allowed=False",
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


def render_technology_radar_intakes(
    intakes: list[TechnologyRadarIntakeContract],
) -> str:
    if not intakes:
        return "No reviewed technology radar intakes found."
    lines: list[str] = []
    for intake in intakes:
        lines.extend(
            [
                f"intake_id={safe_console_value(intake.intake_id)}",
                f"candidate_ref={safe_console_value(intake.candidate_ref)}",
                f"intake_version={safe_console_value(intake.intake_version)}",
                f"technology_name={safe_console_value(intake.technology_name)}",
                f"source_kind={safe_console_value(intake.source_kind)}",
                f"source_locator={safe_console_value(intake.source_locator)}",
                "source_version_ref="
                + safe_console_value(intake.source_version_ref),
                "source_content_sha256="
                + safe_console_value(intake.source_content_sha256),
                f"license_id={safe_console_value(intake.license_id)}",
                f"license_status={safe_console_value(intake.license_status)}",
                f"retrieved_at={safe_console_value(intake.retrieved_at)}",
                f"claims={safe_console_list(intake.claims)}",
                f"risks={safe_console_list(intake.risks)}",
                "absorption_class="
                + safe_console_value(intake.absorption_class),
                f"target_gap_refs={safe_console_list(intake.target_gap_refs)}",
                f"review_status={safe_console_value(intake.review_status)}",
                f"reviewer_ref={safe_console_value(intake.reviewer_ref)}",
                f"reviewed_at={safe_console_value(intake.reviewed_at)}",
                "source_trust_status="
                + safe_console_value(intake.source_trust_status),
                "network_fetch_allowed=False",
                "knowledge_ingestion_allowed=False",
                "dependency_installation_allowed=False",
                "execution_allowed=False",
                "runtime_activation_allowed=False",
                "promotion_authorized=False",
                "automatic_promotion_allowed=False",
                "core_mutation_allowed=False",
                "priority_mutation_allowed=False",
                "---",
            ]
        )
    if lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)


def render_technology_radar_intake_registration(
    result: TechnologyRadarIntakeRegistrationResult,
) -> str:
    return "\n".join(
        [
            f"intake_id={safe_console_value(result.intake.intake_id)}",
            f"candidate_ref={safe_console_value(result.intake.candidate_ref)}",
            f"intake_version={safe_console_value(result.intake.intake_version)}",
            f"intake_fingerprint={safe_console_value(result.intake_fingerprint)}",
            f"assessment_status={safe_console_value(result.assessment.status)}",
            f"persistence_status={safe_console_value(result.persistence_status)}",
            "source_trusted=False",
            "network_fetch_performed=False",
            "knowledge_ingestion_performed=False",
            "evolution_proposal_created=False",
            "dependency_installation_performed=False",
            "execution_performed=False",
            "runtime_activation_performed=False",
            "promotion_performed=False",
            "core_mutation_performed=False",
            "priority_mutation_performed=False",
        ]
    )


def render_technology_experiment_registration(
    result: TechnologyExperimentRegistrationResult,
) -> str:
    pack = result.pack
    return "\n".join(
        [
            f"experiment_pack_id={safe_console_value(pack.experiment_pack_id)}",
            f"pack_version={safe_console_value(pack.pack_version)}",
            f"pack_fingerprint={safe_console_value(result.pack_fingerprint)}",
            f"intake_id={safe_console_value(pack.intake_id)}",
            f"pattern_id={safe_console_value(pack.pattern_id)}",
            "sovereign_consumer_ref="
            + safe_console_value(pack.sovereign_consumer_ref),
            f"pack_status={safe_console_value(pack.pack_status)}",
            f"persistence_status={safe_console_value(result.persistence_status)}",
            "sandbox_only=True",
            "source_fetched=False",
            "dependency_installed=False",
            "candidate_imported=False",
            "candidate_executed=False",
            "core_called=False",
            "tool_dispatched=False",
            "runtime_activated=False",
            "promotion_performed=False",
            "core_mutated=False",
            "priority_mutated=False",
        ]
    )


def render_technology_experiment_packs(
    packs: list[TechnologyExperimentPackContract],
) -> str:
    if not packs:
        return "No verified technology experiment packs found."
    lines: list[str] = []
    for pack in packs:
        lines.extend(
            [
                f"experiment_pack_id={safe_console_value(pack.experiment_pack_id)}",
                f"pack_version={safe_console_value(pack.pack_version)}",
                f"intake_id={safe_console_value(pack.intake_id)}",
                f"candidate_ref={safe_console_value(pack.candidate_ref)}",
                f"pattern_id={safe_console_value(pack.pattern_id)}",
                f"pattern_name={safe_console_value(pack.pattern_name)}",
                f"translation_kind={safe_console_value(pack.translation_kind)}",
                "sovereign_consumer_ref="
                + safe_console_value(pack.sovereign_consumer_ref),
                f"target_gap_refs={safe_console_list(pack.target_gap_refs)}",
                f"license_id={safe_console_value(pack.license_id)}",
                f"license_status={safe_console_value(pack.license_status)}",
                f"pack_status={safe_console_value(pack.pack_status)}",
                f"case_count={safe_console_value(len(pack.cases))}",
                f"rollback_plan_ref={safe_console_value(pack.rollback_plan_ref)}",
                "network_fetch_allowed=False",
                "dependency_installation_allowed=False",
                "external_code_execution_allowed=False",
                "tool_dispatch_allowed=False",
                "runtime_activation_allowed=False",
                "release_authorized=False",
                "promotion_authorized=False",
                "automatic_promotion_allowed=False",
                "core_mutation_allowed=False",
                "priority_mutation_allowed=False",
                "---",
            ]
        )
    lines.pop()
    return "\n".join(lines)


def render_technology_experiment_runs(
    runs: list[TechnologyExperimentEvalRunContract],
) -> str:
    if not runs:
        return "No verified technology experiment evaluation runs found."
    lines: list[str] = []
    for run in runs:
        lines.extend(
            [
                f"run_id={safe_console_value(run.run_id)}",
                f"experiment_pack_id={safe_console_value(run.experiment_pack_id)}",
                f"pack_version={safe_console_value(run.pack_version)}",
                f"intake_id={safe_console_value(run.intake_id)}",
                f"pattern_id={safe_console_value(run.pattern_id)}",
                "sovereign_consumer_ref="
                + safe_console_value(run.sovereign_consumer_ref),
                f"status={safe_console_value(run.status)}",
                f"readiness_status={safe_console_value(run.readiness_status)}",
                "promotion_readiness="
                + safe_console_value(run.promotion_readiness),
                "comparison_conclusion="
                + safe_console_value(run.comparison_conclusion),
                f"pass_rate={safe_console_value(run.pass_rate)}",
                f"total_cases={safe_console_value(run.total_cases)}",
                f"regression_flags={safe_console_list(run.regression_flags)}",
                f"limitations={safe_console_list(run.limitations)}",
                f"blockers={safe_console_list(run.blockers)}",
                "execution_allowed=False",
                "tool_dispatch_allowed=False",
                "runtime_activation_allowed=False",
                "release_authorized=False",
                "promotion_authorized=False",
                "automatic_promotion_allowed=False",
                "core_mutation_allowed=False",
                "priority_mutation_allowed=False",
                "---",
            ]
        )
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


def _render_workflow_lifecycle_transition(
    transition: object,
    *,
    prefix: str = "",
) -> list[str]:
    return [
        f"{prefix}transition_id="
        + safe_console_value(getattr(transition, "transition_id", None)),
        f"{prefix}workflow_profile="
        + safe_console_value(getattr(transition, "workflow_profile", None)),
        f"{prefix}route="
        + safe_console_value(getattr(transition, "route", None)),
        f"{prefix}transition_action="
        + safe_console_value(getattr(transition, "transition_action", None)),
        f"{prefix}transition_status="
        + safe_console_value(getattr(transition, "transition_status", None)),
        f"{prefix}revision="
        + safe_console_value(getattr(transition, "revision", None)),
        f"{prefix}previous_transition_id="
        + safe_console_value(getattr(transition, "previous_transition_id", None)),
        f"{prefix}previous_transition_fingerprint="
        + safe_console_value(
            getattr(transition, "previous_transition_fingerprint", None)
        ),
        f"{prefix}source_registry_ref="
        + safe_console_value(getattr(transition, "source_registry_ref", None)),
        f"{prefix}source_registry_fingerprint="
        + safe_console_value(
            getattr(transition, "source_registry_fingerprint", None)
        ),
        f"{prefix}active_version_ref="
        + safe_console_value(getattr(transition, "active_version_ref", None)),
        f"{prefix}active_definition_hash="
        + safe_console_value(getattr(transition, "active_definition_hash", None)),
        f"{prefix}baseline_version_ref="
        + safe_console_value(getattr(transition, "baseline_version_ref", None)),
        f"{prefix}baseline_definition_hash="
        + safe_console_value(
            getattr(transition, "baseline_definition_hash", None)
        ),
        f"{prefix}candidate_version_ref="
        + safe_console_value(getattr(transition, "candidate_version_ref", None)),
        f"{prefix}candidate_definition_hash="
        + safe_console_value(
            getattr(transition, "candidate_definition_hash", None)
        ),
        f"{prefix}active_workflow_steps="
        + safe_console_list(list(getattr(transition, "active_workflow_steps", []))),
        f"{prefix}active_workflow_checkpoints="
        + safe_console_list(
            list(getattr(transition, "active_workflow_checkpoints", []))
        ),
        f"{prefix}active_workflow_decision_points="
        + safe_console_list(
            list(getattr(transition, "active_workflow_decision_points", []))
        ),
        f"{prefix}active_success_criteria="
        + safe_console_list(list(getattr(transition, "active_success_criteria", []))),
        f"{prefix}evolution_proposal_id="
        + safe_console_value(getattr(transition, "evolution_proposal_id", None)),
        f"{prefix}proposal_fingerprint="
        + safe_console_value(getattr(transition, "proposal_fingerprint", None)),
        f"{prefix}review_decision_id="
        + safe_console_value(getattr(transition, "review_decision_id", None)),
        f"{prefix}review_decision_fingerprint="
        + safe_console_value(
            getattr(transition, "review_decision_fingerprint", None)
        ),
        f"{prefix}release_checklist_id="
        + safe_console_value(getattr(transition, "release_checklist_id", None)),
        f"{prefix}release_checklist_fingerprint="
        + safe_console_value(
            getattr(transition, "release_checklist_fingerprint", None)
        ),
        f"{prefix}promotion_gate_id="
        + safe_console_value(getattr(transition, "promotion_gate_id", None)),
        f"{prefix}promotion_gate_fingerprint="
        + safe_console_value(
            getattr(transition, "promotion_gate_fingerprint", None)
        ),
        f"{prefix}workflow_eval_run_id="
        + safe_console_value(getattr(transition, "workflow_eval_run_id", None)),
        f"{prefix}workflow_eval_run_fingerprint="
        + safe_console_value(
            getattr(transition, "workflow_eval_run_fingerprint", None)
        ),
        f"{prefix}rollback_plan_id="
        + safe_console_value(getattr(transition, "rollback_plan_id", None)),
        f"{prefix}rollback_plan_fingerprint="
        + safe_console_value(
            getattr(transition, "rollback_plan_fingerprint", None)
        ),
        f"{prefix}human_authorization_ref="
        + safe_console_value(getattr(transition, "human_authorization_ref", None)),
        f"{prefix}operator_ref="
        + safe_console_value(getattr(transition, "operator_ref", None)),
        f"{prefix}evidence_refs="
        + safe_console_list(list(getattr(transition, "evidence_refs", []))),
        f"{prefix}completed_test_refs="
        + safe_console_list(list(getattr(transition, "completed_test_refs", []))),
        f"{prefix}failure_refs="
        + safe_console_list(list(getattr(transition, "failure_refs", []))),
        f"{prefix}timestamp="
        + safe_console_value(getattr(transition, "timestamp", None)),
    ]


def render_workflow_lifecycle_view(
    *,
    current_transition: object | None,
    transitions: list[object],
    workflow_profile: str | None,
    route: str | None,
    offset: int,
    integrity_reasons: list[str] | None = None,
) -> str:
    integrity_reasons = list(integrity_reasons or [])
    integrity_attention_required = bool(integrity_reasons)
    if workflow_profile is None or route is None:
        active_status = "scope_required"
    elif current_transition is not None:
        active_status = "found"
    elif transitions or integrity_reasons:
        active_status = "unavailable_unverified_tail"
        integrity_attention_required = True
    else:
        active_status = "not_found"
    lines = [
        "workflow_lifecycle_view=read_only",
        f"workflow_profile_filter={safe_console_value(workflow_profile)}",
        f"route_filter={safe_console_value(route)}",
        f"active_transition_status={active_status}",
        "integrity_attention_required="
        + safe_console_value(integrity_attention_required),
        "integrity_reasons=" + safe_console_list(integrity_reasons),
        f"history_offset={safe_console_value(offset)}",
        f"history_count={safe_console_value(len(transitions))}",
        "verified_records_only=True",
        "memory_write_allowed=False",
        "runtime_execution_allowed=False",
        "tool_dispatch_allowed=False",
        "active_registry_write_allowed=False",
        "automatic_promotion_allowed=False",
        "automatic_rollback_allowed=False",
        "core_mutation_allowed=False",
    ]
    if current_transition is not None:
        lines.extend(
            _render_workflow_lifecycle_transition(
                current_transition,
                prefix="active_",
            )
        )
    for transition in transitions:
        lines.append("---")
        lines.extend(_render_workflow_lifecycle_transition(transition))
    return "\n".join(lines)


def render_workflow_transition_result(
    *,
    transition: object,
    assessment: object,
    transition_recorded: bool,
    release_bundle_verified: bool,
) -> str:
    governance_status = getattr(assessment, "status", None)
    lines = [
        "workflow_transition=explicit_human_action",
        f"workflow_transition_status="
        f"{'recorded' if transition_recorded else 'governance_blocked'}",
        f"transition_recorded={safe_console_value(transition_recorded)}",
        f"release_bundle_verified={safe_console_value(release_bundle_verified)}",
        "governance_assessment_id="
        + safe_console_value(getattr(assessment, "assessment_id", None)),
        f"governance_status={safe_console_value(governance_status)}",
        "governance_blockers="
        + safe_console_list(list(getattr(assessment, "blockers", []))),
        "governance_conditions="
        + safe_console_list(list(getattr(assessment, "conditions", []))),
        "governance_policy_refs="
        + safe_console_list(list(getattr(assessment, "policy_refs", []))),
        "human_review_required="
        + safe_console_value(getattr(assessment, "human_review_required", None)),
        "human_authorization_verified="
        + safe_console_value(
            getattr(assessment, "human_authorization_verified", None)
        ),
        "transition_recording_authorized="
        + safe_console_value(
            getattr(assessment, "transition_recording_authorized", None)
        ),
        "memory_write_mode="
        + safe_console_value(getattr(assessment, "memory_write_mode", None)),
        "active_registry_write_allowed=False",
        "runtime_execution_allowed=False",
        "tool_dispatch_allowed=False",
        "automatic_promotion_allowed=False",
        "automatic_rollback_allowed=False",
        "core_mutation_allowed=False",
        "next_operator_step="
        + (
            "verify_active_runtime_binding"
            if transition_recorded
            else "resolve_governance_blockers"
        ),
    ]
    lines.extend(_render_workflow_lifecycle_transition(transition))
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


def render_daily_operator_workspace(
    workspace: DailyOperatorWorkspaceContract,
) -> str:
    lines = [
        "daily_operator_workspace=read_only",
        f"workspace_id={safe_console_value(workspace.workspace_id)}",
        f"workspace_status={safe_console_value(workspace.workspace_status)}",
        f"generated_at={safe_console_value(workspace.generated_at)}",
        f"mission_count={workspace.mission_count}",
        f"active_objective_count={workspace.active_objective_count}",
        f"active_work_item_count={workspace.active_work_item_count}",
        f"active_artifact_count={workspace.active_artifact_count}",
        f"open_checkpoint_count={workspace.open_checkpoint_count}",
        f"pending_review_count={workspace.pending_review_count}",
        f"stale_mission_count={workspace.stale_mission_count}",
        "pending_evolution_review_refs="
        + safe_console_list(workspace.pending_evolution_review_refs),
        "pending_memory_review_refs="
        + safe_console_list(workspace.pending_memory_review_refs),
        f"next_decision_refs={safe_console_list(workspace.next_decision_refs)}",
        "next_operator_decision="
        + safe_console_value(workspace.next_operator_decision),
        f"freshness_policy={safe_console_value(workspace.freshness_policy)}",
        f"ordering_policy={safe_console_value(workspace.ordering_policy)}",
        f"evidence_refs={safe_console_list(workspace.evidence_refs)}",
        f"memory_write_mode={safe_console_value(workspace.memory_write_mode)}",
        f"autonomous_resume_allowed={workspace.autonomous_resume_allowed}",
        f"autonomous_scheduling_allowed={workspace.autonomous_scheduling_allowed}",
    ]
    for mission in workspace.missions:
        lines.extend(
            [
                "---",
                f"mission_id={safe_console_value(mission.mission_id)}",
                f"mission_goal={safe_console_value(mission.mission_goal)}",
                f"mission_status={safe_console_value(mission.mission_status)}",
                f"project_ref={safe_console_value(mission.project_ref)}",
                f"objective_ref={safe_console_value(mission.objective_ref)}",
                f"objective_status={safe_console_value(mission.objective_status)}",
                f"updated_at={safe_console_value(mission.updated_at)}",
                f"freshness_status={safe_console_value(mission.freshness_status)}",
                "freshness_age_hours="
                + safe_console_value(mission.freshness_age_hours),
                "operator_attention_status="
                + safe_console_value(mission.operator_attention_status),
                f"next_action_status={safe_console_value(mission.next_action_status)}",
                f"next_action_ref={safe_console_value(mission.next_action_ref)}",
                f"work_item_refs={safe_console_list(mission.work_item_refs)}",
                f"active_work_items={safe_console_list(mission.active_work_items)}",
                "ordered_work_item_refs="
                + safe_console_list(mission.ordered_work_item_refs),
                "executable_work_item_refs="
                + safe_console_list(mission.executable_work_item_refs),
                "blocked_work_item_refs="
                + safe_console_list(mission.blocked_work_item_refs),
                f"artifact_refs={safe_console_list(mission.artifact_refs)}",
                "active_artifact_refs="
                + safe_console_list(mission.active_artifact_refs),
                "open_checkpoint_refs="
                + safe_console_list(mission.open_checkpoint_refs),
                f"open_loops={safe_console_list(mission.open_loops)}",
                "pending_decision_refs="
                + safe_console_list(mission.pending_decision_refs),
                f"mission_evidence_refs={safe_console_list(mission.evidence_refs)}",
            ]
        )
    return "\n".join(lines)


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


def render_daily_operator_utility_report(
    report: DailyOperatorUtilityReportContract,
) -> str:
    lines = [
        "operator_outcomes=read_only",
        f"report_id={safe_console_value(report.report_id)}",
        f"report_status={safe_console_value(report.report_status)}",
        f"period_start={safe_console_value(report.period_start)}",
        f"period_end={safe_console_value(report.period_end)}",
        f"generated_at={safe_console_value(report.generated_at)}",
        f"mission_count={report.mission_count}",
        f"event_count={report.event_count}",
        f"work_item_event_count={report.work_item_event_count}",
        f"observed_work_item_count={report.observed_work_item_count}",
        f"completed_work_item_count={report.completed_work_item_count}",
        f"reworked_work_item_count={report.reworked_work_item_count}",
        f"completion_rate={safe_console_metric(report.completion_rate)}",
        f"rework_rate={safe_console_metric(report.rework_rate)}",
        f"artifact_event_count={report.artifact_event_count}",
        f"observed_artifact_count={report.observed_artifact_count}",
        f"resume_count={report.resume_count}",
        f"stale_open_loop_count={safe_console_metric(report.stale_open_loop_count)}",
        f"feedback_count={report.feedback_count}",
        f"feedback_mission_count={report.feedback_mission_count}",
        f"feedback_coverage={safe_console_metric(report.feedback_coverage)}",
        f"helpful_feedback_count={report.helpful_feedback_count}",
        f"helpful_feedback_rate={safe_console_metric(report.helpful_feedback_rate)}",
        "time_to_next_action_observation_count="
        + safe_console_value(report.time_to_next_action_observation_count),
        "average_time_to_next_action_seconds="
        + safe_console_metric(report.average_time_to_next_action_seconds),
        "time_to_next_action_definition="
        + safe_console_value(report.time_to_next_action_definition),
        f"limitations={safe_console_list(report.limitations)}",
        f"saved_time_claim_status={safe_console_value(report.saved_time_claim_status)}",
        "memory_write_mode=read_only",
        "autonomous_action_allowed=False",
    ]
    for metric in report.mission_metrics:
        lines.extend(
            [
                "---",
                f"mission_id={safe_console_value(metric.mission_id)}",
                f"mission_completion_rate={safe_console_metric(metric.completion_rate)}",
                f"mission_rework_rate={safe_console_metric(metric.rework_rate)}",
                f"mission_artifact_count={metric.observed_artifact_count}",
                f"mission_resume_count={metric.resume_count}",
                "mission_stale_open_loop_count="
                + safe_console_metric(metric.stale_open_loop_count),
                f"mission_feedback_count={metric.feedback_count}",
                "mission_helpful_feedback_rate="
                + safe_console_metric(metric.helpful_feedback_rate),
                "mission_average_time_to_next_action_seconds="
                + safe_console_metric(metric.average_time_to_next_action_seconds),
                f"mission_limitations={safe_console_list(metric.limitations)}",
            ]
        )
    return "\n".join(lines)


def render_decision_attribution_report(
    report: DecisionOutcomeAttributionReportContract,
) -> str:
    lines = [
        "decision_attribution=read_only",
        f"report_id={safe_console_value(report.report_id)}",
        f"report_status={safe_console_value(report.report_status)}",
        f"generated_at={safe_console_value(report.generated_at)}",
        f"record_count={report.record_count}",
        f"correlation_only_count={report.correlation_only_count}",
        f"declared_causality_count={report.declared_causality_count}",
        f"insufficient_evidence_count={report.insufficient_evidence_count}",
        f"feedback_linked_count={report.feedback_linked_count}",
        f"comparator_count={report.comparator_count}",
        f"failed_record_count={report.failed_record_count}",
        "source_record_limit_reached="
        f"{safe_console_value(report.source_record_limit_reached)}",
        "source_event_limit_reached="
        f"{safe_console_value(report.source_event_limit_reached)}",
        f"limitations={safe_console_list(report.limitations)}",
        f"evidence_refs={safe_console_list(report.evidence_refs)}",
        f"read_only={safe_console_value(report.read_only)}",
        f"causality_scope={safe_console_value(report.causality_scope)}",
        f"causal_effect_proven={safe_console_value(report.causal_effect_proven)}",
        f"gain_claim_status={safe_console_value(report.gain_claim_status)}",
        "memory_write_allowed=False",
        "execution_allowed=False",
        "tool_dispatch_allowed=False",
        f"promotion_authorized={safe_console_value(report.promotion_authorized)}",
        "automatic_promotion_allowed="
        f"{safe_console_value(report.automatic_promotion_allowed)}",
        f"core_mutation_allowed={safe_console_value(report.core_mutation_allowed)}",
    ]
    for item in report.items:
        attribution = item.attribution
        lines.extend(
            [
                "---",
                f"item_id={safe_console_value(item.item_id)}",
                "attribution_record_id="
                f"{safe_console_value(attribution.attribution_record_id)}",
                f"request_id={safe_console_value(attribution.request_id)}",
                f"mission_id={safe_console_value(attribution.mission_id)}",
                "workflow_profile="
                f"{safe_console_value(attribution.workflow_profile)}",
                "attribution_status="
                f"{safe_console_value(attribution.attribution_status)}",
                "participating_refs="
                f"{safe_console_list(attribution.participating_refs)}",
                "declared_causal_refs="
                f"{safe_console_list(attribution.declared_causal_refs)}",
                f"correlated_refs={safe_console_list(attribution.correlated_refs)}",
                f"feedback_status={safe_console_value(item.feedback_status)}",
                f"feedback_refs={safe_console_list(item.feedback_refs)}",
                f"comparator_status={safe_console_value(item.comparator_status)}",
                f"comparator_refs={safe_console_list(item.comparator_refs)}",
                f"item_limitations={safe_console_list(item.limitations)}",
                f"item_read_only={safe_console_value(item.read_only)}",
                "item_causal_effect_proven="
                f"{safe_console_value(item.causal_effect_proven)}",
                f"item_gain_claim_status={safe_console_value(item.gain_claim_status)}",
                "item_promotion_authorized="
                f"{safe_console_value(item.promotion_authorized)}",
                "item_automatic_promotion_allowed="
                f"{safe_console_value(item.automatic_promotion_allowed)}",
                "item_core_mutation_allowed="
                f"{safe_console_value(item.core_mutation_allowed)}",
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
        requested_autonomy_level=args.requested_autonomy_level,
        max_autonomy_level=args.max_autonomy_level,
        autonomy_confirmation_mode=args.autonomy_confirmation_mode,
        action_confirmation_receipt_id=args.action_confirmation_receipt_id,
        action_confirmation_origin_request_id=(
            args.action_confirmation_origin_request_id
        ),
    )
    return [render_response(response, debug=args.debug)]


def run_action_confirm_command(
    console: JarvisConsole,
    args: Namespace,
) -> list[str]:
    receipt = console.confirm_action_challenge(
        challenge_id=args.challenge_id,
        action_fingerprint=args.action_fingerprint,
        operator_identity_ref=args.operator_identity_ref,
    )
    return [render_action_confirmation_receipt(receipt)]


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
        dependency_refs=([] if args.clear_dependencies else args.dependency_refs),
        priority_level=args.priority_level,
        blocker_refs=args.blocker_refs,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_work_item_transition(result)]


def run_open_loops_command(console: JarvisConsole, args: Namespace) -> list[str]:
    registry = console.get_open_loop_registry(mission_id=args.mission_id)
    return [render_open_loop_registry(registry, mission_id=args.mission_id)]


def run_resume_loop_command(console: JarvisConsole, args: Namespace) -> list[str]:
    result = console.resume_open_loop(
        mission_id=args.mission_id,
        open_loop_ref=args.open_loop_ref,
        session_id=args.session_id,
        operator_identity_ref=args.operator_identity_ref,
        canonical_user_ref=args.canonical_user_ref,
    )
    return [render_open_loop_resume(result)]


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


def run_technology_radar_intake_command(args: Namespace) -> list[str]:
    intake, assessment = assess_technology_radar_intake_manifest(
        args.manifest,
        intake_root=args.intake_root,
        expected_manifest_sha256=args.manifest_sha256,
        knowledge_service=KnowledgeService(),
    )
    result = register_technology_radar_intake(
        intake,
        assessment=assessment,
        evolution_service=_evolution_service_from_args(args),
    )
    return [render_technology_radar_intake_registration(result)]


def run_technology_radar_command(args: Namespace) -> list[str]:
    service = _evolution_service_from_args(args, read_only=True)
    if args.intake_id is not None or args.candidate_ref is not None:
        intake = service.get_technology_radar_intake(
            intake_id=args.intake_id,
            candidate_ref=args.candidate_ref,
            intake_version=args.intake_version,
        )
        records = [intake] if intake is not None else []
    else:
        if args.intake_version is not None:
            raise ValueError(
                "intake-version requires intake-id or candidate-ref"
            )
        records = service.list_technology_radar_intakes(
            source_kind=args.source_kind,
            absorption_class=args.absorption_class,
            target_gap_ref=args.target_gap_ref,
            limit=args.limit,
            offset=args.offset,
        )
    return [render_technology_radar_intakes(records)]


def run_technology_experiment_pack_command(args: Namespace) -> list[str]:
    reader = _evolution_service_from_args(args, read_only=True)
    pack = assess_technology_experiment_pack_manifest(
        args.manifest,
        manifest_root=args.manifest_root,
        expected_manifest_sha256=args.manifest_sha256,
        intake_reader=reader,
    )
    intake = reader.get_technology_radar_intake(
        intake_id=pack.intake_id,
        intake_version=pack.intake_version,
    )
    if intake is None:
        raise ValueError("technology experiment requires an exact verified intake")
    result = register_technology_experiment_pack(
        pack,
        intake=intake,
        evolution_service=_evolution_service_from_args(args),
    )
    return [render_technology_experiment_registration(result)]


def run_technology_experiment_eval_command(args: Namespace) -> list[str]:
    reader = _evolution_service_from_args(args, read_only=True)
    pack, claim, run = prepare_technology_experiment_eval_manifest(
        args.manifest,
        manifest_root=args.manifest_root,
        expected_manifest_sha256=args.manifest_sha256,
        pack_reader=reader,
    )
    recorded = record_technology_experiment_eval(
        pack=pack,
        claim=claim,
        run=run,
        evolution_service=_evolution_service_from_args(args),
    )
    return [render_technology_experiment_runs([recorded])]


def run_technology_experiments_command(args: Namespace) -> list[str]:
    service = _evolution_service_from_args(args, read_only=True)
    if (
        isinstance(args.limit, bool)
        or not isinstance(args.limit, int)
        or not 1 <= args.limit <= 500
    ):
        raise ValueError("technology experiment limit must be between 1 and 500")
    if (
        isinstance(args.offset, bool)
        or not isinstance(args.offset, int)
        or args.offset < 0
    ):
        raise ValueError("technology experiment offset must be non-negative")
    if args.view == "runs":
        if args.run_id is not None:
            run = service.get_technology_experiment_eval_run(run_id=args.run_id)
            runs = (
                [run]
                if run is not None
                and (
                    args.experiment_pack_id is None
                    or run.experiment_pack_id == args.experiment_pack_id
                )
                and (
                    args.pack_version is None
                    or run.pack_version == args.pack_version
                )
                and (args.intake_id is None or run.intake_id == args.intake_id)
                and (
                    args.candidate_ref is None
                    or run.candidate_ref == args.candidate_ref
                )
                and (args.status is None or run.status == args.status)
                else []
            )
            runs = runs[args.offset : args.offset + args.limit]
        else:
            runs = service.list_technology_experiment_eval_runs(
                experiment_pack_id=args.experiment_pack_id,
                pack_version=args.pack_version,
                intake_id=args.intake_id,
                candidate_ref=args.candidate_ref,
                status=args.status,
                limit=args.limit,
                offset=args.offset,
            )
        return [render_technology_experiment_runs(runs)]
    if args.run_id is not None:
        raise ValueError("run-id requires --view runs")
    if args.status is not None and args.status != "sandbox_ready":
        raise ValueError("unsupported technology experiment pack status")
    if args.experiment_pack_id is not None:
        if args.pack_version is None:
            raise ValueError("pack-version is required with experiment-pack-id")
        pack = service.get_technology_experiment_pack(
            experiment_pack_id=args.experiment_pack_id,
            pack_version=args.pack_version,
        )
        packs = (
            [pack]
            if pack is not None
            and (args.intake_id is None or pack.intake_id == args.intake_id)
            and (
                args.candidate_ref is None
                or pack.candidate_ref == args.candidate_ref
            )
            and (args.status is None or pack.pack_status == args.status)
            else []
        )
        packs = packs[args.offset : args.offset + args.limit]
    else:
        if args.pack_version is not None:
            raise ValueError("pack-version requires experiment-pack-id")
        packs = service.list_technology_experiment_packs(
            intake_id=args.intake_id,
            candidate_ref=args.candidate_ref,
            limit=args.limit,
            offset=args.offset,
        )
    return [render_technology_experiment_packs(packs)]


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


def _evolution_service_from_args(
    args: Namespace,
    *,
    read_only: bool = False,
) -> EvolutionLabService:
    evolution_db = (
        Path(args.evolution_db)
        if args.evolution_db
        else ROOT / ".jarvis_runtime" / "evolution.db"
    )
    evolution_db = evolution_db.expanduser()
    if not evolution_db.is_absolute():
        evolution_db = (Path.cwd() / evolution_db).resolve()
    return EvolutionLabService(database_path=str(evolution_db), read_only=read_only)


def _workflow_lifecycle_memory_service_from_args(
    args: Namespace,
    *,
    evolution_service: EvolutionLabService,
) -> MemoryService:
    memory_db = (
        Path(args.memory_db)
        if args.memory_db
        else ROOT / ".jarvis_runtime" / "memory.db"
    )
    memory_db = memory_db.expanduser()
    if not memory_db.is_absolute():
        memory_db = (Path.cwd() / memory_db).resolve()
    return MemoryService(
        database_url=f"sqlite:///{memory_db.as_posix()}",
        workflow_lifecycle_transition_verifier=(
            evolution_service.verify_persisted_workflow_lifecycle_transition
        ),
    )


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


def run_workflow_lifecycle_command(args: Namespace) -> list[str]:
    if (args.workflow_profile is None) != (args.route is None):
        raise ValueError(
            "workflow lifecycle current view requires workflow profile and route together"
        )
    if not 1 <= args.limit <= 100:
        raise ValueError("workflow lifecycle limit must be between 1 and 100")
    if args.offset < 0:
        raise ValueError("workflow lifecycle offset must be non-negative")
    evolution_service = _evolution_service_from_args(args)
    memory_service = _workflow_lifecycle_memory_service_from_args(
        args,
        evolution_service=evolution_service,
    )
    integrity_reasons: list[str] = []
    try:
        current_transition = (
            memory_service.get_active_workflow_lifecycle(
                workflow_profile=args.workflow_profile,
                route=args.route,
            )
            if args.workflow_profile is not None and args.route is not None
            else None
        )
    except WorkflowLifecycleIntegrityError as exc:
        current_transition = None
        integrity_reasons.append(str(exc))
    transitions = memory_service.list_workflow_lifecycle_transitions(
        workflow_profile=args.workflow_profile,
        route=args.route,
        limit=args.limit,
        offset=args.offset,
    )
    visible_transitions = [
        transition
        for transition in [current_transition, *transitions]
        if transition is not None
    ]
    verified_transition_ids: set[str] = set()
    for transition in visible_transitions:
        if transition.transition_id in verified_transition_ids:
            continue
        if not evolution_service.verify_persisted_workflow_lifecycle_transition(
            transition
        ):
            raise ValueError(
                "workflow lifecycle release bundle verification failed: "
                + safe_console_value(transition.transition_id)
            )
        verified_transition_ids.add(transition.transition_id)
    return [
        render_workflow_lifecycle_view(
            current_transition=current_transition,
            transitions=list(transitions),
            workflow_profile=args.workflow_profile,
            route=args.route,
            offset=args.offset,
            integrity_reasons=integrity_reasons,
        )
    ]


def run_workflow_transition_command(
    args: Namespace,
) -> list[str] | CommandExecutionResult:
    failure_refs = list(args.failure_ref)
    if args.action == "rollback_to_baseline" and not failure_refs:
        raise ValueError("workflow rollback requires at least one failure reference")
    if args.action == "activate_candidate" and failure_refs:
        raise ValueError("workflow activation does not accept failure references")

    evolution_service = _evolution_service_from_args(args)
    memory_service = _workflow_lifecycle_memory_service_from_args(
        args,
        evolution_service=evolution_service,
    )
    current_transition = memory_service.get_active_workflow_lifecycle(
        workflow_profile=args.workflow_profile,
        route=args.route,
    )
    if args.action == "rollback_to_baseline" and current_transition is None:
        raise ValueError("workflow rollback requires an active promoted transition")

    transition = evolution_service.prepare_workflow_lifecycle_transition(
        action=args.action,
        evolution_proposal_id=args.proposal_id,
        workflow_eval_run_id=args.workflow_eval_run_id,
        human_authorization_ref=args.human_authorization_ref,
        operator_ref=args.operator_ref,
        evidence_refs=list(args.evidence_ref),
        completed_test_refs=list(args.completed_test_ref),
        completed_external_gates=list(args.completed_external_gate),
        failure_refs=failure_refs,
        current_transition=current_transition,
        transition_id=args.transition_id,
    )
    release_bundle_verified = (
        evolution_service.verify_persisted_workflow_lifecycle_transition(transition)
    )
    if not release_bundle_verified:
        raise ValueError("prepared workflow lifecycle release bundle failed verification")
    if (
        transition.workflow_profile != args.workflow_profile
        or transition.route != args.route
    ):
        raise ValueError("prepared workflow lifecycle scope does not match operator scope")

    assessment = GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        current_transition=current_transition,
        release_bundle_verifier=(
            evolution_service.verify_persisted_workflow_lifecycle_transition
        ),
    )
    transition_recorded = False
    if assessment.status == "approved":
        memory_service.record_workflow_lifecycle_transition(
            transition,
            assessment,
        )
        transition_recorded = True
    rendered = render_workflow_transition_result(
        transition=transition,
        assessment=assessment,
        transition_recorded=transition_recorded,
        release_bundle_verified=release_bundle_verified,
    )
    if transition_recorded:
        return [rendered]
    return CommandExecutionResult(
        outputs=[rendered],
        status="failed",
        exit_code=int(ConsoleExitCode.GOVERNANCE_BLOCKED),
        warnings=list(assessment.blockers),
    )


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


def run_daily_workspace_command(args: Namespace) -> list[str]:
    limit = max(1, min(args.limit, 200))
    generated_at = OperationalService.now()
    memory_service = _memory_service_from_args(args)
    evolution_service = _evolution_service_from_args(args)
    evolution_review_refs = [
        str(item.evolution_proposal_id)
        for item in evolution_service.list_human_review_queue(limit=limit)
        if item.review_status
        in {"observed", "candidate", "needs_review", "sandboxed"}
    ]
    memory_review_refs = [
        item.candidate_id
        for item in memory_service.list_memory_lifecycle_review_queue(
            limit=limit,
            generated_at=generated_at,
        )
        if item.review_status == "needs_review"
    ]
    workspace = OperationalService.build_daily_operator_workspace(
        mission_states=memory_service.list_mission_states(limit=limit),
        pending_evolution_review_refs=evolution_review_refs,
        pending_memory_review_refs=memory_review_refs,
        generated_at=generated_at,
    )
    return [render_daily_operator_workspace(workspace)]


def run_operator_outcomes_command(args: Namespace) -> list[str]:
    observability_db = Path(args.observability_db).expanduser()
    if not observability_db.is_absolute():
        observability_db = (Path.cwd() / observability_db).resolve()
    report = build_daily_operator_utility_report(
        observability_service=ObservabilityService(
            database_path=str(observability_db)
        ),
        memory_service=_memory_service_from_args(args),
        period_start=args.period_start,
        period_end=args.period_end,
        event_limit=args.event_limit,
        mission_limit=args.mission_limit,
    )
    return [render_daily_operator_utility_report(report)]


def run_decision_attribution_command(args: Namespace) -> list[str]:
    observability_db = Path(args.observability_db).expanduser()
    if not observability_db.is_absolute():
        observability_db = (Path.cwd() / observability_db).resolve()
    report = build_decision_attribution_report(
        observability_service=ObservabilityService(
            database_path=str(observability_db)
        ),
        memory_service=_memory_service_from_args(args),
        request_id=args.request_id,
        mission_id=args.mission_id,
        workflow_profile=args.workflow_profile,
        limit=args.limit,
    )
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser()
        if not output_dir.is_absolute():
            output_dir = (Path.cwd() / output_dir).resolve()
        save_decision_attribution_report(report, output_dir=output_dir)
    return [render_decision_attribution_report(report)]


def run_command_reference_command(args: Namespace) -> list[str]:
    return [render_command_reference(COMMAND_REGISTRY, build_parser()).rstrip("\n")]


def run_completion_command(args: Namespace) -> list[str]:
    return [
        render_shell_completion(
            COMMAND_REGISTRY,
            build_parser(),
            shell=args.shell,
        ).rstrip("\n")
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


def run_doctor_command(args: Namespace) -> CommandExecutionResult:
    runtime_dir = _resolve_doctor_path(args.runtime_dir, ROOT / ".jarvis_runtime")
    report = build_doctor_report(
        root=ROOT,
        runtime_dir=runtime_dir,
        memory_db=_resolve_doctor_path(args.memory_db, runtime_dir / "memory.db"),
        evolution_db=_resolve_doctor_path(
            args.evolution_db,
            runtime_dir / "evolution.db",
        ),
        observability_db=_resolve_doctor_path(
            args.observability_db,
            runtime_dir / "observability.db",
        ),
    )
    result_status = {
        "healthy": "success",
        "degraded": "degraded",
        "failed": "failed",
    }[report.status]
    return CommandExecutionResult(
        outputs=[render_doctor_report(report)],
        status=result_status,
        exit_code=report.recommended_exit_code,
        warnings=[
            check.check_id for check in report.checks if check.status == "warning"
        ],
    )


def _resolve_doctor_path(value: str | None, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


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


def run_physical_command(args: Namespace) -> list[str] | CommandExecutionResult:
    from apps.jarvis_console.physical_cli import run_physical

    return run_physical(args)


def run_memory_recall_command(args: Namespace) -> CommandExecutionResult:
    from apps.jarvis_console.recall_cli import run_memory_recall

    return run_memory_recall(args)


def run_code_review_command(args: Namespace) -> CommandExecutionResult:
    from apps.jarvis_console.code_review_cli import build_code_review
    from apps.jarvis_console.review_input import run_review_product

    return run_review_product(args, build_code_review)


def run_chatgpt_account_command(args: Namespace) -> CommandExecutionResult:
    from apps.jarvis_console.chatgpt_account_cli import run_chatgpt_account

    return run_chatgpt_account(args)


def run_transcript_review_command(args: Namespace) -> CommandExecutionResult:
    from apps.jarvis_console.transcript_review_cli import run_transcript_review

    return run_transcript_review(
        args, core_factory=lambda: JarvisConsole.build(
            runtime_dir=ROOT / ".jarvis_runtime" / "console",
            local_observability_only=True,
        ).orchestrator,
    )


def run_job_inspect_command(args: Namespace) -> CommandExecutionResult:
    from apps.jarvis_console.job_inspect_cli import build_job_inspection
    from apps.jarvis_console.review_input import _requires_redaction

    try:
        options = dict(actor_ref=args.actor_ref, session_ref=args.session_ref,
                       job_ids=tuple(args.job_id))
        product = build_job_inspection(args.job_db, **options, include_refs=args.include_refs)
        redactor = ConsoleRuntime(
            output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
        )
        if _requires_redaction(product, redactor):
            product = build_job_inspection(args.job_db, **options, include_refs=False)
            product["references_withheld"] = True
        encoded = json.dumps(product, ensure_ascii=True, allow_nan=False, sort_keys=True)
        if len(encoded.encode("utf-8")) > 262_144 or redactor.redact(encoded)[1]:
            raise ValueError("job_inspection_output_refused")
        return CommandExecutionResult(outputs=[encoded])
    except Exception:
        raise ConsoleCommandError(
            "Job inspection refused; supply exact scope and a valid quiescent ledger.",
            error_code="job_inspection_refused", exit_code=ConsoleExitCode.USAGE_ERROR,
        ) from None


def run_research_review_command(args: Namespace) -> CommandExecutionResult:
    from apps.jarvis_console.research_cli import build_research_dossier
    from apps.jarvis_console.review_input import run_review_product

    return run_review_product(args, build_research_dossier)


BOUND_COMMAND_REGISTRY = COMMAND_REGISTRY.bind(globals())


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else list(process_argv[1:])
    requested_format = _requested_output_format(raw_argv)
    try:
        args = build_parser().parse_args(raw_argv)
    except ConsoleCommandError as exc:
        safe_error = exc
        if _requested_command_id(raw_argv) in {
            "memory-recall", "code-review", "research-review", "job-inspect", "chatgpt-account",
            "transcript-review",
        }:
            safe_error = ConsoleCommandError(
                "Invalid review command usage; consult command help.",
                error_code="invalid_cli_usage", exit_code=ConsoleExitCode.USAGE_ERROR,
            )
        return ConsoleRuntime(
            output_format=requested_format,
            sensitive_paths=(str(ROOT), str(Path.home())),
        ).report_error(
            command_id=_requested_command_id(raw_argv),
            error=safe_error,
        )
    runtime = ConsoleRuntime(
        output_format=args.output_format,
        sensitive_paths=(str(ROOT), str(Path.home())),
    )
    return runtime.execute(
        registry=BOUND_COMMAND_REGISTRY,
        command_id=args.command,
        args=args,
        console_factory=lambda: JarvisConsole.build(
            runtime_dir=ROOT / ".jarvis_runtime" / "console"
        ),
    )


def _requested_output_format(argv: list[str]) -> str:
    for index, argument in enumerate(argv):
        if argument.startswith("--format="):
            value = argument.partition("=")[2]
            return value if value in {"text", "json"} else "text"
        if argument == "--format" and index + 1 < len(argv):
            value = argv[index + 1]
            return value if value in {"text", "json"} else "text"
    return "text"


def _requested_command_id(argv: list[str]) -> str:
    command_ids = {
        definition.command_id for definition in COMMAND_REGISTRY.definitions
    }
    return next((argument for argument in argv if argument in command_ids), "unknown")
