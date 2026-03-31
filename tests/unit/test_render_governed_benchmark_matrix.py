from tools.archive.render_governed_benchmark_matrix import build_payload, render_markdown


def test_governed_benchmark_matrix_payload_lists_active_candidates() -> None:
    payload = build_payload()

    assert payload["decision"] == "complete_sprint_3_governed_benchmarks"
    assert payload["candidate_totals"]["benchmark_now"] == 3
    assert payload["active_benchmark_candidates"] == [
        "Mastra",
        "AutoGPT Platform",
        "Mem0",
    ]
    assert len(payload["family_summaries"]) == 3
    assert len(payload["promotion_trigger_rules"]) == 5


def test_governed_benchmark_matrix_markdown_mentions_reference_envelope() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "V2 Governed Benchmark Matrix" in rendered
    assert "AutoGPT Platform" in rendered
    assert "LangGraph" in rendered
    assert "reference_envelope" in rendered
    assert "Quando `absorver_depois` pode subir" in rendered
