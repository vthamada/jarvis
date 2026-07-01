# ruff: noqa: E402
"""Minimal console surface for the JARVIS v1 baseline."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths

ensure_src_paths()

from evolution_lab.service import EvolutionLabService, PostTaskReflectionInput
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import (
    ObjectiveTransitionResult,
    OrchestratorResponse,
    OrchestratorService,
)

from shared.contracts import InputContract, MissionStateContract
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId

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

    mission_cycle_parser = subparsers.add_parser(
        "mission-cycle",
        help="Show a read-only operator learning loop for one mission.",
    )
    mission_cycle_parser.add_argument("--mission-id", required=True)
    mission_cycle_parser.add_argument("--memory-db")
    mission_cycle_parser.add_argument("--evolution-db")
    mission_cycle_parser.add_argument("--workflow-profile")
    mission_cycle_parser.add_argument("--limit", type=int, default=5)

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

    return parser


def render_response(response: OrchestratorResponse, *, debug: bool) -> str:
    lines = [response.response_text]
    if debug:
        lines.extend(
            [
                f"request_id={response.request_id}",
                f"decision={response.governance_decision.decision.value}",
                f"continuity={response.deliberative_plan.continuity_action or 'none'}",
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
    return MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")


def _evolution_service_from_args(args: Namespace) -> EvolutionLabService:
    evolution_db = (
        Path(args.evolution_db)
        if args.evolution_db
        else ROOT / ".jarvis_runtime" / "evolution.db"
    )
    return EvolutionLabService(database_path=str(evolution_db))


def run_experience_reflections_command(args: Namespace) -> list[str]:
    service = _memory_service_from_args(args)
    records = service.list_experience_reflections(
        mission_id=args.mission_id,
        workflow_profile=args.workflow_profile,
        limit=max(1, args.limit),
    )
    return [render_experience_reflections(records)]


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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = JarvisConsole.build(runtime_dir=ROOT / ".jarvis_runtime" / "console")
    outputs = (
        run_ask_command(console, args)
        if args.command == "ask"
        else run_experience_reflections_command(args)
        if args.command == "experience-reflections"
        else run_evolution_review_queue_command(args)
        if args.command == "evolution-review-queue"
        else run_evolution_review_command(args)
        if args.command == "evolution-review"
        else run_mission_cycle_command(console, args)
        if args.command == "mission-cycle"
        else run_mission_workflow_command(console, args)
        if args.command == "mission-workflow"
        else run_technology_candidates_command(args)
        if args.command == "technology-candidates"
        else run_objective_command(console, args)
        if args.command == "objective"
        else run_objectives_command(console, args)
        if args.command == "objectives"
        else run_chat_command(console, args)
    )
    if args.command in {
        "ask",
        "objective",
        "objectives",
        "technology-candidates",
        "experience-reflections",
        "evolution-review-queue",
        "evolution-review",
        "mission-cycle",
        "mission-workflow",
    }:
        print(outputs[0])
    elif args.message:
        for item in outputs:
            print(item)
    return 0
