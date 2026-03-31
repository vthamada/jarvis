from tools.archive.render_memory_gap_decision import build_payload, render_markdown


def test_render_memory_gap_decision_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-memory-gap-evidence-cut"
    assert payload["sprint_id"] == "sprint-3-reopen-or-hold-decision"
    assert payload["decision_id"] == "memory_gap_hold_decision"
    assert payload["final_decision"] == "manter_fechado"
    assert payload["mem0_status"] == "absorver_depois"


def test_render_memory_gap_decision_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Memory Gap Decision" in rendered
    assert "`manter_fechado`" in rendered
    assert "`absorver_depois`" in rendered
    assert "## Backlog Before Any Absorption" in rendered
    assert "## Reopen Signals" in rendered
