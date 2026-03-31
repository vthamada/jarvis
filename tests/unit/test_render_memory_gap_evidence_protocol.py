from tools.archive.render_memory_gap_evidence_protocol import build_payload, render_markdown


def test_render_memory_gap_evidence_protocol_payload() -> None:
    payload = build_payload()

    assert payload["cut_id"] == "v2-memory-gap-evidence-cut"
    assert payload["sprint_id"] == "sprint-1-gap-evidence-protocol"
    assert payload["hypothesis_count"] == 3


def test_render_memory_gap_evidence_protocol_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Memory Gap Evidence Protocol" in rendered
    assert "## user scope is typed but not runtime rich" in rendered
    assert "## shared memory does not fully cover a stronger agent scope" in rendered
    assert "## organization scope is still a future shape, not a proven gap" in rendered
