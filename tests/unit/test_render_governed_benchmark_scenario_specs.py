from tools.render_governed_benchmark_scenario_specs import build_payload, render_markdown


def test_render_governed_benchmark_scenario_specs_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-governed-benchmark-execution-cut"
    assert payload["sprint_id"] == "sprint-2-scenario-specs"
    assert payload["scenario_count"] == 3


def test_render_governed_benchmark_scenario_specs_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Governed Benchmark Scenario Specs" in rendered
    assert "## Mastra" in rendered
    assert "## AutoGPT Platform" in rendered
    assert "## Mem0" in rendered
