from pathlib import Path

from tools.benchmarks.harness import (
    ADOPT_IN_V1,
    DEFER_TO_V2,
    MAINTAIN_BASELINE,
    BenchmarkHarness,
)


def test_benchmark_harness_runs_and_persists_auditable_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    harness = BenchmarkHarness(output_dir=str(tmp_path / "benchmarks"))

    report = harness.run()

    assert Path(report.json_report_path).exists()
    assert Path(report.markdown_report_path).exists()
    allowed_decisions = {ADOPT_IN_V1, MAINTAIN_BASELINE, DEFER_TO_V2}
    assert all(track.decision in allowed_decisions for track in report.tracks.values())
    assert report.tracks["memory"].decision == MAINTAIN_BASELINE
    assert report.tracks["knowledge"].decision == MAINTAIN_BASELINE
    assert report.tracks["observability"].decision == ADOPT_IN_V1
    assert report.tracks["evolution"].decision == ADOPT_IN_V1

