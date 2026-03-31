from tools.render_governed_benchmark_execution_plan import build_payload, render_markdown


def test_render_governed_benchmark_execution_plan_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-governed-benchmark-execution-cut"
    assert payload["benchmark_now_count"] == 3
    assert payload["technology_ids"] == ["mastra", "autogpt_platform", "mem0"]


def test_render_governed_benchmark_execution_plan_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Governed Benchmark Execution Plan" in rendered
    assert "### Mastra" in rendered
    assert "### AutoGPT Platform" in rendered
    assert "### Mem0" in rendered
