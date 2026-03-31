from tools.close_domain_consumers_and_workflows_cut import build_payload, render_markdown


def test_close_domain_consumers_and_workflows_cut_builds_payload() -> None:
    payload = build_payload()

    assert payload["decision"] == "complete_v2_domain_consumers_and_workflows_cut"
    assert payload["next_cut_recommendation"] == "v2-governed-benchmark-execution-cut"
    assert payload["evidence_summary"]["baseline_decision"] == "baseline_release_ready"
    assert payload["evidence_summary"]["benchmark_now_candidates"] == 3
    assert payload["next_cut_scope"][0]["item_id"] == (
        "v2-workflow-orchestration-benchmark-execution"
    )


def test_close_domain_consumers_and_workflows_cut_renders_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "Fechamento do V2 Domain Consumers and Workflows Cut" in rendered
    assert "v2-governed-benchmark-execution-cut" in rendered
    assert "execucao sandbox de benchmarks de workflow orchestration" in rendered
