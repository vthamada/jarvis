from tools.render_memory_gap_baseline_evidence import build_payload, render_markdown


def test_render_memory_gap_baseline_evidence_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-memory-gap-evidence-cut"
    assert payload["sprint_id"] == "sprint-2-baseline-evidence-collection"
    assert payload["scope_count"] == 6
    assert payload["overall_decision"] == "hold_mem0_as_conditional_candidate"
    assert payload["scope_totals"]["implemented"] == 3
    assert payload["scope_totals"]["typed_tracking_only"] == 1
    assert payload["scope_totals"]["core_mediated_handoff_only"] == 1
    assert payload["scope_totals"]["future_shape_only"] == 1
    assert payload["scope_totals"]["inconsistent"] == 0


def test_render_memory_gap_baseline_evidence_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Memory Gap Baseline Evidence" in rendered
    assert "## conversation scope is already operational in the baseline" in rendered
    assert "## user scope is typed and tracked, but not yet runtime rich" in rendered
    assert "## specialist shared memory covers handoff, but not a stronger agent scope" in rendered
    assert "## organization scope is still only a future shape" in rendered
    assert "### user_scope_is_typed_but_not_runtime_rich" in rendered
    assert "`hold_mem0_as_conditional_candidate`" in rendered
