from tools.archive.close_governed_benchmark_execution_cut import build_payload, render_markdown


def test_close_governed_benchmark_execution_cut_builds_payload() -> None:
    payload = build_payload()

    assert payload["decision"] == "complete_v2_governed_benchmark_execution_cut"
    assert payload["next_cut_recommendation"] == "v2-memory-gap-evidence-cut"
    assert payload["decision_summary"]["benchmark_now_count"] == 3
    assert payload["decision_summary"]["absorver_depois"] == 1


def test_close_governed_benchmark_execution_cut_renders_markdown() -> None:
    payload = build_payload()

    rendered = render_markdown(payload)

    assert "Fechamento do V2 Governed Benchmark Execution Cut" in rendered
    assert "v2-memory-gap-evidence-cut" in rendered
    assert "recorte de evidencia para lacunas reais de memoria multicamada" in rendered
