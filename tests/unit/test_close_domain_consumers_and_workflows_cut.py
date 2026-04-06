from tools.archive.close_domain_consumers_and_workflows_cut import build_payload, render_markdown


def test_close_domain_consumers_and_workflows_cut_builds_payload() -> None:
    payload = build_payload()

    assert payload["decision"] == "complete_v2_domain_consumers_and_workflows_cut"
    assert payload["next_cut_recommendation"] == "v2-governed-benchmark-execution-cut"
    assert payload["evidence_summary"]["baseline_decision"] == "baseline_release_ready"
    assert payload["evidence_summary"]["benchmark_now_candidates"] == 3
    assert payload["evidence_summary"]["promoted_routes_covered_by_pilot"] == 6
    assert payload["evidence_summary"]["targeted_route_matches"] == 7
    assert payload["evidence_summary"]["memory_causality_ready_scenarios"] == 1
    assert payload["evidence_summary"]["mind_domain_specialist_ready_scenarios"] >= 1
    assert payload["evidence_summary"]["dominant_tension_ready_scenarios"] >= 1
    assert payload["evidence_summary"]["specialist_subflow_ready_scenarios"] >= 1
    assert payload["evidence_summary"]["mission_runtime_state_ready_scenarios"] >= 1
    assert payload["evidence_summary"]["cognitive_recomposition_ready_scenarios"] == 1
    assert payload["next_cut_scope"][0]["item_id"] == (
        "v2-workflow-orchestration-benchmark-execution"
    )


def test_close_domain_consumers_and_workflows_cut_renders_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "Fechamento do V2 Domain Consumers and Workflows Cut" in rendered
    assert "v2-governed-benchmark-execution-cut" in rendered
    assert "execucao sandbox de benchmarks de workflow orchestration" in rendered
    assert "targeted pilot route matches" in rendered
    assert "memory causality scenarios ready" in rendered
    assert "mind-domain-specialist scenarios ready" in rendered
    assert "dominant tension scenarios ready" in rendered
    assert "specialist subflow scenarios ready" in rendered
    assert "mission runtime state scenarios ready" in rendered
