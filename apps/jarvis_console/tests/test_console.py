from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from evolution_lab.service import EvolutionLabService, TechnologyAbsorptionInput
from memory_service.service import MemoryService

from apps.jarvis_console.cli import (
    JarvisConsole,
    build_parser,
    render_experience_reflections,
    render_objective_state,
    render_response,
    run_chat_command,
    run_experience_reflections_command,
    run_objective_command,
    run_objectives_command,
    run_technology_candidates_command,
)
from shared.contracts import (
    ExperienceRecordContract,
    MissionStateContract,
    PostTaskReflectionContract,
)
from shared.types import MissionId, MissionStatus


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_console_ask_returns_orchestrated_response() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-ask"))
    response = console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console",
        mission_id="mission-console",
    )
    rendered = render_response(response, debug=True)

    assert response.intent == "planning"
    assert "Leitura do objetivo" in response.response_text
    assert "request_id=" in rendered
    assert "decision=" in rendered
    assert response.operation_dispatch is not None
    assert response.operation_dispatch.surface_id == "surface://jarvis_console"
    assert response.operation_dispatch.surface_kind == "console"
    assert response.operation_dispatch.surface_session_id == "sess-console"
    assert response.operation_dispatch.surface_continuity_status == "single_surface"


def test_console_accepts_operator_surface_identity_overrides() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-surface"))
    response = console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-surface",
        mission_id="mission-console-surface",
        operator_identity_ref="operator://ricardo",
        canonical_user_ref="user://ricardo",
    )

    assert response.operation_dispatch is not None
    assert response.operation_dispatch.operator_identity_ref == "operator://ricardo"
    assert response.operation_dispatch.canonical_user_ref == "user://ricardo"


def test_console_objectives_shows_persisted_project_objective_state() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objectives"))
    mission_id = "mission-console-objectives"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objectives",
        mission_id=mission_id,
    )
    parser = build_parser()
    args = parser.parse_args(["objectives", "--mission-id", mission_id])

    outputs = run_objectives_command(console, args)

    assert len(outputs) == 1
    assert f"mission_id={mission_id}" in outputs[0]
    assert "project_ref=project:mission:mission-console-objectives" in outputs[0]
    assert "objective_ref=objective:mission:mission-console-objectives" in outputs[0]
    assert "objective_status=completed" in outputs[0]
    assert "next_action_ref=next_action:" in outputs[0]
    event_names = [
        event.event_name
        for event in console.orchestrator.observability_service.list_recent_events()
    ]
    assert "objective_state_inspected" in event_names


def test_console_objectives_handles_missing_mission_without_side_effects() -> None:
    rendered = render_objective_state(None, mission_id="missing-mission")

    assert rendered == "No objective state found for mission_id=missing-mission"


def test_console_technology_candidates_shows_recent_absorption_candidate() -> None:
    temp_dir = runtime_dir("console-technology-candidates")
    evolution_db = temp_dir / "evolution.db"
    service = EvolutionLabService(database_path=str(evolution_db))
    service.create_proposal_from_technology_absorption_candidate(
        TechnologyAbsorptionInput(
            candidate_ref="tech-candidate://openai-agents-sdk/handoff-adapters",
            technology_name="OpenAI Agents SDK",
            absorption_class="promotable_translation",
            target_gap_refs=["TA-005"],
            hypothesis="Handoff adapters can improve bounded edge tracing.",
            expected_gain="Better trace evidence without replacing the core.",
            evidence_refs=["evidence://comparison/handoff-adapter"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            status="validated",
            requested_core_role="adapter",
            rollback_plan_ref="rollback://sovereign-core/current",
        )
    )
    args = build_parser().parse_args(
        [
            "technology-candidates",
            "--evolution-db",
            str(evolution_db),
            "--limit",
            "3",
        ]
    )

    outputs = run_technology_candidates_command(args)

    assert len(outputs) == 1
    assert "candidate_ref=tech-candidate://openai-agents-sdk/handoff-adapters" in outputs[0]
    assert "technology_name=OpenAI Agents SDK" in outputs[0]
    assert "absorption_decision=manual_promotion_review" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "core_replacement_allowed=False" in outputs[0]


def test_console_experience_reflections_shows_recent_records() -> None:
    temp_dir = runtime_dir("console-experience-reflections")
    memory_db = temp_dir / "memory.db"
    service = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    service.record_experience_reflection(
        experience=ExperienceRecordContract(
            experience_id="experience://mission-console-reflection/001",
            mission_id=MissionId("mission-console-reflection"),
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            evidence_refs=["trace://req-console-reflection"],
            timestamp="2026-05-17T00:00:00Z",
        ),
        reflection=PostTaskReflectionContract(
            reflection_id="reflection://mission-console-reflection/001",
            experience_id="experience://mission-console-reflection/001",
            reflection_status="candidate",
            learning_candidate="contract-first implementation reduced drift",
            recommendation="keep the improvement sandbox-only",
            proposed_change_type="workflow",
            evidence_refs=["trace://req-console-reflection"],
            timestamp="2026-05-17T00:00:01Z",
        ),
    )
    args = build_parser().parse_args(
        [
            "experience-reflections",
            "--memory-db",
            str(memory_db),
            "--mission-id",
            "mission-console-reflection",
        ]
    )

    outputs = run_experience_reflections_command(args)

    assert "experience_id=experience://mission-console-reflection/001" in outputs[0]
    assert "reflection_status=candidate" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "core_mutation_allowed=False" in outputs[0]


def test_console_experience_reflections_handles_empty_records() -> None:
    assert render_experience_reflections([]) == "No experience reflections found."


def test_console_objectives_sanitizes_control_characters_in_persisted_state() -> None:
    rendered = render_objective_state(
        MissionStateContract(
            mission_id="mission-safe",
            mission_goal="Goal\nobjective_status=spoofed",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-16T00:00:00Z",
            work_item_refs=["item\rspoofed"],
        ),
        mission_id="mission-safe",
    )

    assert "mission_goal=Goal objective_status=spoofed" in rendered
    assert "\nobjective_status=spoofed" not in rendered
    assert "work_item_refs=item spoofed" in rendered


def test_console_objective_pause_updates_state_through_governed_core() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-pause"))
    mission_id = "mission-console-objective-pause"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-pause",
        mission_id=mission_id,
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-pause",
            "--action",
            "pause",
        ]
    )

    outputs = run_objective_command(console, args)
    mission_state = console.get_objective_state(mission_id=mission_id)
    recent_events = console.orchestrator.observability_service.list_recent_events()
    event_names = [event.event_name for event in recent_events]

    assert len(outputs) == 1
    assert "transition_status=updated" in outputs[0]
    assert "governance_decision=allow_with_conditions" in outputs[0]
    assert "memory_write_mode=through_core_only" in outputs[0]
    assert mission_state is not None
    assert mission_state.objective_status == "paused"
    assert mission_state.mission_status == MissionStatus.PAUSED
    assert any(
        ref.startswith("objective_transition:pause:")
        for ref in mission_state.checkpoint_refs
    )
    assert "governance_checked" in event_names
    assert "mission_updated" in event_names


def test_console_objective_redefine_next_action_requires_explicit_ref() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-next"))
    mission_id = "mission-console-objective-next"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-next",
        mission_id=mission_id,
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-next",
            "--action",
            "redefine-next-action",
            "--next-action-ref",
            "next_action:operator-selected",
        ]
    )

    outputs = run_objective_command(console, args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=updated" in outputs[0]
    assert mission_state is not None
    assert mission_state.next_action_ref == "next_action:operator-selected"


def test_console_objective_blocks_unbounded_next_action_ref() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-unsafe-ref"))
    mission_id = "mission-console-objective-unsafe-ref"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-unsafe-ref",
        mission_id=mission_id,
    )
    previous = console.get_objective_state(mission_id=mission_id)
    parser = build_parser()
    args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-unsafe-ref",
            "--action",
            "redefine-next-action",
            "--next-action-ref",
            "next_action:unsafe\nspoofed",
        ]
    )

    outputs = run_objective_command(console, args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=blocked" in outputs[0]
    assert "governance_decision=block" in outputs[0]
    assert previous is not None
    assert mission_state is not None
    assert mission_state.next_action_ref == previous.next_action_ref


def test_console_objective_blocks_unsafe_terminal_resume() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-block"))
    mission_id = "mission-console-objective-block"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-block",
        mission_id=mission_id,
    )
    parser = build_parser()
    complete_args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-block",
            "--action",
            "complete",
        ]
    )
    resume_args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-block",
            "--action",
            "resume",
        ]
    )

    run_objective_command(console, complete_args)
    outputs = run_objective_command(console, resume_args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=blocked" in outputs[0]
    assert "governance_decision=block" in outputs[0]
    assert mission_state is not None
    assert mission_state.mission_status == MissionStatus.COMPLETED
    assert mission_state.objective_status == "completed"


def test_console_ask_surfaces_active_objective_state_in_final_synthesis() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-synthesis"))
    mission_id = "mission-console-objective-synthesis"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-synthesis",
        mission_id=mission_id,
    )
    parser = build_parser()
    pause_args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-synthesis",
            "--action",
            "pause",
        ]
    )
    run_objective_command(console, pause_args)

    response = console.ask(
        "What is the next safe step?",
        session_id="sess-console-objective-synthesis",
        mission_id=mission_id,
    )

    assert "Estado do objetivo:" in response.response_text
    assert "status paused" in response.response_text
    assert "decisao pendente retomar ou redefinir proxima acao" in response.response_text


def test_console_chat_keeps_session_continuity() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-chat"))
    parser = build_parser()
    args = parser.parse_args(
        [
            "chat",
            "--session-id",
            "sess-console-chat",
            "--mission-id",
            "mission-console-chat",
            "--message",
            "Plan the final validation window.",
            "--message",
            "Analyze the previous plan.",
        ]
    )

    outputs = run_chat_command(console, args)

    assert len(outputs) == 2
    assert "Leitura do objetivo" in outputs[0]
    assert "Julgamento" in outputs[1]
    assert "continuidade ativa" in outputs[1].lower()
