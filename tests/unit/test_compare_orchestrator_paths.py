from tools.compare_orchestrator_paths import compare_results, serialize_comparisons
from tools.internal_pilot_support import PilotExecutionResult


def make_result(  # type: ignore[no-untyped-def]
    *,
    scenario_id: str,
    path_name: str,
    intent: str = "planning",
    governance_decision: str = "allow_with_conditions",
    operation_status: str | None = "completed",
    continuity_action: str | None = "continuar",
    continuity_source: str | None = "active_mission",
    continuity_trace_status: str = "healthy",
    continuity_anomaly_flags: list[str] | None = None,
    missing_continuity_signals: list[str] | None = None,
    trace_status: str = "healthy",
    anomaly_flags: list[str] | None = None,
    missing_required_events: list[str] | None = None,
) -> PilotExecutionResult:
    return PilotExecutionResult(
        scenario_id=scenario_id,
        path_name=path_name,
        request_id=f"req-{path_name}-{scenario_id}",
        session_id=f"sess-{scenario_id}",
        mission_id=None,
        intent=intent,
        governance_decision=governance_decision,
        operation_status=operation_status,
        continuity_action=continuity_action,
        continuity_source=continuity_source,
        continuity_trace_status=continuity_trace_status,
        missing_continuity_signals=missing_continuity_signals or [],
        continuity_anomaly_flags=continuity_anomaly_flags or [],
        trace_status=trace_status,
        anomaly_flags=anomaly_flags or [],
        missing_required_events=missing_required_events or [],
        total_events=8,
        duration_seconds=2.0,
        active_domains=["strategy"],
        specialist_hints=["especialista_planejamento_operacional"],
        response_preview="preview",
    )


def test_compare_results_flags_mismatch_fields() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline")]
    candidate = [
        make_result(
            scenario_id="x",
            path_name="langgraph",
            operation_status=None,
            trace_status="attention_required",
        )
    ]

    comparisons = compare_results(baseline, candidate)

    assert comparisons[0].mismatch_fields == ["operation_status", "trace_status"]
    assert comparisons[0].core_match is False


def test_compare_results_flags_continuity_mismatch_fields() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline", continuity_action="retomar")]
    candidate = [
        make_result(
            scenario_id="x",
            path_name="langgraph",
            continuity_action="continuar",
            continuity_trace_status="attention_required",
        )
    ]

    comparisons = compare_results(baseline, candidate)

    assert comparisons[0].mismatch_fields == [
        "continuity_action",
        "continuity_trace_status",
    ]


def test_serialize_comparisons_reports_equivalent_verdict() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline")]
    candidate = [make_result(scenario_id="x", path_name="langgraph")]

    payload = serialize_comparisons(
        compare_results(baseline, candidate),
        profile="development",
        langgraph_status="available",
    )

    assert payload["overall_verdict"] == "equivalent"
