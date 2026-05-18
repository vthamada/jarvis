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

from evolution_lab.service import EvolutionLabService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
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
        lines.extend(
            [
                f"experience_id={safe_console_value(experience.experience_id)}",
                f"mission_id={safe_console_value(experience.mission_id)}",
                f"workflow_profile={safe_console_value(experience.workflow_profile)}",
                f"outcome_status={safe_console_value(experience.outcome_status)}",
                f"reflection_status={safe_console_value(reflection.reflection_status)}",
                f"proposed_change_type={safe_console_value(reflection.proposed_change_type)}",
                f"learning_candidate={safe_console_value(reflection.learning_candidate)}",
                f"recommendation={safe_console_value(reflection.recommendation)}",
                f"blockers={safe_console_list(list(reflection.blockers))}",
                f"automatic_promotion={safe_console_value(reflection.automatic_promotion_allowed)}",
                f"core_mutation_allowed={safe_console_value(reflection.core_mutation_allowed)}",
                "---",
            ]
        )
    if lines and lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)


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


def run_experience_reflections_command(args: Namespace) -> list[str]:
    memory_db = (
        Path(args.memory_db)
        if args.memory_db
        else ROOT / ".jarvis_runtime" / "memory.db"
    )
    service = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    records = service.list_experience_reflections(
        mission_id=args.mission_id,
        workflow_profile=args.workflow_profile,
        limit=max(1, args.limit),
    )
    return [render_experience_reflections(records)]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = JarvisConsole.build(runtime_dir=ROOT / ".jarvis_runtime" / "console")
    outputs = (
        run_ask_command(console, args)
        if args.command == "ask"
        else run_experience_reflections_command(args)
        if args.command == "experience-reflections"
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
    }:
        print(outputs[0])
    elif args.message:
        for item in outputs:
            print(item)
    return 0
