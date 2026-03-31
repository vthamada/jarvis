from tools.verify_active_cut_baseline import build_payload, render_markdown


def test_verify_active_cut_baseline_reports_release_ready() -> None:
    payload = build_payload()

    assert payload["decision"] == "baseline_release_ready"
    assert payload["summary"]["active_routes_missing_workflows"] == 0
    assert payload["summary"]["promoted_routes_missing_consumer_contract"] == 0
    assert payload["summary"]["promoted_routes_missing_specialist_contract"] == 0
    assert payload["summary"]["benchmark_now_candidates"] == 3
    assert payload["summary"]["promotion_trigger_rules"] >= 5


def test_verify_active_cut_baseline_markdown_mentions_notes() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "Active V2 Cut Release Baseline" in rendered
    assert "benchmark_now candidates" in rendered
    assert "consumer contract" in rendered
