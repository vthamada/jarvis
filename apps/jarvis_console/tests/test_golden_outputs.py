from argparse import Namespace
from io import StringIO
from pathlib import Path

from apps.jarvis_console.cli import (
    render_daily_operator_utility_report,
    render_daily_operator_workspace,
)
from apps.jarvis_console.registry import (
    CommandCategory,
    CommandDefinition,
    CommandExecutionMode,
    CommandRegistry,
)
from apps.jarvis_console.runtime import ConsoleRuntime
from shared.contracts import (
    DailyOperatorMissionOutcomeContract,
    DailyOperatorUtilityReportContract,
    DailyOperatorWorkspaceContract,
    DailyWorkspaceMissionContract,
)

GOLDEN_DIR = Path(__file__).with_name("golden")


def test_daily_workspace_text_matches_golden() -> None:
    mission = DailyWorkspaceMissionContract(
        mission_id="mission-golden",
        mission_goal="Ship a deterministic operator slice",
        mission_status="active",
        objective_status="active",
        updated_at="2026-07-18T10:00:00+00:00",
        freshness_status="fresh",
        operator_attention_status="ready",
        next_action_status="ready",
        next_action_ref="next-action://golden/validate",
        work_item_refs=["work-item://golden/validate"],
        active_work_items=["work-item://golden/validate"],
        ordered_work_item_refs=["work-item://golden/validate"],
        executable_work_item_refs=["work-item://golden/validate"],
        evidence_refs=["mission-state://golden"],
        freshness_age_hours=2.0,
    )
    workspace = DailyOperatorWorkspaceContract(
        workspace_id="daily-workspace://golden",
        workspace_status="ready_for_next_action",
        generated_at="2026-07-18T12:00:00+00:00",
        missions=[mission],
        mission_count=1,
        active_objective_count=1,
        active_work_item_count=1,
        active_artifact_count=0,
        open_checkpoint_count=0,
        pending_review_count=0,
        stale_mission_count=0,
        next_decision_refs=["continue_mission:mission-golden"],
        next_operator_decision="continue_mission:mission-golden",
        evidence_refs=["mission-state://golden"],
    )

    rendered = render_daily_operator_workspace(workspace) + "\n"

    assert rendered == (GOLDEN_DIR / "daily-workspace.txt").read_text(
        encoding="utf-8"
    )


def test_operator_outcomes_text_matches_golden() -> None:
    mission = DailyOperatorMissionOutcomeContract(
        mission_id="mission-golden",
        work_item_event_count=2,
        observed_work_item_count=1,
        completed_work_item_count=1,
        reworked_work_item_count=0,
        artifact_event_count=1,
        observed_artifact_count=1,
        resume_count=1,
        feedback_count=1,
        helpful_feedback_count=1,
        time_to_next_action_observation_count=1,
        completion_rate=1.0,
        rework_rate=0.0,
        helpful_feedback_rate=1.0,
        average_time_to_next_action_seconds=300.0,
        stale_open_loop_count=0,
        evidence_refs=["event://golden"],
    )
    report = DailyOperatorUtilityReportContract(
        report_id="operator-utility-report://golden",
        report_status="measured",
        period_start="2026-07-18T00:00:00+00:00",
        period_end="2026-07-18T12:00:00+00:00",
        generated_at="2026-07-18T12:00:00+00:00",
        mission_count=1,
        mission_metrics=[mission],
        event_count=5,
        work_item_event_count=2,
        observed_work_item_count=1,
        completed_work_item_count=1,
        reworked_work_item_count=0,
        completion_rate=1.0,
        rework_rate=0.0,
        artifact_event_count=1,
        observed_artifact_count=1,
        resume_count=1,
        stale_open_loop_count=0,
        feedback_count=1,
        feedback_mission_count=1,
        feedback_coverage=1.0,
        helpful_feedback_count=1,
        helpful_feedback_rate=1.0,
        time_to_next_action_observation_count=1,
        average_time_to_next_action_seconds=300.0,
        limitations=[],
        evidence_refs=["event://golden"],
    )

    rendered = render_daily_operator_utility_report(report) + "\n"

    assert rendered == (GOLDEN_DIR / "operator-outcomes.txt").read_text(
        encoding="utf-8"
    )


def test_json_success_envelope_matches_golden() -> None:
    definition = CommandDefinition(
        command_id="golden-report",
        help_text="Emit deterministic output.",
        handler_name="run_golden_report_command",
        category=CommandCategory.OBSERVABILITY,
        execution_mode=CommandExecutionMode.STANDALONE,
        supports_json=True,
    )
    registry = CommandRegistry((definition,)).bind(
        {"run_golden_report_command": lambda args: ["status=ready\nvalue=fixed"]}
    )
    stdout = StringIO()

    exit_code = ConsoleRuntime(
        output_format="json",
        stdout_stream=stdout,
        stderr_stream=StringIO(),
    ).execute(
        registry=registry,
        command_id="golden-report",
        args=Namespace(),
        console_factory=lambda: None,
    )

    assert exit_code == 0
    assert stdout.getvalue() == (GOLDEN_DIR / "runtime-success.json").read_text(
        encoding="utf-8"
    )
