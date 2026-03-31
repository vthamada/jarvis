from tools.close_memory_gap_evidence_cut import build_payload, render_markdown


def test_close_memory_gap_evidence_cut_builds_payload() -> None:
    payload = build_payload()

    assert payload["decision"] == "complete_v2_memory_gap_evidence_cut"
    assert payload["next_cut_recommendation"] == "v2-native-memory-scope-hardening-cut"
    assert payload["decision_summary"]["final_decision"] == "manter_fechado"
    assert payload["decision_summary"]["mem0_status"] == "absorver_depois"
    assert payload["decision_summary"]["partial_gap_candidates"] == 2


def test_close_memory_gap_evidence_cut_renders_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "Fechamento do V2 Memory Gap Evidence Cut" in rendered
    assert "v2-native-memory-scope-hardening-cut" in rendered
    assert "endurecimento nativo de user scope e shared specialist scope" in rendered
